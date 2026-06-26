from src.feishu_schema import PLATFORM_TABLES, PRODUCT_TABLE_NAME, REVIEW_STATUS_OPTIONS, build_table_payloads
from src.generator import generate_outputs
from src.models import ProductInput


def test_build_table_payloads_creates_main_and_platform_tables() -> None:
    output = generate_outputs(
        [
            ProductInput(
                product_id="product-001",
                product_name="日常通勤润色唇膏",
                category="美妆个护",
                price_range="59-129元",
                target_user="通勤用户",
                core_features=["低饱和润色", "滋润质地"],
                usage_scenarios=["通勤补妆"],
                platform_style=["小红书", "抖音", "电商平台"],
            )
        ]
    )

    payloads = build_table_payloads(output)

    assert [payload.name for payload in payloads] == [PRODUCT_TABLE_NAME, *PLATFORM_TABLES.values()]
    assert all(payload.records for payload in payloads)


def test_platform_table_has_review_status_single_select() -> None:
    payloads = build_table_payloads(generate_outputs([]))
    platform_fields = payloads[1].fields

    review_field = next(field for field in platform_fields if field["field_name"] == "审核状态")

    assert review_field["type"] == 3
    assert [option["name"] for option in review_field["property"]["options"]] == REVIEW_STATUS_OPTIONS
