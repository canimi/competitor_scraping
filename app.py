import streamlit as st
import pandas as pd
import os
import json
import re
import google.generativeai as genai
import requests

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="LCW Home Global", layout="wide", page_icon="🏠")

# --- YAN MENÜ ---
st.sidebar.markdown(
    """
    <div style="padding: 15px; background-color: #f0f2f6; border-left: 5px solid #1c54b2; border-radius: 4px; margin-bottom: 20px;">
        <h1 style='color: #1c54b2; font-weight: 900; margin:0; padding:0; font-family: "Segoe UI", sans-serif; font-size: 24px;'>LCW HOME</h1>
        <p style='color: #555; font-size: 11px; margin:0; letter-spacing: 1px;'>GLOBAL PRICE INTELLIGENCE</p>
    </div>
    """, 
    unsafe_allow_html=True
)

# --- API KEY KONTROLÜ ---
# Google Gemini Key
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_KEY:
    GOOGLE_KEY = st.sidebar.text_input("1. Google API Key:", type="password")

# Serper Search Key
SERPER_KEY = os.environ.get("SERPER_API_KEY")
if not SERPER_KEY:
    SERPER_KEY = st.sidebar.text_input("2. Serper API Key (serper.dev):", type="password")

if not GOOGLE_KEY or not SERPER_KEY:
    st.warning("⚠️ Lütfen Google ve Serper anahtarlarını giriniz.")
    st.stop()

# --- GOOGLE MODEL KURULUMU ---
try:
    genai.configure(api_key=GOOGLE_KEY)
except Exception as e:
    st.error(f"Google Key Hatalı: {e}")
    st.stop()

# --- SABİTLER ---
COUNTRIES = {
    "Türkiye": {"curr": "TRY", "gl": "tr", "hl": "tr"},
    "Almanya": {"curr": "EUR", "gl": "de", "hl": "de"},
    "Bosna Hersek": {"curr": "BAM", "gl": "ba", "hl": "bs"},
    "Sırbistan": {"curr": "RSD", "gl": "rs", "hl": "sr"},
    "Bulgaristan": {"curr": "BGN", "gl": "bg", "hl": "bg"},
    "Yunanistan": {"curr": "EUR", "gl": "gr", "hl": "el"},
    "İngiltere": {"curr": "GBP", "gl": "uk", "hl": "en"},
    "Polonya": {"curr": "PLN", "gl": "pl", "hl": "pl"},
    "Romanya": {"curr": "RON", "gl": "ro", "hl": "ro"},
    "Arnavutluk": {"curr": "ALL", "gl": "al", "hl": "sq"},
    "Karadağ": {"curr": "EUR", "gl": "me", "hl": "sr"},
    "Moldova": {"curr": "MDL", "gl": "md", "hl": "ro"},
    "Rusya": {"curr": "RUB", "gl": "ru", "hl": "ru"},
    "Ukrayna": {"curr": "UAH", "gl": "ua", "hl": "uk"}
}

BRANDS = ["LC Waikiki", "Sinsay", "Pepco", "Zara", "H&M", "Mango", "Primark", "English Home", "IKEA", "Jysk"]

# --- CANLI KUR ---
@st.cache_data(ttl=3600)
def fetch_live_rates():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/TRY"
        response = requests.get(url)
        data = response.json()
        rates = data["rates"]
        live_rates = {}
        for currency, rate in rates.items():
            if rate > 0:
                live_rates[currency] = 1 / rate
        if "EUR" in live_rates:
            live_rates["BAM"] = live_rates["EUR"] / 1.95583 
        return live_rates, data["date"]
    except:
        return None, None

LIVE_RATES, RATE_DATE = fetch_live_rates()

st.sidebar.header("🔎 Filtreler")
selected_country = st.sidebar.selectbox("Ülke", list(COUNTRIES.keys()))
selected_brand = st.sidebar.selectbox("Marka", BRANDS)
query_turkish = st.sidebar.text_input("Ürün Adı (TR)", "Çift Kişilik Battaniye")

with st.sidebar.expander("💸 Canlı Kur Bilgisi", expanded=True):
    if LIVE_RATES:
        st.write(f"🇺🇸 USD: **{LIVE_RATES.get('USD',0):.2f} ₺**")
        st.write(f"🇪🇺 EUR: **{LIVE_RATES.get('EUR',0):.2f} ₺**")
        target_curr = COUNTRIES[selected_country]["curr"]
        if target_curr not in ["USD", "EUR", "TRY"]:
             st.write(f"🏳️ {target_curr}: **{LIVE_RATES.get(target_curr,0):.2f} ₺**")
        st.caption(f"Tarih: {RATE_DATE}")

