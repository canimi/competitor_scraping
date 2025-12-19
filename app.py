import streamlit as st
import pandas as pd
import os
import json
import requests
import re
import time
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup

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

st.markdown("<h1>🧿 LCW HOME | GLOBAL INTELLIGENCE</h1>", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = None

# --- API KEYS ---
PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY") or st.secrets.get("PERPLEXITY_API_KEY", "")
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY") or st.secrets.get("SCRAPER_API_KEY", "")

# --- URL DATABASE ---
URL_DB = {
    "Bulgaristan": { 
        "Pepco": {"base": "https://pepco.bg/", "search": "bg-bg/search?q={query}"}, 
        "Sinsay": {"base": "https://www.sinsay.com/bg/bg/", "search": "search?q={query}"}, 
        "Zara Home": {"base": "https://www.zarahome.com/bg/", "search": "search?searchTerm={query}"}, 
        "H&M Home": {"base": "https://www2.hm.com/bg_bg/", "search": "search?q={query}"}, 
        "Jysk": {"base": "https://jysk.bg/", "search": "search?query={query}"}, 
        "English Home": {"base": "https://englishhome.bg/", "search": "arama?q={query}"}
    },
    "Bosna Hersek": { 
        "Pepco": {"base": "https://pepco.ba/", "search": "ba-ba/search?q={query}"}, 
        "Sinsay": {"base": "https://www.sinsay.com/ba/bs/", "search": "search?q={query}"}, 
        "Zara Home": {"base": "https://www.zarahome.com/ba/", "search": "search?searchTerm={query}"}, 
        "Jysk": {"base": "https://jysk.ba/", "search": "search?query={query}"}, 
        "English Home": {"base": "https://englishhome.ba/", "search": "arama?q={query}"}
    },
    "Sırbistan": { 
        "Pepco": {"base": "https://pepco.rs/", "search": "rs-sr/search?q={query}"}, 
        "Sinsay": {"base": "https://www.sinsay.com/rs/sr/", "search": "search?q={query}"}, 
        "Zara Home": {"base": "https://www.zarahome.com/rs/", "search": "search?searchTerm={query}"}, 
        "Jysk": {"base": "https://jysk.rs/", "search": "search?query={query}"}, 
        "English Home": {"base": "https://englishhome.rs/", "search": "arama?q={query}"}
    },
}

# --- SITE SELECTORS ---
SITE_SELECTORS = {
    "Pepco": {
        "product": ["div.product-tile", "div[class*='product']"],
        "name": ["h3.product-tile-name", "a.product-tile-link", "h3", "h2"],
        "price": ["span.product-tile-price-value", "span[class*='price']", ".price"]
    },
    "Sinsay": {
        "product": ["article.product", "div.product-tile", "div[class*='product']"],
        "name": ["h2.product-name", "h3.product-title", "a.product-link"],
        "price": ["span.price", "span[class*='price']", ".price"]
    },
    "Zara Home": {
        "product": ["li.product-grid-item", "div.product-grid-product", "article"],
        "name": ["a.product-link", "h2.product-detail-info__header-name"],
        "price": ["span.price-current__amount", "span.money-amount__main"]
    },
}

COUNTRIES_META = {
    "Bulgaristan":  {"curr": "BGN", "lang": "bg"},
    "Bosna Hersek": {"curr": "BAM", "lang": "bs"},
    "Sırbistan":    {"curr": "RSD", "lang": "sr"},
}

BRANDS = ["Pepco", "Sinsay", "Zara Home", "H&M Home", "Jysk", "English Home"]

# --- FONKSİYONLAR ---
@st.cache_data(ttl=3600)
def get_rates():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/TRY", timeout=10).json()['rates']
        rates = {k: 1/v for k, v in r.items() if v > 0}
        if "EUR" in rates: rates["BAM"] = rates["EUR"] / 1.95583
        return rates
    except: return None

def translate_logic(text, mode="to_local", target_lang="en"):
    if not text: return text
    try:
        if mode == "to_local":
            return GoogleTranslator(source='auto', target=target_lang).translate(text)
        elif mode == "to_english":
            return GoogleTranslator(source='auto', target='en').translate(text)
        else:
            return GoogleTranslator(source='auto', target='tr').translate(text)
    except: return text

def clean_price(price_raw, currency_code="USD"):
    if not price_raw: return 0.0
    s = str(price_raw).lower()
    for bad in ["from", "start", "to", "price", "fiyat", "only", "now", "was", "de", "от"]:
        s = s.replace(bad, "")
    for code in ["rsd", "din", "km", "bam", "лв", "bgn", "eur", "ron", "lei", "tl", "try", "$", "€", "£", "₺"]:
        s = s.replace(code, "")
    s = re.sub(r'[^\d.,]', '', s.strip())
    if not s: return 0.0
    numbers = re.findall(r'[\d.,]+', s)
    if not numbers: return 0.0
    s = numbers[0]
    try:
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
        elif ',' in s:
            s = s.replace(',', '.') if len(s.split(',')[-1]) == 2 else s.replace(',', '')
        return float(s)
    except: return 0.0

def validate_relevance(product_name, query_english):
    try:
        prod_en = GoogleTranslator(source='auto', target='en').translate(product_name).lower()
        keywords = [k for k in query_english.lower().split() if len(k) > 2]
        main = keywords[-1] if keywords else ""
        if main in prod_en: return True
        return any(k in prod_en for k in keywords)
    except:
        return True

# --- SCRAPERAPI SCRAPER ---
def scrape_with_scraperapi(brand, site_config, product_local):
    """ScraperAPI ile JavaScript render + scraping"""
    
    if not SCRAPER_API_KEY or brand not in SITE_SELECTORS:
        return None
    
    base_url = site_config["base"]
    search_path = site_config["search"].format(query=product_local.replace(" ", "+"))
    full_url = base_url + search_path
    
    api_url = "http://api.scraperapi.com"
    params = {
        "api_key": SCRAPER_API_KEY,
        "url": full_url,
        "render": "true",
        "country_code": "bg"
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=90)
        
        if response.status_code != 200:
            st.warning(f"{brand}: HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        selectors = SITE_SELECTORS[brand]
        products = []
        
        # Ürün kartlarını bul (birden fazla selector dene)
        cards = []
        for product_selector in selectors["product"]:
            cards = soup.select(product_selector)
            if cards:
                break
        
        for card in cards[:20]:
            try:
                # İsim bul
                name = None
                for name_sel in selectors["name"]:
                    elem = card.select_one(name_sel)
                    if elem:
                        name = elem.get_text(strip=True)
                        break
                
                # Fiyat bul
                price = None
                for price_sel in selectors["price"]:
                    elem = card.select_one(price_sel)
                    if elem:
                        price = elem.get_text(strip=True)
                        break
                
                # Link bul
                link_elem = card.select_one("a")
                link = link_elem.get("href", "") if link_elem else ""
                
                if name and price:
                    if link and not link.startswith("http"):
                        link = base_url.rstrip("/") + "/" + link.lstrip("/")
                    
                    products.append({"name": name, "price": price, "url": link})
            except:
                continue
        
        if products:
            return {"products": products}
        return None
        
    except Exception as e:
        st.warning(f"{brand} scraping hatası: {str(e)[:80]}")
        return None

# --- PERPLEXITY (Yedek) ---
def search_sonar(brand, product_local, product_english, site_config):
    if not PERPLEXITY_KEY:
        return None
    
    url = "https://api.perplexity.ai/chat/completions"
    full_url = site_config["base"]
    
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "You are a product data scraper. Extract real products with prices."},
            {"role": "user", "content": f"""
Search for '{product_english}' (local: '{product_local}') on {full_url}

List 10-15 products with EXACT prices.

OUTPUT JSON:
{{"products": [{{"name": "Product 1", "price": "15.99", "url": "link"}}]}}
"""}
        ],
        "temperature": 0.1,
        "max_tokens": 3000
    }
    
    try:
        res = requests.post(url, json=payload, headers={"Authorization": f"Bearer {PERPLEXITY_KEY}", "Content-Type": "application/json"}, timeout=60)
        if res.status_code == 200:
            raw = res.json()['choices'][0]['message']['content']
            clean = raw.replace("``````", "").strip()
            start = clean.find("{")
            end = clean.rfind("}")
            if start != -1 and end != -1:
                return json.loads(clean[start:end+1])
    except: pass
    return None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 style="color:#4da6ff;">🧿 LCW HOME</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e;font-size:12px;">COMPETITOR PRICE TRACKER</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    if not SCRAPER_API_KEY and not PERPLEXITY_KEY:
        st.error("⚠️ En az bir API key gerekli!")
        st.stop()
    
    scrape_method = st.radio("🔧 Scraping Yöntemi", ["Hybrid", "ScraperAPI", "Perplexity"])
    
    st.markdown("---")
    sel_country = st.selectbox("🌍 Ülke", list(URL_DB.keys()))
    available_brands = [b for b in BRANDS if URL_DB.get(sel_country, {}).get(b)]
    sel_brands = st.multiselect("🏪 Markalar", available_brands, default=available_brands[:2] if len(available_brands) >= 2 else available_brands)
    q_tr = st.text_input("🛍️ Ürün (Türkçe)", "Yüz Havlusu")
    
    st.markdown("---")
    btn = st.button("🚀 FİYATLARI ÇEK", use_container_width=True)

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
if btn:
    if not rates: st.error("❌ Kur verisi alınamadı"); st.stop()
    if not sel_brands: st.error("❌ En az 1 marka seçin"); st.stop()
    
    q_local = translate_logic(q_tr, "to_local", conf["lang"])
    q_english = translate_logic(q_tr, "to_english")
    
    st.info(f"🔎 Aranıyor: **{q_local}** (Yerel) | **{q_english}** (Global)")
    
    all_results = []
    usd_rate = rates.get("USD", 1)
    loc_rate = rates.get(curr, 1)
    
    progress = st.progress(0, text="Başlatılıyor...")
    
    for idx, brand in enumerate(sel_brands):
        site_config = URL_DB.get(sel_country, {}).get(brand)
        if not site_config: 
            continue
        
        progress.progress((idx + 1) / len(sel_brands), text=f"🔍 {brand} taranıyor...")
        
        data = None
        method = ""
        
        if scrape_method == "ScraperAPI":
            data = scrape_with_scraperapi(brand, site_config, q_local)
            method = "scraperapi"
        elif scrape_method == "Perplexity":
            data = search_sonar(brand, q_local, q_english, site_config)
            method = "perplexity"
        else:  # Hybrid
            data = scrape_with_scraperapi(brand, site_config, q_local) if SCRAPER_API_KEY else None
            if not data or len(data.get("products", [])) < 3:
                data = search_sonar(brand, q_local, q_english, site_config)
                method = "perplexity"
            else:
                method = "scraperapi"
        
        if data and data.get("products"):
            for p in data["products"]:
                name = p.get("name", "")
                if validate_relevance(name, q_english):
                    p_raw = clean_price(p.get("price", 0), curr)
                    if p_raw > 0:
                        p_tl = p_raw * loc_rate
                        all_results.append({
                            "Marka": brand,
                            "Ürün Yerel": name,
                            "Ürün Türkçe": translate_logic(name, "to_turkish"),
                            f"Fiyat ({curr})": p_raw,
                            "USD": p_tl / usd_rate,
                            "TL": p_tl,
                            "Link": p.get("url", ""),
                            "Kaynak": method.upper()
                        })
        
        time.sleep(2)
    
    progress.empty()
    
    if all_results:
        st.session_state['search_results'] = {"df": pd.DataFrame(all_results), "curr": curr}
        st.success(f"✅ Toplam {len(all_results)} ürün bulundu!")
    else:
        st.error("⚠️ Hiçbir markada ürün bulunamadı")
        st.session_state['search_results'] = None

