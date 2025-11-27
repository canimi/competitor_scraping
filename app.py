import streamlit as st
import pandas as pd
import requests
import json
import os
import re
from deep_translator import GoogleTranslator
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="LCW Home Global", layout="wide", page_icon="🏠")

# --- ENV KONTROLÜ ---
API_KEY = os.environ.get("PERPLEXITY_API_KEY")

if not API_KEY:
    st.error("🚨 HATA: API Anahtarı bulunamadı! Lütfen Environment Variables kontrol edin.")
    st.stop()

# --- SABİTLER ---
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
FINAL_MODEL = "sonar"

# --- DOMAIN İPUÇLARI (Sinsay ve Pepco Sorunu İçin Çözüm) ---
# Yapay zekaya doğru siteyi fısıldıyoruz.
DOMAIN_MAP = {
    "Sinsay": {
        "Bulgaristan": "sinsay.com/bg", "Romanya": "sinsay.com/ro",
        "Polonya": "sinsay.com/pl", "Türkiye": "sinsay.com/tr",
        "Bosna Hersek": "sinsay.com/ba", "Sırbistan": "sinsay.com/rs"
    },
    "Pepco": {
        "Bulgaristan": "pepco.bg", "Romanya": "pepco.ro",
        "Polonya": "pepco.pl", "Bosna Hersek": "pepco.ba",
        "Sırbistan": "pepco.rs"
    },
    "Zara": {"Bulgaristan": "zara.com/bg", "Türkiye": "zara.com/tr"},
    "H&M": {"Bulgaristan": "hm.com/bg", "Türkiye": "hm.com/tr"}
}

COUNTRIES = {
    "Türkiye": "TRY", "Almanya": "EUR", "Bosna Hersek": "BAM",
    "Sırbistan": "RSD", "Bulgaristan": "BGN", "Yunanistan": "EUR",
    "İngiltere": "GBP", "Polonya": "PLN", "Romanya": "RON",
    "Arnavutluk": "ALL", "Karadağ": "EUR", "Moldova": "MDL",
    "Rusya": "RUB", "Ukrayna": "UAH"
}

BRANDS = ["LC Waikiki", "Sinsay", "Pepco", "Zara", "H&M", "Mango", "Primark", "English Home", "IKEA", "Jysk"]

# --- CANLI KUR ---
@st.cache_data(ttl=3600)
def fetch_live_rates():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/TRY"
        response = requests.get(url)
        data = response.json()
        rates = data["rates"]
        live_rates = {}
        for currency, rate in rates.items():
            if rate > 0:
                live_rates[currency] = 1 / rate
        if "EUR" in live_rates:
            live_rates["BAM"] = live_rates["EUR"] / 1.95583 
        return live_rates, data["date"]
    except:
        return None, None

LIVE_RATES, RATE_DATE = fetch_live_rates()

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

with st.sidebar.expander("💸 Canlı Kur Bilgisi", expanded=True):
    if LIVE_RATES:
        st.write(f"🇺🇸 USD: **{LIVE_RATES.get('USD',0):.2f} ₺**")
        st.write(f"🇪🇺 EUR: **{LIVE_RATES.get('EUR',0):.2f} ₺**")
        target_curr = COUNTRIES[selected_country]
        if target_curr not in ["USD", "EUR", "TRY"]:
             st.write(f"🏳️ {target_curr}: **{LIVE_RATES.get(target_curr,0):.2f} ₺**")
        st.caption(f"Tarih: {RATE_DATE}")

# --- FONKSİYONLAR ---
def extract_price_number(price_str):
    if not price_str: return 0.0
    clean_str = str(price_str).replace(" ", "")
    if "," in clean_str and "." in clean_str:
        if clean_str.find(",") < clean_str.find("."):
            clean_str = clean_str.replace(",", "")
        else:
            clean_str = clean_str.replace(".", "").replace(",", ".")
    elif "," in clean_str:
        clean_str = clean_str.replace(",", ".")
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", clean_str)
    return float(nums[0]) if nums else 0.0

def calculate_prices(raw_price_str, currency_code):
    amount = extract_price_number(raw_price_str)
    if amount == 0 or not LIVE_RATES: return 0, 0
    rate_to_tl = LIVE_RATES.get(currency_code, 0)
    price_tl = amount * rate_to_tl
    price_usd = price_tl / LIVE_RATES.get("USD", 1)
    return round(price_tl, 2), round(price_usd, 2)

def translate_text(text, target="tr"):
    try:
        if target == "tr": return text
        # Google Translate ile kesin çeviri
        return GoogleTranslator(source='auto', target=target).translate(text)
    except:
        return text

