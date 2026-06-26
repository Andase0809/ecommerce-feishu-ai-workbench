from src.competitor_models import CompetitorInput
from src.jd_scraper import DrissionPageHtmlFetcher, PlaywrightHtmlFetcher, collect_jd_snapshots, create_html_fetcher


HTML = """
<html>
  <body>
    <div class="sku-name">明澈 国AA级护眼学习台灯</div>
    <ul class="parameter2">
      <li>品牌：明澈</li>
      <li>照度：国AA级</li>
    </ul>
  </body>
</html>
"""


def test_collect_jd_snapshots_keeps_failed_competitor_records() -> None:
    data = CompetitorInput(
        keyword="台灯",
        target_url="https://item.jd.com/100000000001.html",
        competitor_urls=[
            f"https://item.jd.com/1000000000{index:02d}.html"
            for index in range(2, 12)
        ],
    )

    def fetch_html(url: str) -> str:
        if url.endswith("005.html"):
            raise RuntimeError("京东验证未通过")
        return HTML

    target, competitors = collect_jd_snapshots(data, fetch_html)

    assert target.scrape_status == "成功"
    assert len(competitors) == 10
    failed = [item for item in competitors if item.scrape_status == "失败"]
    assert len(failed) == 1
    assert failed[0].error_message == "京东验证未通过"


def test_headless_fetcher_reports_verification_without_manual_prompt(monkeypatch) -> None:
    fetcher = PlaywrightHtmlFetcher(headful=False, wait_seconds=0)

    class FakePage:
        url = "https://search.jd.com/Search?keyword=台灯"

        def goto(self, *args, **kwargs) -> None:
            return None

        def content(self) -> str:
            return ""

    monkeypatch.setattr("src.jd_scraper._looks_like_verification_page", lambda page: True)
    fetcher._page = FakePage()

    try:
        fetcher.fetch("https://search.jd.com/Search?keyword=台灯")
    except RuntimeError as exc:
        assert "--headful true" in str(exc)
    else:
        raise AssertionError("expected verification RuntimeError")


def test_create_html_fetcher_defaults_to_drissionpage_backend() -> None:
    fetcher = create_html_fetcher("drissionpage", user_data_dir=".browser/test-profile", browser_path="C:/Browser/chrome.exe")

    assert isinstance(fetcher, DrissionPageHtmlFetcher)
    assert str(fetcher._browser_path).endswith("chrome.exe")


def test_create_html_fetcher_keeps_playwright_backend_available() -> None:
    fetcher = create_html_fetcher("playwright", user_data_dir=".browser/test-profile")

    assert isinstance(fetcher, PlaywrightHtmlFetcher)


def test_drissionpage_fetch_search_result_listens_before_navigation(monkeypatch) -> None:
    events: list[str] = []

    class FakeResponse:
        body = {"data": {"wareInfo": []}}

    class FakePacket:
        response = FakeResponse()

    class FakeListener:
        def start(self, target: str) -> None:
            events.append(f"listen:{target}")

        def wait(self, count: int, timeout: float, fit_count: bool):
            events.append(f"wait:{count}:{timeout}:{fit_count}")
            return [FakePacket()]

        def pause(self, clear: bool) -> None:
            events.append(f"pause:{clear}")

    class FakePage:
        listen = FakeListener()
        html = "<html></html>"

        def get(self, url: str) -> None:
            events.append(f"get:{url}")

    monkeypatch.setattr("src.jd_scraper._looks_like_verification_page", lambda page: False)
    fetcher = DrissionPageHtmlFetcher(headful=True, wait_seconds=0)
    fetcher._page = FakePage()

    result = fetcher.fetch_search_result(
        "https://search.jd.com/Search?keyword=台灯",
        listen_pattern="api?appid=search-pc-java",
        listen_timeout=5,
        listen_count=3,
    )

    assert events[:2] == ["listen:api?appid=search-pc-java", "get:https://search.jd.com/Search?keyword=台灯"]
    assert events[-1] == "pause:True"
    assert result.api_bodies == [{"data": {"wareInfo": []}}]
    assert result.html == "<html></html>"
