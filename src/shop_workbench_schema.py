from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .feishu_schema import (
    ATTACHMENT_FIELD,
    AttachmentUpload,
    MULTI_SELECT_FIELD,
    NUMBER_FIELD,
    REVIEW_STATUS_OPTIONS,
    SINGLE_SELECT_FIELD,
    TEXT_FIELD,
    URL_FIELD,
    TablePayload,
    ViewFilter,
    ViewPayload,
)


OVERVIEW_TABLE_NAME = "运营总览表"
SHOP_PRODUCT_TABLE_NAME = "店铺主要商品表"
SKU_VARIANT_TABLE_NAME = "SKU款式变体表"
COMPETITOR_TASK_TABLE_NAME = "竞品任务/分析表"
SUGGESTION_TABLE_NAME = "运营建议表"

PRODUCT_TABLE_SOURCE_NAME = "店铺主要商品表"
VARIANT_TABLE_SOURCE_NAME = "SKU款式变体表"

COMPETITOR_STATUS_OPTIONS = ["竞品未采集", "待分析", "已分析", "需补充数据"]
SKU_VARIANT_STATUS_OPTIONS = ["已采集", "未采集"]
TASK_STATUS_OPTIONS = ["待补充数据", "竞品未采集", "待分析", "已完成"]
PRIORITY_OPTIONS = ["待定", "高", "中", "低"]
SUMMARY_TYPES = ["总览", "价格带分布", "商品定位分布", "审核状态分布", "SKU状态分布"]

SELECT_COLORS = {
    "待审核": 2,
    "需修改": 1,
    "已通过": 3,
    "已采集": 3,
    "未采集": 1,
    "竞品未采集": 2,
    "待分析": 5,
    "已分析": 3,
    "需补充数据": 1,
    "待补充数据": 1,
    "待定": 0,
    "高": 1,
    "中": 5,
    "低": 3,
}


def load_shop_workbench_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_shop_workbench_table_payloads(payload: dict[str, Any]) -> list[TablePayload]:
    products = _records_for_table(payload, PRODUCT_TABLE_SOURCE_NAME)
    variants = _records_for_table(payload, VARIANT_TABLE_SOURCE_NAME)
    return [
        _overview_payload(products, variants),
        _product_payload(products),
        _variant_payload(variants),
        _competitor_task_payload(products),
        _suggestion_payload(payload),
    ]


def redesigned_base_name(payload: dict[str, Any]) -> str:
    base_name = str(payload.get("base_name") or "电商商品数据工作台").strip()
    suffix = "重设计版"
    return base_name if base_name.endswith(suffix) else f"{base_name}-{suffix}"


def _records_for_table(payload: dict[str, Any], table_name: str) -> list[dict[str, Any]]:
    for table in payload.get("tables", []):
        if table.get("table_name") == table_name:
            return list(table.get("records") or [])
    return []


def _overview_payload(products: list[dict[str, Any]], variants: list[dict[str, Any]]) -> TablePayload:
    records: list[dict[str, Any]] = []
    records.extend(
        [
            _overview_record("总览", "店铺商品数", "全部商品", len(products), "来自店铺主要商品表"),
            _overview_record("总览", "SKU变体数", "已采集变体", len(variants), "来自SKU款式变体表"),
            _overview_record(
                "总览",
                "已采集SKU主商品数",
                "SKU变体状态",
                _count_equals(products, "SKU变体状态", "已采集"),
                "店铺主商品中已完成款式变体采集的数量",
            ),
            _overview_record(
                "总览",
                "待竞品采集商品数",
                "竞品分析状态",
                _count_equals(products, "竞品分析状态", "竞品未采集"),
                "仅标记工作流状态，不生成竞品结论",
            ),
        ]
    )
    records.extend(_distribution_records(products, "价格带", "价格带分布", "店铺主要商品表"))
    records.extend(_distribution_records(products, "商品定位", "商品定位分布", "店铺主要商品表"))
    records.extend(_distribution_records(products, "审核状态", "审核状态分布", "店铺主要商品表"))
    records.extend(_distribution_records(products, "SKU变体状态", "SKU状态分布", "店铺主要商品表"))
    return TablePayload(
        name=OVERVIEW_TABLE_NAME,
        default_view_name="运营总览",
        fields=[
            _text_field("指标名称"),
            _single_select_field("指标类型", SUMMARY_TYPES),
            _text_field("维度值"),
            _number_field("数值", "0"),
            _text_field("说明"),
            _text_field("数据源"),
        ],
        records=records,
        views=[
            ViewPayload("价格带分布", filters=[ViewFilter("指标类型", "is", "价格带分布")]),
            ViewPayload("定位分布", filters=[ViewFilter("指标类型", "is", "商品定位分布")]),
            ViewPayload("审核状态分布", filters=[ViewFilter("指标类型", "is", "审核状态分布")]),
        ],
    )


