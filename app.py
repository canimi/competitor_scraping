import streamlit as st
import pandas as pd
import os
import json
import requests
import re
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
import hashlib
import time

# ═══════════════════════════════════════════════════════════════════════════════
# LCW GLOBAL INTELLIGENCE v2.0
# Competitor Price Tracking System
# ═══════════════════════════════════════════════════════════════════════════════

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="LCW Global Intelligence",
    layout="wide",
    page_icon="🧿",
    initial_sidebar_state="expanded"
)

# --- GELIŞMIŞ CSS ---
st.markdown("""
<style>
    /* Ana Layout */
    .block-container { padding-top: 1rem !important; padding-bottom: 5rem; max-width: 1400px; }
    header {visibility: hidden;}
    .stApp { background: linear-gradient(135deg, #0e1117 0%, #1a1f2e 100%); font-family: 'Segoe UI', sans-serif; }
    
    /* Başlık */
    .main-title {
        color: #4da6ff;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 3px;
        text-shadow: 0 0 20px rgba(77, 166, 255, 0.5);
        font-size: 2.2rem;
        margin: 0 0 10px 0;
        padding: 20px 0;
    }
    .sub-title {
        color: #8b949e;
        text-align: center;
        font-size: 0.9rem;
        margin-bottom: 30px;
    }
    
    /* Metrik Kartları */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #161b22 0%, #21262d 100%);
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #4da6ff;
    }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-size: 26px !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 13px !important; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid #30363d;
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stMultiSelect label {
        color: #8b949e !important;
        font-size: 12px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Butonlar */
    div.stButton > button {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white;
        border: none;
        padding: 14px 28px;
        font-weight: bold;
        width: 100%;
        border-radius: 10px;
        font-size: 14px;
        letter-spacing: 1px;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #2ea043 0%, #3fb950 100%);
        box-shadow: 0 4px 20px rgba(46, 160, 67, 0.4);
    }
    
    /* Tablo */
    .stDataFrame {
        border: 1px solid #30363d;
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Tab Stilleri */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #161b22;
        padding: 10px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #21262d;
        border-radius: 8px;
        color: #8b949e;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #238636 !important;
        color: white !important;
    }
    
    /* Info/Warning/Error Boxes */
    .stAlert { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; }
    
    /* Progress Bar */
    .stProgress > div > div { background-color: #238636; }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
    }
    
    /* Custom Cards */
    .price-card {
        background: linear-gradient(145deg, #161b22 0%, #21262d 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }
    .price-card-header {
        color: #4da6ff;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .price-card-value {
        color: #ffffff;
        font-size: 24px;
        font-weight: 700;
    }
    .price-card-sub {
        color: #8b949e;
        font-size: 12px;
        margin-top: 5px;
    }
    
    /* Comparison Matrix */
    .matrix-cell {
        text-align: center;
        padding: 10px;
        border-radius: 8px;
    }
    .matrix-cell-cheap { background-color: rgba(46, 160, 67, 0.2); border: 1px solid #238636; }
    .matrix-cell-mid { background-color: rgba(210, 153, 34, 0.2); border: 1px solid #d29922; }
    .matrix-cell-expensive { background-color: rgba(248, 81, 73, 0.2); border: 1px solid #f85149; }
</style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
st.markdown('<h1 class="main-title">🧿 LCW HOME | GLOBAL INTELLIGENCE</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Competitor Price Tracking & Analysis System v2.0</p>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# VERİ YAPILARI
# ═══════════════════════════════════════════════════════════════════════════════

# Genişletilmiş URL Veritabanı
URL_DB = {
    "Bulgaristan": {
        "Pepco": {"url": "https://pepco.bg/", "search_pattern": "/search?q={query}"},
        "Sinsay": {"url": "https://www.sinsay.com/bg/bg/", "search_pattern": "/search?q={query}"},
        "Zara Home": {"url": "https://www.zarahome.com/bg/", "search_pattern": "/search?term={query}"},
        "H&M Home": {"url": "https://www2.hm.com/bg_bg/home.html", "search_pattern": "/search?q={query}"},
        "Jysk": {"url": "https://jysk.bg/", "search_pattern": "/search?query={query}"},
        "Jumbo": {"url": "https://www.jumbo.bg/", "search_pattern": "/search?q={query}"},
        "English Home": {"url": "https://englishhome.bg/", "search_pattern": "/arama?q={query}"},
        "Primark": {"url": "https://www.primark.com/en-us", "search_pattern": "/search?q={query}"},
    },
    "Bosna Hersek": {
        "Pepco": {"url": "https://pepco.ba/", "search_pattern": "/search?q={query}"},
        "Sinsay": {"url": "https://www.sinsay.com/ba/bs/", "search_pattern": "/search?q={query}"},
        "Zara Home": {"url": "https://www.zarahome.com/ba/", "search_pattern": "/search?term={query}"},
        "H&M Home": {"url": "https://www.hm.com/ba", "search_pattern": "/search?q={query}"},
        "Jysk": {"url": "https://jysk.ba/", "search_pattern": "/search?query={query}"},
        "Jumbo": {"url": "https://www.jumbo.ba/", "search_pattern": "/search?q={query}"},
        "English Home": {"url": "https://englishhome.ba/", "search_pattern": "/arama?q={query}"},
    },
    "Yunanistan": {
        "Pepco": {"url": "https://pepco.gr/", "search_pattern": "/search?q={query}"},
        "Sinsay": {"url": "https://www.sinsay.com/gr/el/", "search_pattern": "/search?q={query}"},
        "Zara Home": {"url": "https://www.zarahome.com/gr/", "search_pattern": "/search?term={query}"},
        "H&M Home": {"url": "https://www2.hm.com/en_gr/home.html", "search_pattern": "/search?q={query}"},
        "Jysk": {"url": "https://jysk.gr/", "search_pattern": "/search?query={query}"},
        "Jumbo": {"url": "https://www.e-jumbo.gr/", "search_pattern": "/search?q={query}"},
        "English Home": {"url": "https://englishhome.gr/", "search_pattern": "/arama?q={query}"},
    },
    "Romanya": {
        "Pepco": {"url": "https://pepco.ro/", "search_pattern": "/search?q={query}"},
        "Sinsay": {"url": "https://www.sinsay.com/ro/ro/", "search_pattern": "/search?q={query}"},
        "Zara Home": {"url": "https://www.zarahome.com/ro/", "search_pattern": "/search?term={query}"},
        "H&M Home": {"url": "https://www2.hm.com/ro_ro/home.html", "search_pattern": "/search?q={query}"},
        "Jysk": {"url": "https://jysk.ro/", "search_pattern": "/search?query={query}"},
        "Jumbo": {"url": "https://www.jumbo.ro/", "search_pattern": "/search?q={query}"},
        "English Home": {"url": "https://englishhome.ro/", "search_pattern": "/arama?q={query}"},
        "Primark": {"url": "https://www.primark.com/ro", "search_pattern": "/search?q={query}"},
    },
    "Sırbistan": {
        "Pepco": {"url": "https://pepco.rs/", "search_pattern": "/search?q={query}"},
        "Sinsay": {"url": "https://www.sinsay.com/rs/sr/", "search_pattern": "/search?q={query}"},
        "Zara Home": {"url": "https://www.zarahome.com/rs/", "search_pattern": "/search?term={query}"},
        "H&M Home": {"url": "https://www2.hm.com/rs_en/home.html", "search_pattern": "/search?q={query}"},
        "Jysk": {"url": "https://jysk.rs/", "search_pattern": "/search?query={query}"},
        "Jumbo": {"url": "https://www.jumbo.rs/", "search_pattern": "/search?q={query}"},
        "English Home": {"url": "https://englishhome.rs/", "search_pattern": "/arama?q={query}"},
    },
    "Hırvatistan": {
        "Pepco": {"url": "https://pepco.hr/", "search_pattern": "/search?q={query}"},
        "Sinsay": {"url": "https://www.sinsay.com/hr/hr/", "search_pattern": "/search?q={query}"},
        "Zara Home": {"url": "https://www.zarahome.com/hr/", "search_pattern": "/search?term={query}"},
        "H&M Home": {"url": "https://www2.hm.com/hr_hr/home.html", "search_pattern": "/search?q={query}"},
        "Jysk": {"url": "https://jysk.hr/", "search_pattern": "/search?query={query}"},
    },
    "Kazakistan": {
        "Sinsay": {"url": "https://www.sinsay.com/kz/ru/", "search_pattern": "/search?q={query}"},
        "Zara Home": {"url": "https://www.zarahome.com/kz/", "search_pattern": "/search?term={query}"},
        "H&M Home": {"url": "https://www.hm.com/kz", "search_pattern": "/search?q={query}"},
        "Jysk": {"url": "https://jysk.kz/", "search_pattern": "/search?query={query}"},
        "English Home": {"url": "https://englishhome.kz/", "search_pattern": "/arama?q={query}"},
    },
    "Ukrayna": {
        "Sinsay": {"url": "https://www.sinsay.com/ua/uk/", "search_pattern": "/search?q={query}"},
        "Zara Home": {"url": "https://www.zarahome.com/ua/", "search_pattern": "/search?term={query}"},
        "H&M Home": {"url": "https://www.hm.com/ua", "search_pattern": "/search?q={query}"},
        "Jysk": {"url": "https://jysk.ua/", "search_pattern": "/search?query={query}"},
        "English Home": {"url": "https://englishhome.ua/", "search_pattern": "/arama?q={query}"},
    },
    "Mısır": {
        "Zara Home": {"url": "https://www.zarahome.com/eg/", "search_pattern": "/search?term={query}"},
        "H&M Home": {"url": "https://eg.hm.com/en/", "search_pattern": "/search?q={query}"},
        "Jysk": {"url": "https://jysk.com.eg/", "search_pattern": "/search?query={query}"},
        "English Home": {"url": "https://englishhome.com.eg/", "search_pattern": "/arama?q={query}"},
    },
    "Irak": {
        "H&M Home": {"url": "https://iq.hm.com/", "search_pattern": "/search?q={query}"},
    },
    "Polonya": {
        "Pepco": {"url": "https://pepco.pl/", "search_pattern": "/search?q={query}"},
        "Sinsay": {"url": "https://www.sinsay.com/pl/pl/", "search_pattern": "/search?q={query}"},
        "Zara Home": {"url": "https://www.zarahome.com/pl/", "search_pattern": "/search?term={query}"},
        "H&M Home": {"url": "https://www2.hm.com/pl_pl/home.html", "search_pattern": "/search?q={query}"},
        "Jysk": {"url": "https://jysk.pl/", "search_pattern": "/search?query={query}"},
    },
    "Macaristan": {
        "Pepco": {"url": "https://pepco.hu/", "search_pattern": "/search?q={query}"},
        "Sinsay": {"url": "https://www.sinsay.com/hu/hu/", "search_pattern": "/search?q={query}"},
        "Zara Home": {"url": "https://www.zarahome.com/hu/", "search_pattern": "/search?term={query}"},
        "H&M Home": {"url": "https://www2.hm.com/hu_hu/home.html", "search_pattern": "/search?q={query}"},
        "Jysk": {"url": "https://jysk.hu/", "search_pattern": "/search?query={query}"},
    },
}

# Ülke Metadata
COUNTRIES_META = {
    "Bulgaristan":  {"curr": "BGN", "lang": "bg", "locale": "bg_BG"},
    "Bosna Hersek": {"curr": "BAM", "lang": "bs", "locale": "bs_BA"},
    "Yunanistan":   {"curr": "EUR", "lang": "el", "locale": "el_GR"},
    "Sırbistan":    {"curr": "RSD", "lang": "sr", "locale": "sr_RS"},
    "Romanya":      {"curr": "RON", "lang": "ro", "locale": "ro_RO"},
    "Hırvatistan":  {"curr": "EUR", "lang": "hr", "locale": "hr_HR"},
    "Kazakistan":   {"curr": "KZT", "lang": "kk", "locale": "kk_KZ"},
    "Rusya":        {"curr": "RUB", "lang": "ru", "locale": "ru_RU"},
    "Ukrayna":      {"curr": "UAH", "lang": "uk", "locale": "uk_UA"},
    "Mısır":        {"curr": "EGP", "lang": "ar", "locale": "ar_EG"},
    "Irak":         {"curr": "IQD", "lang": "ar", "locale": "ar_IQ"},
    "Polonya":      {"curr": "PLN", "lang": "pl", "locale": "pl_PL"},
    "Macaristan":   {"curr": "HUF", "lang": "hu", "locale": "hu_HU"},
}

# Marka Listesi
ALL_BRANDS = ["Pepco", "Sinsay", "Zara Home", "H&M Home", "Jysk", "Primark", "Jumbo", "English Home"]

# Ürün Kategorileri (Hızlı Seçim İçin)
PRODUCT_CATEGORIES = {
    "Banyo": ["Havlu", "Yüz Havlusu", "Banyo Havlusu", "El Havlusu", "Bornoz", "Banyo Paspası", "Duş Perdesi"],
    "Yatak Odası": ["Nevresim", "Çarşaf", "Yastık", "Yorgan", "Battaniye", "Pike", "Yatak Örtüsü"],
    "Mutfak": ["Mutfak Havlusu", "Masa Örtüsü", "Peçete", "Önlük", "Tutacak"],
    "Salon": ["Kırlent", "Perde", "Halı", "Kilim", "Puf"],
}

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE YÖNETİMİ
# ═══════════════════════════════════════════════════════════════════════════════

if 'search_results' not in st.session_state:
    st.session_state['search_results'] = None
if 'comparison_data' not in st.session_state:
    st.session_state['comparison_data'] = None
if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []
if 'api_call_count' not in st.session_state:
    st.session_state['api_call_count'] = 0

# ═══════════════════════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def get_exchange_rates():
    """Döviz kurlarını çeker ve cache'ler (1 saat)"""
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/TRY", timeout=10)
        data = response.json()['rates']
        rates = {k: 1/v for k, v in data.items() if v > 0}
        # BAM için özel hesaplama (EUR'a sabitli)
        if "EUR" in rates:
            rates["BAM"] = rates["EUR"] / 1.95583
        return rates
    except Exception as e:
        st.error(f"Kur verisi alınamadı: {e}")
        return None

def translate_text(text, mode="to_local", target_lang="en"):
    """Metin çevirisi yapar"""
    if not text or len(text.strip()) == 0:
        return text
    try:
        if mode == "to_local":
            return GoogleTranslator(source='auto', target=target_lang).translate(text)
        elif mode == "to_english":
            return GoogleTranslator(source='auto', target='en').translate(text)
        else:  # to_turkish
            return GoogleTranslator(source='auto', target='tr').translate(text)
    except Exception:
        return text

def clean_price(price_raw, currency_code="USD"):
    """Fiyat string'ini float'a çevirir"""
    if not price_raw:
        return 0.0
    
    s = str(price_raw).lower().strip()
    
    # Gereksiz kelimeleri temizle
    remove_words = ["from", "start", "to", "price", "fiyat", "only", "now", "was", "sale", "indirim", "от", "цена"]
    for word in remove_words:
        s = s.replace(word, "")
    
    # Para birimi sembollerini temizle
    currency_symbols = ["rsd", "din", "km", "bam", "лв", "bgn", "eur", "ron", "lei", "tl", "try", 
                       "huf", "ft", "pln", "zł", "uah", "грн", "egp", "iqd", "kzt", "₸",
                       "$", "€", "£", "₺", "zl"]
    for symbol in currency_symbols:
        s = s.replace(symbol, "")
    
    s = s.strip()
    s = re.sub(r'[^\d.,\s]', '', s)
    s = s.strip()
    
    if not s:
        return 0.0
    
    # Birden fazla sayı varsa ilkini al
    numbers = re.findall(r'[\d.,]+', s)
    if not numbers:
        return 0.0
    s = numbers[0]
    
    try:
        # Ondalık ayırıcı tespiti
        if ',' in s and '.' in s:
            if s.rfind(',') > s.rfind('.'):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        elif ',' in s:
            parts = s.split(',')
            if len(parts[-1]) <= 2:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
        return float(s)
    except:
        return 0.0

def validate_product_relevance(product_name, search_query_english, threshold=0.3):
    """Ürün alakalılığını kontrol eder"""
    try:
        # Ürün adını İngilizceye çevir
        product_english = GoogleTranslator(source='auto', target='en').translate(product_name).lower()
        query_lower = search_query_english.lower()
        
        # Anahtar kelimeleri çıkar
        query_keywords = [w for w in query_lower.split() if len(w) > 2]
        
        # Ana objeyi bul (genelde son kelime)
        main_object = query_keywords[-1] if query_keywords else ""
        
        # Tam eşleşme kontrolü
        if main_object and main_object in product_english:
            return True, product_english, 1.0
        
        # Kısmi eşleşme kontrolü
        matches = sum(1 for k in query_keywords if k in product_english)
        score = matches / len(query_keywords) if query_keywords else 0
        
        return score >= threshold, product_english, score
        
    except Exception:
        return True, product_name, 0.5

def generate_cache_key(brand, country, product):
    """Benzersiz cache key üretir"""
    raw = f"{brand}_{country}_{product}_{datetime.now().strftime('%Y%m%d')}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

# ═══════════════════════════════════════════════════════════════════════════════
# PERPLEXITY API FONKSİYONLARI
# ═══════════════════════════════════════════════════════════════════════════════

def search_with_perplexity(api_key, brand, product_local, product_english, country, currency_code, site_url, max_retries=2):
    """
    Perplexity API ile ürün araması yapar.
    İyileştirilmiş prompt ve retry mekanizması ile.
    """
    
    url = "https://api.perplexity.ai/chat/completions"
    domain = site_url.replace("https://", "").replace("http://", "").split("/")[0]
    
    # Geliştirilmiş system prompt
    system_prompt = """You are a precise e-commerce data extraction specialist. 
Your task is to find REAL product listings with ACCURATE prices from specific websites.

CRITICAL RULES:
1. Only report products that ACTUALLY EXIST on the website
2. Prices must be EXACT as shown on the website
3. If you cannot find products, say "NO_RESULTS" - never make up data
4. Product URLs must be real and clickable
5. Include product variations (different sizes, colors) as separate items"""

    # Optimized user prompt
    user_prompt = f"""Search for "{product_english}" (local term: "{product_local}") on {site_url}

TASK: Find and list ALL matching products in the "{product_english}" category.

For each product found, provide:
- Exact product name (as shown on website)
- Exact price in {currency_code} (numbers only, with decimals)
- Direct product URL

OUTPUT FORMAT (strict JSON):
{{
    "status": "found" or "not_found",
    "product_count": <number>,
    "products": [
        {{
            "name": "Product Name",
            "price": "29.99",
            "url": "https://..."
        }}
    ],
    "search_notes": "Any relevant notes about the search"
}}

If no products found, return:
{{
    "status": "not_found",
    "product_count": 0,
    "products": [],
    "search_notes": "Reason why no products found"
}}"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 4000,
        "return_images": False,
        "return_related_questions": False
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                st.session_state['api_call_count'] += 1
                content = response.json()['choices'][0]['message']['content']
                
                # JSON parsing
                clean_content = content.replace("```json", "").replace("```", "").strip()
                
                # JSON başlangıç ve bitişini bul
                start_idx = clean_content.find("{")
                end_idx = clean_content.rfind("}")
                
                if start_idx != -1 and end_idx != -1:
                    json_str = clean_content[start_idx:end_idx + 1]
                    result = json.loads(json_str)
                    return result
                    
            elif response.status_code == 429:
                # Rate limit - bekle ve tekrar dene
                time.sleep(2 ** attempt)
                continue
            else:
                st.warning(f"API Hatası: {response.status_code}")
                return None
                
        except json.JSONDecodeError as e:
            st.warning(f"JSON parse hatası (deneme {attempt + 1}): {e}")
            continue
        except requests.exceptions.Timeout:
            st.warning(f"Timeout (deneme {attempt + 1})")
            continue
        except Exception as e:
            st.error(f"Beklenmeyen hata: {e}")
            return None
    
    return None

def search_multiple_brands(api_key, brands, product_tr, country, rates):
    """Birden fazla marka için paralel arama yapar"""
    results = {}
    conf = COUNTRIES_META.get(country, {"curr": "USD", "lang": "en"})
    curr = conf["curr"]
    lang = conf["lang"]
    
    # Çevirileri bir kez yap
    product_local = translate_text(product_tr, "to_local", lang)
    product_english = translate_text(product_tr, "to_english")
    
    total_brands = len(brands)
    progress_bar = st.progress(0, text="Markalar taranıyor...")
    
    for idx, brand in enumerate(brands):
        brand_data = URL_DB.get(country, {}).get(brand)
        
        if not brand_data:
            results[brand] = {"status": "unavailable", "message": f"{brand} bu ülkede mevcut değil"}
            continue
            
        site_url = brand_data.get("url")
        if not site_url:
            results[brand] = {"status": "unavailable", "message": "URL bulunamadı"}
            continue
        
        progress_bar.progress((idx + 1) / total_brands, text=f"🔍 {brand} taranıyor...")
        
        # API çağrısı
        api_result = search_with_perplexity(
            api_key, brand, product_local, product_english, 
            country, curr, site_url
        )
        
        if api_result and api_result.get("status") == "found":
            processed_products = []
            usd_rate = rates.get("USD", 1)
            loc_rate = rates.get(curr, 1)
            
            for product in api_result.get("products", []):
                name = product.get("name", "")
                is_valid, name_en, score = validate_product_relevance(name, product_english)
                
                if is_valid:
                    price_local = clean_price(product.get("price", 0), curr)
                    if price_local > 0:
                        price_tl = price_local * loc_rate
                        price_usd = price_tl / usd_rate
                        
                        processed_products.append({
                            "name_local": name,
                            "name_tr": translate_text(name, "to_turkish"),
                            "name_en": name_en,
                            "price_local": price_local,
                            "price_tl": price_tl,
                            "price_usd": price_usd,
                            "url": product.get("url", ""),
                            "relevance_score": score
                        })
            
            if processed_products:
                prices_tl = [p["price_tl"] for p in processed_products]
                results[brand] = {
                    "status": "found",
                    "products": processed_products,
                    "stats": {
                        "count": len(processed_products),
                        "avg_tl": sum(prices_tl) / len(prices_tl),
                        "min_tl": min(prices_tl),
                        "max_tl": max(prices_tl),
                        "avg_usd": (sum(prices_tl) / len(prices_tl)) / usd_rate
                    }
                }
            else:
                results[brand] = {"status": "filtered", "message": "Ürünler filtreye takıldı"}
        else:
            results[brand] = {"status": "not_found", "message": "Ürün bulunamadı"}
        
        # Rate limiting
        time.sleep(0.5)
    
    progress_bar.empty()
    return results, product_english, curr

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<h2 style="color:#4da6ff; margin-bottom:5px;">🧿 LCW HOME</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e; font-size:11px; margin-top:0;">COMPETITOR INTELLIGENCE</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # API Key
    PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY") or st.text_input(
        "🔑 Perplexity API Key", 
        type="password",
        help="Perplexity API anahtarınızı girin"
    )
    
    if not PERPLEXITY_KEY:
        st.warning("⚠️ API Key gerekli")
        st.stop()
    
    st.markdown("---")
    
    # Arama Modu
    search_mode = st.radio(
        "📊 Arama Modu",
        ["Tek Marka", "Çoklu Marka Karşılaştırma"],
        help="Tek marka detaylı analiz veya çoklu marka karşılaştırması"
    )
    
    st.markdown("---")
    
    # Ülke Seçimi
    available_countries = list(URL_DB.keys())
    selected_country = st.selectbox("🌍 Ülke", available_countries)
    
    # Ülkeye göre mevcut markaları filtrele
    available_brands_for_country = [b for b in ALL_BRANDS if URL_DB.get(selected_country, {}).get(b)]
    
    if search_mode == "Tek Marka":
        selected_brands = [st.selectbox("🏪 Marka", available_brands_for_country)]
    else:
        selected_brands = st.multiselect(
            "🏪 Markalar",
            available_brands_for_country,
            default=available_brands_for_country[:3] if len(available_brands_for_country) >= 3 else available_brands_for_country,
            help="Karşılaştırmak istediğiniz markaları seçin"
        )
    
    st.markdown("---")
    
    # Ürün Seçimi
    st.markdown("##### 🛍️ Ürün Seçimi")
    
    # Kategori bazlı hızlı seçim
    selected_category = st.selectbox("Kategori", ["Manuel Giriş"] + list(PRODUCT_CATEGORIES.keys()))
    
    if selected_category != "Manuel Giriş":
        product_query_tr = st.selectbox("Ürün", PRODUCT_CATEGORIES[selected_category])
    else:
        product_query_tr = st.text_input("Ürün (Türkçe)", "Yüz Havlusu", help="Aramak istediğiniz ürünü Türkçe yazın")
    
    st.markdown("---")
    
    # Arama Butonu
    btn_search = st.button("🚀 FİYATLARI ÇEK", use_container_width=True)
    
    # Döviz Kurları
    rates = get_exchange_rates()
    if rates:
        st.markdown("---")
        st.markdown("##### 💱 Güncel Kurlar")
        conf = COUNTRIES_META.get(selected_country, {"curr": "USD"})
        curr = conf["curr"]
        
        col1, col2 = st.columns(2)
        col1.metric("USD", f"{rates.get('USD', 0):.2f}₺")
        col2.metric(curr, f"{rates.get(curr, 0):.2f}₺")
    
    # API Kullanım Sayacı
    st.markdown("---")
    st.markdown(f"<p style='color:#8b949e; font-size:11px;'>API Çağrısı: {st.session_state['api_call_count']}</p>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ANA İŞLEM
# ═══════════════════════════════════════════════════════════════════════════════

if btn_search:
    if not rates:
        st.error("❌ Döviz kuru verisi alınamadı. Lütfen sayfayı yenileyin.")
        st.stop()
    
    if not selected_brands:
        st.error("❌ En az bir marka seçmelisiniz.")
        st.stop()
    
    # Arama başlat
    with st.spinner("🔍 Veriler toplanıyor..."):
        results, product_english, currency = search_multiple_brands(
            PERPLEXITY_KEY,
            selected_brands,
            product_query_tr,
            selected_country,
            rates
        )
    
    # Sonuçları kaydet
    st.session_state['search_results'] = {
        "results": results,
        "product_tr": product_query_tr,
        "product_en": product_english,
        "country": selected_country,
        "currency": currency,
        "timestamp": datetime.now().isoformat(),
        "rates": rates
    }
    
    # Arama geçmişine ekle
    st.session_state['search_history'].append({
        "product": product_query_tr,
        "country": selected_country,
        "brands": selected_brands,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })

# ═══════════════════════════════════════════════════════════════════════════════
# SONUÇLARI GÖSTER
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state['search_results']:
    data = st.session_state['search_results']
    results = data['results']
    currency = data['currency']
    rates = data['rates']
    usd_rate = rates.get("USD", 1)
    loc_rate = rates.get(currency, 1)
    
    # Başarılı sonuçları filtrele
    successful_results = {k: v for k, v in results.items() if v.get("status") == "found"}
    
    if not successful_results:
        st.warning("⚠️ Hiçbir markada ürün bulunamadı. Farklı bir ürün veya ülke deneyin.")
    else:
        # Tab'lar oluştur
        tab1, tab2, tab3 = st.tabs(["📊 Özet", "📋 Detaylı Liste", "📈 Karşılaştırma"])
        
        # ═══════════════════════════════════════════════════════════════════
        # TAB 1: ÖZET
        # ═══════════════════════════════════════════════════════════════════
        with tab1:
            st.markdown(f"### 🎯 {data['product_tr']} - {data['country']}")
            st.markdown(f"<p style='color:#8b949e;'>Aranan: {data['product_en']} | Para Birimi: {currency}</p>", unsafe_allow_html=True)
            
            # Marka kartları
            cols = st.columns(len(successful_results))
            
            sorted_brands = sorted(
                successful_results.items(),
                key=lambda x: x[1]['stats']['avg_tl']
            )
            
            for idx, (brand, brand_data) in enumerate(sorted_brands):
                with cols[idx]:
                    stats = brand_data['stats']
                    
                    # En ucuz markayı vurgula
                    is_cheapest = idx == 0
                    border_color = "#238636" if is_cheapest else "#30363d"
                    badge = "🏆 EN UCUZ" if is_cheapest else ""
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(145deg, #161b22, #21262d); 
                                border: 2px solid {border_color}; 
                                border-radius: 16px; 
                                padding: 20px; 
                                text-align: center;">
                        <p style="color: #8b949e; font-size: 12px; margin: 0;">{badge}</p>
                        <h3 style="color: #4da6ff; margin: 10px 0;">{brand}</h3>
                        <p style="color: #ffffff; font-size: 28px; font-weight: bold; margin: 10px 0;">
                            {stats['avg_tl']:,.0f}₺
                        </p>
                        <p style="color: #8b949e; font-size: 14px; margin: 5px 0;">
                            ${stats['avg_usd']:,.2f} | {stats['avg_tl']/loc_rate:,.2f} {currency}
                        </p>
                        <hr style="border-color: #30363d; margin: 15px 0;">
                        <p style="color: #8b949e; font-size: 12px; margin: 5px 0;">
                            📦 {stats['count']} ürün
                        </p>
                        <p style="color: #8b949e; font-size: 12px; margin: 5px 0;">
                            📉 Min: {stats['min_tl']:,.0f}₺ | 📈 Max: {stats['max_tl']:,.0f}₺
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Genel özet
            st.markdown("---")
            
            all_prices = []
            for brand_data in successful_results.values():
                all_prices.extend([p['price_tl'] for p in brand_data['products']])
            
            if all_prices:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Toplam Ürün", f"{len(all_prices)} adet")
                col2.metric("Genel Ortalama", f"{sum(all_prices)/len(all_prices):,.0f}₺")
                col3.metric("En Düşük", f"{min(all_prices):,.0f}₺")
                col4.metric("En Yüksek", f"{max(all_prices):,.0f}₺")
        
        # ═══════════════════════════════════════════════════════════════════
        # TAB 2: DETAYLI LİSTE
        # ═══════════════════════════════════════════════════════════════════
        with tab2:
            all_products = []
            
            for brand, brand_data in successful_results.items():
                for product in brand_data['products']:
                    all_products.append({
                        "Marka": brand,
                        "Ülke": data['country'],
                        "Ürün (Yerel)": product['name_local'],
                        "Ürün (TR)": product['name_tr'],
                        f"Fiyat ({currency})": product['price_local'],
                        "Fiyat (USD)": product['price_usd'],
                        "Fiyat (TL)": product['price_tl'],
                        "Link": product['url'],
                        "Alakalılık": f"{product['relevance_score']:.0%}"
                    })
            
            if all_products:
                df = pd.DataFrame(all_products)
                
                # Filtreleme seçenekleri
                col1, col2 = st.columns([1, 3])
                with col1:
                    sort_by = st.selectbox("Sırala", ["Fiyat (TL)", "Marka", "Alakalılık"])
                    sort_asc = st.checkbox("Artan", value=True)
                
                df_sorted = df.sort_values(sort_by, ascending=sort_asc)
                
                # Tablo
                st.dataframe(
                    df_sorted,
                    column_config={
                        "Link": st.column_config.LinkColumn("🔗 Link", display_text="Git"),
                        f"Fiyat ({currency})": st.column_config.NumberColumn(f"Fiyat ({currency})", format="%.2f"),
                        "Fiyat (USD)": st.column_config.NumberColumn("USD ($)", format="$%.2f"),
                        "Fiyat (TL)": st.column_config.NumberColumn("TL (₺)", format="%.0f ₺"),
                    },
                    use_container_width=True,
                    hide_index=True,
                    height=500
                )
                
                # CSV İndirme
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "💾 CSV İndir",
                    csv,
                    f"lcw_analysis_{data['country']}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    "text/csv",
                    use_container_width=True
                )
        
        # ═══════════════════════════════════════════════════════════════════
        # TAB 3: KARŞILAŞTIRMA
        # ═══════════════════════════════════════════════════════════════════
        with tab3:
            if len(successful_results) > 1:
                st.markdown("### 📊 Marka Karşılaştırma Matrisi")
                
                # Fiyat karşılaştırma grafiği için veri hazırla
                comparison_data = []
                for brand, brand_data in successful_results.items():
                    stats = brand_data['stats']
                    comparison_data.append({
                        "Marka": brand,
                        "Ortalama (TL)": stats['avg_tl'],
                        "Minimum (TL)": stats['min_tl'],
                        "Maximum (TL)": stats['max_tl'],
                        "Ürün Sayısı": stats['count']
                    })
                
                df_comparison = pd.DataFrame(comparison_data)
                df_comparison = df_comparison.sort_values("Ortalama (TL)")
                
                # Bar chart
                st.bar_chart(df_comparison.set_index("Marka")[["Ortalama (TL)", "Minimum (TL)", "Maximum (TL)"]])
                
                # Detaylı tablo
                st.dataframe(
                    df_comparison,
                    column_config={
                        "Ortalama (TL)": st.column_config.NumberColumn("Ortalama", format="%.0f ₺"),
                        "Minimum (TL)": st.column_config.NumberColumn("Min", format="%.0f ₺"),
                        "Maximum (TL)": st.column_config.NumberColumn("Max", format="%.0f ₺"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Fiyat farkı analizi
                st.markdown("---")
                st.markdown("### 💡 Fiyat Farkı Analizi")
                
                if len(comparison_data) >= 2:
                    cheapest = comparison_data[0]
                    most_expensive = comparison_data[-1]
                    
                    diff_tl = most_expensive['Ortalama (TL)'] - cheapest['Ortalama (TL)']
                    diff_pct = (diff_tl / cheapest['Ortalama (TL)']) * 100
                    
                    col1, col2 = st.columns(2)
                    col1.success(f"🏆 En Uygun: **{cheapest['Marka']}** - {cheapest['Ortalama (TL)']:,.0f}₺")
                    col2.error(f"💰 En Pahalı: **{most_expensive['Marka']}** - {most_expensive['Ortalama (TL)']:,.0f}₺")
                    
                    st.info(f"📊 Fiyat Farkı: **{diff_tl:,.0f}₺** (%{diff_pct:.1f})")
            else:
                st.info("Karşılaştırma için en az 2 marka seçin.")
    
    # Başarısız sonuçları göster
    failed_results = {k: v for k, v in results.items() if v.get("status") != "found"}
    if failed_results:
        with st.expander("⚠️ Sonuç Bulunamayan Markalar"):
            for brand, info in failed_results.items():
                st.markdown(f"- **{brand}**: {info.get('message', 'Bilinmeyen hata')}")

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #8b949e; font-size: 12px; padding: 20px;">
    <p>LCW Global Intelligence v2.0 | Competitor Price Tracking System</p>
    <p>Powered by Perplexity AI | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)
