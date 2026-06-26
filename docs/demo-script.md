# 演示脚本

这份脚本用于 GitHub、作品集或面试展示。演示时建议使用脱敏样例数据，不展示真实 `.env`、真实飞书 `app_token`、真实浏览器缓存或未脱敏采集结果。

## 1. 项目介绍

可以这样开场：

> 这是一个电商商品数据分析与飞书自动化工作台。我把商品信息生成、商品数据清洗、竞品分析和飞书多维表格同步做成一个 Python CLI。重点不是展示爬取能力，而是展示如何把清洗后的商品数据变成企业可协作、可筛选、可审核的运营工作台。

## 2. 本地验证

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q --basetemp .pytest-tmp
```

展示重点：

- 测试覆盖输入校验、规则分析、飞书字段映射和视图配置。
- `dry-run` 可以在没有飞书凭证时验证输出结构。

## 3. 商品信息生成 v0

```powershell
python -m src.main --input samples/products.json --dry-run true
```

展示重点：

- 输入 demo 商品 JSON。
- 输出商品标题、卖点、平台文案、标签和人工检查清单。
- 强调 demo 数据边界，不虚构真实业务效果。

## 4. 商品运营视觉工作台 v0.1

```powershell
python -m src.main sync-shop-workbench --input samples/shop-workbench.example.json --dry-run true --upload-images true
```

如果本地 `.env` 已配置飞书应用权限，可以把 `--dry-run true` 改成 `--dry-run false`。

展示重点：

- 自动创建飞书 Base。
- 自动创建运营总览、店铺主要商品、SKU 变体、竞品任务和运营建议表。
- 商品主图写入附件字段，链接写入 URL 字段。
- 彩色标签、筛选视图和画册视图提升可视化程度。

## 5. 竞品分析工作台 v0.1

```powershell
python -m src.main analyze-competitors --input samples/jd-lamp-urls.example.json --dry-run true --headful true
```

展示重点：

- 输入 1 个主商品 URL 和 10 个竞品 URL。
- 输出竞品共性、主商品差异点、机会方向、标题方向、详情页方向和人工审核清单。
- 分析只做定性分层，不输出销量、排名、GMV 或转化率。

## 6. 截图建议

建议展示 3-5 张脱敏截图：

- 飞书商品图库视图。
- 店铺主要商品表，突出主图、标题、价格带和彩色标签。
- SKU 变体矩阵。
- 竞品工作台，展示本店商品和竞品卡片。
- 竞品分析表，展示机会方向和人工审核清单。

## 7. 面试讲解顺序

推荐按这个顺序讲：

1. 业务问题：商品和竞品数据散乱，不适合团队协作。
2. 数据建模：用统一字段描述商品、SKU、竞品和审核状态。
3. 自动化同步：用飞书 OpenAPI 创建 Base、字段、记录和视图。
4. 规则分析：先用可测规则跑通流程，后续可以替换为大模型。
5. 边界意识：不虚构业务效果，不提交敏感数据，遵守平台访问规则。
