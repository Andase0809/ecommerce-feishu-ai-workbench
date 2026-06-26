import json

from src.jd_discovery import (
    discover_competitor_input_from_items,
    discover_competitor_urls,
    parse_jd_search_api_bodies,
    parse_jd_search_html,
)
from src.jd_scraper import SearchFetchResult


SEARCH_HTML = """
<html>
  <body>
    <li class="gl-item" data-sku="100000000001">
      <div class="p-price"><i>119.00</i></div>
      <div class="p-name"><a href="//item.jd.com/100000000001.html"><em>欧普照明 国A级护眼学习台灯</em></a></div>
      <div class="p-shop"><a>欧普照明京东自营旗舰店</a></div>
    </li>
    <li class="gl-item" data-sku="100000000002">
      <div class="p-price"><i>99.00</i></div>
      <div class="p-name"><a href="//item.jd.com/100000000002.html"><em>松下 学生宿舍阅读台灯</em></a></div>
      <div class="p-shop"><a>松下灯具旗舰店</a></div>
    </li>
    <li class="gl-item" data-sku="100000000003">
      <div class="p-price"><i>139.00</i></div>
      <div class="p-name"><a href="//item.jd.com/100000000003.html"><em>飞利浦 护眼台灯</em></a></div>
      <div class="p-shop"><a>飞利浦照明旗舰店</a></div>
    </li>
    <li class="gl-item" data-sku="100000000004"><div class="p-price"><i>89.00</i></div><div class="p-name"><a href="//item.jd.com/100000000004.html"><em>雷士 儿童学习台灯</em></a></div></li>
    <li class="gl-item" data-sku="100000000005"><div class="p-price"><i>109.00</i></div><div class="p-name"><a href="//item.jd.com/100000000005.html"><em>好视力 LED台灯</em></a></div></li>
    <li class="gl-item" data-sku="100000000006"><div class="p-price"><i>129.00</i></div><div class="p-name"><a href="//item.jd.com/100000000006.html"><em>米家 桌面台灯</em></a></div></li>
    <li class="gl-item" data-sku="100000000007"><div class="p-price"><i>149.00</i></div><div class="p-name"><a href="//item.jd.com/100000000007.html"><em>孩视宝 护眼灯</em></a></div></li>
    <li class="gl-item" data-sku="100000000008"><div class="p-price"><i>79.00</i></div><div class="p-name"><a href="//item.jd.com/100000000008.html"><em>公牛 可调光台灯</em></a></div></li>
    <li class="gl-item" data-sku="100000000009"><div class="p-price"><i>159.00</i></div><div class="p-name"><a href="//item.jd.com/100000000009.html"><em>美的 阅读台灯</em></a></div></li>
    <li class="gl-item" data-sku="100000000010"><div class="p-price"><i>118.00</i></div><div class="p-name"><a href="//item.jd.com/100000000010.html"><em>欧普照明 卧室台灯</em></a></div></li>
    <li class="gl-item" data-sku="100000000011"><div class="p-price"><i>105.00</i></div><div class="p-name"><a href="//item.jd.com/100000000011.html"><em>得力 学习台灯</em></a></div></li>
    <li class="gl-item" data-sku="100000000012"><div class="p-price"><i>135.00</i></div><div class="p-name"><a href="//item.jd.com/100000000012.html"><em>华为智选 台灯</em></a></div></li>
  </body>
</html>
"""


SEARCH_API_BODY = {
    "data": {
        "wareInfo": [
            {
                "skuId": "100000000001",
                "wname": "<em>欧普照明</em> 国A级护眼学习台灯",
                "jdPrice": "119.00",
                "shopName": "欧普照明京东自营旗舰店",
            },
            {"skuId": "100000000002", "wname": "松下 学生宿舍阅读台灯", "jdPrice": "99.00", "shopName": "松下灯具旗舰店"},
            {"skuId": "100000000003", "wname": "飞利浦 护眼台灯", "jdPrice": "139.00", "shopName": "飞利浦照明旗舰店"},
            {"skuId": "100000000004", "wname": "雷士 儿童学习台灯", "jdPrice": "89.00"},
            {"skuId": "100000000005", "wname": "好视力 LED台灯", "jdPrice": "109.00"},
            {"skuId": "100000000006", "wname": "米家 桌面台灯", "jdPrice": "129.00"},
            {"skuId": "100000000007", "wname": "孩视宝 护眼灯", "jdPrice": "149.00"},
            {"skuId": "100000000008", "wname": "公牛 可调光台灯", "jdPrice": "79.00"},
            {"skuId": "100000000009", "wname": "美的 阅读台灯", "jdPrice": "159.00"},
            {"skuId": "100000000010", "wname": "欧普照明 卧室台灯", "jdPrice": "118.00"},
            {"skuId": "100000000011", "wname": "得力 学习台灯", "jdPrice": "105.00"},
            {"skuId": "100000000012", "wname": "华为智选 台灯", "jdPrice": "135.00"},
        ]
    }
}


def test_parse_jd_search_html_extracts_items() -> None:
    items = parse_jd_search_html(SEARCH_HTML)

    assert len(items) == 12
    assert items[0].sku_id == "100000000001"
    assert items[0].url == "https://item.jd.com/100000000001.html"
    assert items[0].price == 119.0
    assert items[0].title == "欧普照明 国A级护眼学习台灯"


def test_parse_jd_search_api_bodies_extracts_items() -> None:
    items = parse_jd_search_api_bodies([f"jsonpCallback({json.dumps(SEARCH_API_BODY, ensure_ascii=False)})"])

    assert len(items) == 12
    assert items[0].sku_id == "100000000001"
    assert items[0].url == "https://item.jd.com/100000000001.html"
    assert items[0].price == 119.0
    assert items[0].title == "欧普照明 国A级护眼学习台灯"


def test_discover_competitor_input_prefers_opple_target_and_price_band() -> None:
    items = parse_jd_search_html(SEARCH_HTML)

    data = discover_competitor_input_from_items(
        items,
        keyword="台灯",
        target_brand="欧普",
        price_min=80,
        price_max=160,
        competitor_count=10,
    )

    assert data.target_url == "https://item.jd.com/100000000001.html"
    assert len(data.competitor_urls) == 10
    assert data.target_url not in data.competitor_urls
    assert data.competitor_urls[0] == "https://item.jd.com/100000000010.html"


def test_discover_competitor_urls_auto_prefers_listened_api(monkeypatch, tmp_path) -> None:
    class FakeFetcher:
        def __enter__(self) -> "FakeFetcher":
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def fetch_search_result(self, url: str, listen_pattern: str, listen_timeout: float, listen_count: int) -> SearchFetchResult:
            assert listen_pattern == "api?appid=search-pc-java"
            return SearchFetchResult(api_bodies=[SEARCH_API_BODY], html="")

        def fetch(self, url: str) -> str:
            raise AssertionError("auto mode should not fall back to HTML when API items are present")

    monkeypatch.setattr("src.jd_discovery.create_html_fetcher", lambda *args, **kwargs: FakeFetcher())

    output_path = tmp_path / "jd-lamp-urls.local.json"
    data = discover_competitor_urls(
        keyword="台灯",
        target_brand="欧普",
        price_min=80,
        price_max=160,
        output_path=output_path,
        discovery_mode="auto",
    )

    assert data.target_url == "https://item.jd.com/100000000001.html"
    assert len(data.competitor_urls) == 10
    assert output_path.exists()
