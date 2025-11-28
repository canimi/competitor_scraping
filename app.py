import streamlit as st
import pandas as pd
import os
import json
import requests
import re
from deep_translator import GoogleTranslator

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
st.markdown("<h1>LCW HOME | GLOBAL INTELLIGENCE</h1>", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 style="color:#4da6ff; margin-bottom:0;">LCW HOME</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e; font-size:12px;">COMPETITOR PRICE TRACKER</p>', unsafe_allow_html=True)
    PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY") or st.text_input("🔑 Perplexity API Key", type="password")
    if not PERPLEXITY_KEY: st.warning("⚠️ API Key Gerekli"); st.stop()

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
    "Arnavutluk":   {"curr": "ALL", "lang": "sq"},
    "Makedonya":    {"curr": "MKD", "lang": "mk"},
    "Kosova":       {"curr": "EUR", "lang": "sq"},
    "Moldova":      {"curr": "MDL", "lang": "ro"},
    "Fas":          {"curr": "MAD", "lang": "ar"},
}

BRANDS = ["Pepco", "Sinsay", "Zara Home", "H&M Home", "Jysk", "Primark", "Jumbo", "English Home"]

# --- FONKSİYONLAR ---

@st.cache_data(ttl=3600)
def get_rates():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/TRY").json()['rates']
        rates = {k: 1/v for k, v in r.items() if v > 0} 
        if "EUR" in rates: rates["BAM"] = rates["EUR"] / 1.95583
        return rates
    except: return None

def translate_logic(text, mode="to_local", target_lang="en"):
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
    
    # Gereksiz kelimeleri temizle
    for bad in ["from", "start", "to", "price", "fiyat", "only"]:
        s = s.replace(bad, "")
        
    # Para birimlerini temizle
    for code in ["rsd", "din", "km", "bam", "лв", "bgn", "eur", "ron", "lei", "tl", "try", "huf", "ft", "$", "€", "£"]:
        s = s.replace(code, "")
    
    s = s.strip()
    # Sadece sayı ve noktalama kalsın
    s = re.sub(r'[^\d.,]', '', s)
    if not s: return 0.0
    
    # Karmaşık sayı formatlarını çözme
    try:
        if ',' in s and '.' in s:
            if s.rfind(',') > s.rfind('.'): # 1.250,00 formatı
                s = s.replace('.', '').replace(',', '.')
            else: # 1,250.00 formatı
                s = s.replace(',', '')
        elif ',' in s:
            if len(s.split(',')[-1]) == 2: s = s.replace(',', '.')
            else: s = s.replace(',', '.')
        
        return float(s)
    except: return 0.0

