# 开源参考与使用边界

## 使用原则

本项目允许参考开源项目的功能拆分、README 结构、交互方式、字段设计和技术选型，但不直接复制开源项目代码后改名包装。

如确实使用任何开源代码片段、模板、Prompt 片段或示例结构，需要：

- 检查许可证。
- 在 README 或文档中注明来源。
- 保留许可证要求。
- 做业务场景改造和二次实现。

## 产品思路参考

### Nutlope/description-generator

- 链接：https://github.com/Nutlope/description-generator
- 可参考方向：商品信息生成商品描述的产品思路。
- 本项目借鉴方式：只参考“输入商品信息后生成描述”的功能拆分，不复制代码。

### mayashavin/product-info-ai-generator

- 链接：https://github.com/mayashavin/product-info-ai-generator
- 可参考方向：从商品信息生成标题、描述、标签的输出结构。
- 本项目借鉴方式：参考标题、描述、标签的字段拆分，不复制代码。

### iamarunbrahma/product-description-generator

- 链接：https://github.com/iamarunbrahma/product-description-generator
- 可参考方向：面向 SEO 商品描述的字段设计。
- 本项目借鉴方式：参考标题、描述、SEO 字段的组织思路，不复制代码。

## 技术依赖参考

### 飞书/Lark 开放平台

- 链接：https://open.larksuite.com/
- 用途：多维表格 Base、数据表、字段、记录、附件和视图创建。
- 使用方式：调用官方 OpenAPI，不复制第三方实现。

### larksuite/oapi-sdk-python

- 链接：https://github.com/larksuite/oapi-sdk-python
- 用途：飞书开放平台 Python SDK。
- 使用方式：作为依赖安装，通过官方 SDK 和 HTTP API 调用。

### Beautiful Soup

- 链接：https://www.crummy.com/software/BeautifulSoup/
- 用途：HTML fixture 解析测试。

### Playwright for Python

- 链接：https://playwright.dev/python/
- 用途：可选浏览器自动化能力和人工可控的数据整理流程。

### DrissionPage

- 链接：https://www.drissionpage.cn/
- 用途：可选浏览器自动化能力和本地调试流程。

### DeepSeek API

- 链接：https://api-docs.deepseek.com/
- 用途：可选 AI 分类建议、商品定位、标签建议和运营建议生成。
- 使用方式：通过用户配置的 API Key 调用 OpenAI-compatible 接口；未配置时项目保持规则化分析流程。

## 本项目差异化

为了避免变成普通商品描述生成器，本项目突出：

- 飞书工作台：自动创建 Base、字段、记录、附件、URL、视图和筛选。
- 商品运营视角：商品主图、价格带、商品定位、SKU 变体、标签和审核状态。
- 竞品分析视角：竞品共性、主商品差异点、机会方向和人工审核清单。
- 发布边界：只提交脱敏或构造样例，不提交真实凭证、真实运行结果和本地缓存。
