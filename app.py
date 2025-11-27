import streamlit as st
import pandas as pd
import os
import json
import requests
import re
from deep_translator import GoogleTranslator

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

# --- API KEY KONTROLÜ ---
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_KEY:
    GOOGLE_KEY = st.sidebar.text_input("1. Google API Key (Flash):", type="password")

SERPER_KEY = os.environ.get("SERPER_API_KEY")
if not SERPER_KEY:
    SERPER_KEY = st.sidebar.text_input("2. Serper API Key:", type="password")

if not GOOGLE_KEY or not SERPER_KEY:
    st.warning("⚠️ Lütfen anahtarları giriniz.")
    st.stop()

# --- SABİTLER ---
COUNTRIES = {
    "Türkiye": {"curr": "TRY", "gl": "tr", "hl": "tr", "lang": "tr"},
    "Almanya": {"curr": "EUR", "gl": "de", "hl": "de", "lang": "de"},
    "Bosna Hersek": {"curr": "BAM", "gl": "ba", "hl": "bs", "lang": "bs"},
    "Sırbistan": {"curr": "RSD", "gl": "rs", "hl": "sr", "lang": "sr"},
    "Bulgaristan": {"curr": "BGN", "gl": "bg", "hl": "bg", "lang": "bg"},
    "Yunanistan": {"curr": "EUR", "gl": "gr", "hl": "el", "lang": "el"},
    "İngiltere": {"curr": "GBP", "gl": "uk", "hl": "en", "lang": "en"},
    "Polonya": {"curr": "PLN", "gl": "pl", "hl": "pl", "lang": "pl"},
    "Romanya": {"curr": "RON", "gl": "ro", "hl": "ro", "lang": "ro"},
    "Rusya": {"curr": "RUB", "gl": "ru", "hl": "ru", "lang": "ru"},
}

BRANDS = ["LC Waikiki", "Sinsay", "Pepco", "Zara", "H&M", "Mango", "Primark", "English Home", "IKEA", "Jysk"]

# --- YARDIMCI: GEMINI FLASH (REST API + JSON CLEANER) ---
def call_gemini_flash(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200: return None
        
        # HAM METNİ AL
        raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        
        # JSON TEMİZLİK İŞLEMİ (SORUN BURADAYDI)
        # Markdown backticks (```json ... ```) temizle
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        
        return json.loads(clean_text)
    except:
        return None

# --- YARDIMCI: SERPER ARAMA ---
def search_serper(query, gl, hl):
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query, "gl": gl, "hl": hl, "num": 20}) # Sayıyı artırdım
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()
    except:
        return None

# --- YARDIMCI: ÇEVİRİ ---
def translate_text(text, target_lang):
    try:
        if target_lang == "tr": return text
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except:
        return text

# --- CANLI KUR ---
@st.cache_data(ttl=3600)
def fetch_live_rates():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/TRY").json()['rates']
        live = {k: 1/v for k, v in r.items() if v > 0}
        if "EUR" in live: live["BAM"] = live["EUR"] / 1.95583 
        return live
    except:
        return None

LIVE_RATES = fetch_live_rates()

# --- FİYAT HESAPLAMA ---
def extract_price(p_str):
    if not p_str: return 0.0
    clean = re.sub(r'[^\d.,]', '', str(p_str))
    if "," in clean and "." in clean:
        if clean.find(",") < clean.find("."): clean = clean.replace(",", "")
        else: clean = clean.replace(".", "").replace(",", ".")
    elif "," in clean: clean = clean.replace(",", ".")
    res = re.findall(r"[-+]?\d*\.\d+|\d+", clean)
    return float(res[0]) if res else 0.0

def calc_prices(raw, code):
    amt = extract_price(raw)
    if amt == 0 or not LIVE_RATES: return 0, 0, 0
    return amt, round(amt * LIVE_RATES.get(code, 0), 2), round((amt * LIVE_RATES.get(code, 0)) / LIVE_RATES.get("USD", 1), 2)

# --- ANA EKRAN ---
st.sidebar.header("🔎 Filtreler")
selected_country = st.sidebar.selectbox("Ülke", list(COUNTRIES.keys()))
selected_brand = st.sidebar.selectbox("Marka", BRANDS)
query_turkish = st.sidebar.text_input("Ürün Adı (TR)", "Çift Kişilik Battaniye")

