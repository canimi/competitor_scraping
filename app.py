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

# --- FİYAT HESAPLAMA (DÜZELTİLDİ: VİRGÜL/NOKTA SORUNU) ---
def parse_price(price_str):
    if not price_str: return 0.0
    # Sadece sayıları ve ayırıcıları al
    clean = re.sub(r'[^\d.,]', '', str(price_str))
    
    # Avrupa formatı (10,00) -> Python formatı (10.00)
    # Eğer virgül sondaysa (kuruş hanesi), onu nokta yap.
    if "," in clean:
        if "." in clean: 
            # Hem nokta hem virgül var (1.200,50 veya 1,200.50)
            if clean.find(",") > clean.find("."): 
                clean = clean.replace(".", "").replace(",", ".") # 1.200,50 -> 1200.50
            else:
                clean = clean.replace(",", "") # 1,200.50 -> 1200.50
        else:
            # Sadece virgül var (10,50 veya 1000,50)
            clean = clean.replace(",", ".")
            
    try:
        return float(clean)
    except:
        return 0.0

def calc_prices_multi(raw_price, currency_code):
    """
    Yerel, TL ve USD fiyatlarını hesaplar.
    """
    amount = parse_price(raw_price)
    if amount == 0 or not LIVE_RATES: return 0, 0, 0
    
    # 1. Yerel Fiyat (Zaten amount)
    val_local = amount
    
    # 2. TL Fiyatı
    # LIVE_RATES["EUR"] -> 1 TL kaç Euro (0.027 gibi)
    # Euro'dan TL'ye geçmek için: amount / rate
    rate_tl = LIVE_RATES.get(currency_code)
    if not rate_tl: return val_local, 0, 0
    
    val_tl = val_local / rate_tl
    
    # 3. USD Fiyatı
    rate_usd = LIVE_RATES.get("USD")
    val_usd = val_tl * rate_usd
    
    return round(val_local, 2), round(val_tl, 2), round(val_usd, 2)

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
                # 3. VERİ HAZIRLAMA
                context = ""
                for i in serper_res["organic"]:
                    full_text = f"{i.get('title','')} {i.get('snippet','')}"
                    price_val = i.get('price', i.get('priceRange', ''))
                    context += f"Item: {full_text} | ExplicitPrice: {price_val} | Link: {i.get('link')}\n---\n"
                
                # 4. AI ANALİZİ (FİLTRELİ PROMPT)
                prompt = f"""
                You are a strict product filter and extractor.
                Brand: "{selected_brand}"
                Searching For: "{translated_query}" (in {conf['lang']})
                Target Currency: {conf['curr']}
                
                RAW DATA:
                {context}
                
                CRITICAL INSTRUCTIONS:
                1. EXTRACT ONLY products that match "{translated_query}".
                2. DISCARD irrelevant items (e.g., if searching for "Bathrobe", DO NOT return "Underwear", "Lingerie", "Bra", "Socks").
                3. EXTRACT PRICE precisely. Handle European formats (e.g., "10,99 €" -> "10.99").
                4. If no specific product is found, return empty list.
                
                JSON OUTPUT:
                {{ "products": [ {{ "name": "Product Name", "price": "10.99", "url": "URL" }} ] }}
                """
                ai_result = call_gemini_flash(prompt)
                status.update(label="Bitti", state="complete")
            else:
                st.error("Arama sonucu bulunamadı.")

        if ai_result and "products" in ai_result and ai_result["products"]:
            products = ai_result["products"]
            rows = []
            excel_rows = ["Ürün (TR)\tOrijinal\tYerel Fiyat\tTL Fiyatı\tUSD Fiyatı\tLink"]
            
            p_local_list, p_tl_list, p_usd_list = [], [], []

            for p in products:
                raw_p = str(p.get("price", "0"))
                name = p.get("name", "-")
                url = p.get("url", "#")
                
                # Fiyat Hesapla (3 Para Birimi)
                v_loc, v_tl, v_usd = calc_prices_multi(raw_p, conf["curr"])
                
                # İsim Çevir
                name_tr = translate_text(name, "tr")

                if v_tl > 0:
                    p_local_list.append(v_loc)
                    p_tl_list.append(v_tl)
                    p_usd_list.append(v_usd)

                # Tablo Satırı
                rows.append({
                    "Ürün (TR)": name_tr, 
                    "Orijinal": name, 
                    f"Fiyat ({conf['curr']})": f"{v_loc:,.2f}", 
                    "Fiyat (TL)": f"{v_tl:,.0f} ₺", 
                    "Fiyat (USD)": f"${v_usd:,.2f}", 
                    "Link": url
                })
                
                # Excel Satırı
                excel_rows.append(f"{name_tr}\t{name}\t{v_loc}\t{v_tl}\t{v_usd}\t{url}")

            # --- İSTATİSTİK PANELLERİ (3 KATMANLI) ---
            st.markdown("---")
            
            # 1. Yerel Para
            if p_local_list:
                avg = sum(p_local_list)/len(p_local_list)
                st.markdown(f"##### 🏳️ Yerel Analiz ({conf['curr']})")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Adet", len(products))
                c2.metric("Ortalama", f"{avg:,.2f}")
                c3.metric("En Düşük", f"{min(p_local_list):,.2f}")
                c4.metric("En Yüksek", f"{max(p_local_list):,.2f}")
            
            # 2. TL
            if p_tl_list:
                avg = sum(p_tl_list)/len(p_tl_list)
                st.markdown("##### 🇹🇷 TL Analiz")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Adet", len(products))
                c2.metric("Ortalama", f"{avg:,.0f} ₺")
                c3.metric("En Düşük", f"{min(p_tl_list):,.0f} ₺")
                c4.metric("En Yüksek", f"{max(p_tl_list):,.0f} ₺")

            # 3. USD
            if p_usd_list:
                avg = sum(p_usd_list)/len(p_usd_list)
                st.markdown("##### 🇺🇸 USD Analiz")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Adet", len(products))
                c2.metric("Ortalama", f"${avg:,.2f}")
                c3.metric("En Düşük", f"${min(p_usd_list):,.2f}")
                c4.metric("En Yüksek", f"${max(p_usd_list):,.2f}")

            st.markdown("---")

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
            with st.expander("Geliştirici Verisi"):
                st.write("Aranan:", translated_query)
                st.json(serper_res)
