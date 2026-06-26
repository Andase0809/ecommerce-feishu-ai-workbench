from __future__ import annotations

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from playwright.sync_api import BrowserContext, Page, sync_playwright

from .competitor_models import CompetitorInput, JdProductSnapshot
from .jd_parser import failed_product_snapshot, parse_jd_product_html


HtmlFetcher = Callable[[str], str]
BrowserBackend = Literal["drissionpage", "playwright"]


@dataclass(frozen=True)
class SearchFetchResult:
    api_bodies: list[Any] = field(default_factory=list)
    html: str = ""


def collect_jd_snapshots(
    data: CompetitorInput,
    fetch_html: HtmlFetcher,
) -> tuple[JdProductSnapshot, list[JdProductSnapshot]]:
    target = _collect_one(data.target_url, "target", fetch_html)
    competitors = [
        _collect_one(url, "competitor", fetch_html)
        for url in data.competitor_urls
    ]
    return target, competitors


def scrape_jd_snapshots(
    data: CompetitorInput,
    headful: bool = True,
    wait_seconds: float = 2,
    user_data_dir: str | Path | None = None,
    browser_path: str | Path | None = None,
    login_first: bool = False,
    manual_wait_seconds: float = 180,
    browser_backend: BrowserBackend = "drissionpage",
) -> tuple[JdProductSnapshot, list[JdProductSnapshot]]:
    with create_html_fetcher(
        browser_backend,
        headful=headful,
        wait_seconds=wait_seconds,
        user_data_dir=user_data_dir,
        browser_path=browser_path,
        login_first=login_first,
        manual_wait_seconds=manual_wait_seconds,
    ) as fetcher:
        return collect_jd_snapshots(data, fetcher.fetch)


def create_html_fetcher(
    browser_backend: BrowserBackend,
    headful: bool = True,
    wait_seconds: float = 2,
    user_data_dir: str | Path | None = None,
    browser_path: str | Path | None = None,
    login_first: bool = False,
    manual_wait_seconds: float = 180,
) -> "DrissionPageHtmlFetcher | PlaywrightHtmlFetcher":
    if browser_backend == "drissionpage":
        return DrissionPageHtmlFetcher(
            headful=headful,
            wait_seconds=wait_seconds,
            user_data_dir=user_data_dir,
            browser_path=browser_path,
            login_first=login_first,
            manual_wait_seconds=manual_wait_seconds,
        )
    if browser_backend == "playwright":
        return PlaywrightHtmlFetcher(
            headful=headful,
            wait_seconds=wait_seconds,
            user_data_dir=user_data_dir,
            browser_path=browser_path,
            login_first=login_first,
            manual_wait_seconds=manual_wait_seconds,
        )
    raise ValueError("browser_backend must be drissionpage or playwright")


