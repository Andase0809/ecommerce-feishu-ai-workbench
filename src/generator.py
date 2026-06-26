from __future__ import annotations

from .ai_client import AIClient, failed_product_insight
from .models import PlatformContent, ProductInput, ProductOutput


REVIEW_CHECKLIST = [
    "核对商品名称、价格带、核心参数是否与原始资料一致",
    "检查是否出现销量、排名、转化率、绝对化功效等无法证明的表达",
    "确认平台口吻是否匹配：小红书偏体验分享，抖音偏口播节奏，电商平台偏清晰成交",
    "检查目标用户和使用场景是否一致，避免泛泛而谈",
    "发布前补充真实商品图、规格参数和售后信息",
]

FORBIDDEN_MARKETING_TERMS = [
    "销量第一",
    "全网第一",
    "行业第一",
    "必买",
    "100%",
    "百分百",
    "治愈",
    "根治",
    "保证提升",
    "转化率",
    "GMV",
]


def generate_product_output(product: ProductInput, ai_client: AIClient | None = None) -> ProductOutput:
    platform_contents = [
        _generate_platform_content(product, platform)
        for platform in product.platform_style
    ]
    ai_insight = None
    if ai_client is not None:
        try:
            ai_insight = ai_client.generate_product_insight(product)
        except Exception as exc:  # noqa: BLE001 - AI fallback should preserve deterministic output.
            ai_insight = failed_product_insight(ai_client.config, exc)
    return ProductOutput(
        product_id=product.product_id,
        product_name=product.product_name,
        category=product.category,
        price_range=product.price_range,
        target_user=product.target_user,
        core_features=product.core_features,
        usage_scenarios=product.usage_scenarios,
        platform_contents=platform_contents,
        review_checklist=REVIEW_CHECKLIST,
        ai_insight=ai_insight,
    )


def generate_outputs(products: list[ProductInput], ai_client: AIClient | None = None) -> list[ProductOutput]:
    return [generate_product_output(product, ai_client=ai_client) for product in products]


def _generate_platform_content(product: ProductInput, platform: str) -> PlatformContent:
    if platform == "小红书":
        return _xiaohongshu_content(product)
    if platform == "抖音":
        return _douyin_content(product)
    if platform == "电商平台":
        return _ecommerce_content(product)
    raise ValueError(f"unsupported platform: {platform}")


def _xiaohongshu_content(product: ProductInput) -> PlatformContent:
    feature = _join(product.core_features[:3], "、")
    scenario = product.usage_scenarios[0]
    return PlatformContent(
        platform="小红书",
        titles=[
            f"{product.product_name}｜{scenario}也能用得顺手",
            f"{product.category}好物分享：适合{product.target_user}",
            f"{product.price_range}预算内的{product.product_name}体验记录",
        ],
        selling_points=[
            f"围绕{scenario}设计，适合日常真实使用场景",
            f"核心特点包含{feature}，信息点清晰好理解",
            f"价格带为{product.price_range}，方便做同类商品对比",
        ],
        platform_copy=(
            f"最近体验{scenario}常用物品时，{product.product_name}是比较容易被记住的一款。"
            f"它的重点不是夸张宣传，而是把{feature}这些实用点放在前面，"
            f"对{product.target_user}来说，选择时能更快判断是否适合自己。"
        ),
        tags=_tags(product, ["好物分享", "使用体验", "电商选品"]),
    )


def _douyin_content(product: ProductInput) -> PlatformContent:
    first_feature = product.core_features[0]
    scenario = product.usage_scenarios[0]
    return PlatformContent(
        platform="抖音",
        titles=[
            f"{scenario}想省心？先看这款{product.product_name}",
            f"{product.price_range}的{product.category}怎么选？",
            f"{product.product_name}，适合{product.target_user}",
        ],
        selling_points=[
            f"开头先点明使用场景：{scenario}",
            f"中段突出核心参数：{_join(product.core_features[:3], '、')}",
            "结尾提醒用户按需求和预算对比，不做绝对化承诺",
        ],
        platform_copy=(
            f"如果你平时有{scenario}需求，可以先看这款{product.product_name}。"
            f"它主打{first_feature}，同时覆盖{_join(product.core_features[1:3], '、')}。"
            f"适合{product.target_user}，下单前建议再核对尺寸、规格和售后信息。"
        ),
        tags=_tags(product, ["短视频口播", "选品参考", "实用好物"]),
    )


def _ecommerce_content(product: ProductInput) -> PlatformContent:
    return PlatformContent(
        platform="电商平台",
        titles=[
            f"{product.product_name} {product.category} {product.price_range}",
            f"{product.product_name}｜{_join(product.core_features[:2], ' / ')}",
            f"适合{product.target_user}的{product.category}",
        ],
        selling_points=[
            f"核心参数：{_join(product.core_features, '、')}",
            f"适用场景：{_join(product.usage_scenarios, '、')}",
            f"目标用户：{product.target_user}",
        ],
        platform_copy=(
            f"{product.product_name}面向{product.target_user}，覆盖{_join(product.usage_scenarios, '、')}等场景。"
            f"商品信息重点包括{_join(product.core_features, '、')}，价格带为{product.price_range}。"
            "建议结合实际规格、图片和售后说明完成上架前复核。"
        ),
        tags=_tags(product, ["商品上架", "详情页文案", "运营审核"]),
    )


def _tags(product: ProductInput, extras: list[str]) -> list[str]:
    base_tags = [product.category, product.price_range, product.usage_scenarios[0]]
    return _unique(base_tags + product.core_features[:2] + extras)[:8]


def _join(values: list[str], separator: str) -> str:
    return separator.join(values)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def find_forbidden_terms(outputs: list[ProductOutput]) -> list[str]:
    generated_text_parts: list[str] = []
    for output in outputs:
        for content in output.platform_contents:
            generated_text_parts.extend(content.titles)
            generated_text_parts.extend(content.selling_points)
            generated_text_parts.append(content.platform_copy)
            generated_text_parts.extend(content.tags)
        if output.ai_insight is not None:
            generated_text_parts.append(output.ai_insight.category_suggestion)
            generated_text_parts.append(output.ai_insight.product_positioning)
            generated_text_parts.extend(output.ai_insight.suggested_tags)
            generated_text_parts.extend(output.ai_insight.operation_suggestions)
            generated_text_parts.extend(output.ai_insight.review_notes)
    text = "\n".join(generated_text_parts)
    return [term for term in FORBIDDEN_MARKETING_TERMS if term in text]
