from __future__ import annotations

from dataclasses import dataclass, field

from .models import ProductOutput


TEXT_FIELD = 1
NUMBER_FIELD = 2
SINGLE_SELECT_FIELD = 3
MULTI_SELECT_FIELD = 4
URL_FIELD = 15
ATTACHMENT_FIELD = 17

PRODUCT_TABLE_NAME = "商品主表"
PLATFORM_TABLES = {
    "小红书": "小红书内容表",
    "抖音": "抖音内容表",
    "电商平台": "电商平台内容表",
}
REVIEW_STATUS_OPTIONS = ["待审核", "需修改", "已通过"]


@dataclass(frozen=True)
class ViewFilter:
    field_name: str
    operator: str
    value: str | list[str] | int | float | bool


@dataclass(frozen=True)
class ViewPayload:
    name: str
    view_type: str = "grid"
    hidden_fields: list[str] = field(default_factory=list)
    filters: list[ViewFilter] = field(default_factory=list)
    conjunction: str = "and"


@dataclass(frozen=True)
class AttachmentUpload:
    record_index: int
    attachment_field: str
    source_url: str
    file_name: str
    fallback_status_field: str | None = None


@dataclass(frozen=True)
class TablePayload:
    name: str
    fields: list[dict]
    records: list[dict]
    default_view_name: str = "默认表格视图"
    views: list[ViewPayload] = field(default_factory=list)
    attachment_uploads: list[AttachmentUpload] = field(default_factory=list)


def build_table_payloads(outputs: list[ProductOutput]) -> list[TablePayload]:
    return [
        TablePayload(
            name=PRODUCT_TABLE_NAME,
            fields=_product_fields(),
            records=[_product_record(item) for item in outputs],
        ),
        *[
            TablePayload(
                name=table_name,
                fields=_platform_fields(),
                records=_platform_records(outputs, platform),
            )
            for platform, table_name in PLATFORM_TABLES.items()
        ],
    ]


def _product_fields() -> list[dict]:
    return [
        _text_field("product_id"),
        _text_field("商品名称"),
        _text_field("品类"),
        _text_field("价格带"),
        _text_field("目标用户"),
        _text_field("核心卖点"),
        _text_field("使用场景"),
        _text_field("AI分类建议"),
        _text_field("AI商品定位"),
        _text_field("AI标签建议"),
        _text_field("AI运营建议"),
        _text_field("AI审核提示"),
        _text_field("AI生成状态"),
        _text_field("AI模型"),
        _text_field("人工检查清单"),
    ]


def _platform_fields() -> list[dict]:
    return [
        _text_field("product_id"),
        _text_field("商品名称"),
        _text_field("标题候选"),
        _text_field("核心卖点"),
        _text_field("平台文案"),
        _text_field("标签"),
        _single_select_field("审核状态", REVIEW_STATUS_OPTIONS),
    ]


def _text_field(name: str) -> dict:
    return {"field_name": name, "type": TEXT_FIELD}


def _single_select_field(name: str, options: list[str]) -> dict:
    return {
        "field_name": name,
        "type": SINGLE_SELECT_FIELD,
        "property": {"options": [{"name": option} for option in options]},
    }


def _product_record(output: ProductOutput) -> dict:
    ai = output.ai_insight
    return {
        "fields": {
            "product_id": output.product_id,
            "商品名称": output.product_name,
            "品类": output.category,
            "价格带": output.price_range,
            "目标用户": output.target_user,
            "核心卖点": "\n".join(output.core_features),
            "使用场景": "\n".join(output.usage_scenarios),
            "AI分类建议": ai.category_suggestion if ai else "",
            "AI商品定位": ai.product_positioning if ai else "",
            "AI标签建议": "，".join(ai.suggested_tags) if ai else "",
            "AI运营建议": "\n".join(ai.operation_suggestions) if ai else "",
            "AI审核提示": "\n".join(ai.review_notes) if ai else "",
            "AI生成状态": ai.status if ai else "未启用",
            "AI模型": f"{ai.provider}/{ai.model}" if ai and ai.provider else "",
            "人工检查清单": "\n".join(output.review_checklist),
        }
    }


def _platform_records(outputs: list[ProductOutput], platform: str) -> list[dict]:
    records: list[dict] = []
    for output in outputs:
        content = next((item for item in output.platform_contents if item.platform == platform), None)
        if content is None:
            continue
        records.append(
            {
                "fields": {
                    "product_id": output.product_id,
                    "商品名称": output.product_name,
                    "标题候选": "\n".join(content.titles),
                    "核心卖点": "\n".join(content.selling_points),
                    "平台文案": content.platform_copy,
                    "标签": "，".join(content.tags),
                    "审核状态": content.review_status,
                }
            }
        )
    return records
