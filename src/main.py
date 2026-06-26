from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from .feishu_client import FeishuBitableClient, FeishuConfig, FeishuError
from .feishu_schema import build_table_payloads
from .generator import find_forbidden_terms, generate_outputs
from .models import load_products, save_outputs


DEFAULT_INPUT = Path("samples/products.json")
DEFAULT_OUTPUT = Path("outputs/generated-products.json")


def main() -> int:
    args = parse_args()
    load_dotenv()

    input_path = Path(args.input)
    output_path = Path(args.output)
    dry_run = _parse_bool(args.dry_run)

    products = load_products(input_path)
    outputs = generate_outputs(products)
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="电商商品信息生成助手 v0")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="商品输入 JSON 路径")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="本地输出 JSON 路径")
    parser.add_argument("--dry-run", default="true", help="是否只生成本地结果并预览飞书表结构")
    return parser.parse_args()


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.lower() in {"1", "true", "yes", "y", "on"}


def _preview(table_payloads: list) -> list[dict]:
    return [
        {
            "table_name": payload.name,
            "field_names": [field["field_name"] for field in payload.fields],
            "record_count": len(payload.records),
        }
        for payload in table_payloads
    ]


if __name__ == "__main__":
    raise SystemExit(main())
