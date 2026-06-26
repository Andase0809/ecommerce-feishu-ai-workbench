from datetime import datetime

from src.competitor_analysis import analyze_workbench
from src.competitor_models import JdProductSnapshot, LampAttributes
from src.jd_feishu_schema import (
    ANALYSIS_TABLE_NAME,
    COMPETITOR_TABLE_NAME,
    OWN_PRODUCT_TABLE_NAME,
    SUGGESTION_TABLE_NAME,
    build_competitor_table_payloads,
)


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
    assert "查看竞品分析" in own_fields
    assert "采集状态" in own_fields
    assert len(payloads[1].records) == 10
    assert payloads[2].records[0]["fields"]["机会层级"] in {"高", "中", "低"}
