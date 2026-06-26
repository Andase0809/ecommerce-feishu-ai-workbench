import json

import pytest
from pydantic import ValidationError

from src.models import load_products


def test_load_products_from_json_array(tmp_path) -> None:
    path = tmp_path / "products.json"
    path.write_text(
        json.dumps(
            [
                {
                    "product_id": "demo-001",
                    "product_name": "桌面分区收纳盒",
                    "category": "家居小物",
                    "price_range": "39-79元",
                    "target_user": "租房用户",
                    "core_features": ["多格分区"],
                    "usage_scenarios": ["桌面整理"],
                    "platform_style": ["小红书", "抖音", "电商平台"],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    products = load_products(path)

    assert products[0].product_id == "demo-001"
    assert products[0].core_features == ["多格分区"]


def test_load_products_requires_array(tmp_path) -> None:
    path = tmp_path / "products.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="array"):
        load_products(path)


def test_product_rejects_unknown_platform(tmp_path) -> None:
    path = tmp_path / "products.json"
    path.write_text(
        json.dumps(
            [
                {
                    "product_id": "demo-001",
                    "product_name": "桌面分区收纳盒",
                    "category": "家居小物",
                    "price_range": "39-79元",
                    "target_user": "租房用户",
                    "core_features": ["多格分区"],
                    "usage_scenarios": ["桌面整理"],
                    "platform_style": ["微博"],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_products(path)
