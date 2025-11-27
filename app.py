import streamlit as st
import pandas as pd
import requests
import json
import os
import re
from deep_translator import GoogleTranslator

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="LCW Home Global", layout="wide", page_icon="🏠")

# --- ENV KONTROLÜ ---
API_KEY = os.environ.get("PERPLEXITY_API_KEY")

if not API_KEY:
    st.error("🚨 HATA: API Anahtarı bulunamadı!")
    st.stop()

# --- SABİTLER ---
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
FINAL_MODEL = "sonar" # Sadece online model

# Kur Bilgileri
EXCHANGE_RATES = {
    "EUR": 38.50, "USD": 36.50, "GBP": 46.20,
    "BGN": 19.65, "BAM": 19.60, "RSD": 0.33,
    "PLN": 9.10,  "RON": 7.75,  "MDL": 2.05,
    "ALL": 0.40,  "TRY": 1.0
}

COUNTRIES = {
    "Türkiye": "TRY", "Almanya": "EUR", "Bosna Hersek": "BAM",
    "Sırbistan": "RSD", "Bulgaristan": "BGN", "Yunanistan": "EUR",
    "İngiltere": "GBP", "Polonya": "PLN", "Romanya": "RON",
    "Arnavutluk": "ALL", "Karadağ": "EUR", "Moldova": "MDL"
}

BRANDS = ["LC Waikiki", "Sinsay", "Pepco", "Zara", "H&M", "Mango", "Primark", "English Home", "IKEA", "Jysk"]

# --- YAN MENÜ ---
st.sidebar.markdown(
    """
    <div style="padding: 10px; background-color: white; border-radius: 5px; margin-bottom: 20px;">
        <h1 style='color: #1c54b2; font-weight: 900; margin:0; padding:0; font-family: sans-serif;'>LCW HOME</h1>
        <p style='color: #555; font-size: 12px; margin:0;'>Global Price Intelligence</p>
    </div>
    """, 
    unsafe_allow_html=True
)

st.sidebar.header("🔎 Arama Parametreleri")
selected_country = st.sidebar.selectbox("Ülke", list(COUNTRIES.keys()))
selected_brand = st.sidebar.selectbox("Marka", BRANDS)
query_turkish = st.sidebar.text_input("Ürün Adı (TR)", "Çift Kişilik Battaniye")

# --- FONKSİYONLAR ---

def extract_price_number(price_str):
    if not price_str: return 0.0
    clean_str = price_str.replace(",", ".")
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", clean_str)
    return float(nums[0]) if nums else 0.0

def calculate_prices(raw_price_str, currency_code):
    amount = extract_price_number(raw_price_str)
    if amount == 0: return 0, 0
    rate_to_tl = EXCHANGE_RATES.get(currency_code, 0)
    price_tl = amount * rate_to_tl
    price_usd = price_tl / EXCHANGE_RATES.get("USD", 1)
    return round(price_tl, 2), round(price_usd, 2)

def translate_text(text, target="tr"):
    try:
        return GoogleTranslator(source='auto', target=target).translate(text)
    except:
        return text

def search_with_perplexity(brand, country, translated_query, currency_hint):
    system_prompt = "You are a strict price scraping bot. Return ONLY JSON. No text."
    user_prompt = f"""
    Go to '{brand}' official website for '{country}'. Search for: '{translated_query}'.
    Currency must be: {currency_hint}.
    Extract 5-10 products. Return JSON with 'products' list:
    - 'name': Local product name
    - 'price': Price string with currency symbol
    - 'url': Product link
    """
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": FINAL_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0.1, "return_citations": False
    }
    try:
        response = requests.post(PERPLEXITY_URL, json=payload, headers=headers)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except:
        return None

# --- ANA AKIŞ ---

st.title(f"🌍 {selected_brand} - {selected_country} Fiyat Analizi")

if st.sidebar.button("Analizi Başlat 🚀", type="primary"):
    if not query_turkish:
        st.warning("Ürün adı giriniz.")
    else:
        with st.status("Veriler toplanıyor...", expanded=True) as status:
            # 1. Çeviri
            lang_map = {"Türkiye":"tr", "Bulgaristan":"bg", "Yunanistan":"el", "Bosna Hersek":"bs", "Sırbistan":"sr", "İngiltere":"en", "Almanya":"de", "Romanya":"ro"}
            target_lang = lang_map.get(selected_country, "en")
            translated_query = translate_text(query_turkish, target_lang) if target_lang != "tr" else query_turkish
            st.write(f"Aranan: **{translated_query}**")
            
            # 2. Arama
            result = search_with_perplexity(selected_brand, selected_country, translated_query, COUNTRIES[selected_country])
            status.update(label="Tamamlandı", state="complete")

        if result and "products" in result and result["products"]:
            products = result["products"]
            currency_code = COUNTRIES[selected_country]
            
            # Rapor Metnini Hazırlama
            report_lines = []
            report_lines.append(f"📊 RAPOR: {selected_brand} - {selected_country}")
            report_lines.append(f"🔎 Aranan: {query_turkish} ({translated_query})")
            report_lines.append("-" * 40)

            enriched_data = []
            
            for item in products:
                local_price = str(item.get("price", "0"))
                local_name = item.get("name", "-")
                link = item.get("url", "#")
                
                # Hesaplamalar
                price_tl, price_usd = calculate_prices(local_price, currency_code)
                name_tr = translate_text(local_name, "tr") if target_lang != "tr" else local_name
                
                # Tablo verisi
                enriched_data.append({
                    "Ürün Adı (TR)": name_tr,
                    "Fiyat (Yerel)": local_price,
                    "Fiyat (TL)": f"{price_tl:,.2f} ₺",
                    "Fiyat (USD)": f"${price_usd:,.2f}",
                    "Link": link
                })
                
                # Metin Raporu için satır ekle
                line = f"🔹 {name_tr}\n   💰 {local_price}  |  🇹🇷 {price_tl:,.0f} TL  |  💵 ${price_usd:,.2f}\n   🔗 {link}\n"
                report_lines.append(line)

            # EKRANA BASMA
            
            # 1. Kopyalanabilir Metin Alanı
            st.subheader("📋 Hızlı Kopyala (Metin)")
            final_report_text = "\n".join(report_lines)
            st.code(final_report_text, language="text") # Bu özellik otomatik copy butonu çıkarır
            
            # 2. Görsel Tablo
            st.subheader("🖼️ Detaylı Tablo")
            df = pd.DataFrame(enriched_data)
            st.data_editor(
                df,
                column_config={"Link": st.column_config.LinkColumn("Link")},
                hide_index=True,
                use_container_width=True
            )
            
        else:
            st.error("Sonuç bulunamadı.")
