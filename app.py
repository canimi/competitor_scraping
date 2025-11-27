import streamlit as st
import pandas as pd
import os
import json
import requests
import re
from deep_translator import GoogleTranslator

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="LCW Home Global Intelligence", layout="wide", page_icon="🌍")

# --- CSS VE ARAYÜZ ---
st.markdown("""
<style>
    .main-header {background-color:#1c54b2; padding:15px; border-radius:10px; color:white; margin-bottom:20px;}
    .metric-card {background-color:#f9f9f9; padding:10px; border-radius:5px; border:1px solid #ddd; text-align:center;}
</style>
<div class="main-header">
    <h1 style='font-size:24px; margin:0;'>LCW HOME | GLOBAL INTELLIGENCE</h1>
    <p style='font-size:12px; margin:0; opacity:0.8;'>Rakip Fiyat Analiz ve Takip Sistemi</p>
</div>
""", unsafe_allow_html=True)

# --- API KEY KONTROLÜ ---
with st.sidebar:
    st.header("🔑 API Anahtarları")
    GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")
    if not GOOGLE_KEY:
        GOOGLE_KEY = st.text_input("Google Gemini API Key", type="password")
    
    SERPER_KEY = os.environ.get("SERPER_API_KEY")
    if not SERPER_KEY:
        SERPER_KEY = st.text_input("Serper API Key", type="password")
    
    st.divider()

if not GOOGLE_KEY or not SERPER_KEY:
    st.warning("⚠️ Lütfen sol menüden API anahtarlarını giriniz.")
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
        # Base TRY alıyoruz, yani 1 TRY = X Yabancı Para
        url = "https://api.exchangerate-api.com/v4/latest/TRY"
        response = requests.get(url)
        data = response.json()
        rates = data.get("rates", {})
        
        # Bize lazım olan: 1 Yabancı Para = Kaç TL? 
        # API 1 TRY = 0.027 EUR veriyorsa, 1 EUR = 1/0.027 = 37 TL'dir.
        conversion_rates = {}
        for code, rate in rates.items():
            if rate > 0:
                conversion_rates[code] = 1 / rate
        
        # Bosna Markı (BAM) genelde EUR'a endekslidir (1 EUR = 1.95583 BAM)
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
        "num": 15 # İlk 15 sonuç yeterli
    })
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        return response.json()
    except Exception as e:
        st.error(f"Arama hatası: {e}")
        return None

def analyze_with_gemini(search_data, brand, product_name, currency_code):
    """Gemini'ye sonuçları yorumlatır ve temiz JSON çıktısı ister"""
    
    # 1. Arama sonuçlarını metne dök
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

    # 2. Prompt Mühendisliği (Sorunları Çözen Kısım)
    prompt = f"""
    You are a pricing analyst AI. I will give you search results for the brand "{brand}" looking for the product "{product_name}".
    
    YOUR TASK:
    1. Identify products that strictly match the category "{product_name}".
    2. IGNORE irrelevant items (e.g., if looking for 'Towel', ignore 'Underwear', 'Socks', 'T-shirt').
    3. EXTRACT the price. IMPORTANT: Convert the price to a purely numeric float format with a DOT (.) as the decimal separator. Do NOT include currency symbols in the 'price' field.
       - Example: "10,99 €" -> 10.99
       - Example: "1.200 RSD" -> 1200.0
    4. Return a JSON object with a key "products".
    
    CONTEXT DATA:
    {context_text}
    
    REQUIRED JSON OUTPUT FORMAT:
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
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    try:
        res = requests.post(url, headers=headers, json=data)
        if res.status_code == 200:
            content = res.json()['candidates'][0]['content']['parts'][0]['text']
            # Temizlik (bazen markdown ```json ile gelebilir)
            clean_json = content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        else:
            st.error(f"AI Hatası: {res.text}")
            return None
    except Exception as e:
        st.error(f"AI Parse Hatası: {e}")
        return None

# --- ANA AKIŞ ---

# Yan Menü
with st.sidebar:
    st.header("🔎 Arama Kriterleri")
    sel_country = st.selectbox("Hedef Ülke", list(COUNTRIES.keys()))
    sel_brand = st.selectbox("Rakip Marka", BRANDS)
    q_tr = st.text_input("Aranacak Ürün (Türkçe)", "Çift Kişilik Nevresim Takımı")
    
    start_btn = st.button("Analizi Başlat 🚀", type="primary")

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
        
    usd_rate = rates.get("USD", 1.0) # 1 USD kaç TL
    local_rate = rates.get(target_currency, 1.0) # 1 Yerel Para kaç TL
    
    # 2. Çeviri
    q_local = translate_text(q_tr, country_conf["lang"])
    st.markdown(f"**Yerel Dilde Arama:** `{q_local}`")
    
    # 3. Google Serper Arama
    search_query = f"{sel_brand} {sel_country} {q_local} price"
    search_results = search_serper(search_query, country_conf["gl"], country_conf["hl"])
    
    if search_results:
        # 4. AI Analizi ve Parsing
        with st.spinner("🤖 Yapay zeka fiyatları ayıklıyor ve filtreliyor..."):
            ai_data = analyze_with_gemini(search_results, sel_brand, q_tr, target_currency)
        
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
                    price_usd = price_tl / usd_rate # (TL'ye çevirip sonra USD kuruna bölüyoruz veya direkt çapraz kur)
                    # Doğrusu: price_raw (Yerel) * (1 Yerel kaç TL) = TL Fiyat
                    # USD Fiyat = TL Fiyat / (1 USD kaç TL)
                    
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
                
                # Tabloyu göster
                st.dataframe(
                    df, 
                    column_config={
                        "Link": st.column_config.LinkColumn("Ürün Linki")
                    },
                    use_container_width=True
                )
                
                # İstatistikler
                avg_price = pd.Series([float(x['Fiyat (TL)'].replace(' ₺','').replace(',','')) for x in df_data]).mean()
                st.metric(label="Ortalama Fiyat (TL)", value=f"{avg_price:,.2f} ₺")
                
            else:
                st.warning("Ürün bulundu ancak fiyatlar 0 veya geçersiz geldi.")
        else:
            st.warning("AI uygun ürün bulamadı. Arama terimini değiştirmeyi deneyin.")
            with st.expander("Ham Arama Sonuçlarını Gör"):
                st.json(search_results)
    else:
        st.error("Google araması sonuç döndürmedi.")
