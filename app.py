import streamlit as st
import pandas as pd
import os
import json
import requests
import re
from deep_translator import GoogleTranslator

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="LCW Home Global (DeepSeek)", layout="wide", page_icon="🚀")

# --- CSS VE ARAYÜZ ---
st.markdown("""
<style>
    .main-header {background-color:#1c54b2; padding:15px; border-radius:10px; color:white; margin-bottom:20px;}
    .metric-card {background-color:#f9f9f9; padding:10px; border-radius:5px; border:1px solid #ddd; text-align:center;}
</style>
<div class="main-header">
    <h1 style='font-size:24px; margin:0;'>LCW HOME | GLOBAL INTELLIGENCE</h1>
    <p style='font-size:12px; margin:0; opacity:0.8;'>Powered by DeepSeek V3 & Serper</p>
</div>
""", unsafe_allow_html=True)

# --- API KEY KONTROLÜ ---
with st.sidebar:
    st.header("🔑 API Anahtarları")
    
    # BURAYI DEĞİŞTİRDİK: ARTIK DEEPSEEK KEY İSTİYORUZ
    DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY")
    if not DEEPSEEK_KEY:
        DEEPSEEK_KEY = st.text_input("DeepSeek API Key:", type="password", help="platform.deepseek.com adresinden alınır")
    
    SERPER_KEY = os.environ.get("SERPER_API_KEY")
    if not SERPER_KEY:
        SERPER_KEY = st.text_input("Serper API Key:", type="password")
    
    st.divider()

if not DEEPSEEK_KEY or not SERPER_KEY:
    st.warning("⚠️ Lütfen DeepSeek ve Serper API anahtarlarını giriniz.")
    st.stop()

# --- SABİTLER VE KONFİGÜRASYON ---
COUNTRIES = {
    "Bulgaristan": {"curr": "BGN", "gl": "bg", "hl": "bg", "lang": "bg"},
    "Sırbistan":   {"curr": "RSD", "gl": "rs", "hl": "sr", "lang": "sr"},
    "Romanya":     {"curr": "RON", "gl": "ro", "hl": "ro", "lang": "ro"},
    "Almanya":     {"curr": "EUR", "gl": "de", "hl": "de", "lang": "de"},
    "Polonya":     {"curr": "PLN", "gl": "pl", "hl": "pl", "lang": "pl"},
    "Türkiye":     {"curr": "TRY", "gl": "tr", "hl": "tr", "lang": "tr"},
}

BRANDS = ["LC Waikiki", "Sinsay", "Pepco", "Zara Home", "H&M Home", "Jysk", "IKEA", "English Home"]

# --- YARDIMCI FONKSİYONLAR ---

@st.cache_data(ttl=3600)
def get_exchange_rates():
    """Güncel kurları çeker. Taban: TRY"""
    try:
        url = "https://api.exchangerate-api.com/v4/latest/TRY"
        response = requests.get(url)
        data = response.json()
        rates = data.get("rates", {})
        
        conversion_rates = {}
        for code, rate in rates.items():
            if rate > 0:
                conversion_rates[code] = 1 / rate
        
        if "EUR" in conversion_rates:
            conversion_rates["BAM"] = conversion_rates["EUR"] / 1.95583
            
        return conversion_rates
    except Exception as e:
        st.error(f"Kur verisi çekilemedi: {e}")
        return None

def translate_text(text, target_lang):
    """Google Translate kullanarak çeviri yapar"""
    if target_lang == 'tr': return text
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except:
        return text

def search_serper(query, gl, hl):
    """Google Serper API üzerinden arama yapar"""
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "gl": gl,
        "hl": hl,
        "num": 15
    })
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        return response.json()
    except Exception as e:
        st.error(f"Arama hatası: {e}")
        return None

