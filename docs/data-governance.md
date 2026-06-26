# 数据治理

## 凭证

运行时凭证通过 `.env` 提供：

```text
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AI_PROVIDER=deepseek
AI_API_KEY=
AI_MODEL=deepseek-v4-flash
```

`.env`、浏览器缓存、真实采集结果和本地输出文件已加入 `.gitignore`。

## 本地文件约定

- `samples/*.example.json`：公开输入样例。
- `samples/*.local.json`：本地真实 URL 或真实输入。
- `outputs/sample-*.json`：公开输出样例。
- `outputs/*.json`：本地真实运行输出，除 `sample-*` 外默认忽略。
- `.browser/`：浏览器用户数据目录和调试缓存。

## 模型服务数据

启用模型增强后，程序会把必要字段发送给配置的模型服务：

- 商品名称
- 价格带
- 商品定位
- 标签
- 卖点
- 参数摘要
- 竞品分析摘要

模型服务只负责生成分类建议、标签建议、运营建议和审核提示。系统不会要求模型输出销量、排名、GMV、转化率等不可验证指标。

## 浏览器辅助采集

浏览器自动化用于人工可控的数据整理流程。遇到登录、验证或访问限制时，由人工处理或停止采集；程序不保存登录态到仓库。

## 分析结果边界

竞品分析输出为定性分析，包含：

- 竞品共性
- 主商品差异点
- 机会方向
- 风险提示
- 审核项

涉及商品资质、护眼参数、防蓝光等级、价格和促销信息时，以来源页面和人工复核为准。
