import streamlit as st
import pandas as pd
import os
import json
import requests
import re
from deep_translator import GoogleTranslator
from datetime import datetime
import hashlib
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from rapidfuzz import fuzz
import plotly.express as px
import plotly.graph_objects as go

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    .insight-box { background-color: #1a1f2e; border-left: 4px solid #4da6ff; padding: 15px; margin: 10px 0; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
st.markdown("<h1>LCW HOME | GLOBAL INTELLIGENCE</h1>", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = None
if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []
if 'last_search_time' not in st.session_state:
    st.session_state['last_search_time'] = {}

# --- HARDCODED URL DB ---
URL_DB = {
    "Bulgaristan": { "Pepco": "https://pepco.bg/", "Sinsay": "https://www.sinsay.com/bg/bg/", "Zara Home": "https://www.zarahome.com/bg/", "H&M Home": "https://www2.hm.com/bg_bg/home.html", "Jysk": "https://jysk.bg/", "Jumbo": "https://www.jumbo.bg/", "English Home": "https://englishhome.bg/", "Primark": "https://www.primark.com/en-us" },
    "Bosna Hersek": { "Pepco": "https://pepco.ba/", "Sinsay": "https://www.sinsay.com/ba/bs/", "Zara Home": "https://www.zarahome.com/ba/", "H&M Home": "https://www.hm.com/ba", "Jysk": "https://jysk.ba/", "Jumbo": "https://www.jumbo.ba/", "English Home": "https://englishhome.ba/", "Primark": None },
    "Yunanistan": { "Pepco": "https://pepco.gr/", "Sinsay": "https://www.sinsay.com/gr/el/", "Zara Home": "https://www.zarahome.com/gr/", "H&M Home": "https://www2.hm.com/en_gr/home.html", "Jysk": "https://jysk.gr/", "Jumbo": "https://www.e-jumbo.gr/", "English Home": "https://englishhome.gr/", "Primark": None },
    "Romanya": { "Pepco": "https://pepco.ro/", "Sinsay": "https://www.sinsay.com/ro/ro/", "Zara Home": "https://www.zarahome.com/ro/", "H&M Home": "https://www2.hm.com/ro_ro/home.html", "Jysk": "https://jysk.ro/", "Jumbo": "https://www.jumbo.ro/", "English Home": "https://englishhome.ro/", "Primark": "https://www.primark.com/ro" },
    "Sırbistan": { "Pepco": "https://pepco.rs/", "Sinsay": "https://www.sinsay.com/rs/sr/", "Zara Home": "https://www.zarahome.com/rs/", "H&M Home": "https://www2.hm.com/rs_en/home.html", "Jysk": "https://jysk.rs/", "Jumbo": "https://www.jumbo.rs/", "English Home": "https://englishhome.rs/", "Primark": None },
    "Hırvatistan": { "Pepco": "https://pepco.hr/", "Sinsay": "https://www.sinsay.com/hr/hr/", "Zara Home": "https://www.zarahome.com/hr/", "H&M Home": "https://www2.hm.com/hr_hr/home.html", "Jysk": "https://jysk.hr/", "Jumbo": None, "English Home": None, "Primark": None },
    "Kazakistan": { "Pepco": None, "Sinsay": "https://www.sinsay.com/kz/ru/", "Zara Home": "https://www.zarahome.com/kz/", "H&M Home": "https://www.hm.com/kz", "Jysk": "https://jysk.kz/", "Jumbo": None, "English Home": "https://englishhome.kz/", "Primark": None },
    "Rusya": { "Pepco": None, "Sinsay": None, "Zara Home": None, "H&M Home": None, "Jysk": None, "Jumbo": None, "English Home": None, "Primark": None },
    "Ukrayna": { "Pepco": None, "Sinsay": "https://www.sinsay.com/ua/uk/", "Zara Home": "https://www.zarahome.com/ua/", "H&M Home": "https://www.hm.com/ua", "Jysk": "https://jysk.ua/", "Jumbo": None, "English Home": "https://englishhome.ua/", "Primark": None },
    "Mısır": { "Pepco": None, "Sinsay": None, "Zara Home": "https://www.zarahome.com/eg/", "H&M Home": "https://eg.hm.com/en/", "Jysk": "https://jysk.com.eg/", "Jumbo": None, "English Home": "https://englishhome.com.eg/", "Primark": None },
    "Irak": { "Pepco": None, "Sinsay": None, "Zara Home": None, "H&M Home": "https://iq.hm.com/", "Jysk": None, "Jumbo": None, "English Home": None, "Primark": None }
}

COUNTRIES_META = {
    "Bulgaristan":  {"curr": "BGN", "lang": "bg"},
    "Bosna Hersek": {"curr": "BAM", "lang": "bs"},
    "Yunanistan":   {"curr": "EUR", "lang": "el"},
    "Sırbistan":    {"curr": "RSD", "lang": "sr"},
    "Romanya":      {"curr": "RON", "lang": "ro"},
    "Hırvatistan":  {"curr": "EUR", "lang": "hr"},
    "Kazakistan":   {"curr": "KZT", "lang": "kk"},
    "Rusya":        {"curr": "RUB", "lang": "ru"},
    "Ukrayna":      {"curr": "UAH", "lang": "uk"},
    "Mısır":        {"curr": "EGP", "lang": "ar"},
    "Irak":         {"curr": "IQD", "lang": "ar"},
}

BRANDS = ["Pepco", "Sinsay", "Zara Home", "H&M Home", "Jysk", "Primark", "Jumbo", "English Home"]

# --- RATE LIMITER CLASS ---
class RateLimiter:
    def __init__(self, calls_per_minute=8):
        self.calls = []
        self.limit = calls_per_minute
    
    def wait_if_needed(self):
        now = time.time()
        self.calls = [c for c in self.calls if now - c < 60]
        
        if len(self.calls) >= self.limit:
            sleep_time = 60 - (now - self.calls[0])
            st.info(f"⏳ API Rate Limit - {sleep_time:.0f} saniye bekleniyor...")
            time.sleep(sleep_time)
            self.calls = []
        
        self.calls.append(now)

rate_limiter = RateLimiter(calls_per_minute=8)

# --- FONKSİYONLAR ---

@st.cache_data(ttl=3600)
def get_rates():
    """Döviz kurlarını çek ve cache'le"""
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/TRY", timeout=10).json()['rates']
        rates = {k: 1/v for k, v in r.items() if v > 0} 
        if "EUR" in rates: 
            rates["BAM"] = rates["EUR"] / 1.95583
        logger.info("✅ Kurlar başarıyla çekildi")
        return rates
    except Exception as e:
        logger.error(f"❌ Kur çekme hatası: {e}")
        st.error("⚠️ Döviz kurları yüklenemedi. Varsayılan değerler kullanılıyor.")
        return {
            "USD": 34.50, "EUR": 37.20, "BGN": 19.01, "BAM": 19.01,
            "RSD": 0.32, "RON": 7.48, "KZT": 0.07, "UAH": 0.83,
            "EGP": 0.69, "IQD": 0.026
        }

def translate_logic(text, mode="to_local", target_lang="en"):
    """Çeviri fonksiyonu - hata yönetimi ile"""
    if not text or text.strip() == "":
        return text
    
    try:
        if mode == "to_local":
            result = GoogleTranslator(source='auto', target=target_lang).translate(text)
        elif mode == "to_english":
            result = GoogleTranslator(source='auto', target='en').translate(text)
        else:
            result = GoogleTranslator(source='auto', target='tr').translate(text)
        return result if result else text
    except Exception as e:
        logger.warning(f"⚠️ Çeviri hatası: {e}")
        return text

def clean_price(price_raw, currency_code="USD"):
    """Fiyat temizleme - geliştirilmiş regex"""
    if not price_raw: 
        return 0.0
    
    s = str(price_raw).lower()
    
    # Gereksiz kelimeleri temizle
    noise_words = ["from", "start", "to", "price", "fiyat", "only", "de la", "desde", "preț"]
    for word in noise_words:
        s = s.replace(word, "")
    
    # Para birimi sembollerini temizle
    currency_symbols = ["rsd", "din", "km", "bam", "лв", "bgn", "eur", "ron", "lei", "tl", 
                       "try", "huf", "ft", "$", "€", "£", "kzt", "₸", "uah", "₴"]
    for symbol in currency_symbols:
        s = s.replace(symbol, "")
    
    s = s.strip()
    s = re.sub(r'[^\d.,]', '', s)
    
    if not s: 
        return 0.0
    
    try:
        # Binlik ayırıcı ve ondalık nokta kontrolü
        if ',' in s and '.' in s:
            if s.rfind(',') > s.rfind('.'):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        elif ',' in s:
            if len(s.split(',')[-1]) == 2:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '.')
        
        return float(s)
    except Exception as e:
        logger.warning(f"⚠️ Fiyat parse hatası: {price_raw} -> {e}")
        return 0.0

def validate_relevance_improved(product_name_local, query_english):
    """Fuzzy matching ile geliştirilmiş doğrulama"""
    try:
        prod_en = GoogleTranslator(source='auto', target='en').translate(product_name_local).lower()
        q_en = query_english.lower()
        
        # Fuzzy matching score
        similarity = fuzz.partial_ratio(q_en, prod_en)
        
        # Keyword extraction
        q_keywords = set(word for word in q_en.split() if len(word) > 2)
        p_keywords = set(word for word in prod_en.split() if len(word) > 2)
        
        # Ortak kelimeler
        common_words = q_keywords & p_keywords
        
        # Scoring sistemi
        if similarity > 75:
            return True, prod_en, "🟢 High Match"
        elif similarity > 55 or len(common_words) >= 2:
            return True, prod_en, "🟡 Partial Match"
        elif any(kw in prod_en for kw in q_keywords):
            return True, prod_en, "🟠 Keyword Match"
        else:
            return False, prod_en, "🔴 No Match"
            
    except Exception as e:
        logger.warning(f"⚠️ Validation hatası: {e}")
        return True, product_name_local, "⚪ Unknown"

def get_cache_key(brand, product, country, currency):
    """Cache key oluştur"""
    key_string = f"{brand}_{product}_{country}_{currency}"
    return hashlib.md5(key_string.encode()).hexdigest()

@st.cache_data(ttl=86400, show_spinner=False)
def search_sonar_cached(brand, product_local, product_english, country, currency_code, hardcoded_url, cache_key):
    """Cached Perplexity API çağrısı"""
    return search_sonar(brand, product_local, product_english, country, currency_code, hardcoded_url)

def search_sonar(brand, product_local, product_english, country, currency_code, hardcoded_url):
    """Perplexity Sonar API ile ürün arama - Geliştirilmiş"""
    url = "https://api.perplexity.ai/chat/completions"
    domain = hardcoded_url.replace("https://", "").replace("http://", "").split("/")[0]

    system_msg = """You are an expert e-commerce product data scraper. 
Your task is to extract comprehensive product listings with accurate prices.
CRITICAL RULES:
1. Extract AT LEAST 15-20 products if available
2. Include different sizes, colors, and variants
3. Ensure prices are numerical and accurate
4. Include direct product URLs
5. Return ONLY valid JSON, no explanations"""
    
    user_msg = f"""
TASK: Search {hardcoded_url} for '{product_english}' (local term: '{product_local}')

REQUIREMENTS:
- Find the category page or search results
- Extract MINIMUM 15-20 products (aim for 30+ if available)
- Include various sizes (e.g., 50x90cm, 70x140cm, etc.)
- Include different colors and models
- Get accurate numerical prices in {currency_code}

OUTPUT FORMAT (JSON only):
{{
    "products": [
        {{
            "name": "Product Full Name",
            "price": "19.99",
            "size": "50x90 cm",
            "color": "Blue",
            "url": "full_product_url"
        }}
    ],
    "total_found": 25,
    "category_url": "category_page_url"
}}

IMPORTANT: Return comprehensive product list, not just top results.
"""
    
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": system_msg}, 
            {"role": "user", "content": user_msg}
        ],
        "temperature": 0.1,
        "max_tokens": 4000
    }
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        rate_limiter.wait_if_needed()
        
        res = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if res.status_code == 200:
            raw = res.json()['choices'][0]['message']['content']
            
            # JSON extraction
            clean = raw.replace("```json", "").replace("```", "").strip()
            start = clean.find("{")
            end = clean.rfind("}")
            
            if start != -1 and end != -1:
                clean = clean[start:end+1]
                data = json.loads(clean)
                
                # Veri kalitesi kontrolü
                if "products" in data and len(data["products"]) > 0:
                    logger.info(f"✅ {brand} - {len(data['products'])} ürün bulundu")
                    return data
                else:
                    logger.warning(f"⚠️ {brand} - Boş sonuç")
                    return None
            else:
                logger.error(f"❌ {brand} - JSON parse edilemedi")
                with st.expander(f"🔍 {brand} Raw Response (Debug)"):
                    st.code(raw)
                return None
        
        elif res.status_code == 429:
            st.error("⚠️ API Rate Limit aşıldı. 1 dakika bekleyin.")
            time.sleep(60)
            return None
        
        else:
            logger.error(f"❌ API Error {res.status_code}: {res.text}")
            st.error(f"API Hatası: {res.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"⏱️ Timeout: {hardcoded_url}")
        st.warning(f"⏱️ {brand} yanıt vermedi (timeout)")
        return None
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON Decode Error: {e}")
        st.error(f"🤖 {brand} - AI beklenmeyen format döndü")
        return None
        
    except Exception as e:
        logger.exception(f"❌ Unexpected error: {e}")
        st.error(f"❌ {brand} - Beklenmeyen hata: {type(e).__name__}")
        return None

def generate_insights(df):
    """Otomatik analiz insights"""
    if df.empty:
        return []
    
    insights = []
    
    try:
        # En ucuz ürün
        cheapest = df.nsmallest(1, 'TL').iloc[0]
        insights.append(f"💰 **En Uygun:** {cheapest['Ürün Türkçe Adı'][:50]}... - **{cheapest['TL']:.0f}₺** ({cheapest['Marka']})")
        
        # En pahalı ürün
        expensive = df.nlargest(1, 'TL').iloc[0]
        insights.append(f"💎 **En Pahalı:** {expensive['Ürün Türkçe Adı'][:50]}... - **{expensive['TL']:.0f}₺** ({expensive['Marka']})")
        
        # Fiyat aralığı analizi
        price_range = df['TL'].max() - df['TL'].min()
        avg_price = df['TL'].mean()
        variance_pct = (price_range / avg_price) * 100 if avg_price > 0 else 0
        
        if variance_pct > 80:
            insights.append(f"📊 **Fiyat Varyasyonu Çok Yüksek:** %{variance_pct:.0f} - Dikkatli seçim yapın!")
        elif variance_pct > 50:
            insights.append(f"📊 **Orta Seviye Fiyat Farkı:** %{variance_pct:.0f}")
        else:
            insights.append(f"📊 **Fiyatlar Tutarlı:** %{variance_pct:.0f} varyasyon")
        
        # Marka bazlı analiz (eğer birden fazla marka varsa)
        if df['Marka'].nunique() > 1:
            brand_avg = df.groupby('Marka')['TL'].mean().sort_values()
            cheapest_brand = brand_avg.index[0]
            expensive_brand = brand_avg.index[-1]
            
            insights.append(f"🏆 **En Ekonomik Marka:** {cheapest_brand} (Ort: {brand_avg.iloc[0]:.0f}₺)")
            insights.append(f"💸 **En Pahalı Marka:** {expensive_brand} (Ort: {brand_avg.iloc[-1]:.0f}₺)")
        
        # Ülke bazlı öneri (eğer birden fazla ülke varsa)
        if df['Ülke'].nunique() > 1:
            country_avg = df.groupby('Ülke')['TL'].mean().sort_values()
            best_country = country_avg.index[0]
            insights.append(f"🌍 **En Avantajlı Pazar:** {best_country} (Ort: {country_avg.iloc[0]:.0f}₺)")
        
    except Exception as e:
        logger.error(f"Insight generation error: {e}")
    
    return insights

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 style="color:#4da6ff; margin-bottom:0;">LCW HOME</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e; font-size:12px;">COMPETITOR PRICE TRACKER v2.0</p>', unsafe_allow_html=True)
    
    PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY") or st.text_input("🔑 Perplexity API Key", type="password")
    
    if not PERPLEXITY_KEY: 
        st.warning("⚠️ API Key Gerekli")
        st.stop()
    
    st.markdown("---")
    
    # Gelişmiş filtreler
    st.header("🔎 Arama Filtreleri")
    
    search_mode = st.radio("Mod Seç", ["Tek Ülke/Marka", "Çoklu Karşılaştırma"])
    
    if search_mode == "Tek Ülke/Marka":
        available_countries = list(URL_DB.keys())
        sel_country = st.selectbox("Ülke", available_countries)
        sel_brands = [st.selectbox("Marka", BRANDS)]
    else:
        available_countries = list(URL_DB.keys())
        sel_country = st.selectbox("Ülke", available_countries)
        sel_brands = st.multiselect("Markalar (max 4)", BRANDS, default=["Pepco", "Zara Home"], max_selections=4)
        
        if not sel_brands:
            st.warning("En az 1 marka seç")
            sel_brands = ["Pepco"]
    
    q_tr = st.text_input("Ürün (Türkçe)", "Yüz Havlusu")
    
    st.markdown("---")
    
    # Gelişmiş ayarlar
    with st.expander("⚙️ Gelişmiş Ayarlar"):
        show_raw_data = st.checkbox("Ham API yanıtlarını göster", value=False)
        min_price_filter = st.number_input("Min Fiyat (TL)", min_value=0, value=0)
        max_price_filter = st.number_input("Max Fiyat (TL)", min_value=0, value=10000)
    
    btn_start = st.button("🚀 FİYATLARI ÇEK", type="primary")

# --- KURLAR ---
rates = get_rates()
conf = COUNTRIES_META.get(sel_country, {"curr": "USD", "lang": "en"})
curr = conf["curr"]

if rates:
    with st.sidebar:
        st.markdown("### 💱 Güncel Kurlar")
        c1, c2 = st.columns(2)
        c1.metric("USD", f"{rates.get('USD',0):.2f}₺")
        c2.metric(curr, f"{rates.get(curr,0):.2f}₺")

# --- ANA İŞLEM ---
if btn_start:
    if not rates: 
        st.error("❌ Kur verisi alınamadı. Lütfen internet bağlantınızı kontrol edin.")
        st.stop()
    
    all_results = []
    
    for sel_brand in sel_brands:
        target_url = URL_DB.get(sel_country, {}).get(sel_brand)
        
        if not target_url:
            st.warning(f"⚠️ {sel_brand} markasının {sel_country} için mağazası yok - atlanıyor")
            continue
        
        st.info(f"🎯 {sel_brand} taranıyor: {target_url}")
        
        q_local = translate_logic(q_tr, "to_local", conf["lang"])
        q_english = translate_logic(q_tr, "to_english")
        
        # Cache kontrolü
        cache_key = get_cache_key(sel_brand, q_tr, sel_country, curr)
        
        with st.spinner(f"🧿 {sel_brand} mağazası taranıyor... (Min 15 ürün hedefleniyor)"):
            data = search_sonar_cached(sel_brand, q_local, q_english, sel_country, curr, target_url, cache_key)
        
        if show_raw_data and data:
            with st.expander(f"🔍 {sel_brand} - Raw API Response"):
                st.json(data)
        
        if data and "products" in data and len(data["products"]) > 0:
            rows = []
            prices_tl = []
            usd_rate = rates.get("USD", 1)
            loc_rate = rates.get(curr, 1)
            
            pbar = st.progress(0, text=f"{sel_brand} ürünleri işleniyor...")
            tot = len(data["products"])
            
            valid_count = 0
            match_qualities = []
            
            for i, p in enumerate(data["products"]):
                loc_name = p.get("name", "Bilinmiyor")
                
                # Geliştirilmiş doğrulama
                is_valid, eng_name_check, match_quality = validate_relevance_improved(loc_name, q_english)
                
                if is_valid:
                    p_raw = clean_price(p.get("price", 0), curr)
                    
                    if p_raw > 0:
                        p_tl = p_raw * loc_rate
                        p_usd = p_tl / usd_rate
                        
                        # Fiyat filtreleme
                        if min_price_filter <= p_tl <= max_price_filter or (min_price_filter == 0 and max_price_filter == 10000):
                            prices_tl.append(p_tl)
                            
                            tr_name = translate_logic(loc_name, "to_turkish")
                            
                            rows.append({
                                "Marka": sel_brand,
                                "Ülke": sel_country,
                                "Ürün Yerel Adı": loc_name,
                                "Ürün Türkçe Adı": tr_name,
                                "Yerel Fiyat": p_raw,
                                "USD": p_usd,
                                "TL": p_tl,
                                "Match Quality": match_quality,
                                "Link": p.get("url", "")
                            })
                            match_qualities.append(match_quality)
                            valid_count += 1
                
                pbar.progress((i + 1) / tot, text=f"{sel_brand}: {valid_count} geçerli ürün bulundu")
            
            pbar.empty()
            
            if rows:
                st.success(f"✅ {sel_brand}: {valid_count} ürün başarıyla eklendi")
                all_results.extend(rows)
            else:
                st.error(f"⚠️ {sel_brand}: Ürünler filtreye takıldı. Aranan: '{q_english}'")
        
        else:
            st.error(f"❌ {sel_brand}: Sonuç bulunamadı")
    
    # Tüm sonuçları birleştir
    if all_results:
        df = pd.DataFrame(all_results)
        cols = ["Marka", "Ülke", "Ürün Yerel Adı", "Ürün Türkçe Adı", "Yerel Fiyat", "USD", "TL", "Match Quality", "Link"]
        df = df[cols]
        
        st.session_state['search_results'] = {
            "df": df,
            "search_time": datetime.now(),
            "query": q_tr,
            "country": sel_country,
            "brands": sel_brands
        }
    else:
        st.error("❌ Hiçbir markadan sonuç alınamadı")
        st.session_state['search_results'] = None

# --- RENDER RESULTS ---
if st.session_state['search_results'] is not None:
    res = st.session_state['search_results']
    df = res["df"]
    
    cnt = len(df)
    
    if cnt > 0:
        # Metrikler
        prices_tl = df['TL'].tolist()
        avg = df['TL'].mean()
        mn = df['TL'].min()
        mx = df['TL'].max()
        usd_rate = rates.get("USD", 1)
        loc_rate = rates.get(curr, 1)
        
        def fmt(val): 
            return f"{val:,.0f}₺\n(${val/usd_rate:,.1f})\n({val/loc_rate:,.1f} {curr})"

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Bulunan Ürün", f"{cnt} Adet")
        k2.metric("Ortalama", "Ort.", delta_color="off")
        k2.markdown(f"<div style='text-align:center;color:white;font-weight:bold;margin-top:-20px;white-space:pre-wrap;'>{fmt(avg)}</div>", unsafe_allow_html=True)
        k3.metric("En Düşük", "Min", delta_color="off")
        k3.markdown(f"<div style='text-align:center;color:white;font-weight:bold;margin-top:-20px;white-space:pre-wrap;'>{fmt(mn)}</div>", unsafe_allow_html=True)
        k4.metric("En Yüksek", "Max", delta_color="off")
        k4.markdown(f"<div style='text-align:center;color:white;font-weight:bold;margin-top:-20px;white-space:pre-wrap;'>{fmt(mx)}</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Insights
        insights = generate_insights(df)
        if insights:
            st.markdown("### 💡 Analiz Önerileri")
            for insight in insights:
                st.markdown(f"<div class='insight-box'>{insight}</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Görselleştirmeler
        if len(sel_brands) > 1 or df['Marka'].nunique() > 1:
            st.markdown("### 📊 Fiyat Karşılaştırmaları")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Marka bazlı box plot
                fig_box = px.box(df, x="Marka", y="TL", color="Marka",
                               title="Marka Bazlı Fiyat Dağılımı",
                               labels={"TL": "Fiyat (₺)", "Marka": ""},
                               template="plotly_dark")
                fig_box.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig_box, use_container_width=True)
            
            with col2:
                # Marka bazlı ortalama fiyat
                brand_avg = df.groupby('Marka')['TL'].mean().sort_values()
                fig_bar = px.bar(brand_avg, orientation='h',
                               title="Marka Ortalama Fiyatları",
                               labels={"value": "Ortalama Fiyat (₺)", "Marka": ""},
                               template="plotly_dark")
                fig_bar.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig_bar, use_container_width=True)
        
        # Fiyat dağılımı histogram
        fig_hist = px.histogram(df, x="TL", nbins=20, 
                               title="Fiyat Dağılımı",
                               labels={"TL": "Fiyat (₺)", "count": "Ürün Sayısı"},
                               template="plotly_dark")
        fig_hist.update_layout(height=300)
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.markdown("---")
        
        # Veri tablosu
        st.markdown("### 📋 Detaylı Sonuçlar")
        
        st.dataframe(
            df,
            column_config={
                "Link": st.column_config.LinkColumn("Link", display_text="🔗 Git"),
                "Yerel Fiyat": st.column_config.NumberColumn(f"Fiyat ({curr})", format="%.2f"),
                "USD": st.column_config.NumberColumn("USD ($)", format="$%.2f"),
                "TL": st.column_config.NumberColumn("TL (₺)", format="%.2f ₺"),
                "Match Quality": st.column_config.TextColumn("Eşleşme Kalitesi")
            },
            use_container_width=True,
            hide_index=True,
            height=500
        )
        
        # Export seçenekleri
        st.markdown("### 💾 İndir")
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 CSV İndir",
                csv,
                f"lcw_analiz_{res['country']}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col_exp2:
            # Excel export (openpyxl ile)
            try:
                from io import BytesIO
                output = BytesIO()
                
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Fiyatlar', index=False)
                    
                    workbook = writer.book
                    worksheet = writer.sheets['Fiyatlar']
                    
                    # Format ayarları
                    header_format = workbook.add_format({
                        'bold': True,
                        'bg_color': '#4da6ff',
                        'font_color': 'white',
                        'border': 1
                    })
                    
                    for col_num, value in enumerate(df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                        worksheet.set_column(col_num, col_num, 20)
                
                excel_data = output.getvalue()
                
                st.download_button(
                    "📊 Excel İndir",
                    excel_data,
                    f"lcw_analiz_{res['country']}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except ImportError:
                st.warning("Excel export için xlsxwriter yükle: pip install xlsxwriter")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#8b949e; font-size:12px;'>"
    f"LCW Global Intelligence v2.0 | Son Arama: {res.get('search_time', 'N/A') if st.session_state['search_results'] else 'Henüz arama yapılmadı'}"
    "</div>",
    unsafe_allow_html=True
)