def search_sonar(brand, product_local, product_english, country, currency_code, hardcoded_url):
    url = "https://api.perplexity.ai/chat/completions"
    domain = hardcoded_url.replace("https://", "").replace("http://", "").split("/")[0]

    system_msg = """You are a strict e-commerce data analyst. 
    You output ONLY valid JSON. 
    Your Highest Priority is RELEVANCE. Do not output mismatched products."""
    
    # --- YENİLENEN KATI PROMPT ---
    user_msg = f"""
    TASK: Find EXACT matches for the product '{product_english}' (Local Name: {product_local}) at '{brand}' in '{country}'.
    WEBSITE: {hardcoded_url}
    
    STRICT FILTERING RULES:
    1. The product MUST be a '{product_english}'.
    2. EXCLUDE unrelated accessories. 
       - If looking for 'Duvet Cover', DO NOT include 'Pillow', 'Cushion', 'Sheet', 'Rug', or 'Blanket'.
       - If looking for 'Towel', DO NOT include 'Bathrobe'.
    3. If the item is a "Set", ensure the main component matches the search query.
    
    SEARCH STEPS:
    1. Search for "{brand} {country} {product_local}".
    2. Check the product titles. If a title contains words meaning "Pillow", "Case", "Sheet" but NOT "Duvet Cover", DISCARD IT.
    
    OUTPUT JSON ONLY:
    {{
        "products": [
            {{ "name": "Exact Product Name", "price": "10.99", "url": "link" }}
        ]
    }}
    
    If no EXACT matches are found, return empty products list []. DO NOT guess.
    """
    
    payload = {
        "model": "sonar",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
        "temperature": 0.1, # Daha da düşürdüm, yaratıcılık istemiyoruz.
        "max_tokens": 3000
    }
    
    headers = { "Authorization": f"Bearer {PERPLEXITY_KEY}", "Content-Type": "application/json" }
    
    try:
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            raw = res.json()['choices'][0]['message']['content']
            clean = raw.replace("```json", "").replace("```", "").strip()
            start = clean.find("{")
            end = clean.rfind("}")
            if start != -1 and end != -1:
                clean = clean[start:end+1]
                return json.loads(clean)
            return None
        return None
    except Exception as e: 
        st.error(f"Hata: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔎 Filtreler")
    available_countries = list(URL_DB.keys())
    sel_country = st.selectbox("Ülke", available_countries)
    sel_brand = st.selectbox("Marka", BRANDS)
    q_tr = st.text_input("Ürün (TR)", "Çift Kişilik Nevresim")
    st.markdown("---")
    btn_start = st.button("FİYATLARI ÇEK 🚀")

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
    if not rates: st.error("Kur verisi yok."); st.stop()
    
    target_url = URL_DB.get(sel_country, {}).get(sel_brand)
    
    if not target_url:
        st.error(f"⚠️ {sel_brand} markasının {sel_country} için mağazası yok.")
        st.session_state['search_results'] = None
    else:
        st.success(f"🎯 Hedef Site: {target_url}")
        
        q_local = translate_logic(q_tr, "to_local", conf["lang"])
        q_english = translate_logic(q_tr, "to_english")
        
        st.info(f"🔎 Aranıyor: **{q_local}** (Yerel) ve **{q_english}** (Global)")
        
        with st.spinner(f"🧿 {sel_brand} üzerinde '{q_english}' aranıyor..."):
            data = search_sonar(sel_brand, q_local, q_english, sel_country, curr, target_url)
        
        if data and "products" in data and len(data["products"]) > 0:
            rows = []
            prices_tl = []
            usd_rate = rates.get("USD", 1)
            loc_rate = rates.get(curr, 1)
            
            pbar = st.progress(0, text="Veriler işleniyor...")
            tot = len(data["products"])
            
            for i, p in enumerate(data["products"]):
                p_raw = clean_price(p.get("price", 0), curr)
                if p_raw > 0:
                    p_tl = p_raw * loc_rate
                    p_usd = p_tl / usd_rate
                    prices_tl.append(p_tl)
                    
                    loc_name = p.get("name", "Bilinmiyor")
                    tr_name = translate_logic(loc_name, "to_turkish")
                    
                    rows.append({
                        "Marka": sel_brand,
                        "Ülke": sel_country,
                        "Ürün Yerel Adı": loc_name,
                        "Ürün Türkçe Adı": tr_name,
                        "Yerel Fiyat": p_raw,
                        "USD": p_usd,
                        "TL": p_tl,
                        "Link": p.get("url")
                    })
                pbar.progress((i + 1) / tot)
            pbar.empty()
            
            if rows:
                df = pd.DataFrame(rows)
                cols = ["Marka", "Ülke", "Ürün Yerel Adı", "Ürün Türkçe Adı", "Yerel Fiyat", "USD", "TL", "Link"]
                df = df[cols]
                
                st.session_state['search_results'] = {
                    "df": df, "prices_tl": prices_tl, 
                    "usd_rate": usd_rate, "loc_rate": loc_rate, "curr": curr
                }
            else:
                st.warning(f"⚠️ {sel_brand} sitesinde fiyat formatı okunamadı.")
        else:
            st.error(f"⚠️ Ürün bulunamadı. '{q_local}' için tam eşleşen ürün bulunamadı. Lütfen aramayı genelleştirin veya farklı bir ürün deneyin.")
            st.session_state['search_results'] = None

# --- RENDER ---
if st.session_state['search_results'] is not None:
    res = st.session_state['search_results']
    df = res["df"]
    prices_tl = res["prices_tl"]
    usd_rate = res["usd_rate"]
    loc_rate = res["loc_rate"]
    curr = res["curr"]
    
    cnt = len(df)
    if cnt > 0:
        avg = sum(prices_tl) / cnt
        mn = min(prices_tl)
        mx = max(prices_tl)
        def fmt(val): return f"{val:,.0f}₺\n(${val/usd_rate:,.1f})\n({val/loc_rate:,.1f} {curr})"

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Bulunan", f"{cnt} Adet")
        k2.metric("Ortalama", "Ort.", delta_color="off")
        k2.markdown(f"<div style='text-align:center;color:white;font-weight:bold;margin-top:-20px;white-space:pre-wrap;'>{fmt(avg)}</div>", unsafe_allow_html=True)
        k3.metric("En Düşük", "Min", delta_color="off")
        k3.markdown(f"<div style='text-align:center;color:white;font-weight:bold;margin-top:-20px;white-space:pre-wrap;'>{fmt(mn)}</div>", unsafe_allow_html=True)
        k4.metric("En Yüksek", "Max", delta_color="off")
        k4.markdown(f"<div style='text-align:center;color:white;font-weight:bold;margin-top:-20px;white-space:pre-wrap;'>{fmt(mx)}</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.dataframe(
            df,
            column_config={
                "Link": st.column_config.LinkColumn("Link", display_text="🔗 Git"),
                "Yerel Fiyat": st.column_config.NumberColumn(f"Fiyat ({curr})", format="%.2f"),
                "USD": st.column_config.NumberColumn("USD ($)", format="$%.2f"),
                "TL": st.column_config.NumberColumn("TL (₺)", format="%.2f ₺")
            },
            use_container_width=True,
            hide_index=True
        )
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("💾 Excel İndir", csv, "lcw_analiz.csv", "text/csv")
