from __future__ import annotations

from .competitor_models import CompetitorWorkbenchOutput, JdProductSnapshot
from .feishu_schema import REVIEW_STATUS_OPTIONS, SINGLE_SELECT_FIELD, TEXT_FIELD, TablePayload


OWN_PRODUCT_TABLE_NAME = "本店商品表"
COMPETITOR_TABLE_NAME = "竞品商品表"
ANALYSIS_TABLE_NAME = "竞品对比分析表"
SUGGESTION_TABLE_NAME = "运营建议表"
SCRAPE_STATUS_OPTIONS = ["成功", "失败"]
OPPORTUNITY_LEVEL_OPTIONS = ["高", "中", "低"]


def build_competitor_table_payloads(workbench: CompetitorWorkbenchOutput) -> list[TablePayload]:
    return [
        TablePayload(
            name=OWN_PRODUCT_TABLE_NAME,
            fields=_product_fields(include_index=False),
            records=[_product_record(workbench.target, workbench.keyword, "见竞品对比分析表")],
        ),
        TablePayload(
            name=COMPETITOR_TABLE_NAME,
            fields=_product_fields(include_index=True),
            records=[
                _product_record(product, workbench.keyword, "", index=index)
                for index, product in enumerate(workbench.competitors, start=1)
            ],
        ),
        TablePayload(
            name=ANALYSIS_TABLE_NAME,
            fields=_analysis_fields(),
            records=[_analysis_record(workbench)],
        ),
        TablePayload(
            name=SUGGESTION_TABLE_NAME,
            fields=_suggestion_fields(),
            records=_suggestion_records(workbench),
        ),
    ]


def _product_fields(include_index: bool) -> list[dict]:
    fields = [
        _text_field("关键词"),
        _text_field("商品角色"),
    ]
    if include_index:
        fields.append(_text_field("竞品序号"))
    fields.extend(
        [
            _text_field("sku_id"),
            _text_field("商品名称"),
            _text_field("京东URL"),
            _text_field("品牌"),
            _text_field("店铺"),
            _text_field("价格文本"),
            _text_field("价格带"),
            _text_field("主图URL"),
            _text_field("详情参数"),
            _text_field("卖点摘要"),
            _text_field("评价量文本"),
            _single_select_field("采集状态", SCRAPE_STATUS_OPTIONS),
            _text_field("失败原因"),
            _text_field("查看竞品分析"),
            _text_field("采集时间"),
        ]
    )
    return fields


def _analysis_fields() -> list[dict]:
    return [
        _text_field("关键词"),
        _text_field("主商品SKU"),
        _text_field("有效竞品数"),
        _single_select_field("机会层级", OPPORTUNITY_LEVEL_OPTIONS),
        _text_field("竞品共性"),
        _text_field("主商品差异点"),
        _text_field("机会方向"),
        _text_field("风险提醒"),
        _text_field("人工审核清单"),
    ]


def _suggestion_fields() -> list[dict]:
    return [
        _text_field("关键词"),
        _text_field("建议类型"),
        _text_field("建议内容"),
        _single_select_field("审核状态", REVIEW_STATUS_OPTIONS),
    ]


def _product_record(
    product: JdProductSnapshot,
    keyword: str,
    analysis_entry: str,
    index: int | None = None,
) -> dict:
    fields = {
        "关键词": keyword,
        "商品角色": "本店商品" if product.role == "target" else "竞品",
        "sku_id": product.sku_id,
        "商品名称": product.product_name,
        "京东URL": product.source_url,
        "品牌": product.brand,
        "店铺": product.shop_name,
        "价格文本": product.price_text,
        "价格带": product.price_range,
        "主图URL": product.image_url,
        "详情参数": _format_params(product),
        "卖点摘要": "\n".join(product.selling_points),
        "评价量文本": product.review_count_text,
        "采集状态": product.scrape_status,
        "失败原因": product.error_message,
        "查看竞品分析": analysis_entry,
        "采集时间": product.collected_at,
    }
    if index is not None:
        fields["竞品序号"] = str(index)
    return {"fields": fields}


def _analysis_record(workbench: CompetitorWorkbenchOutput) -> dict:
    analysis = workbench.analysis
    return {
        "fields": {
            "关键词": analysis.keyword,
            "主商品SKU": analysis.target_sku_id,
            "有效竞品数": str(analysis.competitor_count),
            "机会层级": analysis.opportunity_level,
            "竞品共性": "\n".join(analysis.common_patterns),
            "主商品差异点": "\n".join(analysis.target_differentiators),
            "机会方向": "\n".join(analysis.opportunities),
            "风险提醒": "\n".join(analysis.risks),
            "人工审核清单": "\n".join(analysis.review_checklist),
        }
    }


def _suggestion_records(workbench: CompetitorWorkbenchOutput) -> list[dict]:
    analysis = workbench.analysis
    groups = [
        ("标题方向", analysis.title_directions),
        ("详情页方向", analysis.detail_page_directions),
        ("平台内容方向", analysis.platform_content_directions),
    ]
    return [
        {
            "fields": {
                "关键词": analysis.keyword,
                "建议类型": label,
                "建议内容": "\n".join(items),
                "审核状态": "待审核",
            }
        }
        for label, items in groups
    ]


def _format_params(product: JdProductSnapshot) -> str:
    attrs = product.lamp_attributes
    lamp_lines = [
        f"照度：{attrs.illuminance}",
        f"色温：{attrs.color_temperature}",
        f"显色指数：{attrs.cri}",
        f"防蓝光：{attrs.blue_light}",
        f"调光：{attrs.dimming}",
        f"功率：{attrs.power}",
        f"适用场景：{attrs.usage_scenario}",
    ]
    raw_lines = [f"{key}：{value}" for key, value in product.detail_params.items()]
    return "\n".join(lamp_lines + raw_lines)


def _text_field(name: str) -> dict:
    return {"field_name": name, "type": TEXT_FIELD}


def _single_select_field(name: str, options: list[str]) -> dict:
    return {
        "field_name": name,
        "type": SINGLE_SELECT_FIELD,
        "property": {"options": [{"name": option} for option in options]},
    }