def _product_payload(products: list[dict[str, Any]]) -> TablePayload:
    price_bands = _unique_values(products, "价格带")
    positions = _unique_values(products, "商品定位")
    tag_options = _unique_tags(products)
    records = [_product_record(product) for product in products]
    uploads = [
        AttachmentUpload(
            record_index=index,
            attachment_field="商品主图",
            source_url=str(product.get("店铺展示主图") or ""),
            file_name=f"shop-product-{product.get('店铺商品SKU') or index}.jpg",
            fallback_status_field="图片上传状态",
        )
        for index, product in enumerate(products)
        if product.get("店铺展示主图")
    ]
    visual_hidden = ["店铺展示主图URL", "店铺列表来源", "商品名称", "备注", "图片上传状态"]
    table_hidden = [
        "店铺展示主图URL",
        "店铺列表来源",
        "商品名称",
        "品牌",
        "店铺名称",
        "价格文本",
        "标签",
        "关联系列品",
        "备注",
        "图片上传状态",
    ]
    return TablePayload(
        name=SHOP_PRODUCT_TABLE_NAME,
        default_view_name="商品清单",
        fields=[
            _text_field("商品识别卡片"),
            _attachment_field("商品主图"),
            _text_field("标签摘要"),
            _single_select_field("商品定位", positions),
            _single_select_field("价格带", price_bands),
            _currency_field("价格数值"),
            _url_field("商品链接"),
            _single_select_field("SKU变体状态", SKU_VARIANT_STATUS_OPTIONS),
            _number_field("关联变体数", "0"),
            _single_select_field("竞品分析状态", COMPETITOR_STATUS_OPTIONS),
            _single_select_field("审核状态", REVIEW_STATUS_OPTIONS),
            _text_field("店铺商品SKU"),
            _text_field("商品名称"),
            _text_field("价格文本"),
            _url_field("店铺展示主图URL"),
            _text_field("品牌"),
            _text_field("店铺名称"),
            _multi_select_field("标签", tag_options),
            _text_field("关联系列品"),
            _text_field("图片上传状态"),
            _url_field("店铺列表来源"),
            _text_field("备注"),
        ],
        records=records,
        views=[
            ViewPayload("商品清单", hidden_fields=table_hidden),
            ViewPayload("商品图库", "gallery", hidden_fields=visual_hidden),
            ViewPayload("按价格带", hidden_fields=table_hidden),
            ViewPayload("按商品定位", hidden_fields=table_hidden),
            ViewPayload(
                "待竞品采集",
                hidden_fields=table_hidden,
                filters=[ViewFilter("竞品分析状态", "is", "竞品未采集")],
            ),
            ViewPayload("原始字段视图"),
        ],
        attachment_uploads=uploads,
    )


