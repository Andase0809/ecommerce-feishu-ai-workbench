from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from .competitor_models import JdProductSnapshot, LampAttributes, ScrapeRole


SKU_RE = re.compile(r"item\.jd\.com/(\d+)\.html")
PRICE_RE = re.compile(r"(\d+(?:\.\d+)?)")
SPACE_RE = re.compile(r"\s+")


def parse_jd_product_html(
    html: str,
    url: str,
    role: ScrapeRole,
    collected_at: datetime | None = None,
) -> JdProductSnapshot:
    soup = BeautifulSoup(html, "html.parser")
    params = _extract_params(soup)
    text_blob = _clean_text(" ".join([soup.get_text(" ", strip=True), " ".join(params.values())]))
    selling_points = _extract_selling_points(soup)
    price_text = _first_text(soup, [".p-price .price", ".summary-price .price", "[class*=price]"])
    brand = _brand_from_params(params) or _first_text(soup, ["#parameter-brand a", "[clstag*=pinpai]"]) or "未识别"

    return JdProductSnapshot(
        role=role,
        source_url=url,
        sku_id=extract_sku_id(url),
        product_name=_extract_product_name(soup),
        brand=brand,
        shop_name=_extract_shop_name(soup),
        price_text=price_text or "未识别",
        price_range=parse_price_range(price_text),
        image_url=_normalize_url(_extract_image_url(soup)),
        detail_params=params,
        selling_points=selling_points,
        review_count_text=_extract_review_count(soup),
        collected_at=(collected_at or datetime.now()).isoformat(timespec="seconds"),
        lamp_attributes=extract_lamp_attributes(params, text_blob),
    )


def failed_product_snapshot(
    url: str,
    role: ScrapeRole,
    error_message: str,
    collected_at: datetime | None = None,
) -> JdProductSnapshot:
    return JdProductSnapshot(
        role=role,
        source_url=url,
        sku_id=extract_sku_id(url),
        product_name="采集失败",
        collected_at=(collected_at or datetime.now()).isoformat(timespec="seconds"),
        scrape_status="失败",
        error_message=error_message,
    )


def extract_sku_id(url: str) -> str:
    match = SKU_RE.search(url)
    return match.group(1) if match else ""


def parse_price_range(price_text: str) -> str:
    match = PRICE_RE.search(price_text or "")
    if not match:
        return "未识别"
    price = float(match.group(1))
    if price < 100:
        return "100元以下"
    if price < 200:
        return "100-199元"
    if price < 400:
        return "200-399元"
    return "400元以上"


def extract_lamp_attributes(params: dict[str, str], text_blob: str) -> LampAttributes:
    joined = " ".join([f"{key} {value}" for key, value in params.items()] + [text_blob])
    return LampAttributes(
        illuminance=_pick_param(params, ["照度", "照明标准", "国AA", "国A"]) or _match(joined, r"国A{1,2}级?"),
        color_temperature=_pick_param(params, ["色温", "光色"]) or _match(joined, r"\d{3,5}K(?:-\d{3,5}K)?"),
        cri=_pick_param(params, ["显色指数", "显指", "CRI"]) or _match(joined, r"(?:Ra|CRI)\s?\d{2,3}"),
        blue_light=_pick_param(params, ["防蓝光", "蓝光", "RG0"]) or _match(joined, r"RG0|低蓝光|防蓝光"),
        dimming=_pick_param(params, ["调光", "调光方式", "亮度调节"]) or _match(joined, r"\d+档调光|无极调光"),
        power=_pick_param(params, ["功率", "额定功率"]) or _match(joined, r"\d+(?:\.\d+)?W"),
        usage_scenario=_pick_param(params, ["适用场景", "场景", "用途"]) or _match(joined, r"学习阅读|卧室床头|办公|儿童学习"),
    )


def _extract_product_name(soup: BeautifulSoup) -> str:
    return (
        _first_text(soup, [".sku-name", "#name .sku-name", "h1"])
        or _meta_content(soup, "property", "og:title")
        or _clean_title(soup.title.get_text(" ", strip=True) if soup.title else "")
        or "未识别"
    )


def _extract_shop_name(soup: BeautifulSoup) -> str:
    return (
        _first_text(soup, [".shopName strong a", ".J-hove-wrap .name", ".popbox-inner .mt h3", "[class*=shopName] a"])
        or "未识别"
    )


def _extract_image_url(soup: BeautifulSoup) -> str:
    return (
        _meta_content(soup, "property", "og:image")
        or _first_attr(soup, ["#spec-img", ".jqzoom img", ".preview img"], "src")
        or _first_attr(soup, ["#spec-img", ".jqzoom img", ".preview img"], "data-origin")
        or ""
    )


def _extract_params(soup: BeautifulSoup) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in soup.select("#parameter2 li, .parameter2 li, .p-parameter li, [class*=parameter] li"):
        raw = item.get_text(" ", strip=True) or item.get("title") or ""
        key, value = _split_param(raw)
        if key and value:
            params[key] = value
    return params


def _extract_selling_points(soup: BeautifulSoup) -> list[str]:
    candidates = [
        _first_text(soup, ["#p-ad", ".p-ad", ".summary-service"]),
        _meta_content(soup, "name", "description"),
    ]
    return [_clean_text(item) for item in candidates if _clean_text(item)][:5]


def _extract_review_count(soup: BeautifulSoup) -> str:
    return _first_text(soup, ["#comment-count a", ".comment-count a", "[class*=comment] a"]) or "未识别"


def _split_param(raw: str) -> tuple[str, str]:
    cleaned = _clean_text(raw)
    for separator in ("：", ":"):
        if separator in cleaned:
            key, value = cleaned.split(separator, 1)
            return key.strip(), value.strip()
    return "", ""


def _brand_from_params(params: dict[str, str]) -> str:
    for key, value in params.items():
        if "品牌" in key:
            return value
    return ""


def _pick_param(params: dict[str, str], names: list[str]) -> str:
    for key, value in params.items():
        if any(name.lower() in key.lower() or name.lower() in value.lower() for name in names):
            return value
    return ""


def _match(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(0) if match else "未识别"


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str:
    for selector in selectors:
        item = soup.select_one(selector)
        if item:
            text = _clean_text(item.get_text(" ", strip=True))
            if text:
                return text
    return ""


def _first_attr(soup: BeautifulSoup, selectors: list[str], attr: str) -> str:
    for selector in selectors:
        item = soup.select_one(selector)
        if item and item.get(attr):
            return str(item.get(attr))
    return ""


def _meta_content(soup: BeautifulSoup, attr: str, value: str) -> str:
    item = soup.find("meta", attrs={attr: value})
    if item and item.get("content"):
        return _clean_text(str(item.get("content")))
    return ""


def _normalize_url(url: str) -> str:
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _clean_title(title: str) -> str:
    return title.replace("京东", "").replace("JD.COM", "").strip(" -_")


def _clean_text(text: str) -> str:
    return SPACE_RE.sub(" ", text or "").strip()
