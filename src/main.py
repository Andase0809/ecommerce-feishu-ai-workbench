from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from .ai_client import AIClient, AIConfig, AIConfigError
from .ai_enrichment import enrich_shop_workbench_payload
from .browser_config import resolve_browser_path
from .competitor_analysis import analyze_workbench, find_forbidden_terms_in_workbench
from .competitor_models import load_competitor_input, save_workbench_output
from .feishu_client import FeishuBitableClient, FeishuConfig, FeishuError
from .feishu_schema import build_table_payloads
from .generator import find_forbidden_terms, generate_outputs
from .jd_discovery import discover_competitor_urls
from .jd_feishu_schema import build_competitor_table_payloads
from .jd_scraper import scrape_jd_snapshots
from .models import load_products, save_outputs
from .shop_workbench_schema import (
    build_shop_workbench_table_payloads,
    load_shop_workbench_payload,
    redesigned_base_name,
)


DEFAULT_INPUT = Path("samples/products.json")
DEFAULT_OUTPUT = Path("outputs/generated-products.json")
DEFAULT_COMPETITOR_INPUT = Path("samples/jd-lamp-urls.local.json")
DEFAULT_COMPETITOR_OUTPUT = Path("outputs/jd-lamp-competitor-analysis.json")
DEFAULT_JD_USER_DATA_DIR = Path(".browser/drission-jd-profile")
DEFAULT_SHOP_WORKBENCH_INPUT = Path("samples/shop-workbench.example.json")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    load_dotenv()

    if argv and argv[0] == "analyze-competitors":
        return run_competitor_analysis(parse_competitor_args(argv[1:]))
    if argv and argv[0] == "discover-competitors":
        return run_competitor_discovery(parse_discovery_args(argv[1:]))
    if argv and argv[0] == "sync-shop-workbench":
        return run_shop_workbench_sync(parse_shop_workbench_args(argv[1:]))
    return run_content_generation(parse_args(argv))


