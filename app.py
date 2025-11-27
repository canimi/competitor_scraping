import streamlit as st
import pandas as pd
import os
import json
import requests
import re
from deep_translator import GoogleTranslator

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="LCW Global Intelligence", layout="wide", page_icon="🧿")

# --- CSS: DARK MODE, NEON VE OKUNABİLİRLİK ---
st.markdown("""
<style>
    /* Genel Arka Plan ve Fontlar */
    .stApp {
        background-color: #0e1117;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Başlık */
    h1 {
        color: #4da6ff;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 0 0 15px rgba(77, 166, 255, 0.6);
        margin-bottom: 20px !important;
    }

    /* KPI Kartları (Siyah Zemin, Beyaz Yazı) */
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
    }
    [data-testid="stMetricValue"] {
        color: #ffffff !important; /* BEYAZ RAKAMLAR */
        font-size: 28px !important;
        font-weight: 700 !important;
        text-shadow: 0 0 10px rgba(255,255,255,0.2);
    }
    [data-testid="stMetricLabel"] {
        color: #8b949e !important; /* Gri Etiket */
        font-size: 14px !important;
    }

    /* Tablo Özelleştirme */
    .stDataFrame { border: 1px solid #30363d; border-radius: 5px; }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0d1117;
        border-right: 1px solid #30363d;
    }
    .sidebar-logo {
        color: #4da6ff;
        font-size: 26px;
        font-weight: 900;
        margin-bottom: 5px;
    }
    .sidebar-sub { color: #8b949e; font-size: 12px; margin-bottom: 30px; }
    
    /* Buton */
    div.stButton > button {
        background: linear-gradient(90deg, #1c54b2 0%, #0d3c85 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        font-weight: bold;
        width: 100%;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px rgba(28, 84, 178, 0.5);
    }
    
    /* Hata/Bilgi Mesajları */
    .stAlert { background-color: #161b22; color: #e6edf3; border: 1px solid #30363d; }
</style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
st.markdown("<h1>LCW HOME | GLOBAL INTELLIGENCE</h1>", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="sidebar-logo">LCW HOME</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">COMPETITOR PRICE TRACKER</div>', unsafe_allow_html=True)

    PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY")
    if not PERPLEXITY_KEY:
        PERPLEXITY_KEY = st.text_input("🔑 Perplexity API Key", type="password")

    if not PERPLEXITY_KEY:
        st.warning("⚠️ API Key Gerekli")
        st.stop()

# --- VERİ SETLERİ ---
COUNTRIES = {
    "Bulgaristan":  {"curr": "BGN", "lang": "bg"},
    "Yunanistan":   {"curr": "EUR", "lang": "el"},
    "Kazakistan":   {"curr": "KZT", "lang": "kk"},
    "Rusya":        {"curr": "RUB", "lang": "ru"},
    "Ukrayna":      {"curr": "UAH", "lang": "uk"},
    "Bosna Hersek": {"curr": "BAM", "lang": "bs"},
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
    """Kurları çeker (Base: TRY)"""
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/TRY").json()['rates']
        rates = {k: 1/v for k, v in r.items() if v > 0} 
        if "EUR" in rates: rates["BAM"] = rates["EUR"] / 1.95583
        return rates
    except:
        return None

def translate_text(text, target_lang):
    if target_lang == 'tr': return text
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except:
        return text

def clean_price(price_raw):
    """Agresif Fiyat Temizleyici"""
    if not price_raw: return 0.0
    s = str(price_raw).lower().replace("лв", "").replace("lei", "").replace("eur", "").replace("rsd", "").strip()
    
    # Sadece rakam, nokta ve virgül kalsın
    s = re.sub(r'[^\d.,]', '', s)
    if not s: return 0.0
    
    # Avrupa formatı (1.200,50) -> (1200.50)
    if ',' in s and '.' in s:
        if s.find(',') > s.find('.'): # 1.000,00
            s = s.replace('.', '').replace(',', '.')
        else: # 1,000.00
            s = s.replace(',', '')
    elif ',' in s:
        if len(s.split(',')[-1]) == 2: # 12,50
            s = s.replace(',', '.')
        else: # 1,200 -> 1200 (Riskli ama genelde doğru)
            s = s.replace(',', '.')
            
    try:
        return float(s)
    except:
        return 0.0

def search_sonar(brand, product_local, country, currency_code):
    """
    SADECE SONAR MODELİ KULLANILIR.
    Render mantığını simüle etmek için "Specific Site Search" komutu verilir.
    """
    url = "https://api.perplexity.ai/chat/completions"
    
    # PROMPT: Modelin 'Researcher' kimliğine bürünmesini sağlıyoruz.
    system_msg = "You are an advanced eCommerce scraper. You extract strictly structured JSON data from search results."
    
    user_msg = f"""
    Perform a targeted search for "{brand}" products in category "{product_local}" for the country "{country}".
    
    INSTRUCTIONS (IMPORTANT):
    1. Search specifically on the official "{brand}" website for {country} (e.g., pepco.bg, sinsay.com/rs).
    2. If official site fails, look at catalog aggregators (like kimbino, catalog.bg) which list current prices.
    3. EXTRACT 5-10 PRODUCTS.
    4. Price MUST be a number. If you see "5,99 лв", output 5.99.
    5. IGNORE items with no price.
    
    OUTPUT JSON FORMAT (STRICT):
    {{
        "products": [
            {{
                "name": "Product Name",
                "price": 10.99,
                "url": "Product Link"
            }}
        ]
    }}
    """
    
    payload = {
        "model": "sonar", # İSTENİLEN MODEL (PRO YOK!)
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        "temperature": 0.1, # Kesinlik için düşük
        "max_tokens": 1000  # Yeterli alan
    }
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            raw = res.json()['choices'][0]['message']['content']
            # JSON Temizliği
            clean = raw.replace("```json", "").replace("```", "").strip()
            # Bazen başında/sonunda yazı olabilir, sadece { ... } arasını al
            start = clean.find('{')
            end = clean.rfind('}') + 1
            if start != -1 and end != -1:
                clean = clean[start:end]
            return json.loads(clean)
        else:
            st.error(f"Sonar Bağlantı Hatası: {res.status_code}")
            return None
    except Exception as e:
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
    q_local = translate_text(q_tr, conf["lang"])
    
    # 2. Sonar Araması
    with st.spinner(f"🧿 Sonar (Standart) '{sel_brand}' sitesini tarıyor: {q_local} ..."):
        data = search_sonar(sel_brand, q_local, sel_country, curr)
    
    if data and "products" in data:
        rows = []
        prices_tl = []
        
        usd_rate = rates.get("USD", 1)
        loc_rate = rates.get(curr, 1)
        
        for p in data["products"]:
            p_raw = clean_price(p.get("price", 0))
            
            if p_raw > 0:
                p_tl = p_raw * loc_rate
                p_usd = p_tl / usd_rate
                prices_tl.append(p_tl)
                
                rows.append({
                    "Ürün Yerel Adı": p.get("name"),
                    "Ürün Türkçe Adı": q_tr,
                    "Yerel Fiyat": p_raw,
                    "USD": p_usd,
                    "TL": p_tl,
                    "Link": p.get("url")
                })
        
        if rows:
            df = pd.DataFrame(rows)
            
            # --- KPI ---
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
            
            # --- TABLO ---
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
            
            # --- EXCEL ---
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("💾 Excel İndir", csv, f"lcw_sonar_{sel_brand}.csv", "text/csv")
            
        else:
            st.warning("Ürün bulundu ama fiyatlar okunamadı (0 geldi).")
            # Debug:
            # st.write(data)
    else:
        st.error("Sonar sonuç bulamadı. Daha genel bir ürün adı deneyin.")
