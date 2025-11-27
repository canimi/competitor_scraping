import streamlit as st
import pandas as pd
import os
import json
import requests
import re

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
    GOOGLE_KEY = st.sidebar.text_input("1. Google API Key (Flash Modeli):", type="password")

SERPER_KEY = os.environ.get("SERPER_API_KEY")
if not SERPER_KEY:
    SERPER_KEY = st.sidebar.text_input("2. Serper API Key:", type="password")

if not GOOGLE_KEY or not SERPER_KEY:
    st.warning("⚠️ Lütfen anahtarları giriniz.")
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
        if response.status_code != 200:
            return None
        result = response.json()
        return json.loads(result['candidates'][0]['content']['parts'][0]['text'])
    except:
        return None

# --- YARDIMCI: SERPER ARAMA ---
def search_serper(query, gl, hl):
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query, "gl": gl, "hl": hl, "num": 10})
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json()
    except:
        return None

# --- CANLI KUR ---
@st.cache_data(ttl=3600)
def fetch_live_rates():
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/TRY")
        data = response.json()
        rates = data["rates"]
        live_rates = {}
        for c, r in rates.items():
            if r > 0: live_rates[c] = 1 / r
        if "EUR" in live_rates: live_rates["BAM"] = live_rates["EUR"] / 1.95583 
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

# --- FİYAT HESAPLAMA ---
def extract_price(price_str):
    if not price_str: return 0.0
    clean = re.sub(r'[^\d.,]', '', str(price_str))
    if "," in clean and "." in clean:
        if clean.find(",") < clean.find("."): clean = clean.replace(",", "")
        else: clean = clean.replace(".", "").replace(",", ".")
    elif "," in clean: clean = clean.replace(",", ".")
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", clean)
    return float(nums[0]) if nums else 0.0

def calc_prices(raw, code):
    amt = extract_price(raw)
    if amt == 0 or not LIVE_RATES: return 0, 0, 0
    return amt, round(amt * LIVE_RATES.get(code, 0), 2), round((amt * LIVE_RATES.get(code, 0)) / LIVE_RATES.get("USD", 1), 2)

# --- ANA EKRAN ---
st.markdown(f"""<h2 style='color: #333;'>🌍 {selected_brand} <span style='color: #999; font-weight: normal;'>|</span> {selected_country}</h2>""", unsafe_allow_html=True)

if st.sidebar.button("Analizi Başlat 🚀", type="primary"):
    if not query_turkish:
        st.warning("Lütfen ürün adı giriniz.")
    else:
        with st.status("İşlemler yapılıyor...", expanded=True) as status:
            country_conf = COUNTRIES[selected_country]
            
            # 1. ÇEVİRİ
            trans_prompt = f"""Translate this Turkish text to the language used in {selected_country}. Return JSON: {{ "translated": "..." }} Text: "{query_turkish}" """
            trans_res = call_gemini_flash(trans_prompt)
            translated_query = trans_res.get("translated", query_turkish) if trans_res else query_turkish
            
            st.write(f"🧩 Çeviri: **{translated_query}**")
            
            # 2. ARAMA (SERPER)
            search_q = f"{selected_brand} {selected_country} {translated_query} price"
            serper_data = search_serper(search_q, country_conf["gl"], country_conf["hl"])
            
            if serper_data and "organic" in serper_data:
                # 3. VERİ AYIKLAMA (AI FLASH)
                context = ""
                # HATA BURADAYDI, DÜZELTİLDİ:
                for i in serper_data["organic"][:10]:
                    title = i.get('title', 'No Title')
                    link = i.get('link', '#')
                    snippet = i.get('snippet', '')
                    price = i.get('price', '')
                    context += f"Title: {title}\nLink: {link}\nDesc: {snippet}\nPrice: {price}\n---\n"
                
                extract_prompt = f"""
                Extract products for "{selected_brand}" matching "{translated_query}".
                Context: {context}
                Currency Hint: {country_conf['curr']}
                JSON Format: {{ "products": [ {{ "name": "...", "price": "...", "url": "..." }} ] }}
                """
                ai_result = call_gemini_flash(extract_prompt)
                
                status.update(label="Tamamlandı", state="complete")
            else:
                ai_result = None
                st.error("Arama sonucu bulunamadı.")

        if ai_result and "products" in ai_result:
            products = ai_result["products"]
            table_data = []
            excel_lines = ["Ürün Adı (TR)\tOrijinal İsim\tYerel Fiyat\tTL Fiyatı\tUSD Fiyatı\tLink"]
            
            p_tl, p_usd, p_loc = [], [], []

            for item in products:
                loc_p = str(item.get("price", "0"))
                name = item.get("name", "-")
                url = item.get("url", "#")
                
                val_loc, val_tl, val_usd = calc_prices(loc_p, country_conf["curr"])
                
                if val_tl > 0:
                    p_tl.append(val_tl); p_usd.append(val_usd); p_loc.append(val_loc)

                table_data.append({
                    "Ürün Adı": name,
                    "Yerel Fiyat": loc_p,
                    "TL Fiyatı": f"{val_tl:,.2f} ₺",
                    "USD Fiyatı": f"${val_usd:,.2f}",
                    "Link": url
                })
                excel_lines.append(f"{name}\t{name}\t{loc_p}\t{val_tl:,.2f}\t{val_usd:,.2f}\t{url}")

            # İSTATİSTİKLER
            def stats(l): return (sum(l)/len(l), min(l), max(l)) if l else (0,0,0)
            avg_t, min_t, max_t = stats(p_tl)
            avg_u, min_u, max_u = stats(p_usd)
            avg_l, min_l, max_l = stats(p_loc)

            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ürün", f"{len(products)}")
            c2.metric("Ortalama (TL)", f"{avg_t:,.0f} ₺")
            c3.metric("En Düşük (TL)", f"{min_t:,.0f} ₺")
            c4.metric("En Yüksek (TL)", f"{max_t:,.0f} ₺")
            
            st.markdown("---")
            st.markdown(f"**Detaylı Analiz ({country_conf['curr']} / USD)**")
            k1, k2 = st.columns(2)
            k1.info(f"Ort: {avg_l:.2f} {country_conf['curr']} | Min: {min_l:.2f} | Max: {max_l:.2f}")
            k2.success(f"Ort: ${avg_u:.2f} | Min: ${min_u:.2f} | Max: ${max_u:.2f}")

            st.markdown("""<h3 style='color: #1c54b2;'>🛍️ Sonuçlar</h3>""", unsafe_allow_html=True)
            st.data_editor(
                pd.DataFrame(table_data),
                column_config={"Link": st.column_config.LinkColumn("Git", display_text="🔗")},
                hide_index=True,
                use_container_width=True
            )

            st.markdown("<br>", unsafe_allow_html=True)
            st.code("\n".join(excel_lines), language="text")
        else:
            st.warning("Ürün bulunamadı.")
