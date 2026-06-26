from __future__ import annotations

from collections import Counter

from .ai_client import AIClient, failed_competitor_insight
from .competitor_models import (
    CompetitorAnalysis,
    CompetitorWorkbenchOutput,
    JdProductSnapshot,
)
from .generator import FORBIDDEN_MARKETING_TERMS


REVIEW_CHECKLIST = [
    "核对本店商品与竞品URL是否来自公开页面，避免混入非台灯商品",
    "检查价格、评价量、促销信息是否为采集时页面可见内容，不做长期承诺",
    "检查是否出现销量、排名、转化率、GMV等无法证明的表达",
    "对主图、店铺名、商品名等公开信息在发布前做脱敏处理",
    "发布前由人工复核护眼、防蓝光、照度等参数是否与详情页一致",
]


def analyze_workbench(
    keyword: str,
    target: JdProductSnapshot,
    competitors: list[JdProductSnapshot],
    ai_client: AIClient | None = None,
) -> CompetitorWorkbenchOutput:
    successful_competitors = [item for item in competitors if item.scrape_status == "成功"]
    common_patterns = _common_patterns(successful_competitors)
    differentiators = _target_differentiators(target, successful_competitors)
    opportunities = _opportunities(target, common_patterns, differentiators)
    risks = _risks(target, competitors)
    level = _opportunity_level(target, successful_competitors)
    analysis = CompetitorAnalysis(
        keyword=keyword,
        target_sku_id=target.sku_id,
        competitor_count=len(successful_competitors),
        opportunity_level=level,
        common_patterns=common_patterns,
        target_differentiators=differentiators,
        opportunities=opportunities,
        risks=risks,
        title_directions=_title_directions(keyword, target),
        detail_page_directions=_detail_page_directions(target),
        platform_content_directions=_platform_content_directions(target),
        review_checklist=REVIEW_CHECKLIST,
    )
    if ai_client is not None:
        try:
            analysis.ai_insight = ai_client.generate_competitor_insight(
                keyword,
                target,
                successful_competitors,
                analysis,
            )
        except Exception as exc:  # noqa: BLE001 - AI fallback should preserve deterministic analysis.
            analysis.ai_insight = failed_competitor_insight(ai_client.config, exc)
    return CompetitorWorkbenchOutput(
        keyword=keyword,
        target=target,
        competitors=competitors,
        analysis=analysis,
    )


def find_forbidden_terms_in_workbench(workbench: CompetitorWorkbenchOutput) -> list[str]:
    parts: list[str] = []
    analysis = workbench.analysis
    parts.extend(analysis.common_patterns)
    parts.extend(analysis.target_differentiators)
    parts.extend(analysis.opportunities)
    parts.extend(analysis.risks)
    parts.extend(analysis.title_directions)
    parts.extend(analysis.detail_page_directions)
    parts.extend(analysis.platform_content_directions)
    if analysis.ai_insight is not None:
        parts.extend(analysis.ai_insight.category_suggestions)
        parts.extend(analysis.ai_insight.operation_suggestions)
        parts.extend(analysis.ai_insight.content_angles)
        parts.extend(analysis.ai_insight.review_notes)
    text = "\n".join(parts)
    return [term for term in FORBIDDEN_MARKETING_TERMS if term in text]


