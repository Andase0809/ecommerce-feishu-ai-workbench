from src.feishu_schema import ATTACHMENT_FIELD, MULTI_SELECT_FIELD, NUMBER_FIELD, URL_FIELD
from src.shop_workbench_schema import (
    COMPETITOR_TASK_TABLE_NAME,
    OVERVIEW_TABLE_NAME,
    SHOP_PRODUCT_TABLE_NAME,
    SKU_VARIANT_TABLE_NAME,
    SUGGESTION_TABLE_NAME,
    build_shop_workbench_table_payloads,
    redesigned_base_name,
)


def _payload() -> dict:
    return {
        "base_name": "公牛LED照明商品数据工作台",
        "generated_at": "2026-06-26T14:59:37",
        "tables": [
            {
                "table_name": "店铺主要商品表",
                "records": [
                    {
                        "店铺商品SKU": "100026582726",
                        "商品名称": "公牛（BULL）LED酷毙灯宿舍寝室家用磁吸灯",
                        "品牌": "公牛",
                        "店铺名称": "公牛LED照明",
                        "价格文本": "￥17.47",
                        "价格数值": 17.47,
                        "价格带": "低价：50元以下",
                        "商品定位": "宿舍长条灯",
                        "店铺展示主图": "https://img.example.com/main.jpg",
                        "商品链接": "https://item.jd.com/100026582726.html",
                        "店铺列表来源": "https://mall.jd.com/list.html",
                        "标签": "4000K、酷毙灯、磁吸、宿舍",
                        "SKU变体状态": "已采集",
                        "关联系列品": "【经济款】酷毙灯",
                        "关联变体数": 8,
                        "竞品分析状态": "竞品未采集",
                        "审核状态": "待审核",
                        "备注": "主图使用店铺列表页展示图。",
                    },
                    {
                        "店铺商品SKU": "100044274675",
                        "商品名称": "公牛（BULL）台灯国AA级无极调光",
                        "品牌": "公牛",
                        "店铺名称": "公牛LED照明",
                        "价格文本": "￥69.98",
                        "价格数值": 69.98,
                        "价格带": "中低价：50-99元",
                        "商品定位": "学习护眼台灯",
                        "店铺展示主图": "",
                        "商品链接": "https://item.jd.com/100044274675.html",
                        "标签": "无极调光、AA级",
                        "SKU变体状态": "未采集",
                        "关联变体数": 0,
                        "竞品分析状态": "竞品未采集",
                        "审核状态": "待审核",
                    },
                ],
            },
            {
                "table_name": "SKU款式变体表",
                "records": [
                    {
                        "店铺商品SKU": "100026582726",
                        "变体SKU": "100014295721",
                        "系列品": "【经济款】酷毙灯",
                        "款式": "4瓦4000K/无开关/线长0.8m",
                        "变体商品名称": "公牛（BULL）LED酷毙灯宿舍寝室家用磁吸灯",
                        "变体价格文本": "¥6.24",
                        "划线价文本": "¥12.3",
                        "评价量文本": "20万+",
                        "店铺展示主图": "https://img.example.com/main.jpg",
                        "变体详情主图": "https://img.example.com/detail.jpg",
                        "款式小图": "https://img.example.com/thumb.jpg",
                        "变体链接": "https://item.jd.com/100014295721.html",
                        "店铺主商品名称": "公牛（BULL）LED酷毙灯宿舍寝室家用磁吸灯",
                        "竞品分析状态": "竞品未采集",
                        "审核状态": "待审核",
                    }
                ],
            },
        ],
    }


def test_build_shop_workbench_creates_visual_tables() -> None:
    payloads = build_shop_workbench_table_payloads(_payload())

    assert [payload.name for payload in payloads] == [
        OVERVIEW_TABLE_NAME,
        SHOP_PRODUCT_TABLE_NAME,
        SKU_VARIANT_TABLE_NAME,
        COMPETITOR_TASK_TABLE_NAME,
        SUGGESTION_TABLE_NAME,
    ]


def test_product_table_uses_visual_field_types_and_record_values() -> None:
    product_table = build_shop_workbench_table_payloads(_payload())[1]
    fields = {field["field_name"]: field for field in product_table.fields}
    record = product_table.records[0]["fields"]

    assert product_table.fields[0]["field_name"] == "商品识别卡片"
    assert product_table.fields[1]["field_name"] == "商品主图"
    assert product_table.fields[2]["field_name"] == "标签摘要"
    assert fields["商品主图"]["type"] == ATTACHMENT_FIELD
    assert fields["商品链接"]["type"] == URL_FIELD
    assert fields["价格数值"]["type"] == NUMBER_FIELD
    assert fields["价格数值"]["ui_type"] == "Currency"
    assert fields["标签"]["type"] == MULTI_SELECT_FIELD
    assert record["商品链接"] == {"text": "打开商品", "link": "https://item.jd.com/100026582726.html"}
    assert record["价格数值"] == 17.47
    assert record["标签"] == ["4000K", "酷毙灯", "磁吸", "宿舍"]
    assert len(product_table.attachment_uploads) == 1


def test_product_identity_and_tags_are_multiline_for_readability() -> None:
    product_table = build_shop_workbench_table_payloads(_payload())[1]
    record = product_table.records[0]["fields"]
    default_view = product_table.views[0]

    assert "\n" in record["商品识别卡片"]
    assert "SKU 100026582726" in record["商品识别卡片"]
    assert record["标签摘要"] == "4000K / 酷毙灯 / 磁吸\n宿舍"
    assert default_view.name == "商品清单"
    assert "商品名称" in default_view.hidden_fields
    assert "标签" in default_view.hidden_fields
    assert "店铺展示主图URL" in default_view.hidden_fields


def test_overview_counts_are_computed_from_payload_only() -> None:
    overview = build_shop_workbench_table_payloads(_payload())[0]
    records = [record["fields"] for record in overview.records]

    assert {"指标名称": "店铺商品数", "指标类型": "总览", "维度值": "全部商品", "数值": 2, "说明": "来自店铺主要商品表", "数据源": "自动摘要"} in records
    assert any(record["指标类型"] == "价格带分布" and record["维度值"] == "低价：50元以下" and record["数值"] == 1 for record in records)
    assert any(record["指标类型"] == "SKU状态分布" and record["维度值"] == "已采集" and record["数值"] == 1 for record in records)


def test_views_include_gallery_hidden_fields_and_filter_workflow() -> None:
    product_table = build_shop_workbench_table_payloads(_payload())[1]
    views = {view.name: view for view in product_table.views}

    assert views["商品图库"].view_type == "gallery"
    assert "店铺展示主图URL" in views["商品图库"].hidden_fields
    assert views["待竞品采集"].filters[0].field_name == "竞品分析状态"
    assert views["待竞品采集"].filters[0].value == "竞品未采集"


def test_competitor_and_suggestion_tables_do_not_fabricate_market_metrics() -> None:
    payloads = build_shop_workbench_table_payloads(_payload())
    competitor_text = str(payloads[3].records)
    suggestion_text = str(payloads[4].records)

    assert "竞品未采集" in competitor_text
    assert "等待竞品数据采集" in suggestion_text
    forbidden = ["销量第一", "排名", "GMV", "转化率"]
    assert not any(term in competitor_text + suggestion_text for term in forbidden)


def test_redesigned_base_name_adds_suffix_once() -> None:
    assert redesigned_base_name(_payload()) == "公牛LED照明商品数据工作台-重设计版"
    assert redesigned_base_name({"base_name": "A-重设计版"}) == "A-重设计版"