def _variant_payload(variants: list[dict[str, Any]]) -> TablePayload:
    series_options = _unique_values(variants, "系列品")
    records = [_variant_record(variant) for variant in variants]
    uploads = [
        AttachmentUpload(
            record_index=index,
            attachment_field="变体图",
            source_url=_variant_image_url(variant),
            file_name=f"sku-variant-{variant.get('变体SKU') or index}.jpg",
            fallback_status_field="图片上传状态",
        )
        for index, variant in enumerate(variants)
        if _variant_image_url(variant)
    ]
    hidden = ["店铺展示主图URL", "变体详情主图URL", "款式小图URL", "备注", "图片上传状态"]
    return TablePayload(
        name=SKU_VARIANT_TABLE_NAME,
        default_view_name="SKU变体矩阵",
        fields=[
            _text_field("变体识别卡片"),
            _attachment_field("变体图"),
            _text_field("店铺商品SKU"),
            _text_field("变体SKU"),
            _single_select_field("系列品", series_options),
            _text_field("款式"),
            _text_field("变体商品名称"),
            _currency_field("变体价格数值"),
            _text_field("变体价格文本"),
            _text_field("划线价文本"),
            _text_field("评价量文本"),
            _url_field("变体链接"),
            _url_field("店铺展示主图URL"),
            _url_field("变体详情主图URL"),
            _url_field("款式小图URL"),
            _text_field("店铺主商品名称"),
            _single_select_field("竞品分析状态", COMPETITOR_STATUS_OPTIONS),
            _single_select_field("审核状态", REVIEW_STATUS_OPTIONS),
            _text_field("图片上传状态"),
            _text_field("备注"),
        ],
        records=records,
        views=[
            ViewPayload("变体图库", "gallery", hidden_fields=hidden),
            ViewPayload("按系列品", hidden_fields=hidden),
            ViewPayload("原始字段视图"),
        ],
        attachment_uploads=uploads,
    )


def _competitor_task_payload(products: list[dict[str, Any]]) -> TablePayload:
    records = [
        {
            "fields": {
                "任务名称": f"采集同价位竞品 - {product.get('店铺商品SKU', '')}",
                "关联店铺SKU": str(product.get("店铺商品SKU", "")),
                "主商品名称": str(product.get("商品名称", "")),
                "价格带": str(product.get("价格带", "")),
                "商品定位": str(product.get("商品定位", "")),
                "商品链接": _url_value("打开商品", product.get("商品链接")),
                "任务状态": "竞品未采集",
                "下一步": "补充同价位竞品商品数据后再生成分析结论",
                "审核状态": "待审核",
            }
        }
        for product in products
    ]
    return TablePayload(
        name=COMPETITOR_TASK_TABLE_NAME,
        default_view_name="竞品任务清单",
        fields=[
            _text_field("任务名称"),
            _text_field("关联店铺SKU"),
            _text_field("主商品名称"),
            _text_field("价格带"),
            _text_field("商品定位"),
            _url_field("商品链接"),
            _single_select_field("任务状态", TASK_STATUS_OPTIONS),
            _text_field("下一步"),
            _single_select_field("审核状态", REVIEW_STATUS_OPTIONS),
        ],
        records=records,
        views=[
            ViewPayload("竞品任务看板", "kanban"),
            ViewPayload("待补充数据", filters=[ViewFilter("任务状态", "is", "竞品未采集")]),
        ],
    )


def _suggestion_payload(payload: dict[str, Any]) -> TablePayload:
    generated_at = str(payload.get("generated_at") or "")
    records = [
        {
            "fields": {
                "建议类型": label,
                "建议内容": "等待竞品数据采集和人工确认后生成",
                "依据数据": f"当前仅有店铺商品与SKU变体数据；payload生成时间：{generated_at}",
                "优先级": "待定",
                "竞品分析状态": "竞品未采集",
                "审核状态": "待审核",
            }
        }
        for label in ["标题方向", "详情页方向", "平台内容方向"]
    ]
    return TablePayload(
        name=SUGGESTION_TABLE_NAME,
        default_view_name="待生成建议",
        fields=[
            _text_field("建议类型"),
            _text_field("建议内容"),
            _text_field("依据数据"),
            _single_select_field("优先级", PRIORITY_OPTIONS),
            _single_select_field("竞品分析状态", COMPETITOR_STATUS_OPTIONS),
            _single_select_field("审核状态", REVIEW_STATUS_OPTIONS),
        ],
        records=records,
        views=[ViewPayload("待审核建议", filters=[ViewFilter("审核状态", "is", "待审核")])],
    )