def _common_patterns(competitors: list[JdProductSnapshot]) -> list[str]:
    if not competitors:
        return ["竞品有效采集数量不足，暂不归纳共性"]
    counters = _attribute_counters(competitors)
    patterns: list[str] = []
    for label, counter in counters.items():
        if not counter:
            continue
        value, count = counter.most_common(1)[0]
        if count >= max(2, len(competitors) // 2):
            patterns.append(f"竞品在{label}上高频出现“{value}”，可作为用户对比时的基础信息")
    if patterns:
        return patterns
    return ["竞品卖点分散，建议先把照度、防蓝光、调光、色温等关键参数整理成统一口径"]


def _target_differentiators(target: JdProductSnapshot, competitors: list[JdProductSnapshot]) -> list[str]:
    attrs = target.lamp_attributes
    items: list[str] = []
    for label, value in _target_attribute_pairs(target).items():
        if value == "未识别":
            items.append(f"主商品的{label}未识别，建议补齐后再进入上架文案")
            continue
        competitor_values = {_target_attribute_pairs(item)[label] for item in competitors}
        if value not in competitor_values:
            items.append(f"主商品的{label}为“{value}”，可作为差异化信息进一步核对")
    if attrs.usage_scenario != "未识别":
        items.append(f"主商品可围绕“{attrs.usage_scenario}”强化使用场景表达")
    return items or ["主商品暂未形成明显差异点，建议补充更具体的参数、场景或套装权益"]


def _opportunities(target: JdProductSnapshot, common_patterns: list[str], differentiators: list[str]) -> list[str]:
    opportunities = [
        "将竞品高频参数整理为对比表，突出本店商品已具备和待补充的信息",
        "标题优先覆盖“护眼学习台灯、宿舍/儿童/办公、调光色温”等用户检索词",
    ]
    if any("未识别" in item for item in differentiators):
        opportunities.append("对未识别参数做人工补录，避免详情页与标题卖点不一致")
    if common_patterns:
        opportunities.append("围绕竞品共性提炼基础卖点，再用主商品差异点补充第二层表达")
    if target.image_url:
        opportunities.append("主图URL已采集，可在飞书中作为人工核对入口，不在仓库下载或发布原图")
    return opportunities


def _risks(target: JdProductSnapshot, competitors: list[JdProductSnapshot]) -> list[str]:
    failed_count = sum(1 for item in competitors if item.scrape_status == "失败")
    risks = [
        "京东页面价格、促销和评价量会变化，分析只代表采集时可见信息",
        "护眼、防蓝光、照度等参数需要以详情页和商品资质为准，发布前必须人工复核",
    ]
    if target.scrape_status == "失败":
        risks.append("主商品采集失败，本轮分析只能作为流程演示")
    if failed_count:
        risks.append(f"有{failed_count}个竞品采集失败，建议补采后再做正式对比")
    return risks


def _title_directions(keyword: str, target: JdProductSnapshot) -> list[str]:
    attrs = target.lamp_attributes
    return [
        f"{keyword} 护眼学习台灯 {attrs.illuminance} {attrs.color_temperature}",
        f"{target.brand}台灯｜{attrs.blue_light}｜{attrs.dimming}",
        f"适合{attrs.usage_scenario}的{keyword}，参数清晰版",
    ]


def _detail_page_directions(target: JdProductSnapshot) -> list[str]:
    attrs = target.lamp_attributes
    return [
        f"首屏参数区展示照度、色温、显色指数、防蓝光：{attrs.illuminance} / {attrs.color_temperature} / {attrs.cri} / {attrs.blue_light}",
        "增加竞品同类参数对比说明，但避免使用无法证明的排名或销量表达",
        "把适用场景拆成学习阅读、卧室床头、桌面办公等模块，方便用户快速判断",
    ]


def _platform_content_directions(target: JdProductSnapshot) -> list[str]:
    scenario = target.lamp_attributes.usage_scenario
    return [
        f"小红书方向：围绕{scenario}做真实桌面使用体验和参数核对清单",
        "抖音方向：用三段式口播讲清痛点、关键参数和下单前复核点",
        "电商平台方向：标题和详情页优先写清参数，不使用绝对化功效承诺",
    ]


def _opportunity_level(target: JdProductSnapshot, competitors: list[JdProductSnapshot]) -> str:
    recognized = sum(1 for value in _target_attribute_pairs(target).values() if value != "未识别")
    if len(competitors) >= 8 and recognized >= 5:
        return "高"
    if len(competitors) >= 5 and recognized >= 3:
        return "中"
    return "低"


def _attribute_counters(products: list[JdProductSnapshot]) -> dict[str, Counter[str]]:
    counters: dict[str, Counter[str]] = {
        "照度": Counter(),
        "色温": Counter(),
        "显色指数": Counter(),
        "防蓝光": Counter(),
        "调光": Counter(),
        "功率": Counter(),
        "场景": Counter(),
    }
    for product in products:
        for label, value in _target_attribute_pairs(product).items():
            if value != "未识别":
                counters[label][value] += 1
    return counters


def _target_attribute_pairs(product: JdProductSnapshot) -> dict[str, str]:
    attrs = product.lamp_attributes
    return {
        "照度": attrs.illuminance,
        "色温": attrs.color_temperature,
        "显色指数": attrs.cri,
        "防蓝光": attrs.blue_light,
        "调光": attrs.dimming,
        "功率": attrs.power,
        "场景": attrs.usage_scenario,
    }
