from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .competitor_models import AICompetitorInsight, CompetitorAnalysis, JdProductSnapshot
from .models import AIProductInsight, ProductInput


DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
}
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
}
DISABLED_PROVIDERS = {"", "off", "none", "false", "0"}

Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


class AIConfigError(ValueError):
    pass


class AIProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class AIConfig:
    provider: str = "off"
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    temperature: float = 0.2
    timeout_seconds: float = 30.0

    @property
    def enabled(self) -> bool:
        return self.provider not in DISABLED_PROVIDERS

    @classmethod
    def from_env(
        cls,
        provider: str = "off",
        model: str = "",
        base_url: str = "",
    ) -> "AIConfig":
        resolved_provider = (provider or os.getenv("AI_PROVIDER") or "off").strip().lower()
        if resolved_provider in DISABLED_PROVIDERS:
            return cls(provider="off")
        if resolved_provider not in {"openai", "deepseek", "custom"}:
            raise AIConfigError("AI_PROVIDER 仅支持 off/openai/deepseek/custom")

        resolved_model = (model or os.getenv("AI_MODEL") or DEFAULT_MODELS.get(resolved_provider) or "").strip()
        resolved_base_url = (base_url or os.getenv("AI_BASE_URL") or DEFAULT_BASE_URLS.get(resolved_provider) or "").strip()
        api_key = _api_key_for_provider(resolved_provider)
        if not api_key:
            raise AIConfigError("启用 AI 后需要配置 AI_API_KEY，或配置对应的 OPENAI_API_KEY / DEEPSEEK_API_KEY")
        if not resolved_model:
            raise AIConfigError("启用 AI 后需要配置 AI_MODEL")
        if not resolved_base_url:
            raise AIConfigError("使用 custom AI_PROVIDER 时需要配置 AI_BASE_URL")
        return cls(
            provider=resolved_provider,
            api_key=api_key,
            model=resolved_model,
            base_url=resolved_base_url,
            temperature=_float_env("AI_TEMPERATURE", 0.2),
            timeout_seconds=_float_env("AI_TIMEOUT_SECONDS", 30.0),
        )


