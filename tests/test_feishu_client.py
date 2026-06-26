import pytest

from src.feishu_client import FeishuBitableClient, FeishuError, _filter_value, _view_property
from src.feishu_schema import AttachmentUpload, TablePayload, ViewFilter, ViewPayload


def test_view_property_maps_hidden_fields_and_filters_to_field_ids() -> None:
    view = ViewPayload(
        name="待竞品采集",
        hidden_fields=["备注"],
        filters=[ViewFilter("竞品分析状态", "is", "竞品未采集")],
    )

    result = _view_property(view, {"备注": "fld_note", "竞品分析状态": "fld_status"})

    assert result["hidden_fields"] == ["fld_note"]
    assert result["filter_info"]["conjunction"] == "and"
    assert result["filter_info"]["conditions"] == [
        {"field_id": "fld_status", "operator": "is", "value": '["竞品未采集"]'}
    ]


def test_view_property_skips_hidden_fields_for_gallery_and_kanban_views() -> None:
    gallery = ViewPayload(name="商品图库", view_type="gallery", hidden_fields=["备注"])
    kanban = ViewPayload(name="竞品任务看板", view_type="kanban", hidden_fields=["备注"])

    assert _view_property(gallery, {"备注": "fld_note"}) == {}
    assert _view_property(kanban, {"备注": "fld_note"}) == {}


def test_filter_value_accepts_scalar_and_list() -> None:
    assert _filter_value("待审核") == '["待审核"]'
    assert _filter_value(["低价", "中价"]) == '["低价", "中价"]'


def test_filter_value_uses_single_select_option_id_when_available() -> None:
    field = {
        "field_id": "fld_status",
        "type": 3,
        "property": {"options": [{"id": "opt_waiting", "name": "待审核"}]},
    }

    assert _filter_value("待审核", field) == '["opt_waiting"]'


def test_prepare_records_uploads_attachments_when_enabled() -> None:
    client = FeishuBitableClient.__new__(FeishuBitableClient)
    uploaded: list[tuple[str, str, str]] = []

    def fake_upload(app_token: str, source_url: str, file_name: str) -> str:
        uploaded.append((app_token, source_url, file_name))
        return "file_token_001"

    client._upload_attachment_from_url = fake_upload  # type: ignore[method-assign]
    payload = TablePayload(
        name="店铺主要商品表",
        fields=[],
        records=[{"fields": {"商品名称": "护眼灯", "商品主图": None, "图片上传状态": "待上传"}}],
        attachment_uploads=[
            AttachmentUpload(
                record_index=0,
                attachment_field="商品主图",
                source_url="https://img.example.com/main.jpg",
                file_name="main.jpg",
                fallback_status_field="图片上传状态",
            )
        ],
    )

    records = client._prepare_records("app_token", payload, upload_attachments=True)

    assert uploaded == [("app_token", "https://img.example.com/main.jpg", "main.jpg")]
    assert records[0]["fields"]["商品主图"] == [{"file_token": "file_token_001"}]
    assert records[0]["fields"]["图片上传状态"] == "已上传"


def test_prepare_records_downgrades_attachment_upload_failure() -> None:
    client = FeishuBitableClient.__new__(FeishuBitableClient)

    def fake_upload(app_token: str, source_url: str, file_name: str) -> str:
        raise RuntimeError("no permission")

    client._upload_attachment_from_url = fake_upload  # type: ignore[method-assign]
    payload = TablePayload(
        name="店铺主要商品表",
        fields=[],
        records=[{"fields": {"商品名称": "护眼灯", "商品主图": None, "图片上传状态": "待上传"}}],
        attachment_uploads=[
            AttachmentUpload(
                record_index=0,
                attachment_field="商品主图",
                source_url="https://img.example.com/main.jpg",
                file_name="main.jpg",
                fallback_status_field="图片上传状态",
            )
        ],
    )

    records = client._prepare_records("app_token", payload, upload_attachments=True)

    assert "商品主图" not in records[0]["fields"]
    assert records[0]["fields"]["图片上传状态"].startswith("上传失败")


def test_create_views_reuses_existing_view_before_creating_new_one() -> None:
    client = FeishuBitableClient.__new__(FeishuBitableClient)
    created_posts: list[dict] = []
    patches: list[tuple[str, dict]] = []

    def fake_list_view_ids(app_token: str, table_id: str) -> dict[str, str]:
        return {"商品清单": "vew_default"}

    def fake_post(uri: str, body: dict) -> dict:
        created_posts.append(body)
        return {"data": {"view": {"view_id": "vew_new"}}}

    def fake_patch(uri: str, body: dict) -> dict:
        patches.append((uri, body))
        return {"code": 0}

    client._list_view_ids = fake_list_view_ids  # type: ignore[method-assign]
    client._post = fake_post  # type: ignore[method-assign]
    client._patch = fake_patch  # type: ignore[method-assign]

    result = client._create_views(
        "app_token",
        "table_id",
        [
            ViewPayload(name="商品清单", hidden_fields=["备注"]),
            ViewPayload(name="商品图库", view_type="gallery"),
        ],
        {"备注": "fld_note"},
    )

    assert result == {"商品清单": "vew_default", "商品图库": "vew_new"}
    assert created_posts == [{"view_name": "商品图库", "view_type": "gallery"}]
    assert patches[0][0].endswith("/views/vew_default")
    assert patches[0][1] == {"property": {"hidden_fields": ["fld_note"]}}


