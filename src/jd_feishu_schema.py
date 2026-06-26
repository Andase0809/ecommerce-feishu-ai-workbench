from __future__ import annotations

import re

from .competitor_models import CompetitorWorkbenchOutput, JdProductSnapshot
from .feishu_schema import (
    ATTACHMENT_FIELD,
    NUMBER_FIELD,
    REVIEW_STATUS_OPTIONS,
    SINGLE_SELECT_FIELD,
    TEXT_FIELD,
    URL_FIELD,
    AttachmentUpload,
    TablePayload,
    ViewFilter,
    ViewPayload,
)


OWN_PRODUCT_TABLE_NAME = "本店商品表"
COMPETITOR_TABLE_NAME = "竞品商品表"
ANALYSIS_TABLE_NAME = "竞品对比分析表"
SUGGESTION_TABLE_NAME = "运营建议表"
SCRAPE_STATUS_OPTIONS = ["成功", "失败"]
OPPORTUNITY_LEVEL_OPTIONS = ["高", "中", "低"]
SELECT_COLORS = {
    "成功": 3,
    "失败": 1,
    "待审核": 2,
    "需修改": 1,
    "已通过": 3,
    "高": 1,
    "中": 5,
    "低": 3,
}


def build_competitor_table_payloads(workbench: CompetitorWorkbenchOutput) -> list[TablePayload]:
    own_records = [_product_record(workbench.target, workbench.keyword, "见竞品对比分析表")]
    competitor_records = [
        _product_record(product, workbench.keyword, "", index=index)
        for index, product in enumerate(workbench.competitors, start=1)
    ]
    return [
        TablePayload(
            name=OWN_PRODUCT_TABLE_NAME,
            default_view_name="本店商品卡片",
            fields=_product_fields(include_index=False),
            records=own_records,
            views=[
                ViewPayload("本店商品卡片", hidden_fields=_product_hidden_fields()),
                ViewPayload("本店商品图库", "gallery", hidden_fields=_gallery_hidden_fields()),
                ViewPayload("原始字段视图"),
            ],
            attachment_uploads=_attachment_uploads(own_records, "本店商品"),
        ),
        TablePayload(
            name=COMPETITOR_TABLE_NAME,
            default_view_name="竞品清单",
            fields=_product_fields(include_index=True),
            records=competitor_records,
            views=[
                ViewPayload("竞品清单", hidden_fields=_product_hidden_fields()),
                ViewPayload("竞品图库", "gallery", hidden_fields=_gallery_hidden_fields()),
                ViewPayload("采集成功", hidden_fields=_product_hidden_fields(), filters=[ViewFilter("采集状态", "is", "成功")]),
                ViewPayload("原始字段视图"),
            ],
            attachment_uploads=_attachment_uploads(competitor_records, "竞品"),
        ),
        TablePayload(
            name=ANALYSIS_TABLE_NAME,
            default_view_name="竞品分析结论",
            fields=_analysis_fields(),
            records=[_analysis_record(workbench)],
        ),
        TablePayload(
            name=SUGGESTION_TABLE_NAME,
            default_view_name="运营建议",
            fields=_suggestion_fields(),
            records=_suggestion_records(workbench),
        ),
    ]


def _product_fields(include_index: bool) -> list[dict]:
    fields = [
        _text_field("商品识别卡片"),
        _attachment_field("商品主图"),
        _url_field("商品链接"),
        _number_field("价格数值", "0.00"),
        _single_select_field("采集状态", SCRAPE_STATUS_OPTIONS),
    ]
    if include_index:
        fields.append(_text_field("竞品序号"))
    fields.extend(
        [
            _text_field("关键词"),
            _text_field("商品角色"),
            _text_field("sku_id"),
            _text_field("商品名称"),
            _url_field("京东URL"),
            _text_field("品牌"),
            _text_field("店铺"),
            _text_field("价格文本"),
            _text_field("价格带"),
            _url_field("主图URL"),
            _text_field("详情参数"),
            _text_field("卖点摘要"),
            _text_field("评价量文本"),
            _text_field("失败原因"),
            _text_field("查看竞品分析"),
            _text_field("采集时间"),
            _text_field("图片上传状态"),
        ]
    )
    return fields


