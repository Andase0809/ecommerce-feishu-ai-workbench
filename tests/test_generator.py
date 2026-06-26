from src.generator import find_forbidden_terms, generate_outputs
from src.models import ProductInput


def _product() -> ProductInput:
    return ProductInput(
        product_id="demo-001",
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
