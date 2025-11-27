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

# --- YARDIMCI: GEMINI FLASH (REST API) ---
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
        return json.loads(response.json()['candidates'][0]['content']['parts'][0]['text'])
    except:
        return None

# --- YARDIMCI: SERPER ARAMA ---
def search_serper(query, gl, hl):
    url = "https://google.serper.dev/search"
    # Pepco gibi katalog siteleri için "fiyat" kelimesini yerel dilde eklemek önemlidir
    payload = json.dumps({"q": query, "gl": gl, "hl": hl, "num": 15}) 
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
    # Sadece sayıları ve virgül/noktayı bırak
    clean = re.sub(r'[^\d.,]', '', str(p_str))
    
    # Avrupa formatı düzeltmesi (8,69 -> 8.69)
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
            
            # 2. ARAMA (Daha geniş kapsamlı)
            search_q = f"{selected_brand} {selected_country} {translated_query} price"
            serper_res = search_serper(search_q, conf["gl"], conf["hl"])
            
            ai_result = None
            if serper_res and "organic" in serper_res:
                # 3. VERİ HAZIRLAMA (AI İÇİN)
                context = ""
                for i in serper_res["organic"]:
                    title = i.get('title', '')
                    link = i.get('link', '')
                    snippet = i.get('snippet', '')
                    # Serper bazen 'price' veya 'priceRange' alanı döner, onu yakalayalım
                    extra_price = i.get('price', i.get('priceRange', ''))
                    
                    context += f"Item: {title}\nLink: {link}\nText: {snippet}\nPriceTag: {extra_price}\n---\n"
                
                # 4. AI ANALİZİ (DAHA AGRESİF PROMPT)
                prompt = f"""
                You are a price scraping expert.
                Target Brand: "{selected_brand}"
                Target Product: "{translated_query}"
                Target Currency Hint: {conf['curr']} (Also accept local symbols like лв, €, £)
                
                Raw Search Data:
                {context}
                
                INSTRUCTIONS:
                1. Identify any product that looks like a "{translated_query}".
                2. EXTRACT PRICES AGGRESSIVELY. If you see "5,99 лв" in the text, take it.
                3. Even if it is a catalog link or facebook post, if it has a price for the item, extract it.
                4. Ignore unrelated items (like hangers if searching for towels).
                5. Output strictly JSON.
                
                JSON Format:
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
                
                # Fiyat Hesapla
                v_loc, v_tl, v_usd = calc_prices(raw_p, conf["curr"])
                
                # İsmi Türkçe yap
                name_tr = translate_text(name, "tr")

                if v_tl > 0:
                    p_tl.append(v_tl); p_usd.append(v_usd); p_loc.append(v_loc)

                rows.append({"Ürün (TR)": name_tr, "Orijinal": name, "Fiyat": raw_p, "TL": f"{v_tl:,.0f} ₺", "USD": f"${v_usd:.2f}", "Link": url})
                excel_rows.append(f"{name_tr}\t{name}\t{raw_p}\t{v_tl:.2f}\t{v_usd:.2f}\t{url}")

            # İSTATİSTİK
            if p_tl:
                avg = sum(p_tl)/len(p_tl)
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Bulunan", len(products))
                col2.metric("Ortalama", f"{avg:,.0f} ₺")
                col3.metric("En Düşük", f"{min(p_tl):,.0f} ₺")
                col4.metric("En Yüksek", f"{max(p_tl):,.0f} ₺")

            # TABLO
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
            st.warning("Ürün bulunamadı.")
            # DEBUG MODU (SADECE SORUN VARSA GÖRÜNÜR)
            with st.expander("Geliştirici Verisi"):
                st.write("Aranan:", translated_query)
                st.json(serper_res)