def _analysis_fields() -> list[dict]:
    return [
        _text_field("关键词"),
        _text_field("主商品SKU"),
        _number_field("有效竞品数", "0"),
        _single_select_field("机会层级", OPPORTUNITY_LEVEL_OPTIONS),
        _text_field("竞品共性"),
        _text_field("主商品差异点"),
        _text_field("机会方向"),
        _text_field("AI分类建议"),
        _text_field("AI运营建议"),
        _text_field("AI内容角度"),
        _text_field("AI审核提示"),
        _text_field("AI生成状态"),
        _text_field("AI模型"),
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
        "商品识别卡片": _product_identity_card(product, index=index),
        "商品主图": None,
        "商品链接": _url_value("打开商品", product.source_url),
        "价格数值": _parse_price_number(product.price_text),
        "sku_id": product.sku_id,
        "商品名称": product.product_name,
        "京东URL": _url_value("打开商品", product.source_url),
        "品牌": product.brand,
        "店铺": product.shop_name,
        "价格文本": product.price_text,
        "价格带": product.price_range,
        "主图URL": _url_value("查看主图", product.image_url),
        "详情参数": _format_params(product),
        "卖点摘要": "\n".join(product.selling_points),
        "评价量文本": product.review_count_text,
        "采集状态": product.scrape_status,
        "失败原因": product.error_message,
        "查看竞品分析": analysis_entry,
        "采集时间": product.collected_at,
        "图片上传状态": "待上传" if product.image_url else "无图片URL",
    }
    if index is not None:
        fields["竞品序号"] = str(index)
    return {"fields": fields}


def _analysis_record(workbench: CompetitorWorkbenchOutput) -> dict:
    analysis = workbench.analysis
    ai = analysis.ai_insight
    return {
        "fields": {
            "关键词": analysis.keyword,
            "主商品SKU": analysis.target_sku_id,
            "有效竞品数": analysis.competitor_count,
            "机会层级": analysis.opportunity_level,
            "竞品共性": "\n".join(analysis.common_patterns),
            "主商品差异点": "\n".join(analysis.target_differentiators),
            "机会方向": "\n".join(analysis.opportunities),
            "AI分类建议": "\n".join(ai.category_suggestions) if ai else "",
            "AI运营建议": "\n".join(ai.operation_suggestions) if ai else "",
            "AI内容角度": "\n".join(ai.content_angles) if ai else "",
            "AI审核提示": "\n".join(ai.review_notes) if ai else "",
            "AI生成状态": ai.status if ai else "未启用",
            "AI模型": f"{ai.provider}/{ai.model}" if ai and ai.provider else "",
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
    if analysis.ai_insight is not None:
        groups.extend(
            [
                ("AI运营建议", analysis.ai_insight.operation_suggestions),
                ("AI内容角度", analysis.ai_insight.content_angles),
            ]
        )
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


def _number_field(name: str, formatter: str) -> dict:
    return {"field_name": name, "type": NUMBER_FIELD, "property": {"formatter": formatter}}


def _url_field(name: str) -> dict:
    return {"field_name": name, "type": URL_FIELD}


def _attachment_field(name: str) -> dict:
    return {"field_name": name, "type": ATTACHMENT_FIELD}


def _single_select_field(name: str, options: list[str]) -> dict:
    return {
        "field_name": name,
        "type": SINGLE_SELECT_FIELD,
        "property": {"options": [{"name": option, "color": SELECT_COLORS.get(option, index % 55)} for index, option in enumerate(options)]},
    }


def _product_identity_card(product: JdProductSnapshot, index: int | None = None) -> str:
    prefix = f"竞品{index:02d}" if index is not None else "本店主品"
    title = _wrap_text(product.product_name, width=24)
    meta = " / ".join(item for item in [product.price_text, product.brand, product.shop_name] if item and item != "未识别")
    sku = f"SKU {product.sku_id}" if product.sku_id else ""
    return "\n".join(line for line in [prefix, title, meta, sku] if line)


def _wrap_text(value: str, width: int) -> str:
    text = str(value or "").strip()
    if len(text) <= width:
        return text
    return "\n".join(text[index : index + width] for index in range(0, len(text), width))


def _url_value(text: str, url: str) -> dict[str, str] | None:
    link = str(url or "").strip()
    if not link:
        return None
    return {"text": text, "link": link}


def _parse_price_number(value: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", value or "")
    return float(match.group()) if match else None


def _product_hidden_fields() -> list[str]:
    return [
        "关键词",
        "商品角色",
        "sku_id",
        "商品名称",
        "京东URL",
        "主图URL",
        "详情参数",
        "卖点摘要",
        "失败原因",
        "采集时间",
        "图片上传状态",
    ]


def _gallery_hidden_fields() -> list[str]:
    return [
        "关键词",
        "商品角色",
        "sku_id",
        "京东URL",
        "主图URL",
        "详情参数",
        "卖点摘要",
        "失败原因",
        "采集时间",
        "图片上传状态",
    ]


def _attachment_uploads(records: list[dict], prefix: str) -> list[AttachmentUpload]:
    uploads: list[AttachmentUpload] = []
    for index, record in enumerate(records):
        fields = record.get("fields", {})
        image_url = fields.get("主图URL", {})
        source_url = image_url.get("link", "") if isinstance(image_url, dict) else ""
        sku_id = str(fields.get("sku_id") or index)
        if source_url:
            uploads.append(
                AttachmentUpload(
                    record_index=index,
                    attachment_field="商品主图",
                    source_url=source_url,
                    file_name=f"{prefix}-{sku_id}.jpg",
                    fallback_status_field="图片上传状态",
                )
            )
    return uploads
