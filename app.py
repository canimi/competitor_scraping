import streamlit as st
import pandas as pd
import os
import json
import requests
from deep_translator import GoogleTranslator

# --- SAYFA AYARLARI (Geniş Ekran) ---
st.set_page_config(page_title="LCW Fiyat Araştırması", layout="wide", page_icon="🛍️")

# --- CSS VE TASARIM (LCW MAVİSİ) ---
st.markdown("""
<style>
    /* Ana Başlık Alanı */
    .block-container {padding-top: 1rem; padding-bottom: 5rem;}
    h1 {color: #1c54b2; font-size: 1.8rem !important; margin-bottom: 0px;}
    
    /* Metrik Kartları */
    div[data-testid="stMetric"] {
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
    }
    div[data-testid="stMetricLabel"] {font-weight: bold; color: #555;}
    
    /* Sidebar Header */
    .sidebar-logo {
        color: #1c54b2;
        font-weight: 900;
        font-size: 28px;
        margin-bottom: 10px;
        text-align: left;
    }
    .sidebar-sub {color: #666; font-size: 12px; margin-top: -10px; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
st.markdown("<h1 style='text-align: center;'>LCW HOME - FİYAT ARAŞTIRMASI</h1>", unsafe_allow_html=True)
st.markdown("<hr style='margin: 5px 0 20px 0;'>", unsafe_allow_html=True)

# --- SIDEBAR BAŞLIK ---
with st.sidebar:
    st.markdown('<div class="sidebar-logo">LCW HOME</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">GLOBAL INTELLIGENCE</div>', unsafe_allow_html=True)

    # API KEY (Gizli Giriş)
    PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY")
    if not PERPLEXITY_KEY:
        PERPLEXITY_KEY = st.text_input("🔑 Sistem Anahtarı", type="password")
    
    if not PERPLEXITY_KEY:
        st.warning("Lütfen API anahtarını giriniz.")
        st.stop()

# --- VERİ SETLERİ ---
# Not: Kosova ve Montenegro resmi olarak Euro kullanır.
COUNTRIES = {
    "Bulgaristan":  {"curr": "BGN", "lang": "bg"},
    "Yunanistan":   {"curr": "EUR", "lang": "el"},
    "Kazakistan":   {"curr": "KZT", "lang": "kk"},
    "Rusya":        {"curr": "RUB", "lang": "ru"},
    "Ukrayna":      {"curr": "UAH", "lang": "uk"},
    "Bosna Hersek": {"curr": "BAM", "lang": "bs"},
    "Sırbistan":    {"curr": "RSD", "lang": "sr"},
    "Montenegro":   {"curr": "EUR", "lang": "sr"}, # Karadağ Euro kullanır
    "Arnavutluk":   {"curr": "ALL", "lang": "sq"},
    "Makedonya":    {"curr": "MKD", "lang": "mk"},
    "Kosova":       {"curr": "EUR", "lang": "sq"}, # Kosova Euro kullanır
    "Moldova":      {"curr": "MDL", "lang": "ro"},
    "Hırvatistan":  {"curr": "EUR", "lang": "hr"},
    "Romanya":      {"curr": "RON", "lang": "ro"},
    "Mısır":        {"curr": "EGP", "lang": "ar"},
    "Fas":          {"curr": "MAD", "lang": "ar"},
    "Irak":         {"curr": "IQD", "lang": "ar"},
}

BRANDS = ["LC Waikiki", "Sinsay", "Pepco", "Zara Home", "H&M Home", "Jysk", "Primark", "Jumbo", "English Home"]

# --- FONKSİYONLAR ---

@st.cache_data(ttl=3600)
def get_rates():
    """Kur verisini çeker"""
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/TRY").json()['rates']
        rates = {k: 1/v for k, v in r.items() if v > 0} # 1 Yabancı Para = Kaç TL
        # BAM (Bosna) Euro'ya endekslidir
        if "EUR" in rates: 
            rates["BAM"] = rates["EUR"] / 1.95583
        return rates
    except:
        return None

def translate_text(text, target_lang):
    if target_lang == 'tr': return text
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except:
        return text

def search_with_perplexity(brand, product_local, country, currency_code):
    """Perplexity Sonar-Pro ile Arama"""
    url = "https://api.perplexity.ai/chat/completions"
    
    system_prompt = "You are a precise pricing assistant. Output only strictly valid JSON."
    user_prompt = f"""
    Search for the product category "{product_local}" for brand "{brand}" in {country}.
    
    RULES:
    1. Find 5 to 10 products from the official site or major local retailers.
    2. Extract the exact price. Convert text like "1.299,99 RSD" to float 1299.99.
    3. Get the original product name in local language.
    4. Ignore out of stock or completely irrelevant items.
    
    OUTPUT JSON:
    {{
        "products": [
            {{ "name": "Local Product Name", "price": 10.50, "url": "http..." }}
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
    except Exception as e:
        st.error(f"Hata: {e}")
        return None

# --- YAN MENÜ FİLTRELERİ ---
with st.sidebar:
    st.header("🔎 Filtreler")
    sel_country = st.selectbox("Ülke", list(COUNTRIES.keys()))
    sel_brand = st.selectbox("Marka", BRANDS)
    q_tr = st.text_input("Ürün (TR)", "Çift Kişilik Nevresim")
    
    st.markdown("---")
    btn_analyze = st.button("Fiyatları Getir 🚀", type="primary", use_container_width=True)

# --- CANLI KUR GÖSTERGESİ (SOL ALT) ---
rates = get_rates()
conf = COUNTRIES[sel_country]
curr_code = conf["curr"]

if rates:
    usd_tl = 1 / rates.get("USD", 1) # 1 USD kaç TL (Kur verisi TRY bazlı olduğu için ters çevir)
    # Düzeltme: get_rates fonksiyonum 1 Yabancı = X TL veriyor.
    # Yani rates["USD"] -> 34.50 gibi.
    
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

# --- ANA EKRAN İŞLEMLERİ ---
if btn_analyze:
    if not rates: st.error("Kur verisi alınamadı!"); st.stop()
    
    # 1. Çeviri
    q_local = translate_text(q_tr, conf["lang"])
    
    with st.spinner(f"🌍 {sel_country} pazarında {sel_brand} aranıyor..."):
        data = search_with_perplexity(sel_brand, q_local, sel_country, curr_code)
        
    if data and "products" in data:
        # 2. Veri İşleme
        table_rows = []
        prices_tl = []
        
        usd_rate = rates.get("USD", 1) # 1 USD = X TL
        local_rate = rates.get(curr_code, 1) # 1 Yerel = Y TL
        
        for p in data["products"]:
            try:
                p_raw = float(p.get("price", 0))
            except:
                p_raw = 0.0
            
            if p_raw > 0:
                p_tl = p_raw * local_rate
                p_usd = p_tl / usd_rate
                
                prices_tl.append(p_tl)
                
                table_rows.append({
                    "Ürün Yerel Adı": p.get("name"),
                    "Ürün Türkçe Adı": q_tr,
                    "Yerel Fiyat": p_raw,     # Sayısal kalsın (sıralama için)
                    "USD": p_usd,             # Sayısal kalsın
                    "TL": p_tl,               # Sayısal kalsın
                    "Link": p.get("url")
                })
        
        if table_rows:
            df = pd.DataFrame(table_rows)
            
            # --- KPI METRİKLERİ ---
            count = len(df)
            avg_tl = sum(prices_tl) / count
            min_tl = min(prices_tl)
            max_tl = max(prices_tl)
            
            # Yardımcı Fonksiyon: 3'lü Fiyat Stringi Oluşturma
            def fmt_price(tl_val):
                usd_val = tl_val / usd_rate
                loc_val = tl_val / local_rate
                return f"{tl_val:,.0f} ₺\n(${usd_val:,.1f})\n({loc_val:,.1f} {curr_code})"

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Bulunan Ürün", f"{count} Adet")
            kpi2.metric("Ortalama", "Ort.", delta=None, help="Ortalama Fiyat")
            kpi2.markdown(f"<div style='text-align:center; font-weight:bold; white-space: pre-line;'>{fmt_price(avg_tl)}</div>", unsafe_allow_html=True)
            
            kpi3.metric("En Düşük", "Min", delta=None)
            kpi3.markdown(f"<div style='text-align:center; font-weight:bold; white-space: pre-line;'>{fmt_price(min_tl)}</div>", unsafe_allow_html=True)
            
            kpi4.metric("En Yüksek", "Max", delta=None)
            kpi4.markdown(f"<div style='text-align:center; font-weight:bold; white-space: pre-line;'>{fmt_price(max_tl)}</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # --- TABLO GÖSTERİMİ ---
            # Gösterim için formatlı kopya oluşturuyoruz, ama orijinali excel için saklıyoruz
            df_display = df.copy()
            
            st.dataframe(
                df_display,
                column_config={
                    "Link": st.column_config.LinkColumn(
                        "Link", display_text="Ürüne Git 🔗"
                    ),
                    "Yerel Fiyat": st.column_config.NumberColumn(f"Fiyat ({curr_code})", format="%.2f"),
                    "USD": st.column_config.NumberColumn("USD ($)", format="$%.2f"),
                    "TL": st.column_config.NumberColumn("TL (₺)", format="%.2f ₺"),
                },
                hide_index=True,
                use_container_width=True
            )
            
            # --- EXCEL İNDİR ---
            @st.cache_data
            def convert_df(df):
                return df.to_csv(index=False).encode('utf-8-sig')

            csv = convert_df(df)
            st.download_button(
                label="💾 Tabloyu Excel Olarak İndir",
                data=csv,
                file_name=f'lcw_analiz_{sel_brand}_{sel_country}.csv',
                mime='text/csv',
            )
            
        else:
            st.warning("Ürün bulundu ancak geçerli fiyat bilgisi okunamadı.")
    else:
        st.error("Perplexity sonuç döndüremedi. Ülke veya marka adını kontrol edin.")
