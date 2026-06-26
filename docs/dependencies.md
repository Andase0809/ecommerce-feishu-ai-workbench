# 依赖与集成

## 飞书开放平台

- 文档：https://open.larksuite.com/
- SDK：https://github.com/larksuite/oapi-sdk-python

用途：

- 创建 Base
- 创建数据表和字段
- 写入记录
- 创建视图和筛选
- 上传附件图片

## DeepSeek

- 文档：https://api-docs.deepseek.com/

用途：

- 商品分类建议
- 商品定位建议
- 标签建议
- 运营建议
- 审核提示

默认配置：

```text
AI_PROVIDER=deepseek
AI_MODEL=deepseek-v4-flash
AI_BASE_URL=https://api.deepseek.com
```

## OpenAI-compatible 接口

`AIClient` 使用 Chat Completions 风格接口：

```text
POST {base_url}/chat/completions
Authorization: Bearer {api_key}
```

只要服务兼容该接口，就可以通过 `AI_PROVIDER=custom` 和 `AI_BASE_URL` 接入。

## HTML 解析与浏览器辅助

- Beautiful Soup：https://www.crummy.com/software/BeautifulSoup/
- Playwright：https://playwright.dev/python/
- DrissionPage：https://www.drissionpage.cn/

用途：

- 使用 fixture 测试页面字段解析。
- 在人工可控流程中整理商品公开字段。
- 保留失败状态，避免单条失败中断整批流程。

## 测试

- pytest：https://docs.pytest.org/

测试覆盖输入校验、字段映射、模型解析、失败降级、飞书 schema 和页面解析。
