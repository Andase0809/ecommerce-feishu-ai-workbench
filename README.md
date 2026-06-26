# 电商商品信息生成助手

这是一个面向电商运营新人和 AI 赋能运营场景的小型工具。它读取 demo 商品基础信息，基于规则化 Prompt 模板生成商品标题、核心卖点、平台口吻文案、标签和人工审核清单，并可自动创建飞书多维表格进行整理。

> 数据说明：本项目所有商品均为 demo 自造数据，不包含真实商家、真实销量、真实转化率或真实商品运营数据。

## 功能

- 读取 JSON 商品输入。
- 为小红书、抖音、电商平台生成差异化文案。
- 输出本地 JSON，便于调试和作品集留档。
- 通过飞书 OpenAPI 自动创建多维表格：商品主表、小红书内容表、抖音内容表、电商平台内容表。
- 为每个平台内容写入“待审核 / 需修改 / 已通过”审核状态，体现 AI 输出后的人工复核流程。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.main --input samples/products.json --dry-run true
```

dry-run 会生成本地文件 `outputs/generated-products.json`，并预览即将创建的飞书表结构，不会调用飞书 API。

## 同步到飞书多维表格

1. 在飞书开放平台创建企业自建应用。
2. 为应用开通多维表格相关权限，并完成权限发布。
3. 复制 `.env.example` 为 `.env`，填入应用凭证：

```text
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

4. 运行同步命令：

```powershell
python -m src.main --input samples/products.json --dry-run false
```

程序会在“我的空间”根目录创建一个名为“电商商品信息生成助手-日期时间”的多维表格，并写入 4 张数据表。

## v0.1：电商商品数据飞书工作台

v0.1 在原有商品文案生成流程之外，新增“采集数据清洗 + AI 规则分析 + 飞书多维表格同步”的数据化工作台能力。它的核心不是绑定某个平台或某个品类，而是把已经采集并清洗好的商品数据，整理为企业可查看、可筛选、可对比、可跟进的飞书表格视图。

当前仓库使用“京东台灯 / 100 元左右商品”作为演示样例，用来验证商品字段抽取、竞品对比、分析结论和飞书同步链路。后续可以替换为其他平台、其他品类或企业内部已整理的数据源。

先安装 Playwright 浏览器：

```powershell
python -m playwright install chromium
```

如果要使用当前演示样例，可以先运行自动发现：

```powershell
python -m src.main discover-competitors --keyword "欧普照明 台灯" --target-brand "欧普" --price-min 80 --price-max 160 --headful true --login-first true --user-data-dir .browser/drission-jd-profile
```

程序会把发现到的 1 个主商品 URL 和 10 个竞品 URL 写入 `samples/jd-lamp-urls.local.json`。默认发现模式为 `--discovery-mode auto`：DrissionPage 会先监听搜索页正常加载出的公开接口响应，优先从接口 JSON 中解析商品候选；如果未解析到商品，再回退到渲染 HTML 解析。监听必须在打开搜索页前启动，程序已按这个顺序处理。

如果页面需要登录或安全确认，程序会保留浏览器窗口，等待用户在浏览器中完成操作后继续处理可见的公开数据。默认浏览器后端为 DrissionPage，`.browser/drission-jd-profile` 会保存本地浏览器登录态，后续批量采集可复用，不会提交到 Git。

排查搜索发现时可以强制指定模式：

```powershell
python -m src.main discover-competitors --discovery-mode listen --listen-pattern "api?appid=search-pc-java&t" --headful true
python -m src.main discover-competitors --discovery-mode html --headful true
```

浏览器路径默认自动检测本机 Chrome / Edge。也可以显式选择：

```powershell
python -m src.main discover-competitors --browser chrome --headful true
python -m src.main discover-competitors --browser edge --headful true
```

如果自动检测失败，可以直接传浏览器可执行文件路径：