def _overview_record(
    metric_type: str,
    metric_name: str,
    dimension: str,
    value: int,
    description: str,
    source: str = "自动摘要",
) -> dict[str, dict[str, Any]]:
    return {
        "fields": {
            "指标名称": metric_name,
            "指标类型": metric_type,
            "维度值": dimension,
            "数值": value,
            "说明": description,
            "数据源": source,
        }
    }


def _distribution_records(
    records: list[dict[str, Any]],
    field_name: str,
    metric_type: str,
    source: str,
) -> list[dict[str, dict[str, Any]]]:
    counter = Counter(str(record.get(field_name) or "未识别") for record in records)
    return [
        _overview_record(metric_type, field_name, dimension, count, f"{field_name}={dimension} 的记录数", source)
        for dimension, count in counter.items()
    ]


def _product_record(product: dict[str, Any]) -> dict[str, dict[str, Any]]:
    image_url = product.get("店铺展示主图")
    return {
        "fields": {
            "商品识别卡片": _product_identity_card(product),
            "店铺商品SKU": str(product.get("店铺商品SKU", "")),
            "商品名称": str(product.get("商品名称", "")),
            "商品定位": str(product.get("商品定位", "")),
            "价格带": str(product.get("价格带", "")),
            "价格数值": _number_or_none(product.get("价格数值")),
            "价格文本": str(product.get("价格文本", "")),
            "商品链接": _url_value("打开商品", product.get("商品链接")),
            "店铺展示主图URL": _url_value("查看主图", image_url),
            "品牌": str(product.get("品牌", "")),
            "店铺名称": str(product.get("店铺名称", "")),
            "标签": _split_tags(product.get("标签")),
            "标签摘要": _tags_summary(product.get("标签")),
            "SKU变体状态": str(product.get("SKU变体状态") or "未采集"),
            "关联系列品": str(product.get("关联系列品", "")),
            "关联变体数": _number_or_zero(product.get("关联变体数")),
            "竞品分析状态": str(product.get("竞品分析状态") or "竞品未采集"),
            "审核状态": str(product.get("审核状态") or "待审核"),
            "图片上传状态": "待上传" if image_url else "无图片URL",
            "店铺列表来源": _url_value("查看来源", product.get("店铺列表来源")),
            "备注": str(product.get("备注", "")),
        }
    }


def _variant_record(variant: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "fields": {
            "变体识别卡片": _variant_identity_card(variant),
            "店铺商品SKU": str(variant.get("店铺商品SKU", "")),
            "变体SKU": str(variant.get("变体SKU", "")),
            "系列品": str(variant.get("系列品", "")),
            "款式": str(variant.get("款式", "")),
            "变体商品名称": str(variant.get("变体商品名称", "")),
            "变体价格数值": _parse_price(variant.get("变体价格文本")),
            "变体价格文本": str(variant.get("变体价格文本", "")),
            "划线价文本": str(variant.get("划线价文本", "")),
            "评价量文本": str(variant.get("评价量文本", "")),
            "变体链接": _url_value("打开变体", variant.get("变体链接")),
            "店铺展示主图URL": _url_value("查看店铺图", variant.get("店铺展示主图")),
            "变体详情主图URL": _url_value("查看详情图", variant.get("变体详情主图")),
            "款式小图URL": _url_value("查看款式图", variant.get("款式小图")),
            "店铺主商品名称": str(variant.get("店铺主商品名称", "")),
            "竞品分析状态": str(variant.get("竞品分析状态") or "竞品未采集"),
            "审核状态": str(variant.get("审核状态") or "待审核"),
            "图片上传状态": "待上传" if _variant_image_url(variant) else "无图片URL",
            "备注": str(variant.get("备注", "")),
        }
    }


def _variant_image_url(variant: dict[str, Any]) -> str:
    return str(variant.get("款式小图") or variant.get("变体详情主图") or variant.get("店铺展示主图") or "")


