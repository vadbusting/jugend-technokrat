import json
import re
import csv
import urllib.request
import xml.etree.ElementTree as ET
import os

products_js_path = "./products.js"
catalog_csv_path = "./catalog.csv"
pinterest_csv_path = "./products_pinterest_catalog.csv"

# Zazzle Associate ID
rf_id = "238192102477642780"

# RSS Feed URL
rss_url = "https://feed.zazzle.com/store/jugendtechnokrat/rss"

JP_TRANSLATIONS = {
    "ZIPPO LIGHTER": "ZIPPOライター", "ZIPPO LIGHTERS": "ZIPPOライター",
    "BEACH TOWEL": "ビーチタオル", "DESK MAT": "デスクマット", "MOUSE PAD": "マウスパッド",
    "SUNGLASSES": "サングラス", "POKER CARDS": "トランプ", "SOCKS": "ソックス",
    "PRINTED BACKPACK": "バックパック", "DUFFLE BAG": "ダッフルバッグ", "FLIP FLOPS": "ビーチサンダル",
    "LAPTOP SLEEVE": "ラップトップスリーブ", "PLANNER": "手帳", "THERMAL WINE TUMBLER": "サーマルワインタンブラー",
    "CALENDAR": "カレンダー", "PILLOW CASE": "枕カバー", "MUG": "マグカップ", "WATER BOTTLE": "ウォーターボトル",
    "WATCH": "腕時計", "JIGSAW PUZZLE": "ジグソーパズル", "PING PONG PADDLE": "卓球ラケット",
    "CROSSBODY BAG": "クロスボディバッグ", "GOLF HEAD COVER": "ゴルフヘッドカバー", "METAL ORNAMENT": "メタルオーナメント",
    "ROUND PILLOW": "ラウンドピロー", "LUMBAR PILLOW": "ランバーピロー", "IPHONE 16 PRO CASE": "iPhone 16 Proケース",
    "IPHONE 16 CASE": "iPhone 16ケース", "BAR KEY": "バーキー", "KITCHEN TOWEL": "キッチンタオル",
    "WAITERS CORKSCREW": "ワインオープナー", "WHISKEY GLASS": "ウィスキーグラス", "OVEN MITT POT HOLDER SET": "オーブンミトン＆鍋敷きセット",
    "OVEN MITT SET": "オーブンミトン＆鍋敷きセット", "APRON": "エプロン", "HAND TOWEL": "ハンドタオル",
    "TIE HEADBAND": "ヘアバンド", "PEN": "ボールペン", "NECK TIE": "ネクタイ", "BOWL": "ボウル",
    "ATHLETIC HEADBAND": "ヘッドバンド", "BATH MAT": "バスマット", "DOORMAT": "ドアマット", "NOTEBOOK": "ノート",
    "METAL LUNCH BOX": "メタルランチボックス", "CERAMIC TILE": "セラミックタイル", "BEVERAGE COASTER": "コースター",
    "STONE COASTER": "ストーンコースター", "THROW PILLOW": "クッション", "LARGE CLOCK": "壁掛け時計",
    "BUTTON": "缶バッジ", "FLASK": "フラスコ", "GLASS": "グラス", "LATTE MUG": "ラテマグ",
    "GIANT COFFEE MUG": "ジャイアントマグカップ", "COFFEE MUG": "コーヒーマグ", "T SHIRT": "Tシャツ", "T-SHIRT": "Tシャツ",
    "POSTER": "ポスター", "TRUCKER HAT": "トラッカーハット", "GOLF TOWEL": "ゴルフタオル", "LEGGINGS": "レギンス",
    "OVEN MITT": "オーブンミトン", "SLING BAG": "スリングバッグ", "CAPRI LEGGINGS": "カプリレギンス",
    "IPHONE 16 PRO MAX CASE": "iPhone 16 Pro Maxケース", "SELTZER CAN COOLER": "缶クローラー",
    "PICKLEBALL PADDLE": "ピックルボールパドル", "WASH CLOTH": "ウォッシュクロス", "LUGGAGE TAG": "ラゲッジタグ",
    "TRAVEL MUG": "トラベルマグ", "CLIPBOARD": "クリップボード", "SKATEBOARD": "スケートボード",
    "SHERPA BLANKET": "ボアブランケット", "FLEECE BLANKET": "フリースブランケット", "THROW BLANKET": "ブランケット",
    "OUTDOOR PILLOW": "アウトドアクッション", "CLOCK": "時計", "CLASSIC ROUND STICKER": "ステッカー",
    "PAPER PLATES": "ペーパープレート"
}

