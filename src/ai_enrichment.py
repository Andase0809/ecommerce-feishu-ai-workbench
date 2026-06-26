from __future__ import annotations

import json
import re
from typing import Any

from .ai_client import AIClient, failed_product_insight
from .models import AIProductInsight, ProductInput


SHOP_PRODUCT_TABLE_NAME = "店铺主要商品表"


def enrich_shop_workbench_payload(payload: dict[str, Any], ai_client: AIClient) -> dict[str, Any]:
    enriched = json.loads(json.dumps(payload, ensure_ascii=False))
    for table in enriched.get("tables", []):
        if table.get("table_name") != SHOP_PRODUCT_TABLE_NAME:
            continue
        for index, record in enumerate(table.get("records") or [], start=1):
            product = _product_input_from_record(record, index)
            try:
                insight = ai_client.generate_product_insight(product)
            except Exception as exc:  # noqa: BLE001 - AI fallback should preserve sync workflow.
                insight = failed_product_insight(ai_client.config, exc)
            _apply_insight(record, insight)
    return enriched


def _product_input_from_record(record: dict[str, Any], index: int) -> ProductInput:
    tags = _split_tags(record.get("标签"))
    positioning = str(record.get("商品定位") or "").strip()
    return ProductInput(
        product_id=str(record.get("店铺商品SKU") or f"shop-product-{index:03d}"),
        product_name=str(record.get("商品名称") or f"商品{index}"),
        category=positioning or str(record.get("品牌") or "未识别"),
        price_range=str(record.get("价格带") or record.get("价格文本") or "未识别"),
        target_user=positioning or "电商商品用户",
        core_features=tags or [positioning or "商品卖点待补充"],
        usage_scenarios=[positioning or "商品运营"],
        platform_style=["电商平台"],
    )


def _apply_insight(record: dict[str, Any], insight: AIProductInsight) -> None:
    record["AI分类建议"] = insight.category_suggestion
    record["AI定位建议"] = insight.product_positioning
    record["AI标签建议"] = "、".join(insight.suggested_tags)
    record["AI运营建议"] = "\n".join(insight.operation_suggestions)
    record["AI审核提示"] = "\n".join(insight.review_notes)
    record["AI生成状态"] = insight.status
    record["AI模型"] = f"{insight.provider}/{insight.model}" if insight.provider else ""
    if insight.error_message:
        record["AI审核提示"] = "\n".join([item for item in [record["AI审核提示"], insight.error_message] if item])


def _split_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value]
    else:
        items = [item.strip() for item in re.split(r"[、,，\s]+", str(value or ""))]
    result: list[str] = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result
