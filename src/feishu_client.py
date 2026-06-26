from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

import lark_oapi as lark

from .feishu_schema import TablePayload


class FeishuError(RuntimeError):
    pass


@dataclass(frozen=True)
class FeishuConfig:
    app_id: str
    app_secret: str

    @classmethod
    def from_env(cls, app_id: str | None, app_secret: str | None) -> "FeishuConfig":
        if not app_id or not app_secret:
            raise FeishuError("缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET，请先配置 .env")
        return cls(app_id=app_id, app_secret=app_secret)


@dataclass(frozen=True)
class FeishuSyncResult:
    app_token: str
    base_name: str
    tables: dict[str, str]


class FeishuBitableClient:
    def __init__(self, config: FeishuConfig) -> None:
        self._client = lark.Client.builder().app_id(config.app_id).app_secret(config.app_secret).build()

    def sync(self, table_payloads: list[TablePayload], base_name: str | None = None) -> FeishuSyncResult:
        name = base_name or f"电商商品信息生成助手-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        app_token = self._create_base(name)
        tables: dict[str, str] = {}
        for payload in table_payloads:
            table_id = self._create_table(app_token, payload)
            tables[payload.name] = table_id
            if payload.records:
                self._batch_create_records(app_token, table_id, payload.records)
        return FeishuSyncResult(app_token=app_token, base_name=name, tables=tables)

    def _create_base(self, name: str) -> str:
        response = self._post("/open-apis/bitable/v1/apps", {"name": name})
        app = response.get("data", {}).get("app", {})
        app_token = app.get("app_token") or response.get("data", {}).get("app_token")
        if not app_token:
            raise FeishuError(f"创建多维表格成功但未返回 app_token：{response}")
        return app_token

    def _create_table(self, app_token: str, payload: TablePayload) -> str:
        body = {
            "table": {
                "name": payload.name,
                "default_view_name": "默认表格视图",
                "fields": payload.fields,
            }
        }
        response = self._post(f"/open-apis/bitable/v1/apps/{app_token}/tables", body)
        table = response.get("data", {}).get("table", {})
        table_id = table.get("table_id") or response.get("data", {}).get("table_id")
        if not table_id:
            raise FeishuError(f"创建数据表成功但未返回 table_id：{response}")
        return table_id

    def _batch_create_records(self, app_token: str, table_id: str, records: list[dict]) -> None:
        response = self._post(
            f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
            {"records": records},
        )
        created = response.get("data", {}).get("records", [])
        if len(created) != len(records):
            raise FeishuError(f"写入记录数量不一致，期望 {len(records)} 条，实际返回 {len(created)} 条")

    def _post(self, uri: str, body: dict) -> dict:
        request = (
            lark.BaseRequest.builder()
            .http_method(lark.HttpMethod.POST)
            .uri(uri)
            .token_types({lark.AccessTokenType.TENANT})
            .body(body)
            .build()
        )
        response = self._client.request(request)
        payload = _decode_response(response)
        if payload.get("code", 0) != 0:
            raise FeishuError(f"飞书 OpenAPI 调用失败：{payload}")
        return payload


def _decode_response(response: object) -> dict:
    raw = getattr(response, "raw", None)
    content = getattr(raw, "content", None)
    if content is None:
        raise FeishuError(f"飞书 SDK 返回格式异常：{response!r}")
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    return json.loads(content)
