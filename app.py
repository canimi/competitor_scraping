import streamlit as st
import pandas as pd
import os
import json
import requests
import re
import time
from deep_translator import GoogleTranslator
from apify_client import ApifyClient

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="LCW Global Intelligence", layout="wide", page_icon="🧿")

# --- CSS ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; padding-bottom: 5rem; }
    header {visibility: hidden;}
    .stApp { background-color: #0e1117; font-family: 'Segoe UI', sans-serif; }
    h1 { color: #4da6ff; text-align: center; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 15px rgba(77, 166, 255, 0.6); margin-top: -20px !important; padding-bottom: 20px; }
    div[data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.5); }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-size: 28px !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 14px !important; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 5px; }
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    div.stButton > button { background: linear-gradient(90deg, #1c54b2 0%, #0d3c85 100%); color: white; border: none; padding: 12px 24px; font-weight: bold; width: 100%; border-radius: 8px; }
    .stAlert { background-color: #161b22; color: #e6edf3; border: 1px solid #30363d; }
</style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
st.markdown("<h1>🧿 LCW HOME | GLOBAL INTELLIGENCE</h1>", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = None

# --- API KEYS ---
PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY") or st.secrets.get("PERPLEXITY_API_KEY", "")
APIFY_KEY = os.environ.get("APIFY_API_KEY") or st.secrets.get("APIFY_API_KEY", "")

# --- URL DB ---
URL_DB = {
    "Bulgaristan": { 
        "Pepco": "https://pepco.bg/", 
        "Sinsay": "https://www.sinsay.com/bg/bg/", 
        "Zara Home": "https://www.zarahome.com/bg/", 
        "H&M Home": "https://www2.hm.com/bg_bg/home.html", 
        "Jysk": "https://jysk.bg/", 
        "Jumbo": "https://www.jumbo.bg/", 
        "English Home": "https://englishhome.bg/"
    },
    "Bosna Hersek": { 
        "Pepco": "https://pepco.ba/", 
        "Sinsay": "https://www.sinsay.com/ba/bs/", 
        "Zara Home": "https://www.zarahome.com/ba/", 
        "H&M Home": "https://www.hm.com/ba", 
        "Jysk": "https://jysk.ba/", 
        "Jumbo": "https://www.jumbo.ba/", 
        "English Home": "https://englishhome.ba/"
    },
    "Yunanistan": { 
        "Pepco": "https://pepco.gr/", 
        "Sinsay": "https://www.sinsay.com/gr/el/", 
        "Zara Home": "https://www.zarahome.com/gr/", 
        "H&M Home": "https://www2.hm.com/en_gr/home.html", 
        "Jysk": "https://jysk.gr/", 
        "Jumbo": "https://www.e-jumbo.gr/", 
        "English Home": "https://englishhome.gr/"
    },
    "Sırbistan": { 
        "Pepco": "https://pepco.rs/", 
        "Sinsay": "https://www.sinsay.com/rs/sr/", 
        "Zara Home": "https://www.zarahome.com/rs/", 
        "H&M Home": "https://www2.hm.com/rs_en/home.html", 
        "Jysk": "https://jysk.rs/", 
        "Jumbo": "https://www.jumbo.rs/", 
        "English Home": "https://englishhome.rs/"
    },
    "Romanya": { 
        "Pepco": "https://pepco.ro/", 
        "Sinsay": "https://www.sinsay.com/ro/ro/", 
        "Zara Home": "https://www.zarahome.com/ro/", 
        "H&M Home": "https://www2.hm.com/ro_ro/home.html", 
        "Jysk": "https://jysk.ro/", 
        "English Home": "https://englishhome.ro/"
    },
}

COUNTRIES_META = {
    "Bulgaristan":  {"curr": "BGN", "lang": "bg"},
    "Bosna Hersek": {"curr": "BAM", "lang": "bs"},
    "Yunanistan":   {"curr": "EUR", "lang": "el"},
    "Sırbistan":    {"curr": "RSD", "lang": "sr"},
    "Romanya":      {"curr": "RON", "lang": "ro"},
}

BRANDS = ["Pepco", "Sinsay", "Zara Home", "H&M Home", "Jysk", "Jumbo", "English Home"]

# --- FONKSİYONLAR ---
@st.cache_data(ttl=3600)
def get_rates():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/TRY", timeout=10).json()['rates']
        rates = {k: 1/v for k, v in r.items() if v > 0}
        if "EUR" in rates: 
            rates["BAM"] = rates["EUR"] / 1.95583
        return rates
    except: 
        return None

def translate_logic(text, mode="to_local", target_lang="en"):
    if not text: return text
    try:
        if mode == "to_local":
            return GoogleTranslator(source='auto', target=target_lang).translate(text)
        elif mode == "to_english":
            return GoogleTranslator(source='auto', target='en').translate(text)
        else:
            return GoogleTranslator(source='auto', target='tr').translate(text)
    except: 
        return text

def clean_price(price_raw, currency_code="USD"):
    if not price_raw: return 0.0
    s = str(price_raw).lower()
    for bad in ["from", "start", "to", "price", "fiyat", "only", "now", "was"]:
        s = s.replace(bad, "")
    for code in ["rsd", "din", "km", "bam", "лв", "bgn", "eur", "ron", "lei", "tl", "try", "huf", "ft", "$", "€", "£", "₺"]:
        s = s.replace(code, "")
    s = s.strip()
    s = re.sub(r'[^\d.,]', '', s)
    if not s: return 0.0
    
    numbers = re.findall(r'[\d.,]+', s)
    if not numbers: return 0.0
    s = numbers[0]
    
    try:
        if ',' in s and '.' in s:
            if s.rfind(',') > s.rfind('.'): 
                s = s.replace('.', '').replace(',', '.')
            else: 
                s = s.replace(',', '')
        elif ',' in s:
            parts = s.split(',')
            if len(parts[-1]) == 2: 
                s = s.replace(',', '.')
            else: 
                s = s.replace(',', '')
        return float(s)
    except: 
        return 0.0

def validate_relevance(product_name_local, query_english):
    try:
        prod_en = GoogleTranslator(source='auto', target='en').translate(product_name_local).lower()
        q_en = query_english.lower()
        keywords = [k for k in q_en.split() if len(k) > 2]
        main_object = keywords[-1] if keywords else ""
        
        if main_object in prod_en:
            return True, prod_en
        
        match = any(k in prod_en for k in keywords)
        return match, prod_en
    except:
        return True, product_name_local

# --- APIFY SCRAPER ---
def scrape_with_apify(brand, product_local, product_english, url, currency_code):
    """Apify ile Web Scraping"""
    if not APIFY_KEY:
        return None
    
    try:
        client = ApifyClient(APIFY_KEY)
        
        # Genel web scraper actor'ı kullan
        run_input = {
            "startUrls": [{"url": url}],
            "linkSelector": "a[href*='product'], a[href*='item'], .product-link",
            "pageFunction": """
                async function pageFunction(context) {
                    const $ = context.jQuery;
                    const results = [];
                    
                    // Farklı site yapılarını destekle
                    const selectors = [
                        '.product-card, .product-item, .product-tile',
                        '.product',
                        '[class*="product"]'
                    ];
                    
                    for (const selector of selectors) {
                        $(selector).each((i, el) => {
                            const $el = $(el);
                            
                            // İsim çek
                            const name = $el.find('h2, h3, h4, .product-name, .product-title, [class*="name"], [class*="title"]').first().text().trim();
                            
                            // Fiyat çek
                            const price = $el.find('.price, [class*="price"], .cost, [class*="cost"]').first().text().trim();
                            
                            // Link çek
                            const link = $el.find('a').first().attr('href');
                            
                            if (name && price) {
                                results.push({
                                    name: name,
                                    price: price,
                                    url: link ? (link.startsWith('http') ? link : context.request.loadedUrl + link) : context.request.loadedUrl
                                });
                            }
                        });
                        
                        if (results.length > 0) break;
                    }
                    
                    return results;
                }
            """,
            "maxPagesPerCrawl": 3,
            "maxConcurrency": 1
        }
        
        # Actor'ı çalıştır
        run = client.actor("apify/web-scraper").call(run_input=run_input)
        
        # Sonuçları al
        products = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            if isinstance(item, list):
                products.extend(item)
            elif isinstance(item, dict) and 'name' in item:
                products.append(item)
        
        if products:
            return {"products": products}
        return None
        
    except Exception as e:
        st.warning(f"Apify hatası: {e}")
        return None

# --- PERPLEXITY SCRAPER (Yedek) ---
def search_sonar(brand, product_local, product_english, country, currency_code, hardcoded_url, api_key):
    url = "https://api.perplexity.ai/chat/completions"
    
    system_msg = "You are a bulk data scraper. Your job is to EXTRACT LISTS of products, not just one item."
    
    user_msg = f"""
ACTION: Go to the '{product_english}' category on {hardcoded_url} (or search for '{product_local}').

TASK: List AS MANY diverse products as possible found in that category.
- Don't stop at 1 result. I need a Price List.
- Look for different sizes (e.g., 50x90, 70x140, 30x50).
- Look for different colors/models.

TARGET: At least 10-15 items.

OUTPUT JSON:
{{
    "products": [
        {{ "name": "Product Name 1", "price": "10.99", "url": "link" }},
        {{ "name": "Product Name 2", "price": "12.99", "url": "link" }},
        ...
    ]
}}
"""
    
    payload = {
        "model": "sonar",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
        "temperature": 0.2,
        "max_tokens": 4000
    }
    
    headers = { "Authorization": f"Bearer {api_key}", "Content-Type": "application/json" }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=60)
        if res.status_code == 200:
            raw = res.json()['choices'][0]['message']['content']
            clean = raw.replace("``````", "").strip()
            start = clean.find("{")
            end = clean.rfind("}")
            if start != -1 and end != -1:
                clean = clean[start:end+1]
                return json.loads(clean)
        return None
    except: 
        return None

# --- HYBRID SCRAPER (Apify + Perplexity) ---
def hybrid_scrape(brand, product_local, product_english, country, currency_code, url):
    """Önce Apify dene, olmazsa Perplexity'ye düş"""
    
    # 1. Apify'ı dene
    st.info(f"🤖 {brand} için Apify ile scraping başlatılıyor...")
    result = scrape_with_apify(brand, product_local, product_english, url, currency_code)
    
    if result and result.get("products") and len(result["products"]) >= 3:
        st.success(f"✅ Apify'dan {len(result['products'])} ürün çekildi!")
        return result, "apify"
    
    # 2. Apify fail oldu, Perplexity'ye geç
    if PERPLEXITY_KEY:
        st.warning(f"⚠️ Apify yetersiz, Perplexity deneniyor...")
        result = search_sonar(brand, product_local, product_english, country, currency_code, url, PERPLEXITY_KEY)
        
        if result and result.get("products"):
            st.success(f"✅ Perplexity'den {len(result['products'])} ürün çekildi!")
            return result, "perplexity"
    
    return None, None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 style="color:#4da6ff;">🧿 LCW HOME</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e; font-size:12px;">COMPETITOR PRICE TRACKER</p>', unsafe_allow_html=True)
    
    if not APIFY_KEY:
        st.error("❌ APIFY_API_KEY eksik!")
        st.stop()
    
    if not PERPLEXITY_KEY:
        st.warning("⚠️ PERPLEXITY_API_KEY yok (Yedek çalışmaz)")
    
    st.markdown("---")
    
    # Scraping metodu seçimi
    scrape_method = st.radio(
        "🔧 Scraping Yöntemi",
        ["Hybrid (Apify + Perplexity)", "Sadece Apify", "Sadece Perplexity"],
        help="Hybrid: Önce Apify, sonra Perplexity dener"
    )
    
    st.markdown("---")
    
    available_countries = list(URL_DB.keys())
    sel_country = st.selectbox("🌍 Ülke", available_countries)
    
    available_brands = [b for b in BRANDS if URL_DB.get(sel_country, {}).get(b)]
    sel_brands = st.multiselect(
        "🏪 Markalar", 
        available_brands, 
        default=available_brands[:3] if len(available_brands) >= 3 else available_brands
    )
    
    q_tr = st.text_input("🛍️ Ürün (Türkçe)", "Yüz Havlusu")
    
    st.markdown("---")
    btn_start = st.button("🚀 FİYATLARI ÇEK", use_container_width=True)

# --- KURLAR ---
rates = get_rates()
conf = COUNTRIES_META.get(sel_country, {"curr": "USD", "lang": "en"})
curr = conf["curr"]

if rates:
    with st.sidebar:
        st.markdown("### 💱 Kurlar")
        c1, c2 = st.columns(2)
        c1.metric("USD", f"{rates.get('USD',0):.2f}₺")
        c2.metric(curr, f"{rates.get(curr,0):.2f}₺")

# --- ANA İŞLEM ---
if btn_start:
    if not rates: 
        st.error("❌ Kur verisi alınamadı"); 
        st.stop()
    
    if not sel_brands: 
        st.error("❌ En az 1 marka seçin"); 
        st.stop()
    
    q_local = translate_logic(q_tr, "to_local", conf["lang"])
    q_english = translate_logic(q_tr, "to_english")
    
    st.info(f"🔎 Aranıyor: **{q_local}** (Yerel) | **{q_english}** (Global)")
    
    all_results = []
    usd_rate = rates.get("USD", 1)
    loc_rate = rates.get(curr, 1)
    
    progress = st.progress(0, text="Markalar taranıyor...")
    
    for idx, brand in enumerate(sel_brands):
        target_url = URL_DB.get(sel_country, {}).get(brand)
        
        if not target_url:
            st.warning(f"⚠️ {brand} - {sel_country} mevcut değil")
            continue
        
        progress.progress((idx + 1) / len(sel_brands), text=f"🔍 {brand} taranıyor...")
        
        # Scraping yöntemini seç
        if scrape_method == "Hybrid (Apify + Perplexity)":
            data, method = hybrid_scrape(brand, q_local, q_english, sel_country, curr, target_url)
        elif scrape_method == "Sadece Apify":
            data = scrape_with_apify(brand, q_local, q_english, target_url, curr)
            method = "apify"
        else:  # Sadece Perplexity
            data = search_sonar(brand, q_local, q_english, sel_country, curr, target_url, PERPLEXITY_KEY)
            method = "perplexity"
        
        if data and "products" in data and len(data["products"]) > 0:
            for p in data["products"]:
                loc_name = p.get("name", "Bilinmiyor")
                is_valid, eng_name = validate_relevance(loc_name, q_english)
                
                if is_valid:
                    p_raw = clean_price(p.get("price", 0), curr)
                    if p_raw > 0:
                        p_tl = p_raw * loc_rate
                        p_usd = p_tl / usd_rate
                        tr_name = translate_logic(loc_name, "to_turkish")
                        
                        all_results.append({
                            "Marka": brand,
                            "Ülke": sel_country,
                            "Ürün Yerel": loc_name,
                            "Ürün Türkçe": tr_name,
                            f"Fiyat ({curr})": p_raw,
                            "USD": p_usd,
                            "TL": p_tl,
                            "Link": p.get("url", ""),
                            "Kaynak": method.upper()
                        })
        
        time.sleep(1)  # Rate limiting
    
    progress.empty()
    
    if all_results:
        df = pd.DataFrame(all_results)
        st.session_state['search_results'] = {"df": df, "curr": curr}
    else:
        st.error("⚠️ Hiçbir markada ürün bulunamadı")
        st.session_state['search_results'] = None

# --- RENDER ---
if st.session_state['search_results']:
    res = st.session_state['search_results']
    df = res["df"]
    curr = res["curr"]
    
    # Kurları al
    rates = get_rates()
    usd_rate = rates.get("USD", 1) if rates else 1
    loc_rate = rates.get(curr, 1) if rates else 1
    
    # Metrikler
    cnt = len(df)
    avg_tl = df["TL"].mean()
    min_tl = df["TL"].min()
    max_tl = df["TL"].max()
    
    # Yerel ve USD hesapla
    avg_usd = avg_tl / usd_rate
    min_usd = min_tl / usd_rate
    max_usd = max_tl / usd_rate
    
    avg_local = avg_tl / loc_rate
    min_local = min_tl / loc_rate
    max_local = max_tl / loc_rate
    
    k1, k2, k3, k4 = st.columns(4)
    
    k1.metric("Toplam Ürün", f"{cnt} adet")
    
    k2.markdown(f"""
    <div style='background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; text-align: center;'>
        <p style='color: #8b949e; font-size: 14px; margin: 0;'>Ortalama</p>
        <p style='color: #ffffff; font-size: 28px; font-weight: bold; margin: 5px 0;'>{avg_tl:,.0f}₺</p>
        <p style='color: #8b949e; font-size: 12px; margin: 0;'>${avg_usd:,.2f} | {avg_local:,.2f} {curr}</p>
    </div>
    """, unsafe_allow_html=True)
    
    k3.markdown(f"""
    <div style='background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; text-align: center;'>
        <p style='color: #8b949e; font-size: 14px; margin: 0;'>En Düşük</p>
        <p style='color: #ffffff; font-size: 28px; font-weight: bold; margin: 5px 0;'>{min_tl:,.0f}₺</p>
        <p style='color: #8b949e; font-size: 12px; margin: 0;'>${min_usd:,.2f} | {min_local:,.2f} {curr}</p>
    </div>
    """, unsafe_allow_html=True)
    
    k4.markdown(f"""
    <div style='background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; text-align: center;'>
        <p style='color: #8b949e; font-size: 14px; margin: 0;'>En Yüksek</p>
        <p style='color: #ffffff; font-size: 28px; font-weight: bold; margin: 5px 0;'>{max_tl:,.0f}₺</p>
        <p style='color: #8b949e; font-size: 12px; margin: 0;'>${max_usd:,.2f} | {max_local:,.2f} {curr}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Kaynak dağılımı göster
    if "Kaynak" in df.columns:
        source_counts = df["Kaynak"].value_counts()
        st.markdown("### 📊 Veri Kaynakları")
        cols = st.columns(len(source_counts))
        for idx, (source, count) in enumerate(source_counts.items()):
            cols[idx].metric(source, f"{count} ürün")
        st.markdown("---")
    
    st.dataframe(
        df,
        column_config={
            "Link": st.column_config.LinkColumn("Link", display_text="🔗 Git"),
            f"Fiyat ({curr})": st.column_config.NumberColumn(f"Fiyat ({curr})", format="%.2f"),
            "USD": st.column_config.NumberColumn("USD ($)", format="$%.2f"),
            "TL": st.column_config.NumberColumn("TL (₺)", format="%.2f ₺")
        },
        use_container_width=True,
        hide_index=True,
        height=500
    )
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("💾 CSV İndir", csv, f"lcw_{sel_country}.csv", "text/csv", use_container_width=True)