class AIClient:
    def __init__(self, config: AIConfig, transport: Transport | None = None) -> None:
        self.config = config
        self._transport = transport or _default_transport

    def generate_product_insight(self, product: ProductInput) -> AIProductInsight:
        payload = {
            "product_name": product.product_name,
            "current_category": product.category,
            "price_range": product.price_range,
            "target_user": product.target_user,
            "core_features": product.core_features,
            "usage_scenarios": product.usage_scenarios,
        }
        data = self._chat_json(PRODUCT_SYSTEM_PROMPT, payload)
        return AIProductInsight(
            provider=self.config.provider,
            model=self.config.model,
            status="成功",
            category_suggestion=_string(data.get("category_suggestion")),
            product_positioning=_string(data.get("product_positioning")),
            suggested_tags=_string_list(data.get("suggested_tags"), limit=8),
            operation_suggestions=_string_list(data.get("operation_suggestions"), limit=6),
            review_notes=_string_list(data.get("review_notes"), limit=6),
        )

    def generate_competitor_insight(
        self,
        keyword: str,
        target: JdProductSnapshot,
        competitors: list[JdProductSnapshot],
        analysis: CompetitorAnalysis,
    ) -> AICompetitorInsight:
        payload = {
            "keyword": keyword,
            "target": _snapshot_payload(target),
            "competitors": [_snapshot_payload(item) for item in competitors if item.scrape_status == "成功"][:10],
            "rule_analysis": {
                "opportunity_level": analysis.opportunity_level,
                "common_patterns": analysis.common_patterns,
                "target_differentiators": analysis.target_differentiators,
                "opportunities": analysis.opportunities,
                "risks": analysis.risks,
            },
        }
        data = self._chat_json(COMPETITOR_SYSTEM_PROMPT, payload)
        return AICompetitorInsight(
            provider=self.config.provider,
            model=self.config.model,
            status="成功",
            category_suggestions=_string_list(data.get("category_suggestions"), limit=6),
            operation_suggestions=_string_list(data.get("operation_suggestions"), limit=8),
            content_angles=_string_list(data.get("content_angles"), limit=6),
            review_notes=_string_list(data.get("review_notes"), limit=6),
        )

    def _chat_json(self, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        request_payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "temperature": self.config.temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        response = self._transport(
            _chat_completions_url(self.config.base_url),
            headers,
            request_payload,
            self.config.timeout_seconds,
        )
        content = _choice_content(response)
        parsed = _parse_json_object(content)
        if not isinstance(parsed, dict):
            raise AIProviderError("AI 返回内容不是 JSON 对象")
        return parsed


def failed_product_insight(config: AIConfig, error: Exception) -> AIProductInsight:
    return AIProductInsight(
        provider=config.provider,
        model=config.model,
        status="失败",
        error_message=_error_message(error),
        review_notes=["AI 调用失败，已保留规则化结果，建议人工复核后再使用。"],
    )


def failed_competitor_insight(config: AIConfig, error: Exception) -> AICompetitorInsight:
    return AICompetitorInsight(
        provider=config.provider,
        model=config.model,
        status="失败",
        error_message=_error_message(error),
        review_notes=["AI 调用失败，已保留规则化竞品分析，建议人工复核后再使用。"],
    )


PRODUCT_SYSTEM_PROMPT = """你是电商商品运营分析助手。请基于输入商品信息做分类和运营建议。
只返回一个 JSON 对象，不要输出 Markdown 或额外解释。
字段必须为：
category_suggestion: string，建议归类，尽量短；
product_positioning: string，商品定位；
suggested_tags: string[]，最多 8 个标签；
operation_suggestions: string[]，最多 6 条运营建议；
review_notes: string[]，最多 6 条人工审核提示。
要求：不得虚构销量、排名、GMV、转化率、平台背书或无法证明的效果。"""


COMPETITOR_SYSTEM_PROMPT = """你是电商竞品分析助手。请基于主商品、竞品列表和规则化分析结果，补充分类和运营建议。
只返回一个 JSON 对象，不要输出 Markdown 或额外解释。
字段必须为：
category_suggestions: string[]，最多 6 条分类或价格带/定位建议；
operation_suggestions: string[]，最多 8 条运营动作建议；
content_angles: string[]，最多 6 条内容表达方向；
review_notes: string[]，最多 6 条人工审核提示。
要求：只能做定性建议，不得虚构销量、排名、GMV、转化率、平台背书或无法证明的效果。"""


def _api_key_for_provider(provider: str) -> str:
    if provider == "openai":
        return (os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if provider == "deepseek":
        return (os.getenv("AI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or "").strip()
    return (os.getenv("AI_API_KEY") or "").strip()


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _chat_completions_url(base_url: str) -> str:
    clean = base_url.rstrip("/")
    if clean.endswith("/chat/completions"):
        return clean
    return f"{clean}/chat/completions"


def _default_transport(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-configured AI API endpoint.
            content = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise AIProviderError(f"AI API 请求失败：HTTP {exc.code} {body[:300]}") from exc
    except URLError as exc:
        raise AIProviderError(f"AI API 请求失败：{exc.reason}") from exc
    return json.loads(content)


def _choice_content(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIProviderError("AI 返回缺少 choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise AIProviderError("AI 返回缺少 message.content")
    return content


def _parse_json_object(content: str) -> Any:
    text = content.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AIProviderError("AI 返回内容无法解析为 JSON") from None
        return json.loads(text[start : end + 1])


def _string(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any, limit: int) -> list[str]:
    if isinstance(value, list):
        values = [_string(item) for item in value]
    elif value:
        values = [_string(value)]
    else:
        values = []
    result: list[str] = []
    for item in values:
        if item and item not in result:
            result.append(item)
    return result[:limit]


def _snapshot_payload(product: JdProductSnapshot) -> dict[str, Any]:
    attrs = product.lamp_attributes
    return {
        "sku_id": product.sku_id,
        "product_name": product.product_name,
        "brand": product.brand,
        "shop_name": product.shop_name,
        "price_text": product.price_text,
        "price_range": product.price_range,
        "selling_points": product.selling_points,
        "review_count_text": product.review_count_text,
        "lamp_attributes": {
            "illuminance": attrs.illuminance,
            "color_temperature": attrs.color_temperature,
            "cri": attrs.cri,
            "blue_light": attrs.blue_light,
            "dimming": attrs.dimming,
            "power": attrs.power,
            "usage_scenario": attrs.usage_scenario,
        },
    }


def _error_message(error: Exception) -> str:
    return str(error)[:500]
