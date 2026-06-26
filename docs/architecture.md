# 架构说明

## 模块边界

项目按数据流拆分为四层：

1. 输入与采集层

- `models.py`：商品输入和输出模型。
- `competitor_models.py`：竞品输入、商品快照、竞品分析输出模型。
- `jd_parser.py`：商品页 HTML 字段解析。
- `jd_scraper.py` / `jd_discovery.py`：浏览器辅助采集与候选 URL 发现。

2. 分析层

- `generator.py`：根据商品字段生成标题、卖点、平台文案、标签和审核项。
- `competitor_analysis.py`：根据主商品和竞品快照生成共性、差异点、机会方向和风险提示。
- `ai_client.py`：封装 DeepSeek、OpenAI 和兼容接口的请求、鉴权、JSON 响应解析和错误处理。
- `ai_enrichment.py`：把店铺商品记录转换为模型输入，并将模型输出写回结构化 payload。

3. 飞书 schema 层

- `feishu_schema.py`：通用表结构、字段类型、视图、筛选和附件上传计划。
- `shop_workbench_schema.py`：商品运营工作台表结构。
- `jd_feishu_schema.py`：竞品分析工作台表结构。

4. 同步层

- `feishu_client.py`：飞书 Base、表、字段、记录、视图和附件上传。
- `main.py`：CLI 入口、参数解析、dry-run、飞书同步和错误提示。

## 关键抽象

### TablePayload

`TablePayload` 是飞书同步的中间表示。上层模块只需要描述表名、字段、记录、视图和附件上传计划，不直接依赖飞书 HTTP API。

### ViewPayload / ViewFilter

视图和筛选条件通过结构化对象描述，方便在不同表结构中复用。

### AIConfig / AIClient

模型服务统一为 OpenAI-compatible 调用方式。`AIClient` 只负责调用、解析和失败包装，不直接处理飞书字段。

### Workbench Output

商品、竞品和模型输出先保存为本地 JSON，再进入飞书同步层。这样可以在飞书失败时保留可复查结果。

## 失败处理

- 模型调用失败：保留规则分析结果，写入 AI 失败状态和错误摘要。
- 图片上传失败：保留图片 URL，写入图片上传状态，不中断其他记录。
- 飞书同步失败：保留本地 JSON 输出，由 CLI 返回明确错误；临时网络错误、限流类返回会自动重试。
- 批量写入：记录按批次提交，字段和视图元数据按页读取，避免单次请求承载过多数据。
- 采集失败：单条记录标记为失败，整体流程继续。
