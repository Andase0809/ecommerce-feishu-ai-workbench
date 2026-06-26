from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


PlatformName = Literal["小红书", "抖音", "电商平台"]


class ProductInput(BaseModel):
    product_id: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    price_range: str = Field(min_length=1)
    target_user: str = Field(min_length=1)
    core_features: list[str] = Field(min_length=1)
    usage_scenarios: list[str] = Field(min_length=1)
    platform_style: list[PlatformName] = Field(default_factory=lambda: ["小红书", "抖音", "电商平台"])

    @field_validator("core_features", "usage_scenarios", mode="after")
    @classmethod
    def strip_list_values(cls, values: list[str]) -> list[str]:
        stripped = [item.strip() for item in values if item.strip()]
        if not stripped:
            raise ValueError("list field must contain at least one non-empty item")
        return stripped


class PlatformContent(BaseModel):
    platform: PlatformName
    titles: list[str] = Field(min_length=1)
    selling_points: list[str] = Field(min_length=1)
    platform_copy: str = Field(min_length=1)
    tags: list[str] = Field(min_length=1)
    review_status: str = "待审核"


class ProductOutput(BaseModel):
    product_id: str
    product_name: str
    category: str
    price_range: str
    target_user: str
    core_features: list[str]
    usage_scenarios: list[str]
    platform_contents: list[PlatformContent]
    review_checklist: list[str]


def load_products(path: Path) -> list[ProductInput]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("input JSON must be an array of products")
    return [ProductInput.model_validate(item) for item in data]


def save_outputs(path: Path, outputs: list[ProductOutput]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [item.model_dump(mode="json") for item in outputs]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