def analyze_with_deepseek(search_data, brand, product_name, currency_code):
    """DeepSeek API (OpenAI Uyumlu) kullanarak analiz yapar"""
    
    context_text = ""
    if "organic" in search_data:
        for item in search_data["organic"]:
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            price = item.get('price', item.get('priceRange', 'N/A'))
            link = item.get('link', '')
            context_text += f"PRODUCT: {title} | DESC: {snippet} | PRICE_TAG: {price} | URL: {link}\n"
    
    if not context_text:
        return None

    # DeepSeek için Prompt
    system_msg = "You are a helpful data extraction assistant. You only output valid JSON."
    user_msg = f"""
    I have search results for "{brand}" looking for "{product_name}".
    
    TASKS:
    1. Filter for products strictly matching "{product_name}". Ignore irrelevant items (like socks when looking for towels).
    2. Extract the price as a FLOAT number (use dot '.' for decimals). 
       - Remove currency symbols. 
       - If price is "10,99 €", output 10.99
       - If price is "1.200 RSD", output 1200.0
    
    SEARCH DATA:
    {context_text}
    
    OUTPUT FORMAT (JSON ONLY):
    {{
      "products": [
        {{
          "name": "Product Name",
          "price": 10.99, 
          "currency": "{currency_code}",
          "url": "Product Link"
        }}
      ]
    }}
    """
    
    # DeepSeek API Endpoint
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_KEY}"
    }
    data = {
        "model": "deepseek-chat",  # DeepSeek V3
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        "response_format": {
            "type": "json_object"
        },
        "temperature": 0.1
    }
    
    try:
        res = requests.post(url, headers=headers, json=data)
        if res.status_code == 200:
            content = res.json()['choices'][0]['message']['content']
            return json.loads(content)
        else:
            st.error(f"DeepSeek Hatası: {res.status_code} | {res.text}")
            return None
    except Exception as e:
        st.error(f"AI Bağlantı Hatası: {e}")
        return None

# --- ANA AKIŞ ---

# Yan Menü
with st.sidebar:
    st.header("🔎 Arama Kriterleri")
    sel_country = st.selectbox("Hedef Ülke", list(COUNTRIES.keys()))
    sel_brand = st.selectbox("Rakip Marka", BRANDS)
    q_tr = st.text_input("Aranacak Ürün (Türkçe)", "Çift Kişilik Nevresim Takımı")
    
    start_btn = st.button("Analizi Başlat (DeepSeek) 🚀", type="primary")

# Ana Ekran
if start_btn:
    # 1. Hazırlık
    country_conf = COUNTRIES[sel_country]
    target_currency = country_conf['curr']
    
    st.info(f"📡 {sel_brand} için '{q_tr}' ürünü {sel_country} ({target_currency}) pazarında aranıyor...")
    
    # Kur verisini çek
    rates = get_exchange_rates()
    if not rates:
        st.stop()
        
    usd_rate = rates.get("USD", 1.0)
    local_rate = rates.get(target_currency, 1.0)
    
    # 2. Çeviri
    q_local = translate_text(q_tr, country_conf["lang"])
    st.markdown(f"**Yerel Dilde Arama:** `{q_local}`")
    
    # 3. Google Serper Arama
    search_query = f"{sel_brand} {sel_country} {q_local} price"
    search_results = search_serper(search_query, country_conf["gl"], country_conf["hl"])
    
    if search_results:
        # 4. AI Analizi (DeepSeek)
        with st.spinner("🧠 DeepSeek V3 verileri analiz ediyor..."):
            ai_data = analyze_with_deepseek(search_results, sel_brand, q_tr, target_currency)
        
        if ai_data and "products" in ai_data and len(ai_data["products"]) > 0:
            # 5. Tablo Oluşturma
            df_data = []
            for p in ai_data["products"]:
                try:
                    price_raw = float(p.get("price", 0))
                except:
                    price_raw = 0.0
                
                if price_raw > 0:
                    price_tl = price_raw * local_rate
                    price_usd = price_tl / usd_rate
                    
                    df_data.append({
                        "Ürün Adı": p.get("name"),
                        f"Fiyat ({target_currency})": f"{price_raw:,.2f}",
                        "Fiyat (TL)": f"{price_tl:,.2f} ₺",
                        "Fiyat (USD)": f"${price_usd:,.2f}",
                        "Link": p.get("url")
                    })
            
            if df_data:
                st.success(f"✅ {len(df_data)} adet ürün bulundu ve analiz edildi.")
                df = pd.DataFrame(df_data)
                
                st.dataframe(
                    df, 
                    column_config={
                        "Link": st.column_config.LinkColumn("Ürün Linki")
                    },
                    use_container_width=True
                )
                
                avg_price = pd.Series([float(x['Fiyat (TL)'].replace(' ₺','').replace(',','')) for x in df_data]).mean()
                st.metric(label="Ortalama Fiyat (TL)", value=f"{avg_price:,.2f} ₺")
                
            else:
                st.warning("Ürün bulundu ancak fiyatlar 0 veya geçersiz geldi.")
        else:
            st.warning("AI uygun ürün bulamadı veya sonuç döndürmedi.")
            with st.expander("Ham Arama Sonuçlarını Gör"):
                st.json(search_results)
    else:
        st.error("Google araması sonuç döndürmedi.")
