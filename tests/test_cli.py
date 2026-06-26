from src.main import parse_competitor_args, parse_discovery_args, parse_shop_workbench_args


def test_parse_competitor_args_defaults_to_local_url_file() -> None:
    args = parse_competitor_args([])

    assert args.input == "samples\\jd-lamp-urls.local.json" or args.input == "samples/jd-lamp-urls.local.json"
    assert args.output == "outputs\\jd-lamp-competitor-analysis.json" or args.output == "outputs/jd-lamp-competitor-analysis.json"
    assert args.dry_run == "true"
    assert args.headful == "true"
    assert args.user_data_dir == ".browser\\drission-jd-profile" or args.user_data_dir == ".browser/drission-jd-profile"
    assert args.login_first == "false"
    assert args.browser_backend == "drissionpage"
    assert args.browser == "auto"
    assert args.browser_path == ""


def test_parse_competitor_args_accepts_explicit_values() -> None:
    args = parse_competitor_args(
        [
            "--input",
            "samples/custom.local.json",
            "--dry-run",
            "false",
            "--headful",
            "false",
            "--wait-seconds",
            "0",
        ]
    )

    assert args.input == "samples/custom.local.json"
    assert args.dry_run == "false"
    assert args.headful == "false"
    assert args.wait_seconds == "0"


def test_parse_discovery_args_defaults_to_opple_lamp_price_band() -> None:
    args = parse_discovery_args([])

    assert args.keyword == "欧普照明 台灯"
    assert args.target_brand == "欧普"
    assert args.search_url == ""
    assert args.price_min == "80"
    assert args.price_max == "160"
    assert args.headful == "true"
    assert args.user_data_dir == ".browser\\drission-jd-profile" or args.user_data_dir == ".browser/drission-jd-profile"
    assert args.login_first == "false"
    assert args.browser_backend == "drissionpage"
    assert args.browser == "auto"
    assert args.browser_path == ""
    assert args.discovery_mode == "auto"
    assert args.listen_pattern == "api?appid=search-pc-java"
    assert args.listen_timeout == "10"
    assert args.listen_count == "8"


def test_parse_discovery_args_accepts_search_url() -> None:
    args = parse_discovery_args(["--search-url", "https://search.jd.com/Search?keyword=%E5%8F%B0%E7%81%AF"])

    assert args.search_url == "https://search.jd.com/Search?keyword=%E5%8F%B0%E7%81%AF"


def test_parse_discovery_args_accepts_listen_mode() -> None:
    args = parse_discovery_args(
        [
            "--discovery-mode",
            "listen",
            "--listen-pattern",
            "api?appid=search-pc-java&t",
            "--listen-timeout",
            "6",
            "--listen-count",
            "4",
        ]
    )

    assert args.discovery_mode == "listen"
    assert args.listen_pattern == "api?appid=search-pc-java&t"
    assert args.listen_timeout == "6"
    assert args.listen_count == "4"


def test_parse_shop_workbench_args_defaults_to_demo_input() -> None:
    args = parse_shop_workbench_args([])

    assert args.input == "samples\\shop-workbench.example.json" or args.input == "samples/shop-workbench.example.json"
    assert args.dry_run == "true"
    assert args.upload_images == "true"
    assert args.base_name == ""


def test_parse_shop_workbench_args_accepts_visual_sync_options() -> None:
    args = parse_shop_workbench_args(
        [
            "--input",
            "cleaned.local.json",
            "--dry-run",
            "false",
            "--upload-images",
            "false",
            "--base-name",
            "重设计测试",
        ]
    )

    assert args.input == "cleaned.local.json"
    assert args.dry_run == "false"
    assert args.upload_images == "false"
    assert args.base_name == "重设计测试"
