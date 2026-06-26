# 数据安全与发布边界

## 不提交的内容

以下内容不进入 GitHub：

- `.env`
- `.browser/`
- `.codegraph/`
- `samples/*.local.json`
- `outputs/*.json` 中的真实运行结果
- 飞书 `app_token`
- 飞书 `tenant_access_token`
- 浏览器登录态、Cookie、缓存和调试目录
- 本地微信、下载目录或个人用户名路径
- 未脱敏截图

仓库只保留：

- `.env.example`
- `samples/*.example.json`
- `outputs/sample-*.json`
- 文档和测试代码

## 飞书凭证

本地运行时通过 `.env` 配置：

```text
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

`.env` 已被 `.gitignore` 忽略。提交前需要确认没有把真实应用凭证写入 README、文档、样例或测试文件。

## 商品数据边界

公开展示时应使用 demo 或脱敏数据：

- 商品名可替换为“示例品牌 A 护眼台灯”。
- 店铺名可替换为“示例照明店”。
- 商品链接可替换为 example URL 或脱敏 URL。
- 商品主图可以使用占位图片 URL。
- 评价量文本只作为页面可见字段保存，不推导销量。

## 分析结论边界

允许输出：

- 竞品共性。
- 主商品差异点。
- 参数补齐建议。
- 标题方向。
- 详情页方向。
- 平台内容方向。
- 人工审核清单。

禁止输出无法证明的结论：

- 销量排名。
- GMV。
- 转化率。
- 平台官方背书。
- 真实商家使用效果。
- 绝对化功效承诺。

## 自动化边界

浏览器自动化只用于人工可控的数据整理流程：

- 不采集评论正文。
- 不提交登录态和 Cookie。
- 遵守平台访问控制和访问规则。
- 遇到验证、登录或访问限制时，应由人工处理或停止采集。

## 发布前检查

提交或发布 GitHub 前执行：

```powershell
git status --short
git diff --check
python -m pytest -q --basetemp .pytest-tmp
```

建议再扫描敏感关键词：

```powershell
rg -n --hidden --glob '!.git/**' --glob '!.env' --glob '!.browser/**' --glob '!outputs/*.json' --glob '!samples/*.local.json' "FEISHU_APP_SECRET|app_token|tenant_access_token" .
```

如果命中的是 `.env.example` 或文档中的安全说明，需要人工确认是否只是占位或说明文本。
