from src.ai_client import AIConfig
from src.ai_enrichment import enrich_shop_workbench_payload
from src.models import AIProductInsight, ProductInput


def test_enrich_shop_workbench_payload_adds_ai_fields() -> None:
    class FakeAIClient:
        config = AIConfig(provider="deepseek", api_key="test-key", model="deepseek-chat", base_url="https://api.test")

        def generate_product_insight(self, product: ProductInput) -> AIProductInsight:
            return AIProductInsight(
                provider="deepseek",
                model="deepseek-chat",
                status="成功",
                category_suggestion="学习护眼台灯",
                product_positioning=product.category,
                suggested_tags=["护眼", "学习"],
                operation_suggestions=["补齐详情页参数"],
                review_notes=["核对照度等级"],
            )

    payload = {
        "tables": [
            {
                "table_name": "店铺主要商品表",
                "records": [
                    {
                        "店铺商品SKU": "shop-product-001",
                        "商品名称": "示例品牌 护眼学习台灯",
                        "商品定位": "学习护眼台灯",
                        "价格带": "100-199元",
                        "标签": "AA级、调光",
                    }
                ],
            }
        ]
    }

    enriched = enrich_shop_workbench_payload(payload, FakeAIClient())
    record = enriched["tables"][0]["records"][0]

    assert record["AI分类建议"] == "学习护眼台灯"
    assert record["AI标签建议"] == "护眼、学习"
    assert record["AI运营建议"] == "补齐详情页参数"
    assert record["AI模型"] == "deepseek/deepseek-chat"
