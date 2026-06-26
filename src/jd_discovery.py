from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .competitor_models import CompetitorInput
from .jd_scraper import BrowserBackend, SearchFetchResult, create_html_fetcher


ITEM_URL_RE = re.compile(r"item\.jd\.com/(\d+)\.html")
PRICE_RE = re.compile(r"(\d+(?:\.\d+)?)")
SPACE_RE = re.compile(r"\s+")
JSONP_RE = re.compile(r"^[\w.$]+\((.*)\)\s*;?$", re.DOTALL)
DEFAULT_JD_SEARCH_LISTEN_PATTERN = "api?appid=search-pc-java"
DiscoveryMode = Literal["auto", "listen", "html"]
SKU_KEYS = ("skuId", "sku_id", "skuid", "wareId", "wareid", "ware_id", "wareID", "productId", "product_id")
FALLBACK_SKU_KEYS = ("id",)
URL_KEYS = ("url", "wareUrl", "itemUrl", "pcUrl", "link", "href")
TITLE_KEYS = ("wname", "skuName", "wareName", "name", "title", "goodsName", "productName")
PRICE_KEYS = ("jdPrice", "jprice", "price", "pc_price", "pcpPrice", "pPrice", "salePrice")
SHOP_KEYS = ("shopName", "shop_name", "shop", "venderName", "vendorName", "storeName")


@dataclass(frozen=True)
class JdSearchItem:
    sku_id: str
    url: str
    title: str
    price_text: str
    price: float | None
    shop_name: str


def discover_competitor_urls(
    keyword: str,
    target_brand: str,
    price_min: float,
    price_max: float,
    output_path: Path,
    search_url: str | None = None,
    headful: bool = True,
    wait_seconds: float = 2,
    user_data_dir: str | Path | None = None,
    browser_path: str | Path | None = None,
    login_first: bool = False,
    manual_wait_seconds: float = 180,
    browser_backend: BrowserBackend = "drissionpage",
    competitor_count: int = 10,
    discovery_mode: DiscoveryMode = "auto",
    listen_pattern: str = DEFAULT_JD_SEARCH_LISTEN_PATTERN,
    listen_timeout: float = 10,
    listen_count: int = 8,
) -> CompetitorInput:
    search_url = search_url or build_jd_search_url(keyword)
    with create_html_fetcher(
        browser_backend,
        headful=headful,
        wait_seconds=wait_seconds,
        user_data_dir=user_data_dir,
        browser_path=browser_path,
        login_first=login_first,
        manual_wait_seconds=manual_wait_seconds,
    ) as fetcher:
        fetch_result = _fetch_search_candidates(
            fetcher,
            search_url,
            discovery_mode=discovery_mode,
            listen_pattern=listen_pattern,
            listen_timeout=listen_timeout,
            listen_count=listen_count,
        )
    items = _items_from_fetch_result(fetch_result, discovery_mode)
    data = discover_competitor_input_from_items(
        items,
        keyword=keyword,
        target_brand=target_brand,
        price_min=price_min,
        price_max=price_max,
        competitor_count=competitor_count,
    )
    save_competitor_input(output_path, data)
    return data


def build_jd_search_url(keyword: str) -> str:
    return f"https://search.jd.com/Search?keyword={quote_plus(keyword)}&enc=utf-8"


