import streamlit as st
import pandas as pd
import os
import json
import requests
import re

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
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_KEY:
    GOOGLE_KEY = st.sidebar.text_input("1. Google API Key (Flash Modeli):", type="password")

SERPER_KEY = os.environ.get("SERPER_API_KEY")
if not SERPER_KEY:
    SERPER_KEY = st.sidebar.text_input("2. Serper API Key:", type="password")

if not GOOGLE_KEY or not SERPER_KEY:
    st.warning("⚠️ Lütfen anahtarları giriniz.")
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

# --- YARDIMCI: GEMINI FLASH'A İSTEK ATMA (REST API) ---
def call_gemini_flash(prompt):
    """
    Doğrudan Google sunucusuna gider. SDK kullanmaz. Hata yapmaz.
    Sadece 'gemini-1.5-flash' kullanır.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            return None
        result = response.json()
        return json.loads(result['candidates'][0]['content']['parts'][0]['text'])
    except:
        return None

# --- YARDIMCI: SERPER ARAMA ---
def search_serper(query, gl, hl):
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query, "gl": gl, "hl": hl, "num": 10})
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()
    except:
        return None

# --- CANLI KUR ---
@st.cache_data(ttl=3600)
def fetch_live_rates():
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/TRY")
        data = response.json()
        rates = data["rates"]
        live_rates = {}
        for c, r in rates.items():
            if r > 0: live_rates[c] = 1 / r
        if "EUR" in live_rates: live_rates["BAM"] = live_rates["EUR"] / 1.95583 
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

# --- FİYAT HESAPLAMA ---
def extract_price(price_str):
    if not price_str: return 0.0
    clean = re.sub(r'[^\d.,]', '', str(price_str))
    if "," in clean and "." in clean:
        if clean.find(",") < clean.find("."): clean = clean.replace(",", "")
        else: clean = clean.replace(".", "").replace(",", ".")
    elif "," in clean: clean = clean.replace(",", ".")
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", clean)
    return float(nums[0]) if nums else 0.0

def calc_prices(raw, code):
    amt = extract_price(raw)
    if amt == 0 or not LIVE_RATES: return 0, 0, 0
    return amt, round(amt * LIVE_RATES.get(code, 0), 2), round((amt * LIVE_RATES.get(code, 0)) / LIVE_RATES.get("USD", 1), 2)

# --- ANA EKRAN ---
st.markdown(f"""<h2 style='color: #333;'>🌍 {selected_brand} <span style='color: #999; font-weight: normal;'>|</span> {selected_country}</h2>""", unsafe_allow_html=True)

if st.sidebar.button("Analizi Başlat 🚀", type="primary"):
    if not query_turkish:
        st.warning("Lütfen ürün adı giriniz.")
    else:
        with st.status("İşlemler yapılıyor...", expanded=True) as status:
            country_conf = COUNTRIES[selected_country]
            
            # 1. ÇEVİRİ (AI İLE YAPALIM Kİ KÜTÜPHANE HATASI OLMASIN)
            trans_prompt = f"""Translate this Turkish text to the language used in {selected_country}. Return JSON: {{ "translated": "..." }} Text: "{query_turkish}" """
            trans_res = call_gemini_flash(trans_prompt)
            translated_query = trans_res.get("translated", query_turkish) if trans_res else query_turkish
            
            st.write(f"🧩 Çeviri: **{translated_query}**")
            
            # 2. ARAMA (SERPER)
            search_q = f"{selected_brand} {selected_country} {translated_query} price"
            serper_data = search_serper(search_q, country_conf["gl"], country_conf["hl"])
            
            if serper_data and "organic" in serper_data:
                # 3. VERİ AYIKLAMA (AI FLASH)
                context = ""
                for i in serper_data["organic"][:10]:
                    context += f"Title: {i.get
