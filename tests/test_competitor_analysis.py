from datetime import datetime

from src.competitor_analysis import analyze_workbench, find_forbidden_terms_in_workbench
from src.competitor_models import JdProductSnapshot, LampAttributes


def _snapshot(sku_id: str, role: str, attrs: LampAttributes) -> JdProductSnapshot:
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
        detail_params={"照度": attrs.illuminance, "色温": attrs.color_temperature},
        selling_points=["国AA级照度", "适合学习阅读"],
        review_count_text="1万+评价",
        collected_at=datetime(2026, 6, 26, 10, 0, 0).isoformat(),
        lamp_attributes=attrs,
    )


def test_analyze_workbench_outputs_qualitative_analysis_without_forbidden_terms() -> None:
    target = _snapshot(
        "100000000001",
        "target",
        LampAttributes(
            illuminance="国AA级",
            color_temperature="3000K-5000K",
            cri="Ra95",
            blue_light="RG0",
            dimming="三档调光",
            power="12W",
            usage_scenario="学习阅读",
        ),
    )
    competitors = [
        _snapshot(
            f"1000000000{index:02d}",
            "competitor",
            LampAttributes(illuminance="国AA级", blue_light="RG0", usage_scenario="学习阅读"),
        )
        for index in range(2, 12)
    ]

    workbench = analyze_workbench("台灯", target, competitors)

    assert workbench.analysis.opportunity_level in {"高", "中", "低"}
    assert workbench.analysis.common_patterns
    assert workbench.analysis.opportunities
    assert workbench.analysis.title_directions
    assert find_forbidden_terms_in_workbench(workbench) == []
