from src.ai_client import AIClient, AIConfig
from src.models import ProductInput


def _product() -> ProductInput:
    return ProductInput(
        product_id="product-001",
        product_name="护眼学习台灯",
        category="学习台灯",
        price_range="100-199元",
        target_user="学生和办公用户",
        core_features=["国AA级照度", "三档调光"],
        usage_scenarios=["学习阅读"],
        platform_style=["电商平台"],
    )


def test_ai_config_uses_provider_specific_key(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    config = AIConfig.from_env(provider="deepseek", model="deepseek-chat")

    assert config.provider == "deepseek"
    assert config.api_key == "test-key"
    assert config.base_url == "https://api.deepseek.com"


def test_ai_client_generates_product_insight_from_json_response() -> None:
    calls = []

    def fake_transport(url, headers, payload, timeout):
        calls.append((url, headers, payload, timeout))
        return {
            "choices": [
                {
                    "message": {
                        "content": """```json
                        {
                          "category_suggestion": "学习护眼台灯",
                          "product_positioning": "百元学习桌面照明",
                          "suggested_tags": ["国AA级", "调光"],
                          "operation_suggestions": ["补齐防蓝光参数"],
                          "review_notes": ["核对参数来源"]
                        }
                        ```"""
                    }
                }
            ]
        }

    client = AIClient(
        AIConfig(
            provider="openai",
            api_key="test-key",
            model="test-model",
            base_url="https://api.test/v1",
        ),
        transport=fake_transport,
    )

    insight = client.generate_product_insight(_product())

    assert calls[0][0] == "https://api.test/v1/chat/completions"
    assert calls[0][1]["Authorization"] == "Bearer test-key"
    assert calls[0][2]["model"] == "test-model"
    assert insight.category_suggestion == "学习护眼台灯"
    assert insight.product_positioning == "百元学习桌面照明"
    assert insight.suggested_tags == ["国AA级", "调光"]
    assert insight.status == "成功"
