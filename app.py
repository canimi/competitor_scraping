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
FINAL_MODEL = "sonar"

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
    <div style="padding: 15px; background-color: #f0f2f6; border-left: 5px solid #1c54b2; border-radius: 4px; margin-bottom: 20px;">
        <h1 style='color: #1c54b2; font-weight: 900; margin:0; padding:0; font-family: "Segoe UI", sans-serif; font-size: 24px;'>LCW HOME</h1>
        <p style='color: #555; font-size: 11px; margin:0; letter-spacing: 1px;'>GLOBAL PRICE INTELLIGENCE</p>
    </div>
    """, 
    unsafe_allow_html=True
)

st.sidebar.header("🔎 Filtreler")
selected_country = st.sidebar.selectbox("Ülke", list(COUNTRIES.keys()))
selected_brand = st.sidebar.selectbox("Marka", BRANDS)
query_turkish = st.sidebar.text_input("Ürün Adı (TR)", "Çift Kişilik Battaniye")

# --- YARDIMCI FONKSİYONLAR ---
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
    system_prompt = "You are a price scraping bot. Return ONLY JSON. No text."
    user_prompt = f"""
    Go to '{brand}' official website for '{country}'. Search for: '{translated_query}'.
    Currency: {currency_hint}.
    Extract 5-10 products. Return JSON with 'products':
    - 'name': Local product name
    - 'price': Price string with currency
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

# --- ANA EKRAN ---

# Başlık Tasarımı
st.markdown(f"""
<h2 style='color: #333;'>🌍 {selected_brand} <span style='color: #999; font-weight: normal;'>|</span> {selected_country}</h2>
""", unsafe_allow_html=True)

if st.sidebar.button("Analizi Başlat 🚀", type="primary"):
    if not query_turkish:
        st.warning("Lütfen ürün adı giriniz.")
    else:
        with st.status("Veri toplanıyor...", expanded=True) as status:
            lang_map = {"Türkiye":"tr", "Bulgaristan":"bg", "Yunanistan":"el", "Bosna Hersek":"bs", "Sırbistan":"sr", "İngiltere":"en", "Almanya":"de", "Romanya":"ro"}
            target_lang = lang_map.get(selected_country, "en")
            translated_query = translate_text(query_turkish, target_lang) if target_lang != "tr" else query_turkish
            st.write(f"🧩 Çeviri: **{translated_query}**")
            
            result = search_with_perplexity(selected_brand, selected_country, translated_query, COUNTRIES[selected_country])
            status.update(label="Tamamlandı", state="complete")

        if result and "products" in result and result["products"]:
            products = result["products"]
            currency_code = COUNTRIES[selected_country]
            
            # Veri Hazırlığı
            table_data = []
            excel_lines = ["Ürün Adı\tOrijinal İsim\tYerel Fiyat\tTL Fiyatı\tUSD Fiyatı\tLink"] # Header (TSV)
            
            prices_tl = [] # Ortalama hesaplamak için

            for item in products:
                local_price = str(item.get("price", "0"))
                local_name = item.get("name", "-")
                link = item.get("url", "#")
                
                price_tl, price_usd = calculate_prices(local_price, currency_code)
                name_tr = translate_text(local_name, "tr") if target_lang != "tr" else local_name
                
                if price_tl > 0: prices_tl.append(price_tl)

                # Tablo için veri
                table_data.append({
                    "Ürün Adı": name_tr,
                    "Yerel Fiyat": local_price,
                    "TL Fiyatı": f"{price_tl:,.2f} ₺",
                    "USD Fiyatı": f"${price_usd:,.2f}",
                    "Link": link
                })
                
                # Excel Kopyalama için veri (Sekme/Tab ile ayrılmış)
                # Excel'e yapıştırınca sütunlar otomatik ayrılır
                line = f"{name_tr}\t{local_name}\t{local_price}\t{price_tl:,.2f}\t{price_usd:,.2f}\t{link}"
                excel_lines.append(line)

            # --- DASHBOARD METRİKLERİ ---
            avg_price = sum(prices_tl) / len(prices_tl) if prices_tl else 0
            min_price = min(prices_tl) if prices_tl else 0
            max_price = max(prices_tl) if prices_tl else 0

            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Bulunan Ürün", f"{len(products)} Adet")
            col2.metric("Ortalama Fiyat", f"{avg_price:,.0f} ₺")
            col3.metric("En Düşük", f"{min_price:,.0f} ₺")
            col4.metric("En Yüksek", f"{max_price:,.0f} ₺")
            st.markdown("---")

            # --- EXCEL İÇİN KOPYALAMA ALANI ---
            st.subheader("📋 Excel'e Kopyala (Hızlı)")
            st.info("👇 Aşağıdaki kutunun sağ üstündeki **Kopyala** butonuna basın, Excel'de bir hücreye tıklayıp **Yapıştır** yapın. Sütunlar otomatik ayrılacaktır.")
            
            # TSV verisini tek parça string yapıyoruz
            final_excel_text = "\n".join(excel_lines)
            st.code(final_excel_text, language="text")

            # --- GÖRSEL TABLO ---
            st.subheader("🖼️ Ürün Detayları")
            df = pd.DataFrame(table_data)
            st.data_editor(
                df,
                column_config={
                    "Link": st.column_config.LinkColumn("Link"),
                },
                hide_index=True,
                use_container_width=True
            )
            
        else:
            st.error("Sonuç bulunamadı.")