def parse_jd_search_html(html: str) -> list[JdSearchItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[JdSearchItem] = []
    seen: set[str] = set()
    cards = soup.select(".gl-item, li[data-sku], div[data-sku]")
    for card in cards:
        item = _parse_card(card)
        if item is None or item.sku_id in seen:
            continue
        seen.add(item.sku_id)
        items.append(item)
    if items:
        return items
    return _parse_links_fallback(soup)


def parse_jd_search_api_bodies(bodies: list[Any]) -> list[JdSearchItem]:
    items: list[JdSearchItem] = []
    for body in bodies:
        items.extend(parse_jd_search_api_body(body))
    return _dedupe_search_items(items)


def parse_jd_search_api_body(body: Any) -> list[JdSearchItem]:
    payload = _normalize_api_payload(body)
    if payload is None:
        return []

    items: list[JdSearchItem] = []
    for node in _walk_dicts(payload):
        item = _parse_api_item(node)
        if item is not None:
            items.append(item)
    return _dedupe_search_items(items)


def discover_competitor_input_from_items(
    items: list[JdSearchItem],
    keyword: str,
    target_brand: str,
    price_min: float,
    price_max: float,
    competitor_count: int = 10,
) -> CompetitorInput:
    if competitor_count != 10:
        raise ValueError("v0.1 expects exactly 10 competitors")
    usable = [item for item in items if item.price is not None]
    if not usable:
        raise ValueError("未在搜索结果中识别到带价格的京东商品")

    target = _choose_target(usable, target_brand, price_min, price_max)
    competitors = _choose_competitors(usable, target, price_min, price_max, competitor_count)
    if len(competitors) < competitor_count:
        raise ValueError(
            f"同价位候选不足，目标商品已选中，但只找到 {len(competitors)} 个竞品；"
            "请扩大价格区间或换一个关键词"
        )
    return CompetitorInput(
        keyword=keyword,
        target_url=target.url,
        competitor_urls=[item.url for item in competitors],
    )


def save_competitor_input(path: Path, data: CompetitorInput) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = data.model_dump(mode="json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_card(card: object) -> JdSearchItem | None:
    sku_id = str(card.get("data-sku") or "")
    link = card.select_one(".p-name a[href], a[href*='item.jd.com']")
    href = str(link.get("href")) if link else ""
    sku_id = sku_id or _sku_from_href(href)
    if not sku_id:
        return None

    title = _clean_text(card.select_one(".p-name").get_text(" ", strip=True) if card.select_one(".p-name") else "")
    if not title and link:
        title = _clean_text(link.get_text(" ", strip=True))
    price_text = _clean_text(card.select_one(".p-price").get_text(" ", strip=True) if card.select_one(".p-price") else "")
    shop_name = _clean_text(card.select_one(".p-shop").get_text(" ", strip=True) if card.select_one(".p-shop") else "")
    return JdSearchItem(
        sku_id=sku_id,
        url=f"https://item.jd.com/{sku_id}.html",
        title=title or "未识别",
        price_text=price_text,
        price=_parse_price(price_text),
        shop_name=shop_name or "未识别",
    )


def _parse_links_fallback(soup: BeautifulSoup) -> list[JdSearchItem]:
    items: list[JdSearchItem] = []
    seen: set[str] = set()
    for link in soup.select("a[href*='item.jd.com']"):
        href = str(link.get("href") or "")
        sku_id = _sku_from_href(href)
        if not sku_id or sku_id in seen:
            continue
        seen.add(sku_id)
        items.append(
            JdSearchItem(
                sku_id=sku_id,
                url=f"https://item.jd.com/{sku_id}.html",
                title=_clean_text(link.get_text(" ", strip=True)) or "未识别",
                price_text="",
                price=None,
                shop_name="未识别",
            )
        )
    return items


def _fetch_search_candidates(
    fetcher: object,
    search_url: str,
    discovery_mode: DiscoveryMode,
    listen_pattern: str,
    listen_timeout: float,
    listen_count: int,
) -> SearchFetchResult:
    if discovery_mode == "html":
        return SearchFetchResult(api_bodies=[], html=fetcher.fetch(search_url))
    fetch_search_result = getattr(fetcher, "fetch_search_result", None)
    if not callable(fetch_search_result):
        if discovery_mode == "listen":
            raise RuntimeError("当前浏览器后端不支持网络监听，请使用 --browser-backend drissionpage")
        return SearchFetchResult(api_bodies=[], html=fetcher.fetch(search_url))
    return fetch_search_result(
        search_url,
        listen_pattern=listen_pattern,
        listen_timeout=listen_timeout,
        listen_count=listen_count,
    )


def _items_from_fetch_result(fetch_result: SearchFetchResult, discovery_mode: DiscoveryMode) -> list[JdSearchItem]:
    api_items = parse_jd_search_api_bodies(fetch_result.api_bodies)
    if api_items:
        return api_items
    if discovery_mode == "listen":
        raise ValueError("已监听到京东搜索接口请求，但未能从接口响应中解析出带价格的商品候选")
    return parse_jd_search_html(fetch_result.html)


def _parse_api_item(node: dict[str, Any]) -> JdSearchItem | None:
    url = _first_text(node, URL_KEYS)
    sku_id = _sku_from_href(url) or _first_text(node, SKU_KEYS)
    title = _clean_html_text(_first_text(node, TITLE_KEYS))
    price_text = _first_text(node, PRICE_KEYS)
    shop_name = _clean_html_text(_first_text(node, SHOP_KEYS))
    if not sku_id and title and price_text:
        sku_id = _first_text(node, FALLBACK_SKU_KEYS)
    if not sku_id or not _looks_like_product_node(node, title, price_text, url):
        return None
    return JdSearchItem(
        sku_id=sku_id,
        url=f"https://item.jd.com/{sku_id}.html",
        title=title or "未识别",
        price_text=price_text,
        price=_parse_price(price_text),
        shop_name=shop_name or "未识别",
    )


def _normalize_api_payload(body: Any) -> Any:
    if isinstance(body, (dict, list)):
        return body
    if isinstance(body, bytes):
        try:
            body = body.decode("utf-8")
        except UnicodeDecodeError:
            body = body.decode("gbk", errors="ignore")
    if not isinstance(body, str):
        return None
    text = body.strip()
    if not text:
        return None
    for candidate in _json_candidates(text):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _json_candidates(text: str) -> list[str]:
    candidates = [text]
    jsonp_match = JSONP_RE.match(text)
    if jsonp_match:
        candidates.append(jsonp_match.group(1))
    first_object = text.find("{")
    last_object = text.rfind("}")
    if first_object != -1 and last_object > first_object:
        candidates.append(text[first_object:last_object + 1])
    first_array = text.find("[")
    last_array = text.rfind("]")
    if first_array != -1 and last_array > first_array:
        candidates.append(text[first_array:last_array + 1])
    return candidates


def _walk_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(_walk_dicts(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_dicts(child))
    return found


def _first_text(node: dict[str, Any], keys: tuple[str, ...]) -> str:
    lowered = {str(key).lower(): value for key, value in node.items()}
    for key in keys:
        value = node.get(key)
        if value is None:
            value = lowered.get(key.lower())
        text = _value_to_text(value)
        if text:
            return text
    return ""


def _value_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, dict):
        for child in value.values():
            text = _value_to_text(child)
            if text:
                return text
    return ""


def _clean_html_text(text: str) -> str:
    if not text:
        return ""
    return _clean_text(BeautifulSoup(text, "html.parser").get_text(" ", strip=True))


def _looks_like_product_node(node: dict[str, Any], title: str, price_text: str, url: str) -> bool:
    if _sku_from_href(url):
        return True
    lowered_keys = {str(key).lower() for key in node}
    product_key_hits = any(key.lower() in lowered_keys for key in SKU_KEYS)
    fallback_key_hits = any(key.lower() in lowered_keys for key in FALLBACK_SKU_KEYS)
    return (product_key_hits and bool(title or price_text)) or (fallback_key_hits and bool(title and price_text))


def _dedupe_search_items(items: list[JdSearchItem]) -> list[JdSearchItem]:
    by_sku: dict[str, JdSearchItem] = {}
    for item in items:
        current = by_sku.get(item.sku_id)
        if current is None or _item_quality(item) > _item_quality(current):
            by_sku[item.sku_id] = item
    return list(by_sku.values())


def _item_quality(item: JdSearchItem) -> int:
    return int(item.price is not None) + int(item.title != "未识别") + int(item.shop_name != "未识别")


def _choose_target(items: list[JdSearchItem], target_brand: str, price_min: float, price_max: float) -> JdSearchItem:
    midpoint = (price_min + price_max) / 2
    in_band = [item for item in items if _in_price_band(item, price_min, price_max)]
    brand_candidates = [
        item
        for item in in_band
        if target_brand and target_brand.lower() in f"{item.title} {item.shop_name}".lower()
    ]
    pool = brand_candidates or in_band or items
    return sorted(pool, key=lambda item: _price_distance(item, midpoint))[0]


def _choose_competitors(
    items: list[JdSearchItem],
    target: JdSearchItem,
    price_min: float,
    price_max: float,
    competitor_count: int,
) -> list[JdSearchItem]:
    midpoint = target.price if target.price is not None else (price_min + price_max) / 2
    candidates = [
        item
        for item in items
        if item.sku_id != target.sku_id and _in_price_band(item, price_min, price_max)
    ]
    if len(candidates) < competitor_count:
        extra = [item for item in items if item.sku_id != target.sku_id and item not in candidates]
        candidates.extend(extra)
    return sorted(candidates, key=lambda item: _price_distance(item, midpoint))[:competitor_count]


def _sku_from_href(href: str) -> str:
    match = ITEM_URL_RE.search(href)
    return match.group(1) if match else ""


def _parse_price(price_text: str) -> float | None:
    match = PRICE_RE.search(price_text or "")
    return float(match.group(1)) if match else None


def _in_price_band(item: JdSearchItem, price_min: float, price_max: float) -> bool:
    return item.price is not None and price_min <= item.price <= price_max


def _price_distance(item: JdSearchItem, reference: float) -> float:
    if item.price is None:
        return float("inf")
    return abs(item.price - reference)


def _clean_text(text: str) -> str:
    return SPACE_RE.sub(" ", text or "").strip()
