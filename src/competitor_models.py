from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


JD_ITEM_URL_RE = re.compile(r"^https?://item\.jd\.com/\d+\.html(?:\?.*)?$")

ScrapeRole = Literal["target", "competitor"]
ScrapeStatus = Literal["成功", "失败"]
OpportunityLevel = Literal["高", "中", "低"]


class CompetitorInput(BaseModel):
    keyword: str = Field(min_length=1)
    target_url: str = Field(min_length=1)
    competitor_urls: list[str] = Field(min_length=1)

    @field_validator("keyword", mode="after")
    @classmethod
    def strip_keyword(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("keyword must not be empty")
        return stripped

    @field_validator("target_url", mode="after")
    @classmethod
    def validate_target_url(cls, value: str) -> str:
        return _validate_jd_item_url(value)

    @field_validator("competitor_urls", mode="after")
    @classmethod
    def validate_competitor_urls(cls, values: list[str]) -> list[str]:
        if len(values) != 10:
            raise ValueError("competitor_urls must contain exactly 10 jd item urls")
        return [_validate_jd_item_url(value) for value in values]


class LampAttributes(BaseModel):
    illuminance: str = "未识别"
    color_temperature: str = "未识别"
    cri: str = "未识别"
    blue_light: str = "未识别"
    dimming: str = "未识别"
    power: str = "未识别"
    usage_scenario: str = "未识别"


class JdProductSnapshot(BaseModel):
    role: ScrapeRole
    source_url: str
    sku_id: str = ""
    product_name: str = ""
    brand: str = "未识别"
    shop_name: str = "未识别"
    price_text: str = "未识别"
    price_range: str = "未识别"
    image_url: str = ""
    detail_params: dict[str, str] = Field(default_factory=dict)
    selling_points: list[str] = Field(default_factory=list)
    review_count_text: str = "未识别"
    collected_at: str
    scrape_status: ScrapeStatus = "成功"
    error_message: str = ""
    lamp_attributes: LampAttributes = Field(default_factory=LampAttributes)


class AICompetitorInsight(BaseModel):
    provider: str = ""
    model: str = ""
    status: str = "未启用"
    category_suggestions: list[str] = Field(default_factory=list)
    operation_suggestions: list[str] = Field(default_factory=list)
    content_angles: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    error_message: str = ""


class CompetitorAnalysis(BaseModel):
    keyword: str
    target_sku_id: str
    competitor_count: int
    opportunity_level: OpportunityLevel
    common_patterns: list[str] = Field(default_factory=list)
    target_differentiators: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    title_directions: list[str] = Field(default_factory=list)
    detail_page_directions: list[str] = Field(default_factory=list)
    platform_content_directions: list[str] = Field(default_factory=list)
    review_checklist: list[str] = Field(default_factory=list)
    ai_insight: AICompetitorInsight | None = None


class CompetitorWorkbenchOutput(BaseModel):
    keyword: str
    target: JdProductSnapshot
    competitors: list[JdProductSnapshot]
    analysis: CompetitorAnalysis


def load_competitor_input(path: Path) -> CompetitorInput:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("input JSON must be an object with keyword, target_url and competitor_urls")
    return CompetitorInput.model_validate(data)


def save_workbench_output(path: Path, output: CompetitorWorkbenchOutput) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = output.model_dump(mode="json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _validate_jd_item_url(value: str) -> str:
    stripped = value.strip()
    if not JD_ITEM_URL_RE.match(stripped):
        raise ValueError("url must be an item.jd.com product URL, for example https://item.jd.com/100000000001.html")
    return stripped