def _product_identity_card(product: dict[str, Any]) -> str:
    title = _wrap_text(str(product.get("商品名称") or ""), width=22)
    meta = [
        str(product.get("价格文本") or "").strip(),
        str(product.get("商品定位") or "").strip(),
    ]
    sku = str(product.get("店铺商品SKU") or "").strip()
    lines = [title, " / ".join(item for item in meta if item)]
    if sku:
        lines.append(f"SKU {sku}")
    return "\n".join(line for line in lines if line)


def _variant_identity_card(variant: dict[str, Any]) -> str:
    title = _wrap_text(str(variant.get("款式") or variant.get("变体商品名称") or ""), width=22)
    meta = [
        str(variant.get("变体价格文本") or "").strip(),
        str(variant.get("评价量文本") or "").strip(),
    ]
    sku = str(variant.get("变体SKU") or "").strip()
    lines = [title, " / ".join(item for item in meta if item)]
    if sku:
        lines.append(f"SKU {sku}")
    return "\n".join(line for line in lines if line)


def _text_field(name: str) -> dict[str, Any]:
    return {"field_name": name, "type": TEXT_FIELD}


def _number_field(name: str, formatter: str) -> dict[str, Any]:
    return {"field_name": name, "type": NUMBER_FIELD, "property": {"formatter": formatter}}


def _currency_field(name: str) -> dict[str, Any]:
    return {
        "field_name": name,
        "type": NUMBER_FIELD,
        "ui_type": "Currency",
        "property": {"formatter": "0.00", "currency_code": "CNY"},
    }


def _url_field(name: str) -> dict[str, Any]:
    return {"field_name": name, "type": URL_FIELD}


def _attachment_field(name: str) -> dict[str, Any]:
    return {"field_name": name, "type": ATTACHMENT_FIELD}


def _single_select_field(name: str, options: list[str]) -> dict[str, Any]:
    return {"field_name": name, "type": SINGLE_SELECT_FIELD, "property": {"options": _select_options(options)}}


def _multi_select_field(name: str, options: list[str]) -> dict[str, Any]:
    return {"field_name": name, "type": MULTI_SELECT_FIELD, "property": {"options": _select_options(options)}}


def _select_options(options: list[str]) -> list[dict[str, Any]]:
    unique = _unique_strings(options)
    return [{"name": option, "color": SELECT_COLORS.get(option, index % 55)} for index, option in enumerate(unique)]


def _url_value(text: str, url: Any) -> dict[str, str] | None:
    link = str(url or "").strip()
    if not link:
        return None
    return {"text": text, "link": link}


def _unique_values(records: list[dict[str, Any]], field_name: str) -> list[str]:
    return _unique_strings([str(record.get(field_name) or "未识别") for record in records])


def _unique_tags(records: list[dict[str, Any]]) -> list[str]:
    tags: list[str] = []
    for record in records:
        tags.extend(_split_tags(record.get("标签")))
    return _unique_strings(tags)


def _unique_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        clean = str(value).strip()
        if clean and clean not in result:
            result.append(clean)
    return result or ["未识别"]


def _split_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        return _unique_strings([str(item) for item in value])
    return _unique_strings([item for item in re.split(r"[、,，\s]+", str(value or "")) if item])


def _tags_summary(value: Any, per_line: int = 3) -> str:
    tags = _split_tags(value)
    lines = [tags[index : index + per_line] for index in range(0, len(tags), per_line)]
    return "\n".join(" / ".join(line) for line in lines)


def _wrap_text(value: str, width: int) -> str:
    text = value.replace("公牛（BULL）", "").strip()
    if len(text) <= width:
        return text
    return "\n".join(text[index : index + width] for index in range(0, len(text), width))


def _number_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _number_or_none(value: Any) -> float | int | None:
    if value in ("", None):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _parse_price(value: Any) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group()) if match else None


def _count_equals(records: list[dict[str, Any]], field_name: str, expected: str) -> int:
    return sum(1 for record in records if str(record.get(field_name) or "") == expected)