# --- RENDER ---
if st.session_state['search_results']:
    res = st.session_state['search_results']
    df = res["df"]
    curr = res["curr"]
    
    usd_rate = rates.get("USD", 1)
    loc_rate = rates.get(curr, 1)
    
    cnt = len(df)
    avg_tl = df["TL"].mean()
    min_tl = df["TL"].min()
    max_tl = df["TL"].max()
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Toplam Ürün", f"{cnt} adet")
    
    k2.markdown(f"""
    <div style='background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; text-align: center;'>
        <p style='color: #8b949e; font-size: 14px; margin: 0;'>Ortalama</p>
        <p style='color: #ffffff; font-size: 28px; font-weight: bold; margin: 5px 0;'>{avg_tl:,.0f}₺</p>
        <p style='color: #8b949e; font-size: 12px; margin: 0;'>${avg_tl/usd_rate:,.2f} | {avg_tl/loc_rate:,.2f} {curr}</p>
    </div>
    """, unsafe_allow_html=True)
    
    k3.markdown(f"""
    <div style='background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; text-align: center;'>
        <p style='color: #8b949e; font-size: 14px; margin: 0;'>En Düşük</p>
        <p style='color: #ffffff; font-size: 28px; font-weight: bold; margin: 5px 0;'>{min_tl:,.0f}₺</p>
        <p style='color: #8b949e; font-size: 12px; margin: 0;'>${min_tl/usd_rate:,.2f} | {min_tl/loc_rate:,.2f} {curr}</p>
    </div>
    """, unsafe_allow_html=True)
    
    k4.markdown(f"""
    <div style='background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; text-align: center;'>
        <p style='color: #8b949e; font-size: 14px; margin: 0;'>En Yüksek</p>
        <p style='color: #ffffff; font-size: 28px; font-weight: bold; margin: 5px 0;'>{max_tl:,.0f}₺</p>
        <p style='color: #8b949e; font-size: 12px; margin: 0;'>${max_tl/usd_rate:,.2f} | {max_tl/loc_rate:,.2f} {curr}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Kaynak dağılımı
    if "Kaynak" in df.columns:
        sources = df["Kaynak"].value_counts()
        st.markdown("### 📊 Veri Kaynakları")
        cols = st.columns(len(sources))
        for i, (src, cnt) in enumerate(sources.items()):
            cols[i].metric(src, f"{cnt} ürün")
        st.markdown("---")
    
    st.dataframe(
        df,
        column_config={
            "Link": st.column_config.LinkColumn("🔗 Link", display_text="Git"),
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