class DrissionPageHtmlFetcher:
    def __init__(
        self,
        headful: bool = True,
        wait_seconds: float = 2,
        user_data_dir: str | Path | None = None,
        browser_path: str | Path | None = None,
        login_first: bool = False,
        manual_wait_seconds: float = 180,
    ) -> None:
        self._headful = headful
        self._wait_seconds = wait_seconds
        self._user_data_dir = Path(user_data_dir) if user_data_dir else None
        self._browser_path = Path(browser_path) if browser_path else None
        self._login_first = login_first
        self._manual_wait_seconds = manual_wait_seconds
        self._page = None

    def __enter__(self) -> "DrissionPageHtmlFetcher":
        from DrissionPage import ChromiumOptions, ChromiumPage

        options = ChromiumOptions()
        options.headless(not self._headful)
        options.set_user_agent(_USER_AGENT)
        if self._browser_path:
            options.set_browser_path(str(self._browser_path))
        if self._user_data_dir:
            self._user_data_dir.mkdir(parents=True, exist_ok=True)
            options.set_user_data_path(str(self._user_data_dir))
        self._page = ChromiumPage(options)
        if self._login_first:
            self.prepare_login()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._page:
            self._page.quit()

    def prepare_login(self) -> None:
        if self._page is None:
            raise RuntimeError("DrissionPage browser is not initialized")
        if not self._headful:
            raise RuntimeError("登录预热需要可见浏览器，请使用 --headful true")
        self._page.get("https://www.jd.com/")
        _wait_for_manual_confirmation(
            "请在浏览器中完成京东登录或安全验证，完成后等待程序继续。",
            self._manual_wait_seconds,
        )

    def fetch(self, url: str) -> str:
        if self._page is None:
            raise RuntimeError("DrissionPage browser is not initialized")
        self._page.get(url)
        if self._wait_seconds:
            time.sleep(self._wait_seconds)
        if _looks_like_verification_page(self._page):
            if not self._headful:
                raise RuntimeError("页面出现京东验证，请使用 --headful true 在可见浏览器中人工通过验证后继续")
            _wait_for_manual_verification(self._page, url, self._manual_wait_seconds)
        return _page_html(self._page)

    def fetch_search_result(
        self,
        url: str,
        listen_pattern: str,
        listen_timeout: float,
        listen_count: int,
    ) -> SearchFetchResult:
        if self._page is None:
            raise RuntimeError("DrissionPage browser is not initialized")
        listener = getattr(self._page, "listen", None)
        if listener is None:
            raise RuntimeError("当前 DrissionPage 页面不支持网络监听")

        listener.start(listen_pattern)
        try:
            self._page.get(url)
            packets = _wait_listen_packets(listener, listen_timeout, listen_count)
            if self._wait_seconds:
                time.sleep(self._wait_seconds)
            if _looks_like_verification_page(self._page):
                if not self._headful:
                    raise RuntimeError("页面出现京东验证，请使用 --headful true 在可见浏览器中人工通过验证后继续")
                _wait_for_manual_verification(self._page, url, self._manual_wait_seconds)
            return SearchFetchResult(
                api_bodies=[_packet_response_body(packet) for packet in packets],
                html=_page_html(self._page),
            )
        finally:
            pause = getattr(listener, "pause", None)
            if callable(pause):
                pause(clear=True)


class PlaywrightHtmlFetcher:
    def __init__(
        self,
        headful: bool = True,
        wait_seconds: float = 2,
        user_data_dir: str | Path | None = None,
        browser_path: str | Path | None = None,
        login_first: bool = False,
        manual_wait_seconds: float = 180,
    ) -> None:
        self._headful = headful
        self._wait_seconds = wait_seconds
        self._user_data_dir = Path(user_data_dir) if user_data_dir else None
        self._browser_path = Path(browser_path) if browser_path else None
        self._login_first = login_first
        self._manual_wait_seconds = manual_wait_seconds
        self._playwright = None
        self._browser = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def __enter__(self) -> "PlaywrightHtmlFetcher":
        self._playwright = sync_playwright().start()
        browser_options = _browser_options()
        launch_options = {"executable_path": str(self._browser_path)} if self._browser_path else {}
        if self._user_data_dir:
            self._user_data_dir.mkdir(parents=True, exist_ok=True)
            self._context = self._playwright.chromium.launch_persistent_context(
                str(self._user_data_dir),
                headless=not self._headful,
                **launch_options,
                **browser_options,
            )
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        else:
            self._browser = self._playwright.chromium.launch(headless=not self._headful, **launch_options)
            self._context = self._browser.new_context(**browser_options)
            self._page = self._context.new_page()
        if self._login_first:
            self.prepare_login()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def prepare_login(self) -> None:
        if self._page is None:
            raise RuntimeError("Playwright browser is not initialized")
        if not self._headful:
            raise RuntimeError("登录预热需要可见浏览器，请使用 --headful true")
        self._page.goto("https://www.jd.com/", wait_until="domcontentloaded", timeout=60_000)
        _wait_for_manual_confirmation(
            "请在浏览器中完成京东登录或安全验证，完成后等待程序继续。",
            self._manual_wait_seconds,
        )

    def fetch(self, url: str) -> str:
        if self._page is None:
            raise RuntimeError("Playwright browser is not initialized")
        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as exc:  # noqa: BLE001 - manual login redirects can interrupt navigation.
            if not self._headful:
                raise
            _wait_for_manual_confirmation(
                f"页面跳转打断了自动导航，请在浏览器中完成当前登录/验证后回到终端等待继续。原始错误：{exc}",
                self._manual_wait_seconds,
            )
            self._page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        if self._wait_seconds:
            time.sleep(self._wait_seconds)
        if _looks_like_verification_page(self._page):
            if not self._headful:
                raise RuntimeError("页面出现京东验证，请使用 --headful true 在可见浏览器中人工通过验证后继续")
            _wait_for_manual_verification(self._page, url, self._manual_wait_seconds)
        return self._page.content()

    def fetch_search_result(
        self,
        url: str,
        listen_pattern: str,
        listen_timeout: float,
        listen_count: int,
    ) -> SearchFetchResult:
        return SearchFetchResult(api_bodies=[], html=self.fetch(url))


