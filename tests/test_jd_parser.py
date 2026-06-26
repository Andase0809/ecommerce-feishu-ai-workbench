from datetime import datetime

from src.jd_parser import parse_jd_product_html, parse_price_range


HTML = """
<html>
  <head>
    <meta property="og:title" content="明澈 国AA级护眼学习台灯 京东自营">
    <meta property="og:image" content="//img10.jd.com/main.jpg">
    <meta name="description" content="国AA级照度，RG0防蓝光，适合学习阅读">
  </head>
  <body>
    <div class="sku-name">明澈 国AA级护眼学习台灯</div>
    <div class="shopName"><strong><a>明澈京东自营旗舰店</a></strong></div>
    <div id="p-ad">三档调光，适合学习阅读和卧室床头使用</div>
    <span class="p-price"><span class="price">￥199.00</span></span>
    <div id="comment-count"><a>20万+评价</a></div>
    <ul class="parameter2">
      <li title="明澈">品牌：明澈</li>
      <li>型号：TD-01</li>
      <li>照度：国AA级</li>
      <li>色温：3000K-5000K</li>
      <li>显色指数：Ra95</li>
      <li>防蓝光：RG0</li>
      <li>功率：12W</li>
      <li>调光方式：三档调光</li>
    </ul>
  </body>
</html>
"""


def test_parse_jd_product_html_extracts_public_fields() -> None:
    snapshot = parse_jd_product_html(
        HTML,
        url="https://item.jd.com/100000000001.html",
        role="target",
        collected_at=datetime(2026, 6, 26, 10, 0, 0),
    )

    assert snapshot.scrape_status == "成功"
    assert snapshot.sku_id == "100000000001"
    assert snapshot.product_name == "明澈 国AA级护眼学习台灯"
    assert snapshot.brand == "明澈"
    assert snapshot.shop_name == "明澈京东自营旗舰店"
    assert snapshot.image_url == "https://img10.jd.com/main.jpg"
    assert snapshot.price_text == "￥199.00"
    assert snapshot.price_range == "100-199元"
    assert snapshot.review_count_text == "20万+评价"
    assert snapshot.lamp_attributes.illuminance == "国AA级"
    assert snapshot.lamp_attributes.color_temperature == "3000K-5000K"
    assert snapshot.lamp_attributes.cri == "Ra95"
    assert snapshot.lamp_attributes.blue_light == "RG0"
    assert snapshot.lamp_attributes.power == "12W"
    assert snapshot.lamp_attributes.dimming == "三档调光"


def test_parse_price_range_returns_unknown_when_missing_price() -> None:
    assert parse_price_range("") == "未识别"
