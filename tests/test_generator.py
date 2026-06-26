from src.generator import find_forbidden_terms, generate_outputs
from src.ai_client import AIConfig
from src.models import AIProductInsight, ProductInput


def _product() -> ProductInput:
    return ProductInput(
        product_id="product-001",
        product_name="便携式桌面补光灯",
        category="数码配件",
        price_range="99-199元",
        target_user="学生和轻办公用户",
        core_features=["三档色温", "可调节亮度", "USB供电"],
        usage_scenarios=["宿舍拍摄", "桌面直播"],
        platform_style=["小红书", "抖音", "电商平台"],
    )


def test_generate_outputs_contains_three_platforms() -> None:
    outputs = generate_outputs([_product()])

    assert len(outputs) == 1
    platforms = {item.platform for item in outputs[0].platform_contents}
    assert platforms == {"小红书", "抖音", "电商平台"}


def test_platform_copy_has_distinct_voice() -> None:
    output = generate_outputs([_product()])[0]
    copies = {item.platform: item.platform_copy for item in output.platform_contents}

    assert "体验" in copies["小红书"]
    assert "如果你平时" in copies["抖音"]
    assert "商品信息重点" in copies["电商平台"]
    assert len(set(copies.values())) == 3


def test_generated_outputs_do_not_include_forbidden_terms() -> None:
    outputs = generate_outputs([_product()])

    assert find_forbidden_terms(outputs) == []


def test_generate_outputs_can_attach_ai_product_insight() -> None:
    class FakeAIClient:
        config = AIConfig(provider="deepseek", api_key="test-key", model="deepseek-v4-flash", base_url="https://api.test")

        def generate_product_insight(self, product: ProductInput) -> AIProductInsight:
            return AIProductInsight(
                provider="deepseek",
                model="deepseek-v4-flash",
                status="成功",
                category_suggestion="桌面照明",
                product_positioning=f"{product.price_range}内容创作补光",
                suggested_tags=["补光", "桌面"],
                operation_suggestions=["按使用场景拆分标题"],
                review_notes=["核对功率参数"],
            )

    output = generate_outputs([_product()], ai_client=FakeAIClient())[0]

    assert output.ai_insight is not None
    assert output.ai_insight.category_suggestion == "桌面照明"
    assert output.ai_insight.operation_suggestions == ["按使用场景拆分标题"]
