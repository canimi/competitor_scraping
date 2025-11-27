import streamlit as st
import pandas as pd
import os
import json
import re
from deep_translator import GoogleTranslator
from datetime import datetime
import google.generativeai as genai
import requests

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="LCW Home Global", layout="wide", page_icon="🏠")

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

# --- API KEY KONTROLÜ (GOOGLE + SERPER) ---
# Google Gemini Key
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_KEY:
    GOOGLE_KEY = st.sidebar.text_input("1. Google API Key:", type="password")

# Serper Search Key (Yeni)
SERPER_KEY = os.environ.get("SERPER_API_KEY")
if not SERPER_KEY:
    SERPER_KEY = st.sidebar.text_input("2. Serper API Key (serper.dev):", type="password")

if not GOOGLE_KEY or not SERPER_KEY:
    st.warning("⚠️ Lütfen her iki anahtarı da giriniz (Google AI + Serper Dev).")
    st.stop()

# --- GOOGLE MODEL KURULUMU ---
try:
    genai.configure(api_key=GOOGLE_KEY)
except Exception as e:
    st.error(f"Google Key Hatalı: {e}")
    st.stop()

# --- SABİTLER ---
COUNTRIES = {
    "Türkiye": {"curr": "TRY", "gl": "tr", "hl": "tr"},
    "Almanya": {"curr": "EUR", "gl": "de", "hl": "de"},
    "Bosna Hersek": {"curr": "BAM", "gl": "ba", "hl": "bs"},
    "Sırbistan": {"curr": "RSD", "gl": "rs", "hl": "sr"},
    "Bulgaristan": {"curr": "BGN", "gl": "bg", "hl": "bg"},
    "Yunanistan": {"curr": "EUR", "gl": "gr", "hl": "el"},
    "İngiltere": {"curr": "GBP", "gl": "uk", "hl": "en"},
    "Polonya": {"curr": "PLN", "gl": "pl", "hl": "pl"},
    "Romanya": {"curr": "RON", "gl": "ro", "hl": "ro"},
    "Arnavutluk": {"curr": "ALL", "gl": "al", "hl": "sq"},
    "Karadağ": {"curr": "EUR", "gl": "me", "hl": "sr"},
    "Moldova": {"curr": "MDL", "gl": "md", "hl": "ro"},
    "Rusya": {"curr": "RUB", "gl": "ru", "hl": "ru"},
    "Ukrayna": {"curr": "UAH", "gl": "ua", "hl": "uk"}
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

# --- SERPER (GOOGLE) ARAMA MOTORU ---
def search_with_serper(brand, country, translated_query):
    """
    Serper.dev API kullanarak gerçek Google araması yapar.
    Bu yöntem DuckDuckGo gibi bloklanmaz.
    """
    url = "https://google.serper.dev/search"
    
    # Ülke ayarları (Daha isabetli sonuç için)
    country_conf = COUNTRIES.get(country, {})
    gl = country_conf.get("gl", "us") # Coğrafi konum
    hl = country_conf.get("hl", "en") # Dil
    
    # Arama Sorgusu
    search_query = f"{brand} {translated_query} price"
    
    payload = json.dumps({
        "q": search_query,
        "gl": gl,
        "hl": hl,
        "num": 10 # 10 Sonuç getir
    })
    
    headers = {
        'X-API-KEY': SERPER_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()
    except Exception as e:
        return None

def process_with_gemini(search_data, brand, translated_query, currency_hint):
    """Google'dan gelen JSON verisini Gemini'ye yorumlatır"""
    
    # Serper'dan gelen veriyi metne döküyoruz
    context_text = ""
    if "organic" in search_data:
        for item in search_data["organic"]:
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            price = item.get("price", "") # Bazen Google direkt fiyatı bulur
            currency = item.get("currency", "")
            
            context_text += f"Product: {title}\nLink: {link}\nDesc: {snippet}\nPrice: {price} {currency}\n---\n"
    
    if not context_text:
        return None, "Google arama sonucunda ürün bulunamadı."

    # Gemini Prompt
    prompt = f"""
    You are a product extractor.
    Source Data (Google Search Results):
    {context_text}
    
    Task: Find products matching "{translated_query}" for brand "{brand}".
    Currency Hint: {currency_hint}
    
    Instructions:
    1. Extract Product Name, Price, URL.
    2. Be careful with prices. If you see '1200 RSD', keep it.
    3. Return ONLY JSON.
    
    JSON:
    {{ "products": [ {{ "name": "...", "price": "...", "url": "..." }} ] }}
    """
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text), None
    except Exception as e:
        return None, f"AI Analiz Hatası: {e}"

# --- ANA EKRAN ---

st.markdown(f"""
<h2 style='color: #333;'>🌍 {selected_brand} <span style='color: #999; font-weight: normal;'>|</span> {selected_country}</h2>
""", unsafe_allow_html=True)

if st.sidebar.button("Analizi Başlat 🚀", type="primary"):
    if not query_turkish:
        st.warning("Lütfen ürün adı giriniz.")
    else:
        with st.status("Google (Serper) üzerinden veri çekiliyor...", expanded=True) as status:
            lang_map = {"Türkiye":"tr", "Bulgaristan":"bg", "Yunanistan":"el", "Bosna Hersek":"bs", "Sırbistan":"sr", "İngiltere":"en", "Almanya":"de", "Romanya":"ro", "Rusya":"ru"}
            target_lang = lang_map.get(selected_country, "en")
            
            translated_query = translate_query_text(query_turkish, target_lang)
            st.write(f"🔍 Arama: **{translated_query}**")
            
            # 1. SERPER İLE ARAMA
            serper_result = search_with_serper(selected_brand, selected_country, translated_query)
            
            if serper_result and "organic" in serper_result:
                # 2. GEMINI İLE İŞLEME
                target_currency = COUNTRIES[selected_country]["curr"]
                result, error_msg = process_with_gemini(serper_result, selected_brand, translated_query, target_currency)
                
                if error_msg:
                    st.error(error_msg)
                
                status.update(label="İşlem Tamamlandı", state="complete")
            else:
                st.error("Serper API sonuç döndürmedi (Kota veya bağlantı hatası).")
                result = None

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

            def get_stats(price_list):
                if not price_list: return 0, 0, 0
                return sum(price_list)/len(price_list), min(price_list), max(price_list)

            avg_tl, min_tl, max_tl = get_stats(prices_tl)
            avg_usd, min_usd, max_usd = get_stats(prices_usd)
            avg_loc, min_loc, max_loc = get_stats(prices_local)
            
            product_count = len(products)

            st.markdown("---")
            
            # İSTATİSTİK PANELLERİ
            st.markdown("##### 🇹🇷 Türk Lirası Analizi")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Bulunan", f"{product_count}")
            col2.metric("Ortalama", f"{avg_tl:,.0f} ₺")
            col3.metric("En Düşük", f"{min_tl:,.0f} ₺")
            col4.metric("En Yüksek", f"{max_tl:,.0f} ₺")
            
            st.markdown("##### 🇺🇸 USD Analizi")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Bulunan", f"{product_count}")
            c2.metric("Ortalama", f"${avg_usd:,.2f}")
            c3.metric("En Düşük", f"${min_usd:,.2f}")
            c4.metric("En Yüksek", f"${max_usd:,.2f}")

            st.markdown(f"##### 🏳️ Yerel Para ({target_currency})")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Bulunan", f"{product_count}")
            k2.metric("Ortalama", f"{avg_loc:,.2f}")
            k3.metric("En Düşük", f"{min_loc:,.2f}")
            k4.metric("En Yüksek", f"{max_loc:,.2f}")

            st.markdown("---")

            st.markdown("""<h3 style='color: #1c54b2; margin-top: 0;'>🛍️ Detaylı Ürün Analizi</h3>""", unsafe_allow_html=True)
            
            df = pd.DataFrame(table_data)
            st.data_editor(
                df,
                column_config={
                    "Link": st.column_config.LinkColumn("İncele", display_text="🔗 Ürüne Git"),
                    "Ürün Adı (TR)": st.column_config.TextColumn("Ürün Adı (TR)", width="medium")
                },
                hide_index=True,
                use_container_width=True
            )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <h3 style='color: #1D6F42; margin: 0;'>📊 Excel Formatı (TSV)</h3>
                    <span style='color: #666; font-size: 14px;'>Tabloyu Kopyalamak İçin Buraya Tıkla ⤵</span>
                </div>
            """, unsafe_allow_html=True)
            st.code("\n".join(excel_lines), language="text")
            
        else:
            if not error_msg:
                st.error(f"Sonuç bulunamadı.")