def search_with_perplexity(brand, country, translated_query, currency_hint):
    # Domain haritasından doğru siteyi bulmaya çalışalım
    specific_domain = DOMAIN_MAP.get(brand, {}).get(country, "")
    
    domain_instruction = ""
    if specific_domain:
        domain_instruction = f"SEARCH ONLY ON THIS DOMAIN: {specific_domain}"
    else:
        domain_instruction = f"Search on the official {brand} website for {country}."

    system_prompt = "You are a price scraping bot. Return ONLY JSON. No text."
    
    # Prompt'u Sinsay ve Pepco bulacak şekilde güçlendirdik
    user_prompt = f"""
    {domain_instruction}
    Search query: '{translated_query}'.
    Currency must be: {currency_hint}.
    
    IMPORTANT: Provide the specific product name in JSON.
    
    Extract 5-10 products. Return JSON with 'products':
    - 'name': Local product name (as seen on site)
    - 'price': Price string with currency
    - 'url': Direct product link
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

st.markdown(f"""
<h2 style='color: #333;'>🌍 {selected_brand} <span style='color: #999; font-weight: normal;'>|</span> {selected_country}</h2>
""", unsafe_allow_html=True)

if st.sidebar.button("Analizi Başlat 🚀", type="primary"):
    if not query_turkish:
        st.warning("Lütfen ürün adı giriniz.")
    else:
        with st.status("Veri toplanıyor...", expanded=True) as status:
            lang_map = {"Türkiye":"tr", "Bulgaristan":"bg", "Yunanistan":"el", "Bosna Hersek":"bs", "Sırbistan":"sr", "İngiltere":"en", "Almanya":"de", "Romanya":"ro", "Rusya":"ru"}
            target_lang = lang_map.get(selected_country, "en")
            
            translated_query = translate_text(query_turkish, target_lang) if target_lang != "tr" else query_turkish
            st.write(f"🧩 Çeviri: **{translated_query}** (Aranan Kelime)")
            
            result = search_with_perplexity(selected_brand, selected_country, translated_query, COUNTRIES[selected_country])
            status.update(label="Tamamlandı", state="complete")

        if result and "products" in result and result["products"]:
            products = result["products"]
            currency_code = COUNTRIES[selected_country]
            
            table_data = []
            # TSV Başlığı (Excel için)
            excel_lines = ["Ürün Adı (TR)\tOrijinal İsim\tYerel Fiyat\tTL Fiyatı\tUSD Fiyatı\tLink"]
            
            prices_tl = []

            # Progress bar ile çeviri işlemini göster
            progress_bar = st.progress(0)
            total_items = len(products)

            for i, item in enumerate(products):
                local_price = str(item.get("price", "0"))
                local_name = item.get("name", "-")
                link = item.get("url", "#")
                
                # Hesaplamalar
                price_tl, price_usd = calculate_prices(local_price, currency_code)
                
                # TÜRKÇE ÇEVİRİSİ (ZORUNLU)
                # Google Translate'i her ürün adı için çalıştırıyoruz
                name_tr = translate_text(local_name, "tr")
                
                if price_tl > 0: prices_tl.append(price_tl)

                # Görsel Tablo Verisi
                table_data.append({
                    "Ürün Adı (TR)": name_tr, # Türkçe en başta
                    "Orijinal İsim": local_name,
                    "Yerel Fiyat": local_price,
                    "TL Fiyatı": f"{price_tl:,.2f} ₺",
                    "USD Fiyatı": f"${price_usd:,.2f}",
                    "Link": link
                })
                
                # Excel Verisi
                excel_lines.append(f"{name_tr}\t{local_name}\t{local_price}\t{price_tl:,.2f}\t{price_usd:,.2f}\t{link}")
                progress_bar.progress((i + 1) / total_items)

            progress_bar.empty()

            # --- METRİKLER ---
            avg_price = sum(prices_tl) / len(prices_tl) if prices_tl else 0
            min_price = min(prices_tl) if prices_tl else 0
            max_price = max(prices_tl) if prices_tl else 0

            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Bulunan Ürün", f"{len(products)}")
            col2.metric("Ortalama", f"{avg_price:,.0f} ₺")
            col3.metric("En Düşük", f"{min_price:,.0f} ₺")
            col4.metric("En Yüksek", f"{max_price:,.0f} ₺")
            st.markdown("---")

            # --- EXCEL KOPYALAMA ---
            st.subheader("📋 Excel'e Kopyala (TSV)")
            st.code("\n".join(excel_lines), language="text")

            # --- GÖRSEL TABLO (GÜZEL LİNKLER) ---
            st.subheader("🖼️ Ürün Detayları")
            df = pd.DataFrame(table_data)
            
            st.data_editor(
                df,
                column_config={
                    "Link": st.column_config.LinkColumn(
                        "İncele",            # Sütun Başlığı
                        help="Ürün sayfasına git",
                        validate="^https://.*",
                        max_chars=100,
                        display_text="🔗 Ürüne Git" # Link yerine bu yazacak
                    ),
                    "Ürün Adı (TR)": st.column_config.TextColumn(
                        "Ürün Adı (TR)",
                        width="medium"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
            
        else:
            st.error(f"Sonuç bulunamadı. '{selected_brand}' sitesi {selected_country} için erişilebilir olmayabilir veya bot koruması çok yüksek olabilir.")
