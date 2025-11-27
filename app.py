import streamlit as st
import pandas as pd
import os
import json
import requests
import re
from deep_translator import GoogleTranslator

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="LCW Global Intelligence", layout="wide", page_icon="🧿")

# --- CSS ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; padding-bottom: 5rem; }
    header {visibility: hidden;}
    .stApp { background-color: #0e1117; font-family: 'Segoe UI', sans-serif; }
    h1 { color: #4da6ff; text-align: center; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 15px rgba(77, 166, 255, 0.6); margin-top: -20px !important; padding-bottom: 20px; }
    div[data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.5); }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-size: 28px !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 14px !important; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 5px; }
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    div.stButton > button { background: linear-gradient(90deg, #1c54b2 0%, #0d3c85 100%); color: white; border: none; padding: 12px 24px; font-weight: bold; width: 100%; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
st.markdown("<h1>LCW HOME | GLOBAL INTELLIGENCE</h1>", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<h2 style="color:#4da6ff; margin-bottom:0;">LCW HOME</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#8b949e; font-size:12px;">COMPETITOR PRICE TRACKER</p>', unsafe_allow_html=True)
    PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY") or st.text_input("🔑 Perplexity API Key", type="password")
    if not PERPLEXITY_KEY: st.warning("⚠️ API Key Gerekli"); st.stop()

# --- HARDCODED URL DB ---
URL_DB = {
    "Bulgaristan": { "Pepco": "https://pepco.bg/", "Sinsay": "https://www.sinsay.com/bg/bg/", "Zara Home": "https://www.zarahome.com/bg/", "H&M Home": "https://www2.hm.com/bg_bg/home.html", "Jysk": "https://jysk.bg/", "Jumbo": "https://www.jumbo.bg/", "English Home": "https://englishhome.bg/", "Primark": "https://www.primark.com/en-us" },
    "Bosna Hersek": { "Pepco": "https://pepco.ba/", "Sinsay": "https://www.sinsay.com/ba/bs/", "Zara Home": "https://www.zarahome.com/ba/", "H&M Home": "https://www.hm.com/ba", "Jysk": "https://jysk.ba/", "Jumbo": "https://www.jumbo.ba/", "English Home": "https://englishhome.ba/", "Primark": None },
    "Yunanistan": { "Pepco": "https://pepco.gr/", "Sinsay": "https://www.sinsay.com/gr/el/", "Zara Home": "https://www.zarahome.com/gr/", "H&M Home": "https://www2.hm.com/en_gr/home.html", "Jysk": "https://jysk.gr/", "Jumbo": "https://www.e-jumbo.gr/", "English Home": "https://englishhome.gr/", "Primark": None },
    "Romanya": { "Pepco": "https://pepco.ro/", "Sinsay": "https://www.sinsay.com/ro/ro/", "Zara Home": "https://www.zarahome.com/ro/", "H&M Home": "https://www2.hm.com/ro_ro/home.html", "Jysk": "https://jysk.ro/", "Jumbo": "https://www.jumbo.ro/", "English Home": "https://englishhome.ro/", "Primark": "https://www.primark.com/ro" },
    "Sırbistan": { "Pepco": "https://pepco.rs/", "Sinsay": "https://www.sinsay.com/rs/sr/", "Zara Home": "https://www.zarahome.com/rs/", "H&M Home": "https://www2.hm.com/rs_en/home.html", "Jysk": "https://jysk.rs/", "Jumbo": "https://www.jumbo.rs/", "English Home": "https://englishhome.rs/", "Primark": None },
    "Hırvatistan": { "Pepco": "https://pepco.hr/", "Sinsay": "https://www.sinsay.com/hr/hr/", "Zara Home": "https://www.zarahome.com/hr/", "H&M Home": "https://www2.hm.com/hr_hr/home.html", "Jysk": "https://jysk.hr/", "Jumbo": None, "English Home": None, "Primark": None },
    "Kazakistan": { "Pepco": None, "Sinsay": "https://www.sinsay.com/kz/ru/", "Zara Home": "https://www.zarahome.com/kz/", "H&M Home": "https://www.hm.com/kz", "Jysk": "https://jysk.kz/", "Jumbo": None, "English Home": "https://englishhome.kz/", "Primark": None },
    "Rusya": { "Pepco": None, "Sinsay": None, "Zara Home": None, "H&M Home": None, "Jysk": None, "Jumbo": None, "English Home": None, "Primark": None },
    "Ukrayna": { "Pepco": None, "Sinsay": "https://www.sinsay.com/ua/uk/", "Zara Home": "https://www.zarahome.com/ua/", "H&M Home": "https://www.hm.com/ua", "Jysk": "https://jysk.ua/", "Jumbo": None, "English Home": "https://englishhome.ua/", "Primark": None },
    "Mısır": { "Pepco": None, "Sinsay": None, "Zara Home": "https://www.zarahome.com/eg/", "H&M Home": "https://eg.hm.com/en/", "Jysk": "https://jysk.com.eg/", "Jumbo": None, "English Home": "https://englishhome.com.eg/", "Primark": None },
    "Irak": { "Pepco": None, "Sinsay": None, "Zara Home": None, "H&M Home": "https://iq.hm.com/", "Jysk": None, "Jumbo": None, "English Home": None, "Primark": None }
}

COUNTRIES_META = {
    "Bulgaristan":  {"curr": "BGN", "lang": "bg"},
    "Bosna Hersek": {"curr": "BAM", "lang": "bs"},
    "Yunanistan":   {"curr": "EUR", "lang": "el"},
    "Sırbistan":    {"curr": "RSD", "lang": "sr"},
    "Romanya":      {"curr": "RON", "lang": "ro"},
    "Hırvatistan":  {"curr": "EUR", "lang": "hr"},
    "Kazakistan":   {"curr": "KZT", "lang": "kk"},
    "Rusya":        {"curr": "RUB", "lang": "ru"},
    "Ukrayna":      {"curr": "UAH", "lang": "uk"},
    "Mısır":        {"curr": "EGP", "lang": "ar"},
    "Irak":         {"curr": "IQD", "lang": "ar"},
    "Arnavutluk":   {"curr": "ALL", "lang": "sq"},
    "Makedonya":    {"curr": "MKD", "lang": "mk"},
    "Kosova":       {"curr": "EUR", "lang": "sq"},
    "Moldova":      {"curr": "MDL", "lang": "ro"},
    "Fas":          {"curr": "MAD", "lang": "ar"},
}

BRANDS = ["Pepco", "Sinsay", "Zara Home", "H&M Home", "Jysk", "Primark", "Jumbo", "English Home"]

# --- FONKSİYONLAR ---

@st.cache_data(ttl=3600)
def get_rates():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/TRY").json()['rates']
        rates = {k: 1/v for k, v in r.items() if v > 0} 
        if "EUR" in rates: rates["BAM"] = rates["EUR"] / 1.95583
        return ra