def test_batch_create_records_splits_large_payloads() -> None:
    client = FeishuBitableClient.__new__(FeishuBitableClient)
    client._record_batch_size = 2
    batch_sizes: list[int] = []

    def fake_post(uri: str, body: dict) -> dict:
        assert uri.endswith("/records/batch_create")
        batch_sizes.append(len(body["records"]))
        return {"data": {"records": [{"record_id": f"rec_{index}"} for index, _ in enumerate(body["records"])]}}

    client._post = fake_post  # type: ignore[method-assign]

    client._batch_create_records("app_token", "table_id", [{"fields": {"序号": index}} for index in range(5)])

    assert batch_sizes == [2, 2, 1]


def test_list_field_metadata_reads_all_pages() -> None:
    client = FeishuBitableClient.__new__(FeishuBitableClient)
    requested_uris: list[str] = []

    def fake_get(uri: str) -> dict:
        requested_uris.append(uri)
        if "page_token=next_page" in uri:
            return {
                "data": {
                    "items": [{"field_name": "价格", "field_id": "fld_price"}],
                    "has_more": False,
                }
            }
        return {
            "data": {
                "items": [{"field_name": "商品名", "field_id": "fld_name"}],
                "has_more": True,
                "page_token": "next_page",
            }
        }

    client._get = fake_get  # type: ignore[method-assign]

    fields = client._list_field_metadata("app_token", "table_id")

    assert list(fields) == ["商品名", "价格"]
    assert requested_uris[0].endswith("/fields?page_size=100")
    assert requested_uris[1].endswith("/fields?page_size=100&page_token=next_page")


def test_list_view_ids_reads_all_pages() -> None:
    client = FeishuBitableClient.__new__(FeishuBitableClient)

    def fake_get(uri: str) -> dict:
        if "page_token=next_page" in uri:
            return {
                "data": {
                    "items": [{"view_name": "商品图库", "view_id": "vew_gallery"}],
                    "has_more": False,
                }
            }
        return {
            "data": {
                "items": [{"view_name": "商品清单", "view_id": "vew_grid"}],
                "has_more": True,
                "page_token": "next_page",
            }
        }

    client._get = fake_get  # type: ignore[method-assign]

    assert client._list_view_ids("app_token", "table_id") == {
        "商品清单": "vew_grid",
        "商品图库": "vew_gallery",
    }


def test_request_retries_retryable_payload_before_success() -> None:
    client = FeishuBitableClient.__new__(FeishuBitableClient)
    client._request_max_attempts = 3
    client._request_backoff_seconds = 0
    calls: list[str] = []

    def fake_request_once(method: object, uri: str, body: dict | None = None) -> dict:
        calls.append(uri)
        if len(calls) == 1:
            return {"code": 99991663, "msg": "rate limit"}
        return {"code": 0, "data": {"ok": True}}

    client._request_once = fake_request_once  # type: ignore[method-assign]

    assert client._request(object(), "/open-apis/test") == {"code": 0, "data": {"ok": True}}
    assert calls == ["/open-apis/test", "/open-apis/test"]


def test_request_retries_transient_exception_before_success() -> None:
    client = FeishuBitableClient.__new__(FeishuBitableClient)
    client._request_max_attempts = 3
    client._request_backoff_seconds = 0
    calls = 0

    def fake_request_once(method: object, uri: str, body: dict | None = None) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("temporary timeout")
        return {"code": 0, "data": {"ok": True}}

    client._request_once = fake_request_once  # type: ignore[method-assign]

    assert client._request(object(), "/open-apis/test")["code"] == 0
    assert calls == 2


def test_request_fails_fast_for_non_retryable_payload() -> None:
    client = FeishuBitableClient.__new__(FeishuBitableClient)
    client._request_max_attempts = 3
    client._request_backoff_seconds = 0
    calls = 0

    def fake_request_once(method: object, uri: str, body: dict | None = None) -> dict:
        nonlocal calls
        calls += 1
        return {"code": 1254001, "msg": "invalid parameter"}

    client._request_once = fake_request_once  # type: ignore[method-assign]

    with pytest.raises(FeishuError, match="飞书 OpenAPI 调用失败"):
        client._request(object(), "/open-apis/test")
    assert calls == 1
