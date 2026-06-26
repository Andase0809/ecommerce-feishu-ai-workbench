from __future__ import annotations

import json
import mimetypes
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import lark_oapi as lark

from .feishu_schema import TablePayload, ViewFilter, ViewPayload


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
    views: dict[str, dict[str, str]]


class FeishuBitableClient:
    def __init__(self, config: FeishuConfig) -> None:
        self._config = config
        self._client = lark.Client.builder().app_id(config.app_id).app_secret(config.app_secret).build()
        self._tenant_access_token: str | None = None

    def sync(
        self,
        table_payloads: list[TablePayload],
        base_name: str | None = None,
        upload_attachments: bool = False,
    ) -> FeishuSyncResult:
        name = base_name or f"电商商品信息生成助手-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        app_token = self._create_base(name)
        tables: dict[str, str] = {}
        views: dict[str, dict[str, str]] = {}
        for payload in table_payloads:
            table_id = self._create_table(app_token, payload)
            tables[payload.name] = table_id
            field_metadata = self._list_field_metadata(app_token, table_id)
            if payload.records:
                records = self._prepare_records(app_token, payload, upload_attachments=upload_attachments)
                self._batch_create_records(app_token, table_id, records)
            if payload.views:
                views[payload.name] = self._create_views(app_token, table_id, payload.views, field_metadata)
        return FeishuSyncResult(app_token=app_token, base_name=name, tables=tables, views=views)

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
                "default_view_name": payload.default_view_name,
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

    def _list_field_metadata(self, app_token: str, table_id: str) -> dict[str, dict]:
        response = self._get(f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields?page_size=100")
        fields = response.get("data", {}).get("items", [])
        return {field["field_name"]: field for field in fields if field.get("field_name") and field.get("field_id")}

    def _list_view_ids(self, app_token: str, table_id: str) -> dict[str, str]:
        response = self._get(f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/views?page_size=100")
        views = response.get("data", {}).get("items", [])
        return {view["view_name"]: view["view_id"] for view in views if view.get("view_name") and view.get("view_id")}

    def _create_views(
        self,
        app_token: str,
        table_id: str,
        view_payloads: list[ViewPayload],
        field_metadata: dict[str, dict],
    ) -> dict[str, str]:
        created: dict[str, str] = {}
        existing_views = self._list_view_ids(app_token, table_id)
        for view in view_payloads:
            view_id = existing_views.get(view.name)
            if not view_id:
                response = self._post(
                    f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/views",
                    {"view_name": view.name, "view_type": view.view_type},
                )
                view_data = response.get("data", {}).get("view", {})
                view_id = view_data.get("view_id") or response.get("data", {}).get("view_id")
                if not view_id:
                    raise FeishuError(f"创建视图成功但未返回 view_id：{response}")
                existing_views[view.name] = view_id
            created[view.name] = view_id
            property_payload = _view_property(view, field_metadata)
            if property_payload:
                self._patch(
                    f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/views/{view_id}",
                    {"property": property_payload},
                )
        return created

    def _prepare_records(self, app_token: str, payload: TablePayload, upload_attachments: bool) -> list[dict]:
        records = json.loads(json.dumps(payload.records, ensure_ascii=False))
        for upload in payload.attachment_uploads:
            if upload.record_index >= len(records):
                continue
            fields = records[upload.record_index].setdefault("fields", {})
            if not upload.source_url:
                if upload.fallback_status_field:
                    fields[upload.fallback_status_field] = "无图片URL"
                continue
            if not upload_attachments:
                if upload.fallback_status_field:
                    fields[upload.fallback_status_field] = "未上传"
                continue
            try:
                token = self._upload_attachment_from_url(app_token, upload.source_url, upload.file_name)
            except Exception as exc:  # noqa: BLE001 - attachment upload is best-effort by design.
                if upload.fallback_status_field:
                    fields[upload.fallback_status_field] = f"上传失败：{exc}"
                continue
            fields[upload.attachment_field] = [{"file_token": token}]
            if upload.fallback_status_field:
                fields[upload.fallback_status_field] = "已上传"
        for record in records:
            fields = record.get("fields", {})
            record["fields"] = {key: value for key, value in fields.items() if value is not None}
        return records

    def _upload_attachment_from_url(self, app_token: str, source_url: str, file_name: str) -> str:
        content, content_type = _download_file(source_url)
        safe_name = _safe_file_name(file_name, source_url, content_type)
        token = self._get_tenant_access_token()
        boundary = f"----codex{uuid.uuid4().hex}"
        body = _multipart_body(
            boundary,
            fields={
                "file_name": safe_name,
                "parent_type": "bitable_image",
                "parent_node": app_token,
                "size": str(len(content)),
            },
            file_name=safe_name,
            file_content=content,
            content_type=content_type,
        )
        request = Request(
            "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        response = _open_json(request)
        if response.get("code", 0) != 0:
            raise FeishuError(f"飞书素材上传失败：{response}")
        file_token = response.get("data", {}).get("file_token")
        if not file_token:
            raise FeishuError(f"飞书素材上传成功但未返回 file_token：{response}")
        return file_token

    def _get_tenant_access_token(self) -> str:
        if self._tenant_access_token:
            return self._tenant_access_token
        body = json.dumps(
            {"app_id": self._config.app_id, "app_secret": self._config.app_secret},
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        response = _open_json(request)
        if response.get("code", 0) != 0:
            raise FeishuError(f"获取 tenant_access_token 失败：{response}")
        token = response.get("tenant_access_token")
        if not token:
            raise FeishuError(f"获取 tenant_access_token 成功但未返回 token：{response}")
        self._tenant_access_token = token
        return token

    def _get(self, uri: str) -> dict:
        return self._request(lark.HttpMethod.GET, uri)

    def _patch(self, uri: str, body: dict) -> dict:
        return self._request(lark.HttpMethod.PATCH, uri, body)

    def _post(self, uri: str, body: dict) -> dict:
        return self._request(lark.HttpMethod.POST, uri, body)

    def _request(self, method: lark.HttpMethod, uri: str, body: dict | None = None) -> dict:
        builder = lark.BaseRequest.builder().http_method(method).uri(uri).token_types({lark.AccessTokenType.TENANT})
        if body is not None:
            builder.body(body)
        request = builder.build()
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


def _view_property(view: ViewPayload, field_metadata: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    hidden_field_ids = [
        _field_id(field_metadata[name])
        for name in view.hidden_fields
        if _supports_hidden_fields(view) and name in field_metadata
    ]
    if hidden_field_ids:
        result["hidden_fields"] = hidden_field_ids
    if view.filters:
        conditions = [_filter_condition(item, field_metadata) for item in view.filters if item.field_name in field_metadata]
        if conditions:
            result["filter_info"] = {"conditions": conditions, "conjunction": view.conjunction}
    return result


def _supports_hidden_fields(view: ViewPayload) -> bool:
    return view.view_type not in {"gallery", "kanban"}


def _filter_condition(item: ViewFilter, field_metadata: dict[str, Any]) -> dict[str, str]:
    field = field_metadata[item.field_name]
    return {
        "field_id": _field_id(field),
        "operator": item.operator,
        "value": _filter_value(item.value, field),
    }


def _field_id(field: str | dict) -> str:
    return field if isinstance(field, str) else str(field["field_id"])


def _filter_value(value: str | list[str] | int | float | bool, field: dict | str | None = None) -> str:
    if isinstance(field, dict) and field.get("type") in {3, 4}:
        option_ids = _select_option_ids(value, field)
        if option_ids:
            return json.dumps(option_ids, ensure_ascii=False)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps([value], ensure_ascii=False)


def _select_option_ids(value: str | list[str] | int | float | bool, field: dict) -> list[str]:
    values = [str(item) for item in value] if isinstance(value, list) else [str(value)]
    options = field.get("property", {}).get("options", [])
    option_ids: list[str] = []
    for item in values:
        option = next((option for option in options if option.get("name") == item), None)
        option_id = option.get("id") or option.get("option_id") if option else None
        if option_id:
            option_ids.append(str(option_id))
    return option_ids


def _download_file(source_url: str) -> tuple[bytes, str]:
    url = f"https:{source_url}" if source_url.startswith("//") else source_url
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - user-provided public image URLs are expected input.
            content = response.read(20 * 1024 * 1024 + 1)
            content_type = response.headers.get_content_type() or "application/octet-stream"
    except URLError as exc:
        raise FeishuError(f"下载图片失败：{exc}") from exc
    if len(content) > 20 * 1024 * 1024:
        raise FeishuError("图片超过 20MB")
    return content, content_type


def _safe_file_name(file_name: str, source_url: str, content_type: str) -> str:
    stem = Path(file_name).stem or "product-image"
    suffix = Path(file_name).suffix
    if not suffix:
        parsed_suffix = Path(urlparse(source_url).path).suffix
        suffix = parsed_suffix or mimetypes.guess_extension(content_type) or ".jpg"
    return f"{stem[:80]}{suffix}"


def _multipart_body(
    boundary: str,
    fields: dict[str, str],
    file_name: str,
    file_content: bytes,
    content_type: str,
) -> bytes:
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                f"{value}\r\n".encode("utf-8"),
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'.encode("utf-8"),
            f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
            file_content,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return b"".join(chunks)


def _open_json(request: Request) -> dict:
    with urlopen(request, timeout=30) as response:  # noqa: S310 - Feishu OpenAPI endpoint.
        content = response.read().decode("utf-8")
    return json.loads(content)