```powershell
python -m src.main discover-competitors --browser-path "C:\Program Files\Google\Chrome\Application\chrome.exe" --headful true
```

也可以复制 URL 模板并手动填入真实链接：

```powershell
Copy-Item samples/jd-lamp-urls.example.json samples/jd-lamp-urls.local.json
```

`samples/jd-lamp-urls.local.json` 不会提交到 Git。文件结构如下：

```json
{
  "keyword": "台灯",
  "target_url": "https://item.jd.com/100000000001.html",
  "competitor_urls": [
    "https://item.jd.com/100000000002.html"
  ]
}
```

真实运行时 `competitor_urls` 需要填写 10 个京东商品页 URL。

运行 dry-run：

```powershell
python -m src.main analyze-competitors --input samples/jd-lamp-urls.local.json --dry-run true --headful true --user-data-dir .browser/drission-jd-profile
```

如果页面需要人工确认，程序会保留浏览器窗口，等待用户在浏览器中完成后继续。dry-run 会生成本地文件 `outputs/jd-lamp-competitor-analysis.json`，但不会调用飞书 API。

同步到飞书：

```powershell
python -m src.main analyze-competitors --input samples/jd-lamp-urls.local.json --dry-run false --headful true --user-data-dir .browser/drission-jd-profile
```

如果 DrissionPage 后端在当前机器上不可用，可以临时回退到 Playwright：

```powershell
python -m src.main discover-competitors --browser-backend playwright --headful true --login-first true
```

程序会创建名为“电商商品数据工作台-日期时间”的 Base，当前演示样例中包含：

- 本店商品表：保存主商品公开信息，并提供“查看竞品分析”入口。
- 竞品商品表：保存 10 个竞品的公开字段、采集状态和失败原因。
- 竞品对比分析表：保存竞品共性、主商品差异点、机会方向、风险提醒和人工审核清单。
- 运营建议表：保存标题方向、详情页方向和平台内容方向，默认“待审核”。

v0.1 采集字段包括商品名、URL、sku_id、品牌、店铺、价格文本、价格带、主图 URL、详情参数、卖点摘要、评价量文本和采集时间。演示样例中还会抽取台灯相关参数；迁移到其他品类时，可以替换为对应品类的核心参数字段。

### 飞书视觉工作台优化

为了让飞书多维表格更适合展示和业务查看，项目新增了“清洗商品数据 -> 飞书视觉工作台”的同步命令。它会新建一套重设计版 Base，不覆盖旧 Base，并自动生成：

- 运营总览表：商品数、SKU 变体数、待竞品采集数、价格带分布、商品定位分布、审核状态分布。
- 店铺主要商品表：商品主图附件、商品链接、价格数值、价格带、商品定位、SKU 变体状态、竞品分析状态。
- SKU款式变体表：变体图片、款式、价格、评价量文本、变体链接和关联系列品。
- 竞品任务/分析表：竞品未采集时只保留任务流和空状态，不虚构竞品结论。
- 运营建议表：等待竞品数据补充后再生成建议，默认待审核。

先运行 dry-run 预览字段、视图和图片上传计划：

```powershell
python -m src.main sync-shop-workbench --input samples/shop-workbench.example.json --dry-run true --upload-images true
```

同步到飞书时会创建新的重设计版 Base：

```powershell
python -m src.main sync-shop-workbench --input samples/shop-workbench.example.json --dry-run false --upload-images true
```

真实店铺清洗数据仍建议放在本地 `*.local.json` 或 `.browser/` 目录，不提交到 Git。当前本机公牛样例可用本地脚本运行：

```powershell
python .browser/local_tools/sync_redesigned_feishu_shop_products.py --upload-images true
```

图片字段采用飞书附件能力：程序会临时读取公开图片 URL 并上传到当前 Base，成功后在画册视图中显示为图片；如果图片上传权限不足或单张图片失败，会保留图片 URL 和上传状态，不中断整批同步。飞书应用除多维表格编辑权限外，还需要具备上传图片和附件到云文档的相关权限。

