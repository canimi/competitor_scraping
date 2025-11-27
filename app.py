import streamlit as st
import pandas as pd
import requests
import json
import os
from deep_translator import GoogleTranslator

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="AI Fiyat Dedektifi", layout="wide", page_icon="🕵️")

# --- ENV KONTROLÜ ---
API_KEY = os.environ.get("PERPLEXITY_API_KEY")

if not API_KEY:
    st.error("🚨 HATA: API Anahtarı bulunamadı!")
    st.info("Render Dashboard -> Environment kısmına 'PERPLEXITY_API_KEY' adıyla anahtarınızı ekleyin.")
    st.stop()

st.title("🕵️ Perplexity Destekli Global Fiyat Dedektifi")
st.markdown("Yapay zeka ile **gerçek zamanlı** ve **global** fiyat analizi.")

# --- SABİTLER ---
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

# GÜNCEL MODEL LİSTESİ (2025 Revizyonu)
# Perplexity eski uzun isimleri (llama-3.1-sonar...) kaldırdı.
AVAILABLE_MODELS = [
    "sonar-pro",       # En güçlüsü (Eski Large/Huge yerine)
    "sonar",           # Hızlı ve ekonomik (Eski Small yerine)
    "sonar-reasoning", # Mantık ağırlıklı
]

COUNTRIES = {
    "Türkiye": "TRY",
    "Almanya": "EUR",
    "Bosna Hersek": "BAM (KM)",
    "Sırbistan": "RSD",
    "Bulgaristan": "BGN",
    "Yunanistan": "EUR",
    "İngiltere": "GBP",
    "Polonya": "PLN",
    "Romanya": "RON",
    "Arnavutluk": "ALL",
    "Karadağ": "EUR",
    "Moldova": "MDL"
}

BRANDS = ["Sinsay", "Pepco", "Zara", "H&M", "Mango", "Primark", "English Home", "LC Waikiki", "Bershka", "Pull&Bear"]

# --- YAN MENÜ ---
st.sidebar.header("⚙️ Model Ayarları")

# 1. Model Seçimi
model_choice = st.sidebar.selectbox("AI Modeli Seç", AVAILABLE_MODELS, index=0)

# 2. Manuel Model Girişi (Acil Durum Butonu)
# Eğer Perplexity yarın yine isim değiştirirse, kodu güncellemeden buraya yeni ismi yazıp çalıştırabilirsin.
custom_model = st.sidebar.text_input("Manuel Model Adı (Opsiyonel)", help="Listede olmayan yeni bir model adı girmeniz gerekirse burayı kullanın.")

# Hangi modeli kullanacağız?
FINAL_MODEL = custom_model if custom_model else model_choice

st.sidebar.divider()
st.sidebar.header("🔍 Arama Kriterleri")

selected_country = st.sidebar.selectbox("Ülke Seçiniz", list(COUNTRIES.keys()))
selected_brand = st.sidebar.selectbox("Marka Seçiniz", BRANDS)
query_turkish = st.sidebar.text_input("Ürün Adı (Türkçe)", "Çift Kişilik Battaniye")

# --- FONKSİYONLAR ---

def translate_query(text, country_name):
    """Türkçe sorguyu hedef ülkenin diline çevirir."""
    lang_map = {
        "Türkiye": "tr", "Almanya": "de", "Bosna Hersek": "bs",
        "Sırbistan": "sr", "Bulgaristan": "bg", "Yunanistan": "el",
        "İngiltere": "en", "Polonya": "pl", "Romanya": "ro",
        "Arnavutluk": "sq", "Karadağ": "sr", "Moldova": "ro"
    }
    
    target_lang = lang_map.get(country_name, "en")
    
    if target_lang == "tr":
        return text, text
    
    try:
        translated = GoogleTranslator(source='tr', target=target_lang).translate(text)
        return text, translated
    except:
        return text, text

def search_with_perplexity(brand, country, translated_query, currency_hint, model_name):
    """API Sorgusu"""
    
    system_prompt = (
        "You are a strict data extraction assistant. "
        "Your goal is to find REAL-TIME product prices from online stores. "
        "Output ONLY valid JSON. No markdown, no conversational text."
    )
    
    user_prompt = f"""
    Search specifically on the official '{brand}' website for '{country}'.
    Search query: '{translated_query}'.
    
    Find 5 to 10 relevant products available right now.
    
    Return a JSON object with a key 'products' containing a list.
    Each item must have:
    - 'name': Product name in the local language
    - 'price': Price value (number or string with currency)
    - 'url': Direct link to the product
    
    The currency should be relevant to {currency_hint}.
    If you cannot find specific products, return an empty list in JSON.
    DO NOT INVENT DATA.
    """

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name, 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "return_citations": False
        # max_tokens parametresi bazı yeni modellerde hata verebiliyor, gerekirse çıkarılabilir.
    }

    try:
        response = requests.post(PERPLEXITY_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        content = response.json()['choices'][0]['message']['content']
        content = content.replace("```json", "").replace("```", "").strip()
        
        return json.loads(content)
        
    except requests.exceptions.HTTPError as err:
        st.error(f"HTTP Hatası: {err}")
        try:
            error_details = response.json()
            st.warning("⚠️ Perplexity API Mesajı:")
            st.json(error_details)
        except:
            pass
        return None
        
    except Exception as e:
        st.error(f"Beklenmeyen Hata: {e}")
        return None

# --- ANA AKIŞ ---

if st.sidebar.button("Fiyatları Getir 🚀"):
    if not query_turkish:
        st.warning("⚠️ Lütfen bir ürün adı giriniz.")
    else:
        # 1. Çeviri
        with st.status("🌍 Dil çevirisi yapılıyor...") as status:
            original, translated = translate_query(query_turkish, selected_country)
            status.update(label=f"Aranıyor: {translated} ({selected_country})", state="complete")
        
        # 2. API Sorgu
        with st.spinner(f"🤖 Yapay zeka ({FINAL_MODEL}) tarıyor..."):
            result = search_with_perplexity(
                selected_brand, 
                selected_country, 
                translated, 
                COUNTRIES[selected_country],
                FINAL_MODEL
            )
            
        # 3. Sonuç
        if result and "products" in result:
            products = result["products"]
            
            if len(products) > 0:
                st.success(f"✅ {len(products)} adet güncel ürün bulundu!")
                
                df = pd.DataFrame(products)
                
                st.data_editor(
                    df,
                    column_config={
                        "url": st.column_config.LinkColumn("Ürün Linki"),
                        "price": st.column_config.TextColumn("Fiyat"),
                        "name": st.column_config.TextColumn("Ürün Adı")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.warning(f"🔍 {selected_brand} sitesinde net sonuç bulunamadı. Ürün ismini daha spesifik yazmayı deneyin.")
