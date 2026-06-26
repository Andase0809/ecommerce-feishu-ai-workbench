import json

import pytest
from pydantic import ValidationError

from src.competitor_models import load_competitor_input


def _payload(competitor_count: int = 10) -> dict:
    return {
        "keyword": "台灯",
        "target_url": "https://item.jd.com/100000000001.html",
        "competitor_urls": [
            f"https://item.jd.com/1000000000{index:02d}.html"
            for index in range(2, competitor_count + 2)
        ],
    }


def test_load_competitor_input_accepts_one_target_and_ten_competitors(tmp_path) -> None:
    path = tmp_path / "jd-lamp-urls.local.json"
    path.write_text(json.dumps(_payload(), ensure_ascii=False), encoding="utf-8")

    data = load_competitor_input(path)

    assert data.keyword == "台灯"
    assert len(data.competitor_urls) == 10


def test_load_competitor_input_requires_ten_competitors(tmp_path) -> None:
    path = tmp_path / "jd-lamp-urls.local.json"
    path.write_text(json.dumps(_payload(competitor_count=9), ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValidationError, match="exactly 10"):
        load_competitor_input(path)


def test_load_competitor_input_rejects_non_jd_item_url(tmp_path) -> None:
    payload = _payload()
    payload["target_url"] = "https://example.com/product/1"
    path = tmp_path / "jd-lamp-urls.local.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValidationError, match="item.jd.com"):
        load_competitor_input(path)