表格默认视图会把“商品识别卡片、商品主图、彩色标签、商品定位、价格带、价格”等高频查看字段放在前面。飞书 OpenAPI 当前不稳定支持行高持久化；如果多行标题或多行标签仍被压缩，可以在飞书表格顶部点击 `行高`，切换为较高行高后截图展示。

## 输入字段

`samples/products.json` 是 JSON 数组，每个商品包含：

- `product_id`：demo 商品 ID，用于各表之间文本关联。
- `product_name`：商品名称。
- `category`：商品品类。
- `price_range`：价格带。
- `target_user`：目标用户。
- `core_features`：核心参数或卖点。
- `usage_scenarios`：使用场景。
- `platform_style`：平台列表，支持“小红书”“抖音”“电商平台”。

## 输出结构

本地 JSON 会保留以下内容：

- 商品基础信息。
- 每个平台的标题候选、核心卖点、平台文案、标签。
- 人工检查清单。

飞书多维表格包含：

- 商品主表：集中保存输入字段和人工检查清单。
- 小红书内容表：偏体验分享和种草表达。
- 抖音内容表：偏短视频口播节奏。
- 电商平台内容表：偏清晰成交和上架说明。

## 展示建议

完成飞书同步后，可以在 README 或作品集中放两类截图：

- 终端运行成功截图：展示一条命令完成生成和同步。
- 飞书多维表格截图：展示商品主表和平台内容表的字段结构。

当前仓库保留 `outputs/sample-generated-products.json` 作为无密钥环境下的样例输出。

## 真实性边界

- 不虚构真实商家、真实 GMV、真实转化率或真实上线效果。
- 不把未完成项目写入正式简历。
- 文案生成规则禁止主动输出销量第一、全网第一、转化率等无法证明的营销表达。
- 飞书同步失败时，本地 JSON 会保留，便于排查。
- v0.1 只处理用户可正常访问或已经整理好的商品数据，运行过程遵守平台访问规则。
- v0.1 不采集评论正文，不下载商品图片，只保存公开页面中的图片 URL。
- 真实平台采集结果只用于本地演示和飞书工作台；GitHub/作品集展示时需要脱敏或遮挡店铺名、商品名、图片和 URL。

## 开源参考

本项目只参考下列项目的产品思路、字段拆分和 README 组织方式，不复制其代码：

- [Nutlope/description-generator](https://github.com/Nutlope/description-generator)
- [mayashavin/product-info-ai-generator](https://github.com/mayashavin/product-info-ai-generator)
- [iamarunbrahma/product-description-generator](https://github.com/iamarunbrahma/product-description-generator)

飞书能力使用官方开放平台和 Python SDK：

- [飞书/Lark 开放平台](https://open.larksuite.com/)
- [larksuite/oapi-sdk-python](https://github.com/larksuite/oapi-sdk-python)

v0.1 使用的网页解析与浏览器自动化依赖：

- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)
- [Playwright for Python](https://playwright.dev/python/)
- [DrissionPage](https://www.drissionpage.cn/)

## 简历草稿

项目完成并可展示后，可作为草稿表达：

```text
电商商品信息生成助手｜个人AI项目

- 围绕电商商品上架和内容种草场景，设计商品信息生成流程，输入商品名称、品类、目标人群、核心参数和平台风格后，输出商品标题、核心卖点、平台口吻文案、商品标签和人工检查清单。
- 使用 Python CLI 读取商品样例或采集清洗后的商品数据，并通过飞书 OpenAPI 自动创建多维表格，将商品基础信息、竞品对比、AI 分析结论和运营建议结构化沉淀。
- 项目强调将分散商品数据转化为企业可查看、可筛选、可复盘的数据工作台，可迁移至电商运营、商品运营、内容运营、数据运营和 AI 赋能业务场景。
```