# --- FONKSİYONLAR ---
def extract_price_number(price_str):
    if not price_str: return 0.0
    clean_str = str(price_str).replace(" ", "")
    clean_str = re.sub(r'[^\d.,]', '', clean_str)
    
    if "," in clean_str and "." in clean_str:
        if clean_str.find(",") < clean_str.find("."):
            clean_str = clean_str.replace(",", "")
        else:
            clean_str = clean_str.replace(".", "").replace(",", ".")
    elif "," in clean_str:
        clean_str = clean_str.replace(",", ".")
        
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", clean_str)
    return float(nums[0]) if nums else 0.0

def calculate_prices(raw_price_str, currency_code):
    amount = extract_price_number(raw_price_str)
    if amount == 0 or not LIVE_RATES: return 0, 0, 0
    rate_to_tl = LIVE_RATES.get(currency_code, 0)
    price_tl = amount * rate_to_tl
    price_usd = price_tl / LIVE_RATES.get("USD", 1)
    return amount, round(price_tl, 2), round(price_usd, 2)

# --- SERPER (GOOGLE) ARAMA MOTORU ---
def search_with_serper(brand, country, query):
    url = "https://google.serper.dev/search"
    country_conf = COUNTRIES.get(country, {})
    
    # Otomatik çeviri yerine Google'a bırakıyoruz, daha iyi sonuç verir
    search_query = f"{brand} {country} {query} price"
    
    payload = json.dumps({
        "q": search_query,
        "gl": country_conf.get("gl", "us"),
        "hl": country_conf.get("hl", "en"),
        "num": 10
    })
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()
    except Exception as e:
        return None

def process_with_gemini(search_data, brand, query, currency_hint):
    context_text = ""
    if "organic" in search_data:
        for item in search_data["organic"]:
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            price = item.get("price", "")
            currency = item.get("currency", "")
            context_text += f"Product: {title}\nLink: {link}\nSnippet: {snippet}\nPrice: {price} {currency}\n---\n"
    
    if not context_text:
        return None, "Google arama sonucunda anlamlı veri bulunamadı."

    # GEMINI PRO İÇİN PROMPT
    prompt = f"""
    You are a data extractor.
    Context:
    {context_text}
    
    Task: Find products matching "{query}" for brand "{brand}".
    Currency Hint: {currency_hint}
    
    Instructions:
    1. Extract Product Name, Price, URL.
    2. Try to capture the Price from snippet if not explicitly stated.
    3. Return ONLY valid JSON.
    
    JSON Format:
    {{ "products": [ {{ "name": "...", "price": "...", "url": "..." }} ] }}
    """
    
    try:
        # GÜVENLİ MODEL: GEMINI PRO (En stabil versiyon)
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        
        # Temizlik (Pro bazen markdown atar)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text), None
    except Exception as e:
        return None, f"AI Analiz Hatası: {e}"

# --- ANA EKRAN ---
st.markdown(f"""
<h2 style='color: #333;'>🌍 {selected_brand} <span style='color: #999; font-weight: normal;'>|</span> {selected_country}</h2>
""", unsafe_allow_html=True)

if st.sidebar.button("Analizi Başlat 🚀", type="primary"):
    if not query_turkish:
        st.warning("Lütfen ürün adı giriniz.")
    else:
        with st.status("Google üzerinden veri çekiliyor...", expanded=True) as status:
            st.write(f"🔍 Arama: **{query_turkish}**")
            
            # 1. SERPER
            serper_result = search_with_serper(selected_brand, selected_country, query_turkish)
            
            if serper_result and "organic" in serper_result:
                # 2. GEMINI PRO
                target_currency = COUNTRIES[selected_country]["curr"]
                result, error_msg = process_with_gemini(serper_result, selected_brand, query_turkish, target_currency)
                
                if error_msg:
                    st.error(error_msg)
                
                status.update(label="İşlem Tamamlandı", state="complete")
            else:
                st.error("Serper API sonuç döndürmedi.")
                result = None

        if result and "products" in result and result["products"]:
            products = result["products"]
            
            table_data = []
            excel_lines = ["Ürün Adı (TR)\tOrijinal İsim\tYerel Fiyat\tTL Fiyatı\tUSD Fiyatı\tLink"]
            
            prices_tl = []
            prices_usd = []
            prices_local = []

            for item in products:
                lo