def translate_title(en_title):
    parts = en_title.split(' ', 1)
    if len(parts) == 2:
        prefix = parts[0]
        suffix = parts[1].strip().upper()
        if suffix in JP_TRANSLATIONS:
            return f"{prefix} {JP_TRANSLATIONS[suffix]}"
    return en_title

def clean_xml_namespaces(xml_data):
    # Remove media namespace prefix and definition
    xml_data = re.sub(r'\sxmlns:media="[^"]+"', '', xml_data)
    xml_data = xml_data.replace('media:', '')
    return xml_data

def fetch_rss_products():
    req = urllib.request.Request(
        rss_url, 
        headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    )
    products = []
    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read().decode('utf-8')
            # Clean namespace prefix to prevent parsing issues
            xml_data = clean_xml_namespaces(xml_data)
            root = ET.fromstring(xml_data)
            
            for item in root.findall('.//item'):
                link = item.find('link').text
                # Extract product ID (18 digits)
                id_match = re.search(r'-(\d{18})(?:\?|$)', link)
                if not id_match:
                    continue
                p_id = id_match[1]
                
                # Zazzle details
                title_en = item.find('title').text.strip()
                # If Zazzle auto-renamed it (without Series prefix), try to restore from URL slug
                if not re.match(r'^[A-Z]\d{2}', title_en) and "PROTO" not in title_en:
                    url_slug = link.split('/')[-1]
                    slug_match = re.match(r'^([a-zA-Z0-9_]+)-\d+$', url_slug)
                    if slug_match:
                        title_en = slug_match.group(1).replace('_', ' ').upper()
                
                price = item.find('price').text.strip()
                if not price.startswith('$'):
                    price = f"${price}"
                
                # Format to self-promotion URL (WITHOUT rf tag to maximize royalty percentage to 35-50%)
                # Zazzle Ambassador tracking handles login sessions automatically.
                # However, for general Pinterest users, we include the associate ID parameter.
                zazzle_url = f"https://www.zazzle.com/{link.split('/')[-1].split('?')[0]}?rf={rf_id}"
                image_url = f"https://rlv.zcache.com/svc/view?pid={p_id}&max_dim=1024"
                
                products.append({
                    "id": p_id,
                    "title_en": title_en,
                    "title_jp": translate_title(title_en),
                    "image_url": image_url,
                    "zazzle_url": zazzle_url,
                    "price": price
                })
    except Exception as e:
        print("Error fetching RSS feed:", e)
    return products

