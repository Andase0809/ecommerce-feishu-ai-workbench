from datetime import datetime

from src.ai_client import AIConfig
from src.competitor_analysis import analyze_workbench, find_forbidden_terms_in_workbench
from src.competitor_models import AICompetitorInsight, CompetitorAnalysis, JdProductSnapshot, LampAttributes


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


def test_analyze_workbench_can_attach_ai_competitor_insight() -> None:
    class FakeAIClient:
        config = AIConfig(provider="openai", api_key="test-key", model="test-model", base_url="https://api.test")

        def generate_competitor_insight(
            self,
            keyword: str,
            target: JdProductSnapshot,
            competitors: list[JdProductSnapshot],
            analysis: CompetitorAnalysis,
        ) -> AICompetitorInsight:
            return AICompetitorInsight(
                provider="openai",
                model="test-model",
                status="成功",
                category_suggestions=[f"{keyword}中价位学习场景"],
                operation_suggestions=["补齐主商品防蓝光参数"],
                content_angles=["学习桌面布光对比"],
                review_notes=["人工核对护眼参数"],
            )

    target = _snapshot("100000000001", "target", LampAttributes(illuminance="国AA级"))
    competitors = [_snapshot(f"1000000000{index:02d}", "competitor", LampAttributes(illuminance="国AA级")) for index in range(2, 12)]

    workbench = analyze_workbench("台灯", target, competitors, ai_client=FakeAIClient())

    assert workbench.analysis.ai_insight is not None
    assert workbench.analysis.ai_insight.operation_suggestions == ["补齐主商品防蓝光参数"]
