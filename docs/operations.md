# 运行与同步策略

## 本地执行

所有外部集成命令都支持 dry-run。dry-run 会生成本地结构化输出和飞书表结构预览，不调用飞书 OpenAPI，也不上传图片。

```powershell
python -m src.main sync-shop-workbench --input samples/shop-workbench.example.json --dry-run true
```

## 飞书同步

飞书同步通过 `TablePayload` 统一描述表、字段、记录、视图和附件上传计划。同步流程按以下顺序执行：

1. 创建 Base。
2. 创建数据表与字段。
3. 分页读取字段元数据，用于视图筛选和隐藏字段配置。
4. 分批写入记录。
5. 分页读取已有视图，复用同名视图或创建新视图。
6. 写入视图属性。

## 重试与降级

- 飞书 OpenAPI 请求遇到限流、临时错误或网络超时时会自动重试。
- 记录写入按批次提交，单批返回数量不一致时会返回明确错误。
- 图片下载和附件上传失败时，记录会保留图片 URL 与上传状态，其他表记录继续处理。
- 模型服务失败时，系统保留规则分析结果，并写入失败状态和错误摘要。

## 自动验证

仓库包含 GitHub Actions 工作流，推送和 Pull Request 会在 Python 3.11 与 3.12 上运行：

```powershell
python -m pytest -q --basetemp .pytest-tmp
```