# Generator for SEO-friendly titles and descriptions (Pinterest SEO Hack)
def generate_seo_meta(title_en, title_jp):
    title_upper = title_en.upper()
    
    # 1. Determine product category and create localized rich title
    if "T SHIRT" in title_upper or "T-SHIRT" in title_upper:
        seo_title = f"{title_en} - テック系グラフィックTシャツ | JUGEND TECHNOKRAT"
        seo_desc = f"【{title_jp}】ミニマリズムとテクノロジー、インダストリアルデザインを融合したグラフィックが特徴のデザイナーズTシャツ。モノトーンコーデやテックウェアとの相性も抜群です。ストリートやクリエイタースタイルに最適な一着。 #テックウェア #グラフィックT #モノトーンコーデ #Zazzle"
    elif "ZIPPO" in title_upper:
        seo_title = f"{title_en} - インダストリアルデザイン ジッポライター | JUGEND TECHNOKRAT"
        seo_desc = f"【{title_jp}】無機質なタイポグラフィと洗練されたミニマルグラフィックを施したZippoライター。日常の持ち物にこだわりたい方へのギフト・プレゼントにも最適なコレクターズアイテムです。 #Zippo #ジッポ #インダストリアル #ミニマルデザイン #Zazzle"
    elif "MUG" in title_upper or "CUP" in title_upper:
        seo_title = f"{title_en} - デスク映えするミニマルデザインマグカップ | JUGEND TECHNOKRAT"
        seo_desc = f"【{title_jp}】デスクワークやコーヒータイムをスタイリッシュに演出するマグカップ。無機質でモダンなミニマルデザインが特徴。自室のデスクセットアップやオフィスのデスク環境をクールに彩ります。 #デスクセットアップ #ミニマリスト #マグカップ #デザイナーズ雑貨 #Zazzle"
    elif "MOUSE PAD" in title_upper or "DESK MAT" in title_upper:
        seo_title = f"{title_en} - デスクセットアップに最適なマウスパッド | JUGEND TECHNOKRAT"
        seo_desc = f"【{title_jp}】デスク環境をモダンにアップデートする高性能マウスパッド / デスクマット。無機質なミニマルグラフィックが、洗練されたガジェットスペースを演出します。クリエイターへのギフトにもおすすめ。 #デスクツアー #ガジェット #マウスパッド #ミニマリスト #Zazzle"
    elif "WATCH" in title_upper:
        seo_title = f"{title_en} - 近未来テイストのミニマルデザイン腕時計 | JUGEND TECHNOKRAT"
        seo_desc = f"【{title_jp}】無機質で研ぎ澄まされたグラフィックが特徴の腕時計。近未来的なテック感とインダストリアルなエッセンスを融合。手元をスマートに飾るスタイリッシュなアクセサリーです。 #腕時計 #プロダクトデザイン #ミニマルファッション #テック系 #Zazzle"
    elif "POSTER" in title_upper:
        seo_title = f"{title_en} - 部屋を格上げするミニマルアートポスター | JUGEND TECHNOKRAT"
        seo_desc = f"【{title_jp}】空間にモダンで知的なアクセントを加える、ミニマル・インダストリアルデザインのアートポスター。書斎、オフィス、リビングなど、クリエイティブなインテリア装飾に最適です。 #インテリアアート #ポスターデザイン #インダストリアルデザイン #書斎インテリア #Zazzle"
    elif "CASE" in title_upper:
        seo_title = f"{title_en} - スマートなミニマルiPhoneケース | JUGEND TECHNOKRAT"
        seo_desc = f"【{title_jp}】インダストリアルなグラフィックを施した耐衝撃デザイナーズiPhoneケース。無機質でスタイリッシュな見た目が、あなたのスマートフォンをモダンにガードします。 #iPhoneケース #ガジェット #スマホケース #ミニマリズム #Zazzle"
    else:
        seo_title = f"{title_en} - インダストリアルミニマルデザイン雑貨 | JUGEND TECHNOKRAT"
        seo_desc = f"【{title_jp}】ミニマリズムとテクノロジー、タイポグラフィを融合したJUGEND TECHNOKRATのプロダクト。実用性と高いデザイン性を兼ね備え、デスク環境やライフスタイルをモダンに演出します。 #ミニマリスト #デザイナーズ雑貨 #プロダクトデザイン #モノトーン #Zazzle"

    return seo_title, seo_desc

def main():
    # 1. Load current products
    current_products = []
    if os.path.exists(products_js_path):
        with open(products_js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
            json_match = re.search(r'window\.products\s*=\s*(\[[\s\S]*?\])\s*;?', js_content)
            if json_match:
                current_products = json.loads(json_match.group(1))

    current_ids = {p['id'] for p in current_products}
    print(f"Current local products: {len(current_products)}")

    # 2. Fetch from RSS
    rss_prods = fetch_rss_products()
    print(f"Fetched {len(rss_prods)} products from Zazzle RSS")

    # 3. Incremental Merge (add new products to top)
    new_added = 0
    for p in reversed(rss_prods):  # reverse so oldest RSS items get processed first
        p_id = p['id']
        if p_id not in current_ids:
            current_products.insert(0, p)
            current_ids.add(p_id)
            new_added += 1
            print(f"New product detected: {p['title_en']} ({p_id}) at {p['price']}")

    # Save update if new products found, or recreate CSVs anyway to apply SEO upgrades
    # 4. Save products.js if updated
    if new_added > 0:
        print(f"Added {new_added} new products. Total lineup: {len(current_products)}")
        js_output = "window.products = " + json.dumps(current_products, indent=2, ensure_ascii=False) + ";\n"
        with open(products_js_path, 'w', encoding='utf-8') as f:
            f.write(js_output)

    # 5. Always rewrite CSVs to apply SEO optimizations to both old and new products
    csv_fields = ["id", "title", "description", "link", "image_link", "price", "availability", "condition"]
    def write_catalog_csv(path):
        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_fields)
            writer.writeheader()
            for p in current_products:
                raw_price = p['price'].replace('$', '').strip()
                # Generate rich title and description
                seo_title, seo_desc = generate_seo_meta(p['title_en'], p['title_jp'])
                writer.writerow({
                    "id": p['id'],
                    "title": seo_title,
                    "description": seo_desc,
                    "link": p['zazzle_url'],
                    "image_link": p['image_url'],
                    "price": raw_price,
                    "availability": "in stock",
                    "condition": "new"
                })
    
    write_catalog_csv(catalog_csv_path)
    write_catalog_csv(pinterest_csv_path)
    print("Successfully updated database and SEO-optimized CSV catalogs.")

if __name__ == "__main__":
    main()
