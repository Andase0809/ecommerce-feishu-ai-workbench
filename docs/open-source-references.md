# 开源参考与使用边界

## 使用原则

这些项目只能作为功能拆分、交互方式、README组织和技术选型参考。不得直接复制代码后改名包装为自己的项目。

如确实使用任何开源代码、模板、Prompt片段或示例结构，需要：

- 检查许可证。
- 在 README 中注明来源。
- 保留许可证要求。
- 做场景改造和二次实现。

## 参考项目

### 1. Nutlope/description-generator

- 链接：https://github.com/Nutlope/description-generator
- 可参考方向：商品图生成商品描述、AI生成商品文案的交互思路。
- 本项目借鉴方式：只参考“输入商品信息/图片后生成描述”的产品思路，不复制代码。

### 2. mayashavin/product-info-ai-generator

- 链接：https://github.com/mayashavin/product-info-ai-generator
- 可参考方向：从商品图片生成标题、描述、标签的输出结构。
- 本项目借鉴方式：参考字段拆分，即标题、描述、标签，不复制代码。

### 3. iamarunbrahma/product-description-generator

- 链接：https://github.com/iamarunbrahma/product-description-generator
- 可参考方向：面向SEO商品描述的字段设计。
- 本项目借鉴方式：参考“SEO/标题/描述”的组织思路，不复制代码。

## 本项目建议差异化

为了避免变成普通商品描述生成器，本项目建议突出：

- 平台口吻适配：小红书、抖音、电商平台三种表达。
- 人工检查清单：避免AI生成夸大、敏感词、参数不一致。
- 商品信息结构化：品类、目标人群、参数、使用场景、卖点。
- 求职展示友好：README中解释业务价值、输入输出和岗位迁移能力。

