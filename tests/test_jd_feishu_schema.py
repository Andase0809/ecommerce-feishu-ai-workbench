from datetime import datetime

from src.competitor_analysis import analyze_workbench
from src.competitor_models import AICompetitorInsight, JdProductSnapshot, LampAttributes
from src.jd_feishu_schema import (
    ANALYSIS_TABLE_NAME,
    COMPETITOR_TABLE_NAME,
    OWN_PRODUCT_TABLE_NAME,
    SUGGESTION_TABLE_NAME,
    build_competitor_table_payloads,
)
from src.feishu_schema import ATTACHMENT_FIELD, NUMBER_FIELD, URL_FIELD


def _snapshot(sku_id: str, role: str) -> JdProductSnapshot:
    return JdProductSnapshot(
        role=role,
        source_url=f"https://item.jd.com/{sku_id}.html",
        sku_id=sku_id,
        product_name=f"护眼学习台灯 {sku_id}",
        brand="明澈",
        shop_name="示例店铺",
        price_text="￥199.00",
        price_range="100-199元",
        image_url="https://img10.jd.com/main.jpg",
        detail_params={"照度": "国AA级"},
        selling_points=["国AA级照度"],
        review_count_text="1万+评价",
        collected_at=datetime(2026, 6, 26, 10, 0, 0).isoformat(),
        lamp_attributes=LampAttributes(illuminance="国AA级", blue_light="RG0"),
    )


def test_build_competitor_table_payloads_creates_four_workbench_tables() -> None:
    target = _snapshot("100000000001", "target")
    competitors = [_snapshot(f"1000000000{index:02d}", "competitor") for index in range(2, 12)]
    workbench = analyze_workbench("台灯", target, competitors)

    payloads = build_competitor_table_payloads(workbench)

    assert [payload.name for payload in payloads] == [
        OWN_PRODUCT_TABLE_NAME,
        COMPETITOR_TABLE_NAME,
        ANALYSIS_TABLE_NAME,
        SUGGESTION_TABLE_NAME,
    ]
    own_fields = [field["field_name"] for field in payloads[0].fields]
    own_field_types = {field["field_name"]: field["type"] for field in payloads[0].fields}
    assert "查看竞品分析" in own_fields
    assert "采集状态" in own_fields
    assert own_fields[:5] == ["商品识别卡片", "商品主图", "商品链接", "价格数值", "采集状态"]
    assert own_field_types["商品主图"] == ATTACHMENT_FIELD
    assert own_field_types["商品链接"] == URL_FIELD
    assert own_field_types["价格数值"] == NUMBER_FIELD
    assert payloads[0].attachment_uploads
    assert len(payloads[1].records) == 10
    assert payloads[1].attachment_uploads
    assert payloads[1].views[0].name == "竞品清单"
    assert payloads[1].views[1].name == "竞品图库"
    assert "主图URL" in payloads[1].views[0].hidden_fields
    assert payloads[2].records[0]["fields"]["机会层级"] in {"高", "中", "低"}


def test_competitor_analysis_table_includes_ai_insight_fields() -> None:
    target = _snapshot("100000000001", "target")
    competitors = [_snapshot(f"1000000000{index:02d}", "competitor") for index in range(2, 12)]
    workbench = analyze_workbench("台灯", target, competitors)
    workbench.analysis.ai_insight = AICompetitorInsight(
        provider="openai",
        model="test-model",
        status="成功",
        category_suggestions=["学习护眼台灯"],
        operation_suggestions=["补齐防蓝光参数"],
        content_angles=["学习桌面场景"],
        review_notes=["核对参数来源"],
    )

    analysis_table = build_competitor_table_payloads(workbench)[2]
    fields = [field["field_name"] for field in analysis_table.fields]
    record = analysis_table.records[0]["fields"]

    assert "AI运营建议" in fields
    assert record["AI分类建议"] == "学习护眼台灯"
    assert record["AI模型"] == "openai/test-model"
