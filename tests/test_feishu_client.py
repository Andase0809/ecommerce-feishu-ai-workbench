from src.feishu_client import FeishuBitableClient, _filter_value, _view_property
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
