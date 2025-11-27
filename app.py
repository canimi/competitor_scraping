import streamlit as st
import pandas as pd
import os
import json
import requests
import re
from deep_translator import GoogleTranslator

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="LCW Fiyat Araştırması", layout="wide", page_icon="🛍️")

# --- CSS VE TASARIM (DÜZELTİLDİ) ---
st.markdown("""
<style>
    /* Ana Başlık */
    .block-container {padding-top: 1rem; padding-bottom: 5rem;}
    h1 {color: #1c54b2; font-size: 1.8rem !important; margin-bottom: 0px;}
    
    /* Metrik Kartları (Kurlar ve KPI) */
    div[data-testid="stMetric"] {
        background-color: #f0f2f6; /* Hafif gri arka plan */
        border: 1px solid #d1d1d1;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
    }
    
    /* ÖNEMLİ: Yazı Rengini SİYAH yapmaya zorluyoruz (Dark Mode sorunu için) */
    [data-testid="stMetricValue"] {
        color: #1c54b2 !important; /* LCW Mavisi Rakamlar */
        font-size: 24px !important;
    }
    [data-testid="stMetricLabel"] {
        color: #333333 !important; /* Koyu Gri Etiketler */
        font-weight: bold !important;
    }
    
    /* Sidebar Logo */
    .sidebar-logo {
        color: #1c54b2;
        font-weight: 900;
        font-size: 28px;
        margin-bottom: 5px;
    }
    .sidebar-sub {color: #555; font-size: 13px; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
st.markdown("<h1 style='text-align: center;'>LCW HOME - FİYAT ARAŞTIRMASI</h1>", unsafe_allow_html=True)
st.markdown("<hr style='margin: 5px 0 20px 0;'>", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="sidebar-logo">LCW HOME</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">FİYAT ARAŞTIRMASI</div>', unsafe_allow_html=True)

    PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY")
    if not PERPLEXITY_KEY:
        PERPLEXITY_KEY = st.text_input("🔑 API Anahtarı", type="password")
    
    if not PERPLEXITY_KEY:
        st.warning("API Key giriniz.")
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

def clean_price_string(price_raw):
    """
    Karmaşık fiyat metinlerini (Örn: '12,99 лв', '1.200 RSD') temizler ve float yapar.
    """
    if isinstance(price_raw, (int, float)):
        return float(price_raw)
    
    # Sadece sayıları, noktayı ve virgülü bırak
    text = str(price_raw)
    clean = re.sub(r'[^\d.,]', '', text)
    
    if not clean: return 0.0
    
    # Virgül/Nokta kargaşasını çözme (Avrupa vs ABD formatı)
    # Eğer hem nokta hem virgül varsa: sondaki ondalıktır.
    if ',' in clean and '.' in clean:
        if clean.find(',') > clean.find('.'): # 1.200,50
            clean = clean.replace('.', '').replace(',', '.')
        else: # 1,200.50
            clean = clean.replace(',', '')
    elif ',' in clean:
        # Sadece virgül varsa ve virgülden sonra 2 basamak varsa ondalıktır (genelde)
        clean = clean.replace(',', '.')
    
    try:
        return float(clean)
    except:
        return 0.0

def search_with_perplexity(brand, product_local, country, currency_code):
    url = "https://api.perplexity.ai/chat/completions"
    
    # PROMPT GÜNCELLEMESİ: Fiyat konusunda daha ısrarcı
    system_prompt = "You are a data extraction bot. You ONLY output JSON."
    user_prompt = f"""
    Search for "{brand}" "{product_local}" in {country}.
    
    TASKS:
    1. Find 5-10 products currently available on the official website or major local retailers.
    2. EXTRACT PRICE CAREFULLY. If the price is "5,50 лв", output 5.50. If "1.200 RSD", output 1200.
    3. IGNORE items with NO price.
    
    OUTPUT JSON FORMAT:
    {{
        "products": [
            {{ 
                "name": "Local Product Name", 
                "price": 10.99, 
                "url": "Product URL" 
            }}
        ]
    }}
    """
    
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }
    headers = { "Authorization": f"Bearer {PERPLEXITY_KEY}", "Content-Type": "application/json" }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            clean = response.json()['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        return None
    except:
        return None

# --- YAN MENÜ ---
with st.sidebar:
    st.header("🔎 Filtreler")
    sel_country = st.selectbox("Ülke", list(COUNTRIES.keys()))
    sel_brand = st.selectbox("Marka", BRANDS)
    q_tr = st.text_input("Ürün (TR)", "Çift Kişilik Nevresim")
    st.markdown("---")
    btn_analyze = st.button("Fiyatları Getir 🚀", type="primary", use_container_width=True)

# --- CANLI KUR GÖSTERGESİ (SOL ALT - DÜZELTİLDİ) ---
rates = get_rates()
conf = COUNTRIES[sel_country]
curr_code = conf["curr"]

if rates:
    usd_val = rates.get("USD", 0)
    local_val = rates.get(curr_code, 0)
    
    with st.sidebar:
        st.markdown("### 💰 Güncel Kurlar")
        c1, c2 = st.columns(2)
        c1.metric("USD/TRY", f"{usd_val:.2f} ₺")
        if curr_code != "TRY":
            c2.metric(f"{curr_code}/TRY", f"{local_val:.2f} ₺")
        else:
            c2.metric("TRY", "1.00")

# --- ANA EKRAN ---
if btn_analyze:
    if not rates: st.error("Kur bağlantısı yok."); st.stop()
    
    # 1. Çeviri
    q_local = translate_text(q_tr, conf["lang"])
    
    with st.spinner(f"🌍 {sel_country} ({q_local}) taranıyor..."):
        data = search_with_perplexity(sel_brand, q_local, sel_country, curr_code)
        
    if data and "products" in data:
        table_rows = []
        prices_tl = []
        
        usd_rate = rates.get("USD", 1)
        local_rate = rates.get(curr_code, 1)
        
        for p in data["products"]:
            # FİYAT PARSE (GÜÇLENDİRİLMİŞ)
            p_raw = clean_price_string(p.get("price", 0))
            
            if p_raw > 0:
                p_tl = p_raw * local_rate
                p_usd = p_tl / usd_rate
                
                prices_tl.append(p_tl)
                table_rows.append({
                    "Ürün Yerel Adı": p.get("name"),
                    "Ürün Türkçe Adı": q_tr,
                    "Yerel Fiyat": p_raw,
                    "USD": p_usd,
                    "TL": p_tl,
                    "Link": p.get("url")
                })
        
        if table_rows:
            df = pd.DataFrame(table_rows)
            
            # --- KPI ---
            count = len(df)
            avg_tl = sum(prices_tl) / count
            min_tl = min(prices_tl)
            max_tl = max(prices_tl)
            
            def fmt_price(tl_val):
                usd_val = tl_val / usd_rate
                loc_val = tl_val / local_rate
                return f"{tl_val:,.0f} ₺\n(${usd_val:,.1f})\n({loc_val:,.1f} {curr_code})"

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Bulunan", f"{count} Adet")
            kpi2.metric("Ortalama", "Ort.", delta=None)
            kpi2.markdown(f"<div style='text-align:center; font-weight:bold; color:#333; white-space: pre-line;'>{fmt_price(avg_tl)}</div>", unsafe_allow_html=True)
            
            kpi3.metric("En Düşük", "Min", delta=None)
            kpi3.markdown(f"<div style='text-align:center; font-weight:bold; color:#333; white-space: pre-line;'>{fmt_price(min_tl)}</div>", unsafe_allow_html=True)
            
            kpi4.metric("En Yüksek", "Max", delta=None)
            kpi4.markdown(f"<div style='text-align:center; font-weight:bold; color:#333; white-space: pre-line;'>{fmt_price(max_tl)}</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # --- TABLO ---
            st.dataframe(
                df,
                column_config={
                    "Link": st.column_config.LinkColumn("Link", display_text="Ürüne Git 🔗"),
                    "Yerel Fiyat": st.column_config.NumberColumn(f"Fiyat ({curr_code})", format="%.2f"),
                    "USD": st.column_config.NumberColumn("USD ($)", format="$%.2f"),
                    "TL": st.column_config.NumberColumn("TL (₺)", format="%.2f ₺"),
                },
                hide_index=True,
                use_container_width=True
            )
            
            # --- EXCEL ---
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="💾 Excel Olarak İndir",
                data=csv,
                file_name=f'lcw_analiz_{sel_brand}_{sel_country}.csv',
                mime='text/csv',
            )
            
        else:
            st.warning("Ürünler bulundu ancak fiyatlar '0' olarak döndü. Site fiyatı gizliyor olabilir.")
            st.json(data) # Debug için ham veriyi gösterelim
    else:
        st.error("Sonuç bulunamadı.")
