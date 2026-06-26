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

## 开源参考

本项目只参考下列项目的产品思路、字段拆分和 README 组织方式，不复制其代码：

- [Nutlope/description-generator](https://github.com/Nutlope/description-generator)
- [mayashavin/product-info-ai-generator](https://github.com/mayashavin/product-info-ai-generator)
- [iamarunbrahma/product-description-generator](https://github.com/iamarunbrahma/product-description-generator)

飞书能力使用官方开放平台和 Python SDK：

- [飞书/Lark 开放平台](https://open.larksuite.com/)
- [larksuite/oapi-sdk-python](https://github.com/larksuite/oapi-sdk-python)

## 简历草稿

项目完成并可展示后，可作为草稿表达：

```text
电商商品信息生成助手｜个人AI项目

- 围绕电商商品上架和内容种草场景，设计商品信息生成流程，输入商品名称、品类、目标人群、核心参数和平台风格后，输出商品标题、核心卖点、平台口吻文案、商品标签和人工检查清单。
- 使用 Python CLI 读取 demo 商品数据，并通过飞书 OpenAPI 自动创建多维表格，将商品主表和不同平台内容表结构化沉淀，辅助运营新人完成初步内容整理。
- 项目包含样例商品数据、运行说明、输出示例和开源参考说明，可迁移至电商运营、商品运营、内容运营和 AI 赋能业务场景。
```
