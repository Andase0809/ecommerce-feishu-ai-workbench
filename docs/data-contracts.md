# 数据契约

## 商品输入

`samples/products.json` 使用数组结构，每个商品包含：

```json
{
  "product_id": "product-light-001",
  "product_name": "便携式桌面补光灯",
  "category": "数码配件",
  "price_range": "99-199元",
  "target_user": "学生和轻办公用户",
  "core_features": ["三档色温", "可调节亮度", "USB供电"],
  "usage_scenarios": ["宿舍拍摄", "桌面直播"],
  "platform_style": ["小红书", "抖音", "电商平台"]
}
```

输出字段包括商品基础信息、平台内容、标签、审核项和可选模型建议。

## 店铺工作台输入

`samples/shop-workbench.example.json` 包含多个表：

- `店铺主要商品表`
- `SKU款式变体表`
- `竞品分析表`
- `运营建议表`

主要商品记录建议包含：

- `店铺商品SKU`
- `商品名称`
- `品牌`
- `店铺名称`
- `价格文本`
- `价格数值`
- `价格带`
- `商品定位`
- `店铺展示主图`
- `商品链接`
- `标签`
- `SKU变体状态`
- `竞品分析状态`
- `审核状态`

启用模型增强后，系统会补充：

- `AI分类建议`
- `AI定位建议`
- `AI标签建议`
- `AI运营建议`
- `AI审核提示`
- `AI生成状态`
- `AI模型`

## 竞品输入

`samples/jd-lamp-urls.example.json` 使用对象结构：

```json
{
  "keyword": "台灯",
  "target_url": "https://item.jd.com/100000000001.html",
  "competitor_urls": [
    "https://item.jd.com/100000000002.html"
  ]
}
```

`competitor_urls` 需要 10 个商品 URL。真实 URL 文件放在 `samples/*.local.json`。

## 飞书字段类型

项目使用的主要飞书字段类型：

- 文本字段：标题、参数、建议、审核项。
- 数字字段：价格、统计值、变体数量。
- URL 字段：商品链接、图片 URL、来源链接。
- 附件字段：商品主图、变体图。
- 单选字段：审核状态、采集状态、价格带、商品定位。
- 多选字段：商品标签。

## 本地输出

默认本地输出路径：

- `outputs/generated-products.json`
- `outputs/jd-lamp-competitor-analysis.json`

真实运行输出不提交到仓库，仓库只保留公开样例输出。