def run_content_generation(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    output_path = Path(args.output)
    dry_run = _parse_bool(args.dry_run)
    ai_client = _build_ai_client(args)

    products = load_products(input_path)
    outputs = generate_outputs(products, ai_client=ai_client)
    save_outputs(output_path, outputs)

    forbidden_terms = find_forbidden_terms(outputs)
    if forbidden_terms:
        raise ValueError(f"生成内容包含禁止虚构或高风险词：{', '.join(forbidden_terms)}")

    table_payloads = build_table_payloads(outputs)
    print(f"已生成 {len(outputs)} 个商品结果：{output_path}")
    print(f"将创建 {len(table_payloads)} 张飞书数据表：{', '.join(item.name for item in table_payloads)}")

    if dry_run:
        print("dry-run 模式：未调用飞书 API。")
        print(json.dumps(_preview(table_payloads), ensure_ascii=False, indent=2))
        return 0

    try:
        config = FeishuConfig.from_env(os.getenv("FEISHU_APP_ID"), os.getenv("FEISHU_APP_SECRET"))
        result = FeishuBitableClient(config).sync(table_payloads)
    except FeishuError as exc:
        print(f"飞书同步失败，本地 JSON 已保留：{output_path}")
        raise SystemExit(str(exc)) from exc

    print(f"飞书多维表格创建成功：{result.base_name}")
    print(f"app_token: {result.app_token}")
    for table_name, table_id in result.tables.items():
        print(f"- {table_name}: {table_id}")
    return 0


def run_competitor_analysis(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    output_path = Path(args.output)
    dry_run = _parse_bool(args.dry_run)
    headful = _parse_bool(args.headful)
    browser_path = _resolve_browser_path_for_cli(args)
    ai_client = _build_ai_client(args)

    competitor_input = load_competitor_input(input_path)
    target, competitors = scrape_jd_snapshots(
        competitor_input,
        headful=headful,
        wait_seconds=float(args.wait_seconds),
        user_data_dir=args.user_data_dir,
        browser_path=browser_path,
        login_first=_parse_bool(args.login_first),
        manual_wait_seconds=float(args.manual_wait_seconds),
        browser_backend=args.browser_backend,
    )
    workbench = analyze_workbench(competitor_input.keyword, target, competitors, ai_client=ai_client)
    save_workbench_output(output_path, workbench)

    forbidden_terms = find_forbidden_terms_in_workbench(workbench)
    if forbidden_terms:
        raise ValueError(f"竞品分析内容包含禁止虚构或高风险词：{', '.join(forbidden_terms)}")

    table_payloads = build_competitor_table_payloads(workbench)
    print(f"已生成京东{competitor_input.keyword}竞品工作台结果：{output_path}")
    print(f"有效竞品数：{workbench.analysis.competitor_count} / {len(workbench.competitors)}")
    print(f"将创建 {len(table_payloads)} 张飞书数据表：{', '.join(item.name for item in table_payloads)}")

    if dry_run:
        print("dry-run 模式：未调用飞书 API。")
        print(json.dumps(_preview(table_payloads), ensure_ascii=False, indent=2))
        return 0

    try:
        config = FeishuConfig.from_env(os.getenv("FEISHU_APP_ID"), os.getenv("FEISHU_APP_SECRET"))
        base_name = f"京东{competitor_input.keyword}竞品工作台-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        result = FeishuBitableClient(config).sync(table_payloads, base_name=base_name, upload_attachments=True)
    except FeishuError as exc:
        print(f"飞书同步失败，本地 JSON 已保留：{output_path}")
        raise SystemExit(str(exc)) from exc

    print(f"飞书竞品工作台创建成功：{result.base_name}")
    print(f"app_token: {result.app_token}")
    for table_name, table_id in result.tables.items():
        print(f"- {table_name}: {table_id}")
    return 0


def run_competitor_discovery(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    headful = _parse_bool(args.headful)
    browser_path = _resolve_browser_path_for_cli(args)
    try:
        data = discover_competitor_urls(
            keyword=args.keyword,
            target_brand=args.target_brand,
            price_min=float(args.price_min),
            price_max=float(args.price_max),
            output_path=output_path,
            search_url=args.search_url or None,
            headful=headful,
            wait_seconds=float(args.wait_seconds),
            user_data_dir=args.user_data_dir,
            browser_path=browser_path,
            login_first=_parse_bool(args.login_first),
            manual_wait_seconds=float(args.manual_wait_seconds),
            browser_backend=args.browser_backend,
            discovery_mode=args.discovery_mode,
            listen_pattern=args.listen_pattern,
            listen_timeout=float(args.listen_timeout),
            listen_count=int(args.listen_count),
        )
    except Exception as exc:  # noqa: BLE001 - CLI should show a concise operator-facing error.
        print(f"竞品URL自动发现失败：{exc}")
        print("建议使用可见浏览器重试：")
        print(
            "python -m src.main discover-competitors "
            f"--keyword \"{args.keyword}\" --target-brand \"{args.target_brand}\" "
            f"--price-min {args.price_min} --price-max {args.price_max} "
            f"--headful true --login-first true --user-data-dir {args.user_data_dir}"
        )
        return 1
    print(f"已发现京东{args.keyword}候选链接并写入：{output_path}")
    print(f"主商品URL：{data.target_url}")
    print(f"竞品URL数量：{len(data.competitor_urls)}")
    print("下一步可运行：")
    print(f"python -m src.main analyze-competitors --input {output_path} --dry-run true --headful true")
    return 0


def run_shop_workbench_sync(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    dry_run = _parse_bool(args.dry_run)
    upload_images = _parse_bool(args.upload_images)
    payload = load_shop_workbench_payload(input_path)
    ai_client = _build_ai_client(args)
    if ai_client is not None:
        payload = enrich_shop_workbench_payload(payload, ai_client)
    table_payloads = build_shop_workbench_table_payloads(payload)
    base_name = args.base_name or f"{redesigned_base_name(payload)}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    print(f"已读取清洗商品数据：{input_path}")
    print(f"将创建飞书 Base：{base_name}")
    print(f"将创建 {len(table_payloads)} 张飞书数据表：{', '.join(item.name for item in table_payloads)}")

    if dry_run:
        print("dry-run 模式：未调用飞书 API。")
        print(json.dumps(_preview(table_payloads), ensure_ascii=False, indent=2))
        return 0

    try:
        config = FeishuConfig.from_env(os.getenv("FEISHU_APP_ID"), os.getenv("FEISHU_APP_SECRET"))
        result = FeishuBitableClient(config).sync(
            table_payloads,
            base_name=base_name,
            upload_attachments=upload_images,
        )
    except FeishuError as exc:
        print(f"飞书视觉工作台同步失败，输入数据仍保留：{input_path}")
        raise SystemExit(str(exc)) from exc

    print(f"飞书视觉工作台创建成功：{result.base_name}")
    print(f"app_token: {result.app_token}")
    for table_name, table_id in result.tables.items():
        print(f"- {table_name}: {table_id}")
        for view_name, view_id in result.views.get(table_name, {}).items():
            print(f"  - 视图 {view_name}: {view_id}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="电商商品信息生成助手")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="商品输入 JSON 路径")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="本地输出 JSON 路径")
    parser.add_argument("--dry-run", default="true", help="是否只生成本地结果并预览飞书表结构")
    _add_ai_args(parser)
    return parser.parse_args(argv)


def parse_competitor_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="京东台灯竞品工作台")
    parser.add_argument("--input", default=str(DEFAULT_COMPETITOR_INPUT), help="京东商品 URL 输入 JSON 路径")
    parser.add_argument("--output", default=str(DEFAULT_COMPETITOR_OUTPUT), help="本地竞品工作台输出 JSON 路径")
    parser.add_argument("--dry-run", default="true", help="是否只生成本地结果并预览飞书表结构")
    parser.add_argument("--headful", default="true", help="是否打开可见浏览器，便于人工通过京东验证")
    parser.add_argument("--wait-seconds", default="2", help="每个商品页打开后等待秒数")
    parser.add_argument("--user-data-dir", default=str(DEFAULT_JD_USER_DATA_DIR), help="保存京东登录态的浏览器资料目录")
    parser.add_argument("--login-first", default="false", help="采集前先打开京东首页，等待人工登录或验证")
    parser.add_argument("--manual-wait-seconds", default="180", help="非交互终端等待人工登录或验证的秒数")
    parser.add_argument("--browser-backend", default="drissionpage", choices=["drissionpage", "playwright"], help="浏览器自动化后端")
    parser.add_argument("--browser", default="auto", choices=["auto", "chrome", "edge"], help="自动选择本机浏览器")
    parser.add_argument("--browser-path", default="", help="可选：显式指定浏览器可执行文件路径")
    _add_ai_args(parser)
    return parser.parse_args(argv)


def parse_discovery_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="京东台灯竞品 URL 自动发现")
    parser.add_argument("--keyword", default="欧普照明 台灯", help="京东搜索关键词")
    parser.add_argument("--search-url", default="", help="可选：直接使用浏览器复制的京东搜索结果页完整 URL")
    parser.add_argument("--target-brand", default="欧普", help="优先作为主商品的品牌关键词")
    parser.add_argument("--price-min", default="80", help="竞品价格区间下限")
    parser.add_argument("--price-max", default="160", help="竞品价格区间上限")
    parser.add_argument("--output", default=str(DEFAULT_COMPETITOR_INPUT), help="输出 URL 清单 JSON 路径")
    parser.add_argument("--headful", default="true", help="是否打开可见浏览器，便于人工通过京东验证")
    parser.add_argument("--wait-seconds", default="2", help="搜索页打开后等待秒数")
    parser.add_argument("--user-data-dir", default=str(DEFAULT_JD_USER_DATA_DIR), help="保存京东登录态的浏览器资料目录")
    parser.add_argument("--login-first", default="false", help="搜索前先打开京东首页，等待人工登录或验证")
    parser.add_argument("--manual-wait-seconds", default="180", help="非交互终端等待人工登录或验证的秒数")
    parser.add_argument("--browser-backend", default="drissionpage", choices=["drissionpage", "playwright"], help="浏览器自动化后端")
    parser.add_argument("--browser", default="auto", choices=["auto", "chrome", "edge"], help="自动选择本机浏览器")
    parser.add_argument("--browser-path", default="", help="可选：显式指定浏览器可执行文件路径")
    parser.add_argument("--discovery-mode", default="auto", choices=["auto", "listen", "html"], help="搜索发现模式：auto 为监听优先、HTML兜底")
    parser.add_argument("--listen-pattern", default="api?appid=search-pc-java", help="DrissionPage 网络监听目标片段")
    parser.add_argument("--listen-timeout", default="10", help="等待京东搜索接口响应的秒数")
    parser.add_argument("--listen-count", default="8", help="最多等待的搜索接口响应包数量")
    return parser.parse_args(argv)


def parse_shop_workbench_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="同步清洗商品数据到飞书视觉工作台")
    parser.add_argument("--input", default=str(DEFAULT_SHOP_WORKBENCH_INPUT), help="清洗后的店铺商品工作台 JSON 路径")
    parser.add_argument("--dry-run", default="true", help="是否只预览表结构、视图和图片上传计划")
    parser.add_argument("--upload-images", default="true", help="是否将公开图片临时上传为飞书附件字段")
    parser.add_argument("--base-name", default="", help="可选：指定新建飞书 Base 名称")
    _add_ai_args(parser)
    return parser.parse_args(argv)


def _add_ai_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ai-provider", default="", help="可选 AI 辅助：off/openai/deepseek/custom")
    parser.add_argument("--ai-model", default="", help="可选：覆盖 AI_MODEL")
    parser.add_argument("--ai-base-url", default="", help="可选：覆盖 AI_BASE_URL，custom provider 必填")


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.lower() in {"1", "true", "yes", "y", "on"}


def _preview(table_payloads: list) -> list[dict]:
    return [
        {
            "table_name": payload.name,
            "fields": [
                {
                    "name": field["field_name"],
                    "type": field["type"],
                    "ui_type": field.get("ui_type", ""),
                }
                for field in payload.fields
            ],
            "record_count": len(payload.records),
            "default_view_name": getattr(payload, "default_view_name", "默认表格视图"),
            "views": [
                {
                    "name": view.name,
                    "type": view.view_type,
                    "hidden_fields": view.hidden_fields,
                    "filters": [
                        {"field_name": item.field_name, "operator": item.operator, "value": item.value}
                        for item in view.filters
                    ],
                }
                for view in getattr(payload, "views", [])
            ],
            "attachment_upload_count": len(getattr(payload, "attachment_uploads", [])),
        }
        for payload in table_payloads
    ]


def _build_ai_client(args: argparse.Namespace) -> AIClient | None:
    try:
        config = AIConfig.from_env(
            provider=getattr(args, "ai_provider", "off"),
            model=getattr(args, "ai_model", ""),
            base_url=getattr(args, "ai_base_url", ""),
        )
    except AIConfigError as exc:
        raise SystemExit(str(exc)) from exc
    if not config.enabled:
        return None
    print(f"AI辅助已启用：{config.provider} / {config.model}")
    return AIClient(config)


def _resolve_browser_path_for_cli(args: argparse.Namespace) -> str | None:
    result = resolve_browser_path(args.browser, args.browser_path)
    if result.path:
        print(f"浏览器路径：{result.path}（{result.browser}, {result.source}）")
        return str(result.path)
    print("未检测到 Chrome/Edge 浏览器路径，将使用浏览器后端默认配置。")
    return None


if __name__ == "__main__":
    raise SystemExit(main())