def _collect_one(url: str, role: str, fetch_html: HtmlFetcher) -> JdProductSnapshot:
    try:
        html = fetch_html(url)
        return parse_jd_product_html(html, url=url, role=role)
    except Exception as exc:  # noqa: BLE001 - each URL should retain its own failure reason.
        return failed_product_snapshot(url, role=role, error_message=str(exc))


def _looks_like_verification_page(page: Page) -> bool:
    title = _page_title(page)
    body = _page_body_text(page)
    markers = ["京东验证", "安全验证", "滑块", "验证码", "passport.jd.com"]
    haystack = f"{title}\n{body}\n{_page_url(page)}"
    return any(marker in haystack for marker in markers)


def _wait_for_manual_verification(page: Page, url: str, manual_wait_seconds: float) -> None:
    _wait_for_manual_action(
        page,
        f"页面出现京东验证，请在浏览器中完成验证后回到终端按 Enter 继续：{url}",
        manual_wait_seconds,
    )
    wait_for_load_state = getattr(page, "wait_for_load_state", None)
    if callable(wait_for_load_state):
        wait_for_load_state("domcontentloaded", timeout=60_000)
    if _looks_like_verification_page(page):
        raise RuntimeError("人工验证后仍停留在京东验证页")


def _wait_for_manual_action(page: Page, message: str, manual_wait_seconds: float) -> None:
    print(message)
    if not sys.stdin.isatty():
        print(f"当前终端无法接收 Enter，将等待 {int(manual_wait_seconds)} 秒供你在浏览器中操作。")
        deadline = time.time() + manual_wait_seconds
        while time.time() < deadline:
            time.sleep(2)
            if not _looks_like_verification_page(page):
                return
        raise RuntimeError("等待人工登录或验证超时，请在本地交互式终端运行，或调大 --manual-wait-seconds")
    try:
        input()
    except EOFError as exc:
        print(f"当前终端无法接收 Enter，将继续等待 {int(manual_wait_seconds)} 秒供你在浏览器中操作。")
        deadline = time.time() + manual_wait_seconds
        while time.time() < deadline:
            time.sleep(2)
            if not _looks_like_verification_page(page):
                return
        raise RuntimeError("等待人工登录或验证超时，请确认浏览器中已完成京东验证") from exc


def _wait_for_manual_confirmation(message: str, manual_wait_seconds: float) -> None:
    print(message)
    if not sys.stdin.isatty():
        print(f"当前终端无法接收 Enter，将等待 {int(manual_wait_seconds)} 秒供你在浏览器中操作。")
        time.sleep(manual_wait_seconds)
        return
    try:
        input()
    except EOFError as exc:
        print(f"当前终端无法接收 Enter，将等待 {int(manual_wait_seconds)} 秒供你在浏览器中操作。")
        time.sleep(manual_wait_seconds)


def _wait_listen_packets(listener: object, listen_timeout: float, listen_count: int) -> list[object]:
    wait = getattr(listener, "wait")
    packets = wait(count=listen_count, timeout=listen_timeout, fit_count=False)
    if packets is False or packets is None:
        return []
    if isinstance(packets, list):
        return packets
    return [packets]


def _packet_response_body(packet: object) -> Any:
    response = getattr(packet, "response", None)
    return getattr(response, "body", None)


def _browser_options() -> dict:
    return {
        "viewport": {"width": 1366, "height": 900},
        "user_agent": _USER_AGENT,
    }


def _page_title(page: object) -> str:
    title = getattr(page, "title", "")
    return title() if callable(title) else str(title or "")


def _page_url(page: object) -> str:
    url = getattr(page, "url", "")
    return url() if callable(url) else str(url or "")


def _page_html(page: object) -> str:
    html = getattr(page, "html", "")
    return html() if callable(html) else str(html or "")


def _page_body_text(page: object) -> str:
    locator = getattr(page, "locator", None)
    if callable(locator):
        try:
            body = page.locator("body")
            return body.inner_text(timeout=5_000) if body.count() else ""
        except Exception:
            return ""
    return _page_html(page)


_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
