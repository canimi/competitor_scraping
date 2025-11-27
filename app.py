import streamlit as st
import pandas as pd
import os
import json
import requests
import re
from deep_translator import GoogleTranslator

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="LCW Global Intelligence", layout="wide", page_icon="🧿")

# --- CSS: BAŞLIK YUKARI + DARK MODE ---
st.markdown("""
<style>
    /* 1. BAŞLIĞI ZORLA YUKARI ÇEKME OPERASYONU */
    .block-container {
        padding-top: 1rem !important; /* Üst boşluğu yok et */
        padding-bottom: 5rem;
    }
    header {visibility: hidden;} /* Streamlit menüsünü gizle (opsiyonel) */
    
    /* Genel Arka Plan */
    .stApp {
        background-color: #0e1117;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Başlık Stili */
    h1 {
        color: #4da6ff;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 0 0 15px rgba(77, 166, 255, 0.6);
        margin-top: -20px !important; /* Negatif margin ile yukarı yapıştır */
        padding-bottom: 20px;
    }

    /* KPI Kartları */
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
    }
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 28px !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #8b949e !important;
        font-size: 14px !important;
    }

    /* Tablo ve Sidebar */
    .stDataFrame { border: 1px solid #30363d; border-radius: 5px; }
    [data-testid="stSidebar"] {
        background-color: #0d1117;
        border-right: 1px solid #30363d;
    }
    
    /* Buton */
    div.stButton > button {
        background: linear-gradient(90deg, #1c54b2 0%, #0d3c85 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        font-weight: bold;
        width: 100%;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- BAŞLIK (ARTIK EN TEPEDE) ---
st.markdown("<h1>LCW HOME | GLOBAL INTELLIGENCE</h1>", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 style="color:#4da6ff; margin-bottom:0;">LCW HOME</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e; font-size:12px;">COMPETITOR PRICE TRACKER</p>', unsafe_allow_html=True)

    PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY")
    if not PERPLEXITY_KEY:
        PERPLEXITY_KEY = st.text_input("🔑 Perplexity API Key", type="password")

    if not PERPLEXITY_KEY:
        st.warning("⚠️ API Key Gerekli")
        st.stop()

# --- VERİ SETLERİ ---
COUNTRIES = {
    "Bulgaristan":  {"curr": "BGN", "lang": "bg"},
    "Bosna Hersek": {"curr": "BAM", "lang": "bs"}, # Pepco Burada Sorunluydu
    "Yunanistan":   {"curr": "EUR", "lang": "el"},
    "Kazakistan":   {"curr": "KZT", "lang": "kk"},
    "Rusya":        {"curr": "RUB", "lang": "ru"},
    "Ukrayna":      {"curr": "UAH", "lang": "uk"},
    "Sırbistan":    {"curr": "RSD", "lang": "sr"},
    "Montenegro":   {"curr": "EUR", "lang": "sr"},
    "Arnavutluk":   {"curr": "ALL", "lang": "sq"},
    "Makedonya":    {"curr": "MKD", "lang": "mk"},
    "Kosova":       {"curr": "EUR", "lang": "sq"},
    "Moldova":      {"curr": "MDL", "lang": "ro"},
    "Hırvatistan":  {"curr": "EUR", "lang": "hr"},
    "Romanya":      {"curr": "RON", "lang": "ro"},
    "Mısır":        {"curr": "EGP", "lang": "ar"},
    "Fas":          {"curr": "MAD", "lang": "ar"},
    "Irak":         {"curr": "IQD", "lang": "ar"},
}

BRANDS = ["LC Waikiki", "Sinsay", "Pepco", "Zara Home", "H&M Home", "Jysk", "Primark", "Jumbo", "English Home", "IKEA"]

# --- FONKSİYONLAR ---

@st.cache_data(ttl=3600)
def get_rates():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/TRY").json()['rates']
        rates = {k: 1/v for k, v in r.items() if v > 0} 
        if "EUR" in rates: rates["BAM"] = rates["EUR"] / 1.95583
        return rates
    except:
        return None

def translate_to_local(text, target_lang):
    if target_lang == 'tr': return text
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except:
        return text

def translate_to_turkish(text):
    try:
        return GoogleTranslator(source='auto', target='tr').translate(text)
    except:
        return text

def clean_price(price_raw):
    if not price_raw: return 0.0
    s = str(price_raw).lower().replace("лв", "").replace("lei", "").replace("eur", "").replace("rsd", "").replace("km", "").strip()
    s = re.sub(r'[^\d.,]', '', s)
    if not s: return 0.0
    
    if ',' in s and '.' in s:
        if s.find(',') > s.find('.'): s = s.replace('.', '').replace(',', '.')
        else: s = s.replace(',', '')
    elif ',' in s:
        if len(s.split(',')[-1]) == 2: s = s.replace(',', '.')
        else: s = s.replace(',', '.')
            
    try: return float(s)
    except: return 0.0

def search_sonar(brand, product_local, country, currency_code):
    url = "https://api.perplexity.ai/chat/completions"
    
    system_msg = "You are an advanced eCommerce scraper. You extract strictly structured JSON data."
    
    # --- GÜNCELLENEN PROMPT (PEPCO BOSNA/BULGARİSTAN İÇİN DÜZELTME) ---
    user_msg = f"""
    Perform a targeted search for "{brand}" products in category "{product_local}" for the country "{country}".
    
    STRICT RULES:
    1. Search ONLY on the OFFICIAL website/domain of "{brand}" for {country} (e.g., pepco.ba, pepco.bg, sinsay.com).
    2. **CRITICAL FOR PEPCO/SINSAY:** If the brand does not have a "Buy Now" webshop, you MUST check their OFFICIAL CATALOG/OFFER pages on their official domain.
       - Example: For Pepco Bosnia (pepco.ba), extract prices from the displayed products in the categories section.
    3. DO NOT use 3rd party aggregators (No Glami, No Kimbino, No Akakce).
    4. If absolutely NO official site exists in {country}, return an empty list.
    
    DATA EXTRACTION:
    - Extract 5-10 specific products.
    - Price MUST be a number.
    - Provide the ORIGINAL local product name.
    
    OUTPUT JSON FORMAT:
    {{
        "products": [
            {{ "name": "Local Product Name", "price": 10.99, "url": "Official URL" }}
        ]
    }}
    """
    
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    }
    
    headers = { "Authorization": f"Bearer {PERPLEXITY_KEY}", "Content-Type": "application/json" }
    
    try:
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            raw = res.json()['choices'][0]['message']['content']
            clean = raw.replace("```json", "").replace("```", "").strip()
            start = clean.find('{')
            end = clean.rfind('}') + 1
            if start != -1 and end != -1: clean = clean[start:end]
            return json.loads(clean)
        else:
            return None
    except:
        return None

# --- SIDEBAR FİLTRELERİ ---
with st.sidebar:
    st.header("🔎 Filtreler")
    sel_country = st.selectbox("Ülke", list(COUNTRIES.keys()))
    sel_brand = st.selectbox("Marka", BRANDS)
    q_tr = st.text_input("Ürün (TR)", "Çift Kişilik Nevresim")
    
    st.markdown("---")
    btn_start = st.button("FİYATLARI ÇEK (SONAR) 🚀")

# --- KURLAR ---
rates = get_rates()
conf = COUNTRIES[sel_country]
curr = conf["curr"]

if rates:
    usd_val = rates.get("USD", 0)
    loc_val = rates.get(curr, 0)
    with st.sidebar:
        st.markdown("### 💱 Canlı Kurlar")
        c1, c2 = st.columns(2)
        c1.metric("USD", f"{usd_val:.2f}₺")
        c2.metric(curr, f"{loc_val:.2f}₺")

# --- ANA AKIŞ ---
if btn_start:
    if not rates: st.error("Kur verisi yok."); st.stop()
    
    # 1. Çeviri
    q_local = translate_to_local(q_tr, conf["lang"])
    
    # 2. Sonar Araması
    with st.spinner(f"🧿 {sel_brand} resmi sitesi taranıyor ({sel_country})..."):
        data = search_sonar(sel_brand, q_local, sel_country, curr)
    
    if data and "products" in data and len(data["products"]) > 0:
        rows = []
        prices_tl = []
        usd_rate = rates.get("USD", 1)
        loc_rate = rates.get(curr, 1)
        
        progress_bar = st.progress(0, text="Ürünler tercüme ediliyor...")
        total_products = len(data["products"])
        
        for i, p in enumerate(data["products"]):
            p_raw = clean_price(p.get("price", 0))
            
            if p_raw > 0:
                p_tl = p_raw * loc_rate
                p_usd = p_tl / usd_rate
                prices_tl.append(p_tl)
                
                local_name = p.get("name", "")
                translated_name = translate_to_turkish(local_name)
                
                rows.append({
                    "Ürün Yerel Adı": local_name,
                    "Ürün Türkçe Adı": translated_name,
                    "Yerel Fiyat": p_raw,
                    "USD": p_usd,
                    "TL": p_tl,
                    "Link": p.get("url")
                })
            progress_bar.progress((i + 1) / total_products)
        progress_bar.empty()
        
        if rows:
            df = pd.DataFrame(rows)
            
            # KPI
            cnt = len(df)
            avg = sum(prices_tl) / cnt
            mn = min(prices_tl)
            mx = max(prices_tl)
            
            def fmt(val):
                return f"{val:,.0f}₺\n(${val/usd_rate:,.1f})\n({val/loc_rate:,.1f} {curr})"

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Bulunan", f"{cnt} Adet")
            k2.metric("Ortalama", "Ort.", delta_color="off")
            k2.markdown(f"<div style='text-align:center;color:white;font-weight:bold;margin-top:-20px;white-space:pre-wrap;'>{fmt(avg)}</div>", unsafe_allow_html=True)
            k3.metric("En Düşük", "Min", delta_color="off")
            k3.markdown(f"<div style='text-align:center;color:white;font-weight:bold;margin-top:-20px;white-space:pre-wrap;'>{fmt(mn)}</div>", unsafe_allow_html=True)
            k4.metric("En Yüksek", "Max", delta_color="off")
            k4.markdown(f"<div style='text-align:center;color:white;font-weight:bold;margin-top:-20px;white-space:pre-wrap;'>{fmt(mx)}</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Tablo
            st.dataframe(
                df,
                column_config={
                    "Link": st.column_config.LinkColumn("Link", display_text="🔗 Ürüne Git"),
                    "Yerel Fiyat": st.column_config.NumberColumn(f"Fiyat ({curr})", format="%.2f"),
                    "USD": st.column_config.NumberColumn("USD ($)", format="$%.2f"),
                    "TL": st.column_config.NumberColumn("TL (₺)", format="%.2f ₺")
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Excel
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("💾 Excel İndir", csv, f"lcw_sonar_{sel_brand}.csv", "text/csv")
            
        else:
            st.warning("Ürün bulundu ancak fiyatlar okunamadı.")
    else:
        st.error(f"⚠️ {sel_brand} markasının {sel_country} ülkesinde erişilebilir resmi bir e-ticaret sitesi veya online kataloğu bulunamadı.")
        st.info("İpucu: Markanın o ülkede web sitesi olmayabilir veya Sonar erişemiyor olabilir.")