st.markdown(f"## 🌍 {selected_brand} | {selected_country}")

if st.sidebar.button("Analizi Başlat 🚀", type="primary"):
    if not query_turkish:
        st.warning("Ürün adı giriniz.")
    else:
        with st.status("Veriler toplanıyor...", expanded=True) as status:
            conf = COUNTRIES[selected_country]
            
            # 1. ÇEVİRİ
            translated_query = translate_text(query_turkish, conf["lang"])
            st.write(f"🧩 Çeviri: **{translated_query}** ({conf['lang']})")
            
            # 2. ARAMA
            search_q = f"{selected_brand} {selected_country} {translated_query} price"
            serper_res = search_serper(search_q, conf["gl"], conf["hl"])
            
            ai_result = None
            if serper_res and "organic" in serper_res:
                # 3. AYIKLAMA (LOGLARI OKUDUK, PROMPT GÜÇLENDİ)
                context = ""
                for i in serper_res["organic"]:
                    # Fiyatı snippet içinden de yakalayabilmesi için hepsini birleştiriyoruz
                    full_text = f"{i.get('title','')} {i.get('snippet','')}"
                    price_val = i.get('price', i.get('priceRange', ''))
                    context += f"Item: {full_text} | ExplicitPrice: {price_val} | Link: {i.get('link')}\n---\n"
                
                prompt = f"""
                You are a smart extractor. I have search results for "{selected_brand}" product: "{translated_query}".
                Currency: {conf['curr']} (Also check for local symbols like лв, BGN, RSD, etc.)
                
                RAW DATA:
                {context}
                
                TASKS:
                1. Identify products.
                2. Extract Price. IMPORTANT: Prices are often hidden in the text (e.g. "5,99 лв", "17.00лв").
                3. If 'ExplicitPrice' is empty, FIND IT in the 'Item' text.
                4. Ignore unrelated items.
                
                OUTPUT JSON:
                {{ "products": [ {{ "name": "...", "price": "...", "url": "..." }} ] }}
                """
                ai_result = call_gemini_flash(prompt)
                status.update(label="Bitti", state="complete")
            else:
                st.error("Serper sonuç bulamadı.")

        if ai_result and "products" in ai_result and ai_result["products"]:
            products = ai_result["products"]
            rows = []
            excel_rows = ["Ürün Adı (TR)\tOrijinal İsim\tFiyat\tTL\tUSD\tLink"]
            
            p_tl, p_usd, p_loc = [], [], []

            for p in products:
                raw_p = str(p.get("price", "0"))
                name = p.get("name", "-")
                url = p.get("url", "#")
                
                v_loc, v_tl, v_usd = calc_prices(raw_p, conf["curr"])
                name_tr = translate_text(name, "tr")

                if v_tl > 0:
                    p_tl.append(v_tl); p_usd.append(v_usd); p_loc.append(v_loc)

                rows.append({"Ürün (TR)": name_tr, "Orijinal": name, "Fiyat": raw_p, "TL": f"{v_tl:.0f} ₺", "USD": f"${v_usd:.2f}", "Link": url})
                excel_rows.append(f"{name_tr}\t{name}\t{raw_p}\t{v_tl}\t{v_usd}\t{url}")

            if p_tl:
                avg = sum(p_tl)/len(p_tl)
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                c1.metric("Ürün", len(products))
                c2.metric("Ortalama", f"{avg:.0f} ₺")
                c3.metric("En Düşük", f"{min(p_tl):.0f} ₺")

            st.markdown("### 🛍️ Sonuçlar")
            st.data_editor(
                pd.DataFrame(rows),
                column_config={"Link": st.column_config.LinkColumn("Git", display_text="🔗")},
                hide_index=True,
                use_container_width=True
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.code("\n".join(excel_rows), language="text")
            
        else:
            st.error("Ürün bulunamadı.")
            # LOGU GÖSTERELİM Kİ HATA VARSA GÖRELİM
            with st.expander("Geliştirici Logları"):
                st.write(serper_res)
