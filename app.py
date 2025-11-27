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
        raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except:
        return None

# --- YARDIMCI: SERPER ARAMA ---
def search_serper(query, gl, hl):
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query, "gl": gl, "hl": hl, "num": 20})
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
    # Eğer gelen fiyat Euro ise ve hedef ülke Bulgaristan ise, onu da çevirmek lazım
    # Ama şimdilik basit tutalım, direkt kurdan çarpalım.
    return amt, round(amt * LIVE_RATES.get(code, 0), 2), round((amt * LIVE_RATES.get(code, 0)) / LIVE_RATES.get("USD", 1), 2)

# --- MANUEL REGEX AYIKLAYICI (AI BAŞARISIZ OLURSA) ---
def manual_fallback_extraction(organic_results, target_currency):
    fallback_products = []
    # Para birimi sembolleri (Basit Regex)
    # 5.99 лв, 5,99лв, 17.00 BGN, 10 EUR, 10€
    patterns = [
        r'(\d+[.,]?\d*)\s?(лв|BGN|lev|bgn)', # Bulgar Levası
        r'(\d+[.,]?\d*)\s?(€|EUR|eur)',       # Euro
        r'(\d+[.,]?\d*)\s?(TL|TRY)',          # TL
        r'(\d+[.,]?\d*)\s?(RSD|din)',         # Dinar
        r'(\d+[.,]?\d*)\s?(KM|BAM)'           # Mark
    ]
    
    for i in organic_results:
        full_text = f"{i.get('title','')} {i.get('snippet','')} {i.get('priceRange','')}"
        price_found = None
        
        # Önce Serper'in kendi bulduğu fiyat var mı?
        if i.get('price'):
            price_found = str(i.get('price'))
        elif i.get('priceRange'):
            price_found = str(i.get('priceRange'))
        
        # Yoksa metin içinde Regex ile ara
        if not price_found:
            for pat in patterns:
                match = re.search(pat, full_text, re.IGNORECASE)
                if match:
                    price_found = match.group(0) # "5.99 лв" gibi tamamını al
                    break
        
        if price_found:
            fallback_products.append({
                "name": i.get('title'),
                "price": price_found,
                "url": i.get('link')
            })
            
    return fallback_products

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
            
            products = []
            
            if serper_res and "organic" in serper_res:
                # 3. ÖNCE AI İLE DENE
                context = ""
                for i in serper_res["organic"]:
                    full_text = f"{i.get('title','')} {i.get('snippet','')}"
                    price_val = i.get('price', i.get('priceRange', ''))
                    context += f"Item: {full_text} | PriceTag: {price_val} | Link: {i.get('link')}\n---\n"
                
                prompt = f"""
                You are a price scraping expert. Extract products for "{selected_brand}" matching "{translated_query}".
                Context: {context}
                Currency Hint: {conf['curr']}
                EXTRACT ALL PRICES VISIBLE (e.g. 5.99 лв, 17.00лв, 8.69 €).
                JSON Format: {{ "products": [ {{ "name": "...", "price": "...", "url": "..." }} ] }}
                """
                ai_result = call_gemini_flash(prompt)
                
                if ai_result and "products" in ai_result and len(ai_result["products"]) > 0:
                    products = ai_result["products"]
                    st.success(f"🤖 Yapay Zeka {len(products)} ürün buldu.")
                else:
                    # 4. AI BULAMAZSA REGEX DEVREYE GİRER (KORUMA KALKANI)
                    st.warning("⚠️ AI fiyatları kaçırdı, Manuel Mod devreye giriyor...")
                    products = manual_fallback_extraction(serper_res["organic"], conf['curr'])
                    st.info(f"🔧 Manuel Mod {len(products)} ürün kurtardı.")
                
                status.update(label="Bitti", state="complete")
            else:
                st.error("Serper sonuç bulamadı.")

        if products:
            rows = []
            excel_rows = ["Ürün Adı (TR)\tOrijinal İsim\tFiyat\tTL\tUSD\tLink"]
            
            p_tl, p_usd, p_loc = [], [], []

            for p in products:
                raw_p = str(p.get("price", "0"))
                name = p.get("name", "-")
                url = p.get("url", "#")
                
                # Fiyat Hesapla
                # Bulgaristan için özel durum: Eğer fiyat Euro ise (€) onu Levaya çevirmek gerekebilir
                # Ama şimdilik basit hesap: Para birimi koduna göre TL karşılığını alıyoruz.
                # Eğer "8.69 €" gelirse, kod extract_price ile 8.69 alır.
                # Eğer seçilen ülke Bulgaristan (BGN) ise, 8.69 * BGN_KURu yapar.
                # Bu küçük sapma yaratabilir ama veri gelir.
                
                target_code = conf["curr"]
                # Eğer fiyat metninde açıkça € varsa ve ülke BGN ise, kuru EUR yapalım geçici olarak
                if "€" in raw_p or "EUR" in raw_p:
                    calc_code = "EUR"
                else:
                    calc_code = target_code

                v_loc, v_tl, v_usd = calc_prices(raw_p, calc_code)
                name_tr = translate_text(name, "tr")

                if v_tl > 0:
                    p_tl.append(v_tl); p_usd.append(v_usd); p_loc.append(v_loc)

                rows.append({"Ürün (TR)": name_tr, "Orijinal": name, "Fiyat": raw_p, "TL": f"{v_tl:.0f} ₺", "USD": f"${v_usd:.2f}", "Link": url})
                excel_rows.append(f"{name_tr}\t{name}\t{raw_p}\t{v_tl}\t{v_usd}\t{url}")

            if p_tl:
                avg = sum(p_tl)/len(p_tl)
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Bulunan", len(products))
                col2.metric("Ortalama", f"{avg:.0f} ₺")
                col3.metric("En Düşük", f"{min(p_tl):,.0f} ₺")
                col4.metric("En Yüksek", f"{max(p_tl):,.0f} ₺")

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
            # LOGU GÖSTER
            with st.expander("Ham Veri (Log)"):
                st.write(serper_res)
