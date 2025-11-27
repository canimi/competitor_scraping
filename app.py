import streamlit as st
import pandas as pd
import os
import json
import re
from deep_translator import GoogleTranslator
from datetime import datetime
import google.generativeai as genai
from duckduckgo_search import DDGS
import requests

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="LCW Home Global", layout="wide", page_icon="🏠")

# --- ENV KONTROLÜ (GOOGLE API) ---
API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    st.error("🚨 HATA: Google API Anahtarı bulunamadı!")
    st.info("Lütfen Streamlit Secrets kısmına GOOGLE_API_KEY ekleyin.")
    st.stop()

# Google Gemini Kurulumu
genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-1.5-flash"

# --- SABİTLER ---
# Domain Map'i sadece referans için tutuyoruz, aramada zorlamayacağız.
COUNTRIES = {
    "Türkiye": {"curr": "TRY", "region": "tr-tr"},
    "Almanya": {"curr": "EUR", "region": "de-de"},
    "Bosna Hersek": {"curr": "BAM", "region": "wt-wt"}, # Bosna için özel bölge yok, global
    "Sırbistan": {"curr": "RSD", "region": "wt-wt"},
    "Bulgaristan": {"curr": "BGN", "region": "bg-bg"},
    "Yunanistan": {"curr": "EUR", "region": "gr-gr"},
    "İngiltere": {"curr": "GBP", "region": "uk-en"},
    "Polonya": {"curr": "PLN", "region": "pl-pl"},
    "Romanya": {"curr": "RON", "region": "ro-ro"},
    "Arnavutluk": {"curr": "ALL", "region": "wt-wt"},
    "Karadağ": {"curr": "EUR", "region": "wt-wt"},
    "Moldova": {"curr": "MDL", "region": "wt-wt"},
    "Rusya": {"curr": "RUB", "region": "ru-ru"},
    "Ukrayna": {"curr": "UAH", "region": "ua-ua"}
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
    <div style="padding: 15px; background-color: #f0f2f6; border-left: 5px solid #EA4335; border-radius: 4px; margin-bottom: 20px;">
        <h1 style='color: #EA4335; font-weight: 900; margin:0; padding:0; font-family: "Segoe UI", sans-serif; font-size: 24px;'>LCW HOME</h1>
        <p style='color: #555; font-size: 11px; margin:0; letter-spacing: 1px;'>POWERED BY GOOGLE</p>
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
        target_curr = COUNTRIES[selected_country]["curr"]
        if target_curr not in ["USD", "EUR", "TRY"]:
             st.write(f"🏳️ {target_curr}: **{LIVE_RATES.get(target_curr,0):.2f} ₺**")
        st.caption(f"Tarih: {RATE_DATE}")

# --- FONKSİYONLAR ---
def extract_price_number(price_str):
    if not price_str: return 0.0
    clean_str = str(price_str).replace(" ", "")
    # Para birimi sembollerini temizle
    clean_str = re.sub(r'[^\d.,]', '', clean_str)
    
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
    if amount == 0 or not LIVE_RATES: return 0, 0, 0
    
    rate_to_tl = LIVE_RATES.get(currency_code, 0)
    price_tl = amount * rate_to_tl
    price_usd = price_tl / LIVE_RATES.get("USD", 1)
    
    return amount, round(price_tl, 2), round(price_usd, 2)

def translate_query_text(text, target_lang):
    try:
        if target_lang == "tr": return text
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except:
        return text

def translate_result_to_tr(text):
    try:
        return GoogleTranslator(source='auto', target='tr').translate(text)
    except:
        return text

# --- YENİ OPTİMİZE EDİLMİŞ ARAMA MOTORU ---
def search_and_process_with_google(brand, country, translated_query, currency_hint):
    
    country_info = COUNTRIES.get(country, {})
    region_code = country_info.get("region", "wt-wt")
    
    # STRATEJİ: Site kısıtlamasını kaldırıyoruz. Daha geniş arama yapıyoruz.
    # Örn: "Zara Bulgaristan [Ürün Adı] price"
    # Bu format DuckDuckGo'nun bot korumasına daha az takılır.
    search_query = f"{brand} {country} {translated_query} price"
        
    try:
        # Backend='html' kullanıyoruz (Daha az bloklanır)
        # Max results artırıldı
        with DDGS() as ddgs:
            results = list(ddgs.text(
                search_query, 
                region=region_code, 
                backend="html", # Kritik değişiklik
                max_results=10
            ))
        
        if not results:
            st.warning(f"DuckDuckGo '{search_query}' için sonuç döndürmedi. Alternatif kaynaklar deneniyor...")
            return None
            
        # Arama sonuçlarını metne dök
        search_context = ""
        for res in results:
            search_context += f"Title: {res['title']}\nLink: {res['href']}\nSnippet: {res['body']}\n---\n"
            
    except Exception as e:
        st.error(f"Arama Motoru Hatası: {e}")
        return None

    # GEMINI PROMPT (Daha Zeki Hale Getirildi)
    prompt = f"""
    You are a smart shopping assistant. I have performed a web search for:
    Product: "{translated_query}"
    Brand: "{brand}"
    Country: "{country}"
    Target Currency: "{currency_hint}"
    
    Here are the raw search results:
    {search_context}
    
    TASK:
    1. Analyze the snippets to find products that match the description.
    2. Extract the Product Name, Price, and Link.
    3. Even if the currency symbol is missing in the snippet, assume it is {currency_hint} if the context matches the country.
    4. If you see text like "19.99 BGN" or "20 лв", capture it as the price.
    5. Ignore generic homepage links; look for specific product pages if possible.
    6. Return ONLY valid JSON.
    
    JSON Structure:
    {{
        "products": [
            {{ "name": "Product Name", "price": "Price with currency", "url": "URL" }}
        ]
    }}
    """
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        st.error(f"AI Analiz Hatası: {e}")
        return None

# --- ANA EKRAN ---

st.markdown(f"""
<h2 style='color: #333;'>🌍 {selected_brand} <span style='color: #999; font-weight: normal;'>|</span> {selected_country}</h2>
""", unsafe_allow_html=True)

if st.sidebar.button("Analizi Başlat 🚀", type="primary"):
    if not query_turkish:
        st.warning("Lütfen ürün adı giriniz.")
    else:
        with st.status("Google (Flash) + DuckDuckGo çalışıyor...", expanded=True) as status:
            lang_map = {"Türkiye":"tr", "Bulgaristan":"bg", "Yunanistan":"el", "Bosna Hersek":"bs", "Sırbistan":"sr", "İngiltere":"en", "Almanya":"de", "Romanya":"ro", "Rusya":"ru"}
            target_lang = lang_map.get(selected_country, "en")
            
            translated_query = translate_query_text(query_turkish, target_lang)
            st.write(f"🔍 Google Araması: **{translated_query}**")
            
            # Fonksiyonu Çağır
            target_currency = COUNTRIES[selected_country]["curr"]
            result = search_and_process_with_google(selected_brand, selected_country, translated_query, target_currency)
            status.update(label="İşlem Tamamlandı", state="complete")

        if result and "products" in result and result["products"]:
            products = result["products"]
            
            table_data = []
            excel_lines = ["Ürün Adı (TR)\tOrijinal İsim\tYerel Fiyat\tTL Fiyatı\tUSD Fiyatı\tLink"]
            
            prices_tl = []
            prices_usd = []
            prices_local = []

            progress_bar = st.progress(0)
            total_items = len(products)

            for i, item in enumerate(products):
                local_price_str = str(item.get("price", "0"))
                local_name = item.get("name", "-")
                link = item.get("url", "#")
                
                val_local, val_tl, val_usd = calculate_prices(local_price_str, target_currency)
                name_tr = translate_result_to_tr(local_name)
                
                if val_tl > 0:
                    prices_tl.append(val_tl)
                    prices_usd.append(val_usd)
                    prices_local.append(val_local)

                table_data.append({
                    "Ürün Adı (TR)": name_tr,
                    "Orijinal İsim": local_name,
                    "Yerel Fiyat": local_price_str,
                    "TL Fiyatı": f"{val_tl:,.2f} ₺",
                    "USD Fiyatı": f"${val_usd:,.2f}",
                    "Link": link
                })
                
                excel_lines.append(f"{name_tr}\t{local_name}\t{local_price_str}\t{val_tl:,.2f}\t{val_usd:,.2f}\t{link}")
                progress_bar.progress((i + 1) / total_items)

            progress_bar.empty()

            # İSTATİSTİK HESAPLAMA
            def get_stats(price_list):
                if not price_list: return 0, 0, 0
                return sum(price_list)/len(price_list), min(price_list), max(price_list)

            avg_tl, min_tl, max_tl = get_stats(prices_tl)
            avg_usd, min_usd, max_usd = get_stats(prices_usd)
            avg_loc, min_loc, max_loc = get_stats(prices_local)
            
            product_count = len(products)

            st.markdown("---")
            
            st.markdown("##### 🇹🇷 Türk Lirası Analizi")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Bulunan Ürün", f"{product_count}")
            col2.metric("Ortalama (TL)", f"{avg_tl:,.0f} ₺")
            col3.metric("En Düşük (TL)", f"{min_tl:,.0f} ₺")
            col4.metric("En Yüksek (TL)", f"{max_tl:,.0f} ₺")
            
            st.markdown("##### 🇺🇸 USD Analizi")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Bulunan Ürün", f"{product_count}")
            c2.metric("Ortalama (USD)", f"${avg_usd:,.2f}")
            c3.metric("En Düşük (USD)", f"${min_usd:,.2f}")
            c4.metric("En Yüksek (USD)", f"${max_usd:,.2f}")

            st.markdown(f"##### 🏳️ Yerel Para Analizi ({target_currency})")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Bulunan Ürün", f"{product_count}")
            k2.metric(f"Ortalama ({target_currency})", f"{avg_loc:,.2f}")
            k3.metric(f"En Düşük ({target_currency})", f"{min_loc:,.2f}")
            k4.metric(f"En Yüksek ({target_currency})", f"{max_loc:,.2f}")

            st.markdown("---")

            # GÖRSEL TABLO
            st.markdown("""
                <h3 style='color: #EA4335; margin-top: 0;'>🛍️ Detaylı Ürün Analizi</h3>
            """, unsafe_allow_html=True)
            
            df = pd.DataFrame(table_data)
            st.data_editor(
                df,
                column_config={
                    "Link": st.column_config.LinkColumn(
                        "İncele",
                        validate="^https://.*",
                        max_chars=100,
                        display_text="🔗 Ürüne Git"
                    ),
                    "Ürün Adı (TR)": st.column_config.TextColumn(
                        "Ürün Adı (TR)",
                        width="medium"
                    )
                },
                hide_index=True,
                use_container_width=True
            )

            # EXCEL KOPYALAMA
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <h3 style='color: #1D6F42; margin: 0;'>📊 Excel Formatı (TSV)</h3>
                    <span style='color: #666; font-size: 14px;'>Tabloyu Kopyalamak İçin Buraya Tıkla ⤵</span>
                </div>
            """, unsafe_allow_html=True)
            st.code("\n".join(excel_lines), language="text")
            
        else:
            st.error(f"Sonuç bulunamadı. '{selected_brand}' sitesinde arama yapılırken DuckDuckGo engeli olabilir veya arama terimi ({translated_query}) sonuç vermemiş olabilir.")
