import json
import math
import os
import re
import sqlite3
import textwrap
from html import escape, unescape
from pathlib import Path
from urllib.parse import urlencode
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None


st.set_page_config(
    page_title="Hisse Analiz Paneli",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


ONERILEN_HISSELER = [
    "TUPRS.IS", "THYAO.IS", "ASELS.IS", "KCHOL.IS", "SISE.IS",
    "BIMAS.IS", "EREGL.IS", "GARAN.IS", "AKBNK.IS", "YKBNK.IS",
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
]

BIST100_HISSELERI = [
    "AEFES.IS", "AGHOL.IS", "AHGAZ.IS", "AKBNK.IS", "AKCNS.IS",
    "AKFGY.IS", "AKFYE.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS",
    "ALBRK.IS", "ALFAS.IS", "ALTNY.IS", "ANHYT.IS", "ANSGR.IS",
    "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "AVPGY.IS", "BERA.IS",
    "BIMAS.IS", "BRSAN.IS", "BRYAT.IS", "BSOKE.IS", "BTCIM.IS",
    "CANTE.IS", "CCOLA.IS", "CIMSA.IS", "CLEBI.IS", "CWENE.IS",
    "DOAS.IS", "DOHOL.IS", "ECILC.IS", "EFORC.IS", "EGEEN.IS",
    "EKGYO.IS", "ENERY.IS", "ENJSA.IS", "ENKAI.IS", "EREGL.IS",
    "EUPWR.IS", "FROTO.IS", "GARAN.IS", "GESAN.IS", "GUBRF.IS",
    "HALKB.IS", "HEKTS.IS", "ISCTR.IS", "ISGYO.IS", "ISMEN.IS",
    "KARSN.IS", "KCAER.IS", "KCHOL.IS", "KLSER.IS", "KONTR.IS",
    "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "KTLEV.IS", "MAVI.IS",
    "MGROS.IS", "MIATK.IS", "MPARK.IS", "OBAMS.IS", "ODAS.IS",
    "OTKAR.IS", "OYAKC.IS", "PASEU.IS", "PETKM.IS", "PGSUS.IS",
    "QUAGR.IS", "REEDR.IS", "SAHOL.IS", "SASA.IS", "SISE.IS",
    "SKBNK.IS", "SMRTG.IS", "SOKM.IS", "TAVHL.IS", "TCELL.IS",
    "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TSKB.IS", "TTKOM.IS",
    "TTRAK.IS", "TUPRS.IS", "TURSG.IS", "ULKER.IS", "VAKBN.IS",
    "VESTL.IS", "YEOTK.IS", "YKBNK.IS", "ZOREN.IS",
]

ONERILEN_HISSELER = sorted(set(ONERILEN_HISSELER + BIST100_HISSELERI))

ANALIZ_EVRENI = sorted(
    set(
        ONERILEN_HISSELER
        + [
            "PATEK.IS", "MIATK.IS", "ASTOR.IS", "KONTR.IS", "CWENE.IS",
            "FROTO.IS", "TOASO.IS", "TTRAK.IS", "OTKAR.IS", "ASUZU.IS",
            "KARSN.IS", "DOAS.IS", "TCELL.IS", "TTKOM.IS",
            "SAHOL.IS", "MGROS.IS", "ULKER.IS", "PETKM.IS", "SASA.IS",
            "KRDMD.IS", "ISCTR.IS", "HALKB.IS", "VAKBN.IS", "ENKAI.IS",
            "KOZAL.IS", "PGSUS.IS", "DOAS.IS", "AEFES.IS", "CCOLA.IS",
            "ORCL", "ADBE", "CRM", "AVGO", "AMD", "INTC", "IBM",
            "NFLX", "DIS", "PYPL", "SHOP", "UBER", "ABNB", "JPM",
            "BAC", "WFC", "GS", "V", "MA", "XOM", "CVX", "SHEL",
            "BP", "KO", "PEP", "WMT", "COST", "HD", "NKE", "MCD",
            "DAL", "UAL", "AAL", "LUV", "RYAAY", "ALK", "CPA", "IAG.L",
            "AIR.PA", "LHA.DE", "LMT", "RTX", "NOC", "GD", "LHX", "BA",
            "OI", "GLW", "GPK", "OC", "5201.T", "5202.T", "VRLA.PA",
            "BRK-B", "EXO.MI", "EXOR.AS", "IEP", "JARD.L",
        ]
    )
)

BIST_EVRENI = sorted([ticker for ticker in ANALIZ_EVRENI if ticker.endswith(".IS")])
GLOBAL_EVRENI = sorted([ticker for ticker in ANALIZ_EVRENI if not ticker.endswith(".IS")])

RAKIP_ONERILERI = {
    "AAPL": ["MSFT", "NVDA", "GOOGL", "META", "AMZN"],
    "MSFT": ["AAPL", "NVDA", "GOOGL", "ORCL", "ADBE"],
    "GOOGL": ["META", "AMZN", "MSFT", "AAPL", "NFLX"],
    "TUPRS.IS": ["PETKM.IS", "SHEL", "BP", "XOM", "CVX"],
    "THYAO.IS": ["PGSUS.IS", "DAL", "UAL", "AAL", "LUV", "RYAAY", "ALK", "CPA"],
    "ASELS.IS": ["LMT", "RTX", "NOC", "GD", "LHX", "BA", "AIR.PA"],
    "SISE.IS": ["OI", "GLW", "GPK", "OC", "5201.T", "5202.T", "VRLA.PA"],
    "KCHOL.IS": ["SAHOL.IS", "BRK-B", "EXO.MI", "EXOR.AS", "IEP", "JARD.L"],
    "SAHOL.IS": ["KCHOL.IS", "BRK-B", "EXO.MI", "EXOR.AS", "IEP", "JARD.L"],
    "FROTO.IS": ["TOASO.IS", "OTKAR.IS", "ASUZU.IS", "KARSN.IS", "DOAS.IS", "TTRAK.IS", "STLA", "F", "GM", "TM"],
    "TOASO.IS": ["FROTO.IS", "OTKAR.IS", "ASUZU.IS", "KARSN.IS", "DOAS.IS", "TTRAK.IS", "STLA", "F", "GM", "TM"],
    "OTKAR.IS": ["FROTO.IS", "TOASO.IS", "ASUZU.IS", "KARSN.IS", "TTRAK.IS", "OSK", "PCAR", "TEX"],
    "ASUZU.IS": ["FROTO.IS", "TOASO.IS", "OTKAR.IS", "KARSN.IS", "TTRAK.IS", "OSK", "PCAR", "TEX"],
    "KARSN.IS": ["FROTO.IS", "TOASO.IS", "OTKAR.IS", "ASUZU.IS", "TTRAK.IS", "STLA", "F", "GM"],
    "TTRAK.IS": ["FROTO.IS", "TOASO.IS", "OTKAR.IS", "ASUZU.IS", "KARSN.IS", "DE", "AGCO", "CNH"],
}

RAKIP_ANAHTAR_KELIMELERI = {
    "THYAO.IS": ["airline", "airlines", "airport", "passenger"],
    "PGSUS.IS": ["airline", "airlines", "airport", "passenger"],
    "ASELS.IS": ["aerospace", "defense", "defence", "security"],
    "TUPRS.IS": ["oil", "gas", "refining", "refinery", "energy"],
    "SISE.IS": ["glass", "container", "packaging", "materials", "building products"],
    "KCHOL.IS": ["holding", "conglomerate", "diversified"],
    "SAHOL.IS": ["holding", "conglomerate", "diversified"],
    "FROTO.IS": ["auto", "automotive", "vehicle", "truck", "commercial"],
    "TOASO.IS": ["auto", "automotive", "vehicle", "truck", "commercial"],
    "OTKAR.IS": ["auto", "automotive", "vehicle", "truck", "commercial", "bus"],
    "ASUZU.IS": ["auto", "automotive", "vehicle", "truck", "commercial", "bus"],
    "KARSN.IS": ["auto", "automotive", "vehicle", "truck", "commercial", "bus"],
    "TTRAK.IS": ["machinery", "tractor", "agricultural", "farm"],
}

ANALIST_KARNESI = [
    {"kurum": "İş Yatırım", "analist": "Analist A", "basari": 78},
    {"kurum": "Ak Yatırım", "analist": "Analist B", "basari": 72},
    {"kurum": "Garanti BBVA Yatırım", "analist": "Analist C", "basari": 76},
    {"kurum": "Yapı Kredi Yatırım", "analist": "Analist D", "basari": 69},
    {"kurum": "HSBC", "analist": "Analist E", "basari": 82},
    {"kurum": "Morgan Stanley", "analist": "Analist F", "basari": 74},
    {"kurum": "JP Morgan", "analist": "Analist G", "basari": 71},
    {"kurum": "Goldman Sachs", "analist": "Analist H", "basari": 79},
    {"kurum": "Citi", "analist": "Analist I", "basari": 67},
    {"kurum": "Ünlü & Co", "analist": "Analist J", "basari": 73},
    {"kurum": "Oyak Yatırım", "analist": "Analist K", "basari": 70},
    {"kurum": "Deniz Yatırım", "analist": "Analist L", "basari": 66},
    {"kurum": "QNB Invest", "analist": "Analist M", "basari": 68},
    {"kurum": "TEB Yatırım", "analist": "Analist N", "basari": 75},
    {"kurum": "Vakıf Yatırım", "analist": "Analist O", "basari": 64},
]

# Kurum bazli hedef fiyat noktalarini yalnizca kaynak linki varsa grafikte goster.
# Ornek kayit formati:
# "TICKER": [
#     {
#         "tarih": "2026-05-01",
#         "kurum": "Kurum Adi",
#         "analist": "Analist / Rapor",
#         "hedef": 123.45,
#         "basari": 0,
#         "kaynak": "https://...",
#         "kaynak_baslik": "Rapor basligi",
#     }
# ]
ANALIST_KAYNAKLARI = {}

DONEMLER = {
    "1 Gün": {"period": "1d", "interval": "5m"},
    "1 Hafta": {"period": "5d", "interval": "30m"},
    "1 Ay": {"period": "1mo", "interval": "1d"},
    "1 Yıl": {"period": "1y", "interval": "1d"},
    "Max": {"period": "15y", "interval": "1wk"},
}

USD_CEVRIMLERI = {
    "TRY": {"ticker": "USDTRY=X", "operation": "divide"},
    "JPY": {"ticker": "JPY=X", "operation": "divide"},
    "CHF": {"ticker": "CHF=X", "operation": "divide"},
    "CAD": {"ticker": "CAD=X", "operation": "divide"},
    "CNY": {"ticker": "CNY=X", "operation": "divide"},
    "HKD": {"ticker": "HKD=X", "operation": "divide"},
    "EUR": {"ticker": "EURUSD=X", "operation": "multiply"},
    "GBP": {"ticker": "GBPUSD=X", "operation": "multiply"},
    "AUD": {"ticker": "AUDUSD=X", "operation": "multiply"},
    "NZD": {"ticker": "NZDUSD=X", "operation": "multiply"},
}

EMTIA_HARITASI = {
    "TUPRS.IS": [("Brent Petrol", "BZ=F"), ("WTI Petrol", "CL=F"), ("Isitma Yagi", "HO=F")],
    "EREGL.IS": [("Demir Cevheri", "TIO=F"), ("Celik Vadeli", "HRC=F"), ("Kok Komuru", "MTF=F")],
    "KRDMD.IS": [("Demir Cevheri", "TIO=F"), ("Celik Vadeli", "HRC=F")],
    "THYAO.IS": [("Jet Yakit Proxy", "HO=F"), ("Brent Petrol", "BZ=F"), ("USD/TRY", "USDTRY=X")],
    "PGSUS.IS": [("Jet Yakit Proxy", "HO=F"), ("Brent Petrol", "BZ=F"), ("USD/TRY", "USDTRY=X")],
    "SISE.IS": [("Dogal Gaz", "NG=F"), ("Soda Kulu Proxy", "TROX"), ("USD/TRY", "USDTRY=X")],
    "FROTO.IS": [("Aluminyum", "ALI=F"), ("Bakir", "HG=F"), ("USD/TRY", "USDTRY=X")],
    "TOASO.IS": [("Aluminyum", "ALI=F"), ("Bakir", "HG=F"), ("USD/TRY", "USDTRY=X")],
}

SEKTOR_EMTIA_HARITASI = [
    (["oil", "gas", "energy", "refining"], [("Brent Petrol", "BZ=F"), ("WTI Petrol", "CL=F")]),
    (["airline", "airport", "aviation"], [("Jet Yakit Proxy", "HO=F"), ("Brent Petrol", "BZ=F")]),
    (["steel", "iron", "metal"], [("Demir Cevheri", "TIO=F"), ("Bakir", "HG=F")]),
    (["auto", "automotive", "vehicle"], [("Aluminyum", "ALI=F"), ("Bakir", "HG=F")]),
    (["bank", "financial"], [("ABD 10Y Tahvil", "^TNX"), ("USD/TRY", "USDTRY=X")]),
]

MAKRO_VERI = {
    "Turkey": {
        "faiz": "TCMB politika faizi: uygulamada manuel/API entegrasyonu ile teyit edilmeli",
        "enflasyon": "TUIK yillik enflasyon: uygulamada manuel/API entegrasyonu ile teyit edilmeli",
        "not": "Turkiye hisselerinde kur, faiz ve enflasyon iskonto oranini dogrudan etkiler.",
    },
    "United States": {
        "faiz": "FED hedef faiz araligi: resmi takvim/API ile teyit edilmeli",
        "enflasyon": "ABD CPI yillik enflasyon: resmi veri/API ile teyit edilmeli",
        "not": "ABD hisselerinde faiz patikasi iskonto oranini ve carpani etkiler.",
    },
}

DB_PATH = Path("data") / "profiles.db"
DEFAULT_PROFILE = "local"


st.markdown(
    """
    <style>
        :root { color-scheme: dark; }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(20, 184, 166, 0.16), transparent 32rem),
                linear-gradient(135deg, #0f172a 0%, #111827 48%, #18181b 100%);
            color: #f8fafc;
        }

        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        #MainMenu,
        footer {
            visibility: hidden !important;
            height: 0 !important;
        }

        header {
            background: transparent !important;
        }

        [data-testid="stToolbar"] {
            opacity: 0.18;
        }

        [data-testid="stToolbar"]:hover {
            opacity: 1;
        }

        .mobile-picker {
            margin-bottom: 1rem;
        }

        [data-testid="stSidebar"] {
            background: rgba(15, 23, 42, 0.96);
            border-right: 1px solid rgba(148, 163, 184, 0.24);
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: #f8fafc !important;
            opacity: 1 !important;
        }

        [data-testid="stSidebar"] p {
            line-height: 1.65;
            font-weight: 500;
        }

        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] div[data-baseweb="select"] > div {
            background: #f8fafc !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
        }

        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] div[data-baseweb="select"] input,
        [data-testid="stSidebar"] div[data-baseweb="select"] span {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
        }

        button,
        [data-testid="stBaseButton-secondary"],
        [data-testid="stBaseButton-secondaryFormSubmit"] {
            background: #f8fafc !important;
            color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            font-weight: 800 !important;
        }

        button p,
        button span,
        [data-testid="stBaseButton-secondary"] p,
        [data-testid="stBaseButton-secondary"] span {
            color: #0f172a !important;
            opacity: 1 !important;
        }

        [data-testid="stBaseButton-primary"],
        [data-testid="stButtonGroup"] button[aria-pressed="true"],
        .stButtonGroup button[aria-pressed="true"] {
            background: #ff4655 !important;
            color: #ffffff !important;
            border-color: #ff6b76 !important;
        }

        [data-testid="stBaseButton-primary"] p,
        [data-testid="stBaseButton-primary"] span,
        [data-testid="stButtonGroup"] button[aria-pressed="true"] p,
        [data-testid="stButtonGroup"] button[aria-pressed="true"] span,
        .stButtonGroup button[aria-pressed="true"] p,
        .stButtonGroup button[aria-pressed="true"] span {
            color: #ffffff !important;
        }

        details,
        details summary {
            background: rgba(15, 23, 42, 0.75) !important;
            color: #f8fafc !important;
            border-color: rgba(148, 163, 184, 0.25) !important;
        }

        details summary p,
        details summary span,
        details summary div {
            color: #f8fafc !important;
            opacity: 1 !important;
        }

        [data-testid="stTabs"] button,
        [data-testid="stTabs"] button p,
        [data-testid="stTabs"] button span {
            background: #f8fafc !important;
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            opacity: 1 !important;
            font-weight: 800 !important;
        }

        [data-testid="stTabs"] button[aria-selected="true"],
        [data-testid="stTabs"] button[aria-selected="true"] p,
        [data-testid="stTabs"] button[aria-selected="true"] span {
            background: #ff4655 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        .modebar,
        .modebar-group,
        .modebar-btn {
            background: #f8fafc !important;
            color: #0f172a !important;
        }

        .modebar-btn svg path { fill: #0f172a !important; }

        [data-testid="stMetric"] {
            background: rgba(15, 23, 42, 0.68);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 8px;
            padding: 1rem;
        }

        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"] {
            color: #f8fafc !important;
            opacity: 1 !important;
        }

        [data-testid="stMetricValue"] { font-size: 2rem; }

        [data-testid="stToggle"] label,
        [data-testid="stToggle"] p,
        [data-testid="stToggle"] span,
        div[class*="st-"] p:has(+ [data-testid="stTooltipIcon"]),
        div[class*="st-"] label p,
        div[class*="st-"] label span {
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
            opacity: 1 !important;
            font-weight: 700 !important;
        }

        .block-container { padding-top: 3.25rem; }

        h1, h2, h3 { letter-spacing: 0; }

        @media (max-width: 768px) {
            .mobile-picker {
                margin-bottom: 0.85rem;
            }

            .desktop-sidebar-hint {
                display: none;
            }

            .block-container {
                padding: 1rem 0.85rem 2rem 0.85rem;
                max-width: 100%;
            }

            h1 {
                font-size: 2rem !important;
                line-height: 1.12 !important;
            }

            h2, h3 {
                font-size: 1.35rem !important;
                line-height: 1.2 !important;
            }

            [data-testid="stSidebar"] {
                border-right: 0;
                border-bottom: 1px solid rgba(148, 163, 184, 0.24);
            }

            [data-testid="stMetric"] {
                padding: 0.8rem;
                min-height: 96px;
            }

            [data-testid="stMetricValue"] {
                font-size: 1.45rem !important;
                white-space: normal !important;
            }

            [data-testid="stButtonGroup"] {
                width: 100%;
                overflow-x: auto;
            }

            [data-testid="stButtonGroup"] button {
                min-width: 72px;
                padding-left: 0.6rem !important;
                padding-right: 0.6rem !important;
            }

            [data-testid="stDataFrame"] {
                overflow-x: auto;
            }

            [data-testid="stDataFrame"] div {
                font-size: 0.82rem !important;
            }

            .stPlotlyChart {
                margin-left: -0.15rem;
                margin-right: -0.15rem;
            }

            iframe,
            canvas,
            svg {
                max-width: 100% !important;
            }

            .analyst-detail-card {
                overflow-x: auto;
            }

            .analyst-row {
                min-width: 620px;
            }
        }

        .analyst-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            color: #ffffff;
            font-weight: 900;
            padding: 0.35rem 0.75rem;
            margin: 0.2rem 0 0.8rem;
            letter-spacing: 0;
        }

        .analyst-detail-card {
            background: rgba(15, 23, 42, 0.62);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 8px;
            overflow: hidden;
        }

        .analyst-row {
            display: grid;
            grid-template-columns: minmax(160px, 1.4fr) minmax(92px, 0.7fr) minmax(110px, 0.8fr) minmax(150px, 1fr);
            gap: 0.75rem;
            align-items: center;
            padding: 0.75rem 0.9rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.14);
            color: #f8fafc;
        }

        .analyst-row:last-child { border-bottom: 0; }

        .analyst-head {
            color: #cbd5e1;
            font-size: 0.82rem;
            font-weight: 900;
            background: rgba(248, 250, 252, 0.06);
        }

        .analyst-row span {
            color: #cbd5e1;
            font-weight: 700;
        }

        .confidence-badge {
            display: inline-flex;
            color: #ffffff !important;
            border-radius: 999px;
            padding: 0.2rem 0.55rem;
            font-size: 0.78rem;
            font-weight: 900 !important;
            white-space: nowrap;
        }

        .analyst-note {
            color: #cbd5e1;
            font-weight: 700;
            margin-top: 0.6rem;
        }

        .event-impact {
            border-left: 4px solid #94a3b8;
            background: rgba(15, 23, 42, 0.62);
            border-radius: 8px;
            padding: 0.9rem 1rem;
        }

        .event-impact span {
            display: inline-flex;
            color: #ffffff;
            border-radius: 999px;
            padding: 0.18rem 0.55rem;
            font-size: 0.78rem;
            font-weight: 900;
            margin-bottom: 0.65rem;
        }

        .event-impact p {
            color: #f8fafc;
            line-height: 1.55;
            margin: 0 0 0.55rem;
        }

        .event-impact small {
            color: #cbd5e1;
            font-weight: 700;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


if "hisse_gecmisi" not in st.session_state:
    st.session_state.hisse_gecmisi = []

if "favoriler" not in st.session_state:
    st.session_state.favoriler = []

if "aktif_profil" not in st.session_state:
    st.session_state.aktif_profil = None

if "ticker_secimi" not in st.session_state:
    st.session_state.ticker_secimi = None

if "ticker_secimi_ana" not in st.session_state:
    st.session_state.ticker_secimi_ana = None

if "ticker_secimi_bekleyen" not in st.session_state:
    st.session_state.ticker_secimi_bekleyen = None

if "sirket_ozeti_goster" not in st.session_state:
    st.session_state.sirket_ozeti_goster = True

if "erisim_onaylandi" not in st.session_state:
    st.session_state.erisim_onaylandi = False


def gizli_deger_getir(anahtar: str) -> str | None:
    try:
        deger = st.secrets.get(anahtar)
        if deger:
            return str(deger)
    except Exception:
        pass
    deger = os.getenv(anahtar)
    return str(deger) if deger else None


def erisim_kapisi_goster() -> None:
    uygulama_sifresi = gizli_deger_getir("APP_PASSWORD")
    if not uygulama_sifresi or st.session_state.erisim_onaylandi:
        return

    st.title("Hisse Analiz Paneli")
    st.info("Bu uygulama ozel kullanim icin sifre korumalidir.")
    girilen_sifre = st.text_input("Sifre", type="password")
    if st.button("Giris Yap", type="primary"):
        if girilen_sifre == uygulama_sifresi:
            st.session_state.erisim_onaylandi = True
            st.rerun()
        else:
            st.error("Sifre hatali.")
    st.stop()


erisim_kapisi_goster()


def db_baglan() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    baglanti = sqlite3.connect(DB_PATH)
    baglanti.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            profile_email TEXT NOT NULL,
            ticker TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (profile_email, ticker)
        )
        """
    )
    return baglanti


def favorileri_yukle(profile_email: str) -> list[str]:
    with db_baglan() as baglanti:
        satirlar = baglanti.execute(
            """
            SELECT ticker
            FROM favorites
            WHERE profile_email = ?
            ORDER BY created_at DESC
            """,
            (profile_email.lower(),),
        ).fetchall()
    return [satir[0] for satir in satirlar]


def favori_kaydet(profile_email: str, ticker: str) -> None:
    with db_baglan() as baglanti:
        baglanti.execute(
            """
            INSERT OR REPLACE INTO favorites (profile_email, ticker, created_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (profile_email.lower(), ticker.upper()),
        )


def favori_sil(profile_email: str, ticker: str) -> None:
    with db_baglan() as baglanti:
        baglanti.execute(
            "DELETE FROM favorites WHERE profile_email = ? AND ticker = ?",
            (profile_email.lower(), ticker.upper()),
        )


def profil_senkronize() -> None:
    profil = DEFAULT_PROFILE
    if st.session_state.aktif_profil != profil:
        st.session_state.aktif_profil = profil
        st.session_state.favoriler = favorileri_yukle(profil)


@st.cache_data(ttl=300, show_spinner=False)
def hisse_bilgisi_getir(ticker: str, period: str, interval: str) -> dict:
    hisse = yf.Ticker(ticker)
    info = hisse.info
    gecmis = hisse.history(period=period, interval=interval)
    fk, pd_dd = guvenilir_fk_pd_dd(ticker, info)

    return {
        "ticker": ticker.upper(),
        "sirket_adi": info.get("longName") or info.get("shortName") or ticker.upper(),
        "guncel_fiyat": info.get("currentPrice") or info.get("regularMarketPrice"),
        "onceki_kapanis": info.get("previousClose"),
        "fk": fk,
        "pd_dd": pd_dd,
        "temettu_verimi": info.get("dividendYield"),
        "temettu_tutari": info.get("dividendRate"),
        "payout_orani": info.get("payoutRatio"),
        "hedef_fiyat": info.get("targetMedianPrice"),
        "hedef_ortalama": info.get("targetMeanPrice"),
        "hedef_yuksek": info.get("targetHighPrice"),
        "hedef_dusuk": info.get("targetLowPrice"),
        "analist_sayisi": info.get("numberOfAnalystOpinions"),
        "analist_gorusu": info.get("recommendationKey"),
        "kazanc_buyumesi": info.get("earningsQuarterlyGrowth"),
        "kazanc_buyumesi_yillik": info.get("earningsGrowth"),
        "ozsermaye_karliligi": info.get("returnOnEquity"),
        "gelir_buyumesi": info.get("revenueGrowth"),
        "borc_ozsermaye": info.get("debtToEquity"),
        "cari_oran": info.get("currentRatio"),
        "sektor": info.get("sector"),
        "endustri": info.get("industry"),
        "ulke": info.get("country") or ("Turkey" if ticker.upper().endswith(".IS") else ""),
        "piyasa_degeri": info.get("marketCap"),
        "borsa": info.get("exchange") or info.get("fullExchangeName") or "",
        "ozet": info.get("longBusinessSummary") or "Şirket özeti bulunamadı.",
        "para_birimi": info.get("currency") or "",
        "gecmis": gecmis,
    }


@st.cache_data(ttl=300, show_spinner=False)
def kur_verisi_getir(para_birimi: str, period: str, interval: str) -> tuple[float | None, pd.Series | None]:
    ayar = USD_CEVRIMLERI.get(para_birimi)
    if not ayar:
        return None, None

    kur_gecmisi = yf.Ticker(ayar["ticker"]).history(period=period, interval=interval)
    if kur_gecmisi.empty:
        kur_gecmisi = yf.Ticker(ayar["ticker"]).history(period=period, interval="1d")

    if kur_gecmisi.empty:
        return None, None

    kur_serisi = kur_gecmisi["Close"].dropna()
    if kur_serisi.empty:
        return None, None

    return float(kur_serisi.iloc[-1]), kur_serisi


@st.cache_data(ttl=86400, show_spinner=False)
def turkce_ozet_getir(metin: str) -> str:
    if not metin or metin == "Şirket özeti bulunamadı.":
        return "Şirket özeti bulunamadı."

    try:
        query = urlencode(
            {
                "client": "gtx",
                "sl": "auto",
                "tl": "tr",
                "dt": "t",
                "q": metin,
            }
        )
        with urlopen(
            f"https://translate.googleapis.com/translate_a/single?{query}",
            timeout=8,
        ) as response:
            sonuc = response.read().decode("utf-8")
        parcalar = json.loads(sonuc)[0]
        return "".join(parca[0] for parca in parcalar if parca and parca[0])
    except Exception:
        pass

    if GoogleTranslator is None:
        return "Türkçe çeviri için `deep-translator` paketini kurun."

    try:
        return GoogleTranslator(source="auto", target="tr").translate(metin)
    except Exception:
        return "Türkçe çeviri şu anda alınamadı."


def usd_degere_cevir(deger: float | None, kur: float | None, para_birimi: str) -> float | None:
    if deger is None or kur is None:
        return None

    islem = USD_CEVRIMLERI.get(para_birimi, {}).get("operation")
    if islem == "divide":
        return deger / kur
    if islem == "multiply":
        return deger * kur
    return deger


def piyasa_degerini_usd_cevir(piyasa_degeri: float | None, para_birimi: str | None) -> float | None:
    if piyasa_degeri is None:
        return None
    if not para_birimi or para_birimi == "USD":
        return piyasa_degeri
    if para_birimi not in USD_CEVRIMLERI:
        return piyasa_degeri

    kur, _ = kur_verisi_getir(para_birimi, "5d", "1d")
    return usd_degere_cevir(float(piyasa_degeri), kur, para_birimi)


def usd_seriye_cevir(seri: pd.Series, kur_serisi: pd.Series | None, para_birimi: str) -> pd.Series:
    if kur_serisi is None or kur_serisi.empty:
        return seri

    kur_hizali = kur_serisi.reindex(seri.index, method="ffill").bfill()
    islem = USD_CEVRIMLERI.get(para_birimi, {}).get("operation")
    if islem == "divide":
        return seri / kur_hizali
    if islem == "multiply":
        return seri * kur_hizali
    return seri


def tarihteki_kur(kur_serisi: pd.Series | None, tarih: pd.Timestamp) -> float | None:
    if kur_serisi is None or kur_serisi.empty:
        return None

    kur_temiz = kur_serisi.copy()
    kur_temiz.index = pd.to_datetime(kur_temiz.index).tz_localize(None).normalize()
    tarih = pd.Timestamp(tarih).tz_localize(None).normalize()
    uygun = kur_temiz.loc[kur_temiz.index <= tarih].dropna()
    if uygun.empty:
        uygun = kur_temiz.dropna()
    if uygun.empty:
        return None
    return float(uygun.iloc[-1])


def yuzde_formatla(deger: float | None) -> str:
    if deger is None:
        return "Veri yok"
    return f"%{deger:.2f}"


def sayi_formatla(deger: float | None, para_birimi: str = "") -> str:
    if deger is None:
        return "Veri yok"
    return f"{deger:,.2f} {para_birimi}".strip()


def oran_formatla(deger: float | None) -> str:
    if deger is None:
        return "Veri yok"
    return f"{deger:.2f}"


def ilk_gecerli_deger(seri: pd.Series | None) -> float | None:
    if seri is None:
        return None
    temiz = seri.dropna()
    if temiz.empty:
        return None
    deger = float(temiz.iloc[0])
    return deger if math.isfinite(deger) else None


@st.cache_data(ttl=3600, show_spinner=False)
def finansal_tablodan_oran_getir(ticker: str, piyasa_degeri: float | None) -> dict:
    if piyasa_degeri is None or piyasa_degeri <= 0:
        return {"fk": None, "pd_dd": None}

    try:
        hisse = yf.Ticker(ticker)
        finansallar = hisse.financials
        ceyreklik_finansallar = hisse.quarterly_financials
        bilanco = hisse.balance_sheet
    except Exception:
        return {"fk": None, "pd_dd": None}

    net_kar = None
    for satir in ["Net Income", "Net Income Common Stockholders"]:
        if not ceyreklik_finansallar.empty and satir in ceyreklik_finansallar.index:
            son_ceyrekler = ceyreklik_finansallar.loc[satir].dropna().head(4)
            if len(son_ceyrekler) >= 4:
                ttm_net_kar = float(son_ceyrekler.sum())
                if math.isfinite(ttm_net_kar) and ttm_net_kar > 0:
                    net_kar = ttm_net_kar
                    break

    for satir in ["Net Income", "Net Income Common Stockholders"]:
        if net_kar:
            break
        if not finansallar.empty and satir in finansallar.index:
            net_kar = ilk_gecerli_deger(finansallar.loc[satir])
            if net_kar:
                break

    ozkaynak = None
    for satir in ["Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"]:
        if not bilanco.empty and satir in bilanco.index:
            ozkaynak = ilk_gecerli_deger(bilanco.loc[satir])
            if ozkaynak:
                break

    return {
        "fk": (piyasa_degeri / net_kar) if net_kar and net_kar > 0 else None,
        "pd_dd": (piyasa_degeri / ozkaynak) if ozkaynak and ozkaynak > 0 else None,
    }


def pozitif_sayi(deger) -> float | None:
    try:
        if deger is None or pd.isna(deger):
            return None
        sayi = float(deger)
        return sayi if math.isfinite(sayi) and sayi > 0 else None
    except (TypeError, ValueError):
        return None


def tercih_edilebilir_oran(deger: float | None, ust_sinir: float) -> bool:
    return deger is not None and 0 < deger < ust_sinir


def oran_gecerli_mi(deger: float | None, oran_tipi: str) -> bool:
    if deger is None or pd.isna(deger) or not math.isfinite(float(deger)):
        return False
    if oran_tipi in ["fk", "pd_dd"]:
        return 0 < float(deger) < (100 if oran_tipi == "fk" else 25)
    if oran_tipi == "temettu":
        return 0 <= float(deger) < 5
    return True


def oran_temizle(deger: float | None, oran_tipi: str) -> float | None:
    return float(deger) if oran_gecerli_mi(deger, oran_tipi) else None


def sapma_orani(aday: float | None, referans: float | None) -> float | None:
    if not aday or not referans:
        return None
    return abs(aday - referans) / referans


def metinden_oran_cek(metin: str, etiketler: list[str]) -> float | None:
    for etiket in etiketler:
        desen = rf"{re.escape(etiket)}\s+(-?\d+(?:[.,]\d+)?)"
        eslesme = re.search(desen, metin, flags=re.IGNORECASE)
        if eslesme:
            return pozitif_sayi(eslesme.group(1).replace(",", ""))
    return None


@st.cache_data(ttl=21600, show_spinner=False)
def public_oranlari_getir(ticker: str) -> dict:
    ticker = ticker.upper()
    if ticker.endswith(".IS"):
        url = f"https://stockanalysis.com/quote/ist/{ticker.removesuffix('.IS')}/statistics/"
    else:
        url = f"https://stockanalysis.com/stocks/{ticker.lower()}/statistics/"

    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=8) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return {"fk": None, "pd_dd": None, "kaynak": None}

    metin = unescape(re.sub(r"<[^>]+>", " ", html))
    metin = re.sub(r"\s+", " ", metin)
    return {
        "fk": metinden_oran_cek(metin, ["PE Ratio", "P/E Ratio"]),
        "pd_dd": metinden_oran_cek(metin, ["PB Ratio", "P/B Ratio", "Price to Book"]),
        "kaynak": url,
    }


def web_sayfasi_getir(url: str, timeout: int = 10) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def html_metinlestir(html: str) -> str:
    temiz = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    temiz = re.sub(r"<style[\s\S]*?</style>", " ", temiz, flags=re.IGNORECASE)
    temiz = unescape(re.sub(r"<[^>]+>", " ", temiz))
    return re.sub(r"\s+", " ", temiz).strip()


def tl_hedef_fiyat_cek(metin: str) -> float | None:
    desenler = [
        r"hedef fiyat(?:ını|ı|i)?[^.]{0,120}(?:'den|den|seviyesinden)\s+([\d.]+,\d+|[\d.]+)\s*(?:TL|₺|'?ye|ye)",
        r"hedef fiyat(?:ını|ı|i)?[^.]{0,120}(?:yükseltti|revize etti|çıkardı|korudu)[^.]{0,80}([\d.]+,\d+|[\d.]+)\s*(?:TL|₺)",
        r"hedef fiyat(?:ını|ı|i)?[^0-9]{0,80}([\d.]+,\d+|[\d.]+)",
        r"([\d.]+,\d+|[\d.]+)\s*(?:TL|₺)[^\.]{0,80}hedef fiyat",
        r"([\d.]+,\d+|[\d.]+)\s*(?:TL|₺)",
    ]
    for desen in desenler:
        eslesme = re.search(desen, metin, flags=re.IGNORECASE)
        if not eslesme:
            continue
        sayi = eslesme.group(1).replace(".", "").replace(",", ".")
        return pozitif_sayi(sayi)
    return None


def kurum_adi_cek(metin: str) -> str:
    kurumlar = [
        "Deniz Yatırım",
        "İş Yatırım",
        "Is Yatırım",
        "Ak Yatırım",
        "Tacirler Yatırım",
        "Global Menkul Değerler",
        "Ünlü & Co",
        "Ünlü Menkul",
        "TERA Yatırım",
        "Oyak Yatırım",
        "Garanti BBVA Yatırım",
        "Yapı Kredi Yatırım",
        "Vakıf Yatırım",
        "QNB Invest",
        "Alnus Yatırım",
        "A1 Capital",
        "Gedik Yatırım",
        "Halk Yatırım",
    ]
    metin_kucuk = metin.lower()
    for kurum in kurumlar:
        if kurum.lower() in metin_kucuk:
            return kurum
    return "HedefFiyat"


def turkce_tarih_cek(metin: str) -> pd.Timestamp | None:
    aylar = {
        "ocak": 1,
        "şubat": 2,
        "subat": 2,
        "mart": 3,
        "nisan": 4,
        "mayıs": 5,
        "mayis": 5,
        "haziran": 6,
        "temmuz": 7,
        "ağustos": 8,
        "agustos": 8,
        "eylül": 9,
        "eylul": 9,
        "ekim": 10,
        "kasım": 11,
        "kasim": 11,
        "aralık": 12,
        "aralik": 12,
    }
    eslesme = re.search(
        r"(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(20\d{2})",
        metin,
        flags=re.IGNORECASE,
    )
    if not eslesme:
        return None
    ay = aylar.get(eslesme.group(2).lower())
    if not ay:
        return None
    return pd.Timestamp(year=int(eslesme.group(3)), month=ay, day=int(eslesme.group(1)))


def ticker_kok(ticker: str) -> str:
    return ticker.upper().removesuffix(".IS")


def public_ile_dogrula(aday: float | None, public_deger: float | None, oran_tipi: str) -> float | None:
    aday = oran_temizle(aday, oran_tipi)
    public_deger = oran_temizle(public_deger, oran_tipi)
    if public_deger is None:
        return aday
    if aday is None:
        return public_deger

    sapma = sapma_orani(aday, public_deger)
    if sapma is not None and sapma > 0.35:
        return public_deger
    return aday


def hisse_basi_oran_hesapla(ticker: str, info: dict) -> tuple[float | None, float | None]:
    fiyat = pozitif_sayi(info.get("currentPrice") or info.get("regularMarketPrice"))
    eps = pozitif_sayi(info.get("trailingEps"))
    defter_degeri = pozitif_sayi(info.get("bookValue"))

    if not fiyat:
        return None, None

    fk = fiyat / eps if eps else None
    pd_dd = fiyat / defter_degeri if defter_degeri else None
    return fk, pd_dd


def guvenilir_fk_pd_dd(ticker: str, info: dict) -> tuple[float | None, float | None]:
    raw_fk = pozitif_sayi(info.get("trailingPE"))
    raw_pd_dd = pozitif_sayi(info.get("priceToBook"))
    hisse_basi_fk, hisse_basi_pd_dd = hisse_basi_oran_hesapla(ticker, info)
    public_oranlar = public_oranlari_getir(ticker)

    if ticker.upper().endswith(".IS"):
        tablo_oranlari = finansal_tablodan_oran_getir(ticker.upper(), info.get("marketCap"))
        tablo_fk = pozitif_sayi(tablo_oranlari.get("fk"))
        tablo_pd_dd = pozitif_sayi(tablo_oranlari.get("pd_dd"))

        fk = (
            hisse_basi_fk
            if tercih_edilebilir_oran(hisse_basi_fk, 80)
            else tablo_fk
            if tercih_edilebilir_oran(tablo_fk, 80)
            else raw_fk
        )
        pd_dd = (
            hisse_basi_pd_dd
            if tercih_edilebilir_oran(hisse_basi_pd_dd, 20)
            else tablo_pd_dd
            if tercih_edilebilir_oran(tablo_pd_dd, 20)
            else raw_pd_dd
        )
        return (
            public_ile_dogrula(fk, public_oranlar.get("fk"), "fk"),
            public_ile_dogrula(pd_dd, public_oranlar.get("pd_dd"), "pd_dd"),
        )

    return (
        public_ile_dogrula(raw_fk, public_oranlar.get("fk"), "fk"),
        public_ile_dogrula(raw_pd_dd, public_oranlar.get("pd_dd"), "pd_dd"),
    )


def gecmise_ekle(ticker: str) -> None:
    ticker = ticker.upper()
    mevcut = [kod for kod in st.session_state.hisse_gecmisi if kod != ticker]
    st.session_state.hisse_gecmisi = [ticker, *mevcut][:20]


def favori_degistir(ticker: str) -> None:
    ticker = ticker.upper()
    profil = st.session_state.aktif_profil or DEFAULT_PROFILE
    if ticker in st.session_state.favoriler:
        st.session_state.favoriler = [
            kod for kod in st.session_state.favoriler if kod != ticker
        ]
        favori_sil(profil, ticker)
    else:
        st.session_state.favoriler = [ticker, *st.session_state.favoriler][:20]
        favori_kaydet(profil, ticker)


def ticker_ac(ticker: str) -> None:
    st.session_state.ticker_secimi_bekleyen = ticker.upper()
    st.session_state.ticker_secimi_ana = ticker.upper()
    st.rerun()


def ticker_satiri(ticker: str, prefix: str) -> None:
    sec_col, fav_col = st.columns([0.78, 0.22])
    if sec_col.button(ticker, key=f"{prefix}_open_{ticker}", use_container_width=True):
        ticker_ac(ticker)

    favori_mi = ticker in st.session_state.favoriler
    favori_etiketi = "★" if favori_mi else "☆"
    if fav_col.button(
        favori_etiketi,
        key=f"{prefix}_fav_{ticker}",
        help="Favorilerden çıkar" if favori_mi else "Favorilere ekle",
        use_container_width=True,
    ):
        favori_degistir(ticker)
        st.rerun()


def grafik_olustur(
    grafik_serisi: pd.Series,
    para_birimi: str,
    yukseklik: int,
    analist_noktalari: list[dict] | None = None,
) -> go.Figure:
    temiz_seri = grafik_serisi.dropna()
    min_deger = float(temiz_seri.min())
    max_deger = float(temiz_seri.max())
    fark = max(max_deger - min_deger, abs(max_deger) * 0.02, 1)
    alt_sinir = min_deger - fark * 0.12
    ust_sinir = max_deger + fark * 0.12

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=temiz_seri.index,
            y=temiz_seri,
            mode="lines",
            name=f"Kapanış Fiyatı ({para_birimi})",
            line={"color": "#38bdf8", "width": 2.4},
            hovertemplate="Tarih: %{x|%d.%m.%Y %H:%M}<br>Fiyat: %{y:,.2f}<extra></extra>",
        )
    )
    if analist_noktalari:
        fig.add_trace(
            go.Scatter(
                x=[nokta["tarih"] for nokta in analist_noktalari],
                y=[nokta["hedef"] for nokta in analist_noktalari],
                mode="markers",
                name="Analist Hedefleri",
                marker={
                    "color": "#ff4655",
                    "size": 9,
                    "symbol": "circle",
                    "line": {"color": "#ffffff", "width": 1},
                },
                customdata=[
                    [nokta["kurum"], nokta["analist"], nokta["kaynak_baslik"]]
                    for nokta in analist_noktalari
                ],
                hovertemplate=(
                    "Tarih: %{x|%d.%m.%Y}<br>"
                    "Kurum: %{customdata[0]}<br>"
                    "Analist: %{customdata[1]}<br>"
                    f"Hedef Fiyat: %{{y:,.2f}} {para_birimi}<br>"
                    "Kaynak: %{customdata[2]}"
                    "<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        height=yukseklik,
        margin={"l": 8, "r": 8, "t": 12, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f8fafc",
        hovermode="x unified",
        xaxis={
            "showgrid": False,
            "rangeslider": {"visible": False},
            "rangeselector": {"visible": False},
        },
        yaxis={
            "range": [alt_sinir, ust_sinir],
            "gridcolor": "#dbe4ef",
            "zeroline": False,
            "fixedrange": False,
        },
        font={"color": "#334155"},
    )
    return fig


@st.cache_data(ttl=3600, show_spinner=False)
def temettu_gecmisi_getir(ticker: str) -> pd.DataFrame:
    hisse = yf.Ticker(ticker)
    temettuler = hisse.dividends
    if temettuler is None or temettuler.empty:
        return pd.DataFrame()

    temettuler = temettuler.copy()
    temettuler.index = pd.to_datetime(temettuler.index).tz_localize(None).normalize()
    baslangic = pd.Timestamp.today().normalize() - pd.DateOffset(years=10)
    temettuler = temettuler[temettuler.index >= baslangic]
    if temettuler.empty:
        return pd.DataFrame()

    fiyat_baslangic = temettuler.index.min() - pd.Timedelta(days=10)
    fiyat_bitis = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)
    fiyatlar = hisse.history(
        start=fiyat_baslangic,
        end=fiyat_bitis,
        interval="1d",
        auto_adjust=False,
    )
    if fiyatlar.empty or "Close" not in fiyatlar:
        return pd.DataFrame()

    kapanis = fiyatlar["Close"].dropna().copy()
    kapanis.index = pd.to_datetime(kapanis.index).tz_localize(None).normalize()

    satirlar = []
    for tarih, temettu in temettuler.sort_index(ascending=False).items():
        fiyat_adaylari = kapanis.loc[kapanis.index <= tarih]
        if fiyat_adaylari.empty:
            continue

        fiyat = float(fiyat_adaylari.iloc[-1])
        temettu = float(temettu)
        temettu_orani = (temettu / fiyat) * 100 if fiyat > 0 else None
        satirlar.append(
            {
                "Tarih": tarih,
                "Temettü": temettu,
                "Hisse Fiyatı": fiyat,
                "Temettü Oranı": temettu_orani,
            }
        )

    return pd.DataFrame(satirlar)


def temettu_gecmisi_goster(
    temettu_df: pd.DataFrame,
    para_birimi: str,
    usd_modu: bool,
    kur_serisi: pd.Series | None,
) -> None:
    st.markdown("### Temettü Geçmişi")

    if temettu_df.empty:
        st.info("Son 10 yılda temettü verisi bulunamadı.")
        return

    gosterim = temettu_df.copy()
    gosterim_para_birimi = "USD" if usd_modu else para_birimi
    hedef_temettu_usd = 12000.0

    if usd_modu:
        for index, satir in gosterim.iterrows():
            kur = tarihteki_kur(kur_serisi, satir["Tarih"])
            gosterim.at[index, "Temettü"] = usd_degere_cevir(satir["Temettü"], kur, para_birimi)
            gosterim.at[index, "Hisse Fiyatı"] = usd_degere_cevir(satir["Hisse Fiyatı"], kur, para_birimi)

    if usd_modu:
        gosterim["Gerekli Hisse Adedi"] = gosterim["Temettü"].apply(
            lambda deger: math.ceil(hedef_temettu_usd / deger) if deger and deger > 0 else None
        )
        gosterim["Gerekli Portföy"] = gosterim.apply(
            lambda satir: satir["Gerekli Hisse Adedi"] * satir["Hisse Fiyatı"]
            if satir["Gerekli Hisse Adedi"] and satir["Hisse Fiyatı"]
            else None,
            axis=1,
        )
    else:
        gosterim["Gerekli Hisse Adedi"] = None
        gosterim["Gerekli Portföy"] = None

    gosterim["Tarih"] = pd.to_datetime(gosterim["Tarih"]).dt.strftime("%d.%m.%Y")
    gosterim["Temettü"] = gosterim["Temettü"].apply(lambda deger: sayi_formatla(deger, gosterim_para_birimi))
    gosterim["Hisse Fiyatı"] = gosterim["Hisse Fiyatı"].apply(lambda deger: sayi_formatla(deger, gosterim_para_birimi))
    gosterim["Temettü Oranı"] = gosterim["Temettü Oranı"].apply(yuzde_formatla)
    gosterim["Gerekli Hisse Adedi"] = gosterim["Gerekli Hisse Adedi"].apply(
        lambda deger: f"{int(deger):,}" if deger else "Veri yok"
    )
    gosterim["Gerekli Portföy"] = gosterim["Gerekli Portföy"].apply(lambda deger: sayi_formatla(deger, "USD"))

    st.dataframe(
        gosterim.rename(
            columns={
                "Temettü": "Hisse Başı Temettü",
                "Temettü Oranı": "Fiyata Oranı",
                "Gerekli Hisse Adedi": "12.000 USD İçin Adet",
                "Gerekli Portföy": "12.000 USD İçin Portföy",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Temettü oranı, temettü tarihindeki kapanış fiyatına göre hesaplanır. "
        "12.000 USD hesabı, temettü ve fiyat USD'ye çevrilebiliyorsa gösterilir. "
        "Temettü tutarı Yahoo Finance'ın hisse başı dağıtım verisidir; kaynak net/brüt ayrımı vermiyorsa aynı tutar gösterilir."
    )


def analist_gorusu_etiketi(gorus: str | None) -> tuple[str, str]:
    harita = {
        "strong_buy": ("GÜÇLÜ AL", "#16a34a"),
        "buy": ("AL", "#22c55e"),
        "hold": ("TUT", "#f59e0b"),
        "underperform": ("ZAYIF", "#f97316"),
        "sell": ("SAT", "#ef4444"),
        "strong_sell": ("GÜÇLÜ SAT", "#dc2626"),
    }
    return harita.get((gorus or "").lower(), ("VERİ YOK", "#94a3b8"))


def analist_guven_etiketi(basari: int) -> tuple[str, str]:
    if basari >= 75:
        return "Yüksek Güven", "#16a34a"
    if basari >= 50:
        return "Orta Güven", "#f59e0b"
    return "Düşük Güven", "#ef4444"


def analist_tahminleri_uret(veri: dict, usd_modu: bool, kur: float | None) -> list[dict]:
    kaynakli_kayitlar = kaynakli_analist_tahminleri_getir(veri["ticker"])
    kaynakli_kayitlar.extend(ANALIST_KAYNAKLARI.get(veri["ticker"].upper(), []))
    tahminler = []
    for kayit in kaynakli_kayitlar:
        kaynak = str(kayit.get("kaynak") or "").strip()
        hedef = pozitif_sayi(kayit.get("hedef"))
        if not kaynak.startswith(("https://", "http://")) or hedef is None:
            continue
        if usd_modu:
            hedef = usd_degere_cevir(hedef, kur, veri["para_birimi"])
        if hedef is None:
            continue
        tahminler.append(
            {
                "tarih": pd.to_datetime(kayit.get("tarih"), errors="coerce"),
                "kurum": kayit.get("kurum") or "Kurum",
                "analist": kayit.get("analist") or "Rapor",
                "basari": int(kayit.get("basari") or 0),
                "hedef": hedef,
                "kaynak": kaynak,
                "kaynak_baslik": kayit.get("kaynak_baslik") or kaynak,
            }
        )
    tahminler = [tahmin for tahmin in tahminler if not pd.isna(tahmin["tarih"])]
    return sorted(tahminler, key=lambda item: item["tarih"])


@st.cache_data(ttl=3600, show_spinner=False)
def kaynakli_analist_tahminleri_getir(ticker: str) -> list[dict]:
    if not ticker.upper().endswith(".IS"):
        return []

    tahminler = []
    tahminler.extend(hedeffiyat_tahminleri_getir(ticker))
    tahminler.extend(rotaborsa_tahminleri_getir(ticker))

    benzersiz = {}
    for tahmin in tahminler:
        anahtar = (
            tahmin.get("kaynak"),
            tahmin.get("hedef"),
            str(tahmin.get("tarih")),
        )
        benzersiz[anahtar] = tahmin
    return list(benzersiz.values())[:8]


def hedeffiyat_tahminleri_getir(ticker: str) -> list[dict]:
    kok = ticker_kok(ticker)
    try:
        html = web_sayfasi_getir("https://hedeffiyat.com.tr/")
    except Exception:
        return []

    aday_url_listesi = []
    for eslesme in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>', html, re.IGNORECASE):
        href, govde = eslesme.groups()
        metin = html_metinlestir(govde)
        href_kucuk = href.lower()
        if kok in (metin + " " + href).upper() and any(parca in href_kucuk for parca in ["/senet/", "/hedef-fiyat/", "/rapor/"]):
            aday_url_listesi.append(urljoin("https://hedeffiyat.com.tr/", href))

    aday_url_listesi = list(dict.fromkeys(aday_url_listesi))[:10]
    if not aday_url_listesi:
        return []

    kayitlar = []
    for detay_url in aday_url_listesi:
        try:
            detay_html = web_sayfasi_getir(detay_url)
        except Exception:
            continue

        metin = html_metinlestir(detay_html)
        hedef = tl_hedef_fiyat_cek(metin)
        tarih = turkce_tarih_cek(metin) or pd.Timestamp.today().normalize()
        if hedef is None or tarih is None:
            continue
        baslik_eslesme = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", detay_html, flags=re.IGNORECASE)
        baslik = html_metinlestir(baslik_eslesme.group(1)) if baslik_eslesme else f"{kok} hedef fiyat"
        kayitlar.append(
            {
                "tarih": tarih,
                "kurum": kurum_adi_cek(metin),
                "analist": "Kaynaklı hedef fiyat",
                "hedef": hedef,
                "basari": 0,
                "kaynak": detay_url,
                "kaynak_baslik": baslik[:120],
            }
        )
        if len(kayitlar) >= 6:
            break
    return kayitlar


def rotaborsa_tahminleri_getir(ticker: str) -> list[dict]:
    kok = ticker_kok(ticker)
    sayfalar = [
        "https://rotaborsa.com/hisse-hedef-fiyat/",
        f"https://rotaborsa.com/?s={kok}+hedef+fiyat",
    ]

    adaylar = []
    for sayfa_url in sayfalar:
        try:
            html = web_sayfasi_getir(sayfa_url)
        except Exception:
            continue
        for eslesme in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>', html, re.IGNORECASE):
            href, govde = eslesme.groups()
            baslik = html_metinlestir(govde)
            if kok in (baslik + " " + href).upper() and "hedef" in (baslik + " " + href).lower():
                adaylar.append((urljoin("https://rotaborsa.com/", href), baslik))
    adaylar = list(dict.fromkeys(adaylar))

    kayitlar = []
    for url, baslik in adaylar[:5]:
        try:
            detay_html = web_sayfasi_getir(url)
        except Exception:
            continue
        metin = html_metinlestir(detay_html)
        hedef = tl_hedef_fiyat_cek(metin)
        tarih = turkce_tarih_cek(metin) or pd.Timestamp.today().normalize()
        if hedef is None:
            continue
        kurum_eslesme = re.search(
            r"(?:aracı kurum|kurum|yatırım kuruluşu)\s+([A-ZÇĞİÖŞÜa-zçğıöşü0-9 .&-]{2,45})",
            metin,
            flags=re.IGNORECASE,
        )
        kurum = kurum_eslesme.group(1).strip() if kurum_eslesme else "Rota Borsa"
        kayitlar.append(
            {
                "tarih": tarih,
                "kurum": kurum,
                "analist": "Hedef fiyat haberi",
                "hedef": hedef,
                "basari": 0,
                "kaynak": url,
                "kaynak_baslik": baslik[:120],
            }
        )
    return kayitlar


def analist_detaylari_goster(veri: dict, tahminler: list[dict], para_birimi: str) -> None:
    if not tahminler:
        st.caption(
            "Kaynak linkiyle doğrulanmış kurum bazlı hedef fiyat bulunamadı. "
            "Bu nedenle grafikte analist hedef noktası gösterilmiyor."
        )
        return

    with st.expander("Analist detayları ve son 6 ay hedef fiyat geçmişi", expanded=False):
        satirlar = []
        for tahmin in sorted(tahminler, key=lambda item: item["tarih"], reverse=True):
            satirlar.append(
                "".join(
                    [
                        '<div class="analyst-row">',
                        f'<div><strong>{escape(tahmin["kurum"])}</strong><br><span>{escape(tahmin["analist"])}</span></div>',
                        f'<div>{escape(pd.Timestamp(tahmin["tarih"]).strftime("%d.%m.%Y"))}</div>',
                        f'<div>{escape(sayi_formatla(tahmin["hedef"], para_birimi))}</div>',
                        f'<div><a href="{escape(tahmin["kaynak"], quote=True)}" target="_blank" rel="noopener noreferrer">Kaynak</a></div>',
                        "</div>",
                    ]
                )
            )

        html = textwrap.dedent(
            f"""
            <div class="analyst-detail-card">
                <div class="analyst-row analyst-head">
                    <div>Kurum / Analist</div>
                    <div>Tarih</div>
                    <div>Hedef Fiyat</div>
                    <div>Kaynak</div>
                </div>
                {''.join(satirlar)}
            </div>
            <p class="analyst-note">
                Bu listede yalnızca kaynak linki eklenmiş, doğrulanabilir kurum hedefleri gösterilir.
            </p>
            """
        )
        st.markdown(html, unsafe_allow_html=True)


def analist_kaynaklari_goster(tahminler: list[dict]) -> None:
    if not tahminler:
        st.caption(
            "Grafikte kurum bazlı analist hedefi gösterilmedi; çünkü bu hisse için kaynak linkiyle doğrulanmış hedef fiyat kaydı yok."
        )
        return

    linkler = []
    for tahmin in sorted(tahminler, key=lambda item: item["tarih"], reverse=True):
        linkler.append(
            "".join(
                [
                    '<li>',
                    f'{escape(pd.Timestamp(tahmin["tarih"]).strftime("%d.%m.%Y"))} - ',
                    f'{escape(tahmin["kurum"])}: ',
                    f'<a href="{escape(tahmin["kaynak"], quote=True)}" target="_blank" rel="noopener noreferrer">',
                    escape(str(tahmin.get("kaynak_baslik") or "Kaynak")),
                    "</a>",
                    "</li>",
                ]
            )
        )
    st.markdown(
        f"""
        <div class="analyst-note">
            <strong>Analist hedef fiyat kaynakları</strong>
            <ul>{''.join(linkler)}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hedef_fiyat_grafigi_olustur(
    guncel_fiyat: float,
    hedef_ortalama: float,
    hedef_dusuk: float,
    hedef_yuksek: float,
    para_birimi: str,
    yukseklik: int,
) -> go.Figure:
    alt = min(hedef_dusuk, hedef_ortalama, hedef_yuksek, guncel_fiyat)
    ust = max(hedef_dusuk, hedef_ortalama, hedef_yuksek, guncel_fiyat)
    pay = (ust - alt) * 0.16 if ust > alt else max(ust * 0.08, 1)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[hedef_dusuk, hedef_yuksek],
            y=[0, 0],
            mode="lines",
            line={"color": "rgba(148, 163, 184, 0.7)", "width": 18},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[guncel_fiyat],
            y=[0],
            mode="markers+text",
            marker={"color": "#38bdf8", "size": 15, "symbol": "diamond"},
            text=["Mevcut"],
            textposition="bottom center",
            name="Mevcut Fiyat",
            hovertemplate=f"Mevcut Fiyat: %{{x:,.2f}} {para_birimi}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[hedef_ortalama],
            y=[0],
            mode="markers+text",
            marker={"color": "#ff4655", "size": 17, "symbol": "circle"},
            text=["Ort. Hedef"],
            textposition="top center",
            name="Ortalama Hedef",
            hovertemplate=f"Ortalama Hedef: %{{x:,.2f}} {para_birimi}<extra></extra>",
        )
    )
    fig.update_layout(
        height=yukseklik,
        margin={"l": 8, "r": 8, "t": 26, "b": 18},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.25)",
        showlegend=False,
        xaxis={
            "range": [alt - pay, ust + pay],
            "tickfont": {"color": "#cbd5e1"},
            "gridcolor": "rgba(148, 163, 184, 0.14)",
            "zeroline": False,
        },
        yaxis={"visible": False, "range": [-0.55, 0.55]},
        annotations=[
            {
                "x": hedef_dusuk,
                "y": 0.28,
                "text": f"En Düşük<br>{sayi_formatla(hedef_dusuk, para_birimi)}",
                "showarrow": False,
                "font": {"color": "#cbd5e1", "size": 12},
                "xanchor": "left",
            },
            {
                "x": hedef_yuksek,
                "y": 0.28,
                "text": f"En Yüksek<br>{sayi_formatla(hedef_yuksek, para_birimi)}",
                "showarrow": False,
                "font": {"color": "#cbd5e1", "size": 12},
                "xanchor": "right",
            },
        ],
        font={"color": "#f8fafc"},
    )
    return fig


def analist_beklentileri_goster(
    veri: dict,
    guncel_fiyat: float | None,
    para_birimi: str,
    usd_modu: bool,
    kur: float | None,
    mobil: bool,
    analist_tahminleri: list[dict],
) -> None:
    st.markdown("### Aracı Kurum Beklentileri")
    st.caption("Analistlerin 1 Yıllık Ortalama Hedef Fiyat Öngörüsü")

    hedef_ortalama = veri.get("hedef_ortalama") or veri.get("hedef_fiyat")
    hedef_yuksek = veri.get("hedef_yuksek")
    hedef_dusuk = veri.get("hedef_dusuk")
    analist_sayisi = veri.get("analist_sayisi")

    if usd_modu:
        hedef_ortalama = usd_degere_cevir(hedef_ortalama, kur, veri["para_birimi"])
        hedef_yuksek = usd_degere_cevir(hedef_yuksek, kur, veri["para_birimi"])
        hedef_dusuk = usd_degere_cevir(hedef_dusuk, kur, veri["para_birimi"])

    gorus_metni, gorus_renk = analist_gorusu_etiketi(veri.get("analist_gorusu"))
    st.markdown(
        f"""
        <div class="analyst-badge" style="background:{gorus_renk};">
            Genel Analist Görüşü: {escape(gorus_metni)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not all([guncel_fiyat, hedef_ortalama, hedef_yuksek, hedef_dusuk]):
        st.info("Bu hisse için yeterli hedef fiyat verisi bulunamadı.")
        return

    beklenen_getiri = ((hedef_ortalama - guncel_fiyat) / guncel_fiyat) * 100
    kolonlar = st.columns(1 if mobil else 3)
    kolonlar[0].metric("Ortalama Hedef", sayi_formatla(hedef_ortalama, para_birimi))
    kolonlar[1].metric("Beklenen Getiri Potansiyeli", yuzde_formatla(beklenen_getiri))
    kolonlar[2].metric("Analist Sayısı", int(analist_sayisi) if analist_sayisi else "Veri yok")
    analist_detaylari_goster(veri, analist_tahminleri, para_birimi)

    st.plotly_chart(
        hedef_fiyat_grafigi_olustur(
            guncel_fiyat,
            hedef_ortalama,
            hedef_dusuk,
            hedef_yuksek,
            para_birimi,
            230 if mobil else 260,
        ),
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False},
    )


def sonraki_ay_gunu(gun: int, ay_ekle: int = 0) -> pd.Timestamp:
    bugun = pd.Timestamp.today().normalize()
    yil = bugun.year + ((bugun.month + ay_ekle - 1) // 12)
    ay = ((bugun.month + ay_ekle - 1) % 12) + 1
    son_gun = pd.Period(f"{yil}-{ay:02d}").days_in_month
    tarih = pd.Timestamp(year=yil, month=ay, day=min(gun, son_gun))
    if tarih < bugun:
        return sonraki_ay_gunu(gun, ay_ekle + 1)
    return tarih


def sonraki_hafta_gunu(hafta_gunu: int, hafta_ekle: int = 0) -> pd.Timestamp:
    bugun = pd.Timestamp.today().normalize()
    fark = (hafta_gunu - bugun.weekday()) % 7
    return bugun + pd.Timedelta(days=fark + hafta_ekle * 7)


def olay_etki_rengi(etki: str) -> str:
    return {
        "Pozitif": "#16a34a",
        "Negatif": "#ef4444",
        "Nötr": "#f59e0b",
    }.get(etki, "#94a3b8")


def olay_etki_ikon(etki: str) -> str:
    return {
        "Pozitif": "🟢",
        "Negatif": "🔴",
        "Nötr": "🟡",
    }.get(etki, "🟡")


def kritik_olaylar_uret(veri: dict) -> list[dict]:
    ticker = veri["ticker"]
    ulke = (veri.get("ulke") or "").lower()
    endustri = (veri.get("endustri") or "").lower()
    sektor = (veri.get("sektor") or "").lower()
    bist_mi = ticker.endswith(".IS") or "turkey" in ulke

    if bist_mi:
        olaylar = [
            {
                "ad": "TCMB Faiz Kararı",
                "tarih": sonraki_hafta_gunu(3, 2),
                "durum": "Politika faizi ve karar metni takip edilir.",
                "beklenti": "Piyasa beklentisi karar haftasında güncellenir.",
                "etki": "Nötr",
                "senaryo_ustu": "Beklentiden daha sıkı duruş, kur ve enflasyon beklentileri için olumlu; faiz hassas sektörlerde kısa vadeli baskı yaratabilir.",
                "senaryo_alti": "Beklentiden gevşek duruş, kredi büyümesi ve iç talep için destekleyici; TL varlıklarda risk primi yaratabilir.",
                "kaynak": "TCMB takvimi",
            },
            {
                "ad": "TÜİK Enflasyon Verisi",
                "tarih": sonraki_ay_gunu(3),
                "durum": "Son açıklanan TÜFE ve ÜFE trendi izlenir.",
                "beklenti": "Aylık/yıllık enflasyon beklentisi anket ve piyasa tahminleriyle güncellenir.",
                "etki": "Nötr",
                "senaryo_ustu": "Beklenti üstü enflasyon, iskonto oranlarını yukarı çekerek değerlemeleri baskılayabilir.",
                "senaryo_alti": "Beklenti altı enflasyon, faiz indirimi beklentisini destekleyerek hisse çarpanlarını rahatlatabilir.",
                "kaynak": "TÜİK veri takvimi",
            },
        ]

        if "bank" in endustri or "financial" in sektor:
            olaylar.append(
                {
                    "ad": "BDDK Bankacılık Sektörü Verileri",
                    "tarih": sonraki_hafta_gunu(4),
                    "durum": "Kredi büyümesi, mevduat kompozisyonu ve takipteki alacaklar izlenir.",
                    "beklenti": "Sektör marjları ve aktif kalitesi beklentileriyle karşılaştırılır.",
                    "etki": "Nötr",
                    "senaryo_ustu": "Güçlü kredi büyümesi ve düşük takip oranı banka hisseleri için pozitif algılanabilir.",
                    "senaryo_alti": "Aktif kalitesinde bozulma veya marj baskısı banka hisselerini negatif etkileyebilir.",
                    "kaynak": "BDDK haftalık/aylık bülten",
                }
            )
        if any(kelime in endustri for kelime in ["airline", "airport"]) or ticker in ["THYAO.IS", "PGSUS.IS"]:
            olaylar.append(
                {
                    "ad": "DHMİ Yolcu ve Trafik Verileri",
                    "tarih": sonraki_ay_gunu(10),
                    "durum": "Yolcu sayısı, dış hat trafiği ve doluluk trendi izlenir.",
                    "beklenti": "Sezonluk trafik ve kapasite beklentileriyle karşılaştırılır.",
                    "etki": "Pozitif",
                    "senaryo_ustu": "Beklentiden güçlü trafik, ciro ve kapasite kullanımını destekleyerek havacılık hisseleri için pozitif olabilir.",
                    "senaryo_alti": "Zayıf trafik veya doluluk, gelir beklentilerini aşağı çekerek negatif fiyatlanabilir.",
                    "kaynak": "DHMİ istatistikleri",
                }
            )
    else:
        olaylar = [
            {
                "ad": "FED Faiz Kararı",
                "tarih": sonraki_hafta_gunu(2, 3),
                "durum": "Fed fonlama faizi ve karar metni takip edilir.",
                "beklenti": "Piyasa beklentisi vadeli faiz kontratlarıyla şekillenir.",
                "etki": "Nötr",
                "senaryo_ustu": "Beklentiden şahin duruş, büyüme hisselerinde değerleme baskısı yaratabilir.",
                "senaryo_alti": "Beklentiden güvercin duruş, risk iştahı ve büyüme hisseleri için destekleyici olabilir.",
                "kaynak": "FOMC takvimi",
            },
            {
                "ad": "ABD Enflasyon (CPI)",
                "tarih": sonraki_ay_gunu(13),
                "durum": "Çekirdek ve manşet CPI trendi izlenir.",
                "beklenti": "Konsensüs aylık/yıllık CPI beklentisiyle karşılaştırılır.",
                "etki": "Nötr",
                "senaryo_ustu": "Beklentiden yüksek CPI, faizlerin yüksek kalacağı algısıyla hisse piyasasını baskılayabilir.",
                "senaryo_alti": "Beklentiden düşük CPI, faiz indirimi beklentisini artırarak pozitif etki yaratabilir.",
                "kaynak": "ABD CPI takvimi",
            },
            {
                "ad": "Tarım Dışı İstihdam",
                "tarih": sonraki_hafta_gunu(4),
                "durum": "İstihdam artışı, ücret büyümesi ve işsizlik oranı izlenir.",
                "beklenti": "Konsensüs istihdam beklentisiyle karşılaştırılır.",
                "etki": "Nötr",
                "senaryo_ustu": "Çok güçlü veri, faiz baskısını artırabilir; döngüsel sektörlerde karışık etki yaratabilir.",
                "senaryo_alti": "Zayıf veri, faiz indirimi beklentisini artırsa da büyüme endişesi doğurabilir.",
                "kaynak": "BLS ekonomik takvimi",
            },
        ]

    return sorted(olaylar, key=lambda olay: olay["tarih"])[:5]


def kritik_tarihler_goster(veri: dict) -> None:
    st.markdown("### Kritik Tarihler ve Stratejik Etki Analizi")
    st.caption(
        "Bu bölüm seçilen hissenin ülke ve faaliyet alanına göre kural tabanlı ekonomik/stratejik olayları listeler. "
        "Tarih ve beklentiler resmi takvimlerle teyit edilmelidir."
    )

    for olay in kritik_olaylar_uret(veri):
        etki = olay["etki"]
        renk = olay_etki_rengi(etki)
        tarih = olay["tarih"].strftime("%d.%m.%Y")
        with st.expander(f"{olay_etki_ikon(etki)} {olay['ad']} - {tarih}", expanded=False):
            st.markdown(
                f"""
                <div class="event-impact" style="border-color:{renk};">
                    <span style="background:{renk};">{escape(etki)} Etki</span>
                    <p><strong>Mevcut Durum:</strong> {escape(olay['durum'])}</p>
                    <p><strong>Beklenti:</strong> {escape(olay['beklenti'])}</p>
                    <p><strong>Senaryo A - Beklenti Üstü:</strong> {escape(olay['senaryo_ustu'])}</p>
                    <p><strong>Senaryo B - Beklenti Altı:</strong> {escape(olay['senaryo_alti'])}</p>
                    <small>Kaynak mantığı: {escape(olay['kaynak'])}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )


def kritik_emtialari_sec(veri: dict) -> list[tuple[str, str]]:
    ticker = veri["ticker"].upper()
    if ticker in EMTIA_HARITASI:
        return EMTIA_HARITASI[ticker]

    metin = " ".join(
        [
            metin_norm(veri.get("sektor")),
            metin_norm(veri.get("endustri")),
            metin_norm(veri.get("sirket_adi")),
        ]
    )
    for anahtarlar, emtialar in SEKTOR_EMTIA_HARITASI:
        if any(anahtar in metin for anahtar in anahtarlar):
            return emtialar
    return [("ABD 10Y Tahvil", "^TNX"), ("Dolar Endeksi", "DX-Y.NYB")]


@st.cache_data(ttl=900, show_spinner=False)
def emtia_snapshot_getir(semboller: tuple[tuple[str, str], ...]) -> list[dict]:
    sonuc = []
    for ad, sembol in semboller:
        try:
            gecmis = yf.Ticker(sembol).history(period="1mo", interval="1d")
            kapanis = gecmis["Close"].dropna() if not gecmis.empty else pd.Series(dtype=float)
            son = float(kapanis.iloc[-1]) if not kapanis.empty else None
            ilk = float(kapanis.iloc[0]) if len(kapanis) > 1 else None
            degisim = ((son - ilk) / ilk) * 100 if son is not None and ilk else None
        except Exception:
            son = None
            degisim = None
        sonuc.append(
            {
                "ad": ad,
                "sembol": sembol,
                "son": son,
                "aylik_degisim": degisim,
            }
        )
    return sonuc


def makro_veri_getir(ulke: str | None) -> dict:
    ulke = ulke or ""
    if "turkey" in ulke.lower() or "turkiye" in ulke.lower():
        return MAKRO_VERI["Turkey"]
    if "united states" in ulke.lower() or "usa" in ulke.lower():
        return MAKRO_VERI["United States"]
    return {
        "faiz": "Ulke politika faizi: veri kaynagi bagli degil",
        "enflasyon": "Ulke enflasyonu: veri kaynagi bagli degil",
        "not": "Makro veri resmi kaynakla teyit edilmelidir.",
    }


def openai_api_key_getir() -> str | None:
    try:
        secret_key = st.secrets.get("OPENAI_API_KEY")
        if secret_key:
            return str(secret_key)
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY")


def ai_prompt_hazirla(veri: dict, emtialar: list[dict], makro: dict) -> str:
    emtia_satirlari = "\n".join(
        [
            f"- {item['ad']} ({item['sembol']}): son={sayi_formatla(item['son'])}, 1 aylik degisim={yuzde_formatla(item['aylik_degisim'])}"
            for item in emtialar
        ]
    )
    return f"""
Hisse Bilgileri:
- Ticker: {veri['ticker']}
- Sirket: {veri['sirket_adi']}
- Ulke: {veri.get('ulke') or 'Veri yok'}
- Sektor: {veri.get('sektor') or 'Veri yok'}
- Endustri: {veri.get('endustri') or 'Veri yok'}
- Mevcut fiyat: {sayi_formatla(veri.get('guncel_fiyat'), veri.get('para_birimi') or '')}
- F/K: {oran_formatla(veri.get('fk'))}
- PD/DD: {oran_formatla(veri.get('pd_dd'))}
- Borc/Ozsermaye: {oran_formatla(veri.get('borc_ozsermaye'))}
- Cari oran: {oran_formatla(veri.get('cari_oran'))}

Dis Veriler / Kritik Emtialar:
{emtia_satirlari or '- Veri yok'}

Makro Veri:
- Faiz: {makro.get('faiz')}
- Enflasyon: {makro.get('enflasyon')}
- Not: {makro.get('not')}

Gorev:
Asagidaki 3 zaman dilimi icin net bir stratejik analiz uret:
1) 1 Haftalik: Haber akisi, teknik momentum ve haftalik ekonomik takvim etkileri.
2) 1 Aylik: Sektorel trendler ve beklenen emtia fiyat hareketleri.
3) 1 Yillik: Sirket yatirim projeleri, ulke buyume beklentisi ve enflasyon/faiz korelasyonu.

Ciktiyi yalnizca gecerli JSON olarak ver. Markdown kullanma.
Format:
{{
  "bir_hafta": {{"tahmin": "...", "guven_skoru": 0, "neden": "...", "baskin_dayanak": "..."}},
  "bir_ay": {{"tahmin": "...", "guven_skoru": 0, "neden": "...", "baskin_dayanak": "..."}},
  "bir_yil": {{"tahmin": "...", "guven_skoru": 0, "neden": "...", "baskin_dayanak": "..."}},
  "analiz_dayanagi": "..."
}}
"""


def openai_analiz_iste(prompt: str) -> dict:
    api_key = openai_api_key_getir()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY bulunamadi. Streamlit secrets veya ortam degiskeni olarak ekleyin.")

    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4.1"),
        "instructions": (
            "Sen profesyonel bir global yatirim stratejistisin. "
            "Belirsiz ifadelerden kacin, eldeki somut ekonomik verilerle hisse fiyati arasinda "
            "mantiksal kopruler kur. Ornek: Petrol artisi rafineri marjini hangi yonde etkiler, "
            "bunu net ifade et. Yatirim tavsiyesi verme; riskleri belirt."
        ),
        "input": prompt,
        "max_output_tokens": 1200,
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))

    metin = data.get("output_text")
    if not metin:
        parcalar = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in ["output_text", "text"]:
                    parcalar.append(content.get("text", ""))
        metin = "\n".join(parcalar)
    return ai_yanitini_ayikla(metin or "")


def ai_yanitini_ayikla(metin: str) -> dict:
    temiz = metin.strip()
    temiz = re.sub(r"^```(?:json)?", "", temiz).strip()
    temiz = re.sub(r"```$", "", temiz).strip()
    try:
        return json.loads(temiz)
    except Exception:
        return {
            "bir_hafta": {
                "tahmin": "Analiz metni ayrisamadi",
                "guven_skoru": 0,
                "neden": temiz[:500] or "Model yaniti bos geldi.",
                "baskin_dayanak": "Veri yok",
            },
            "bir_ay": {"tahmin": "Veri yok", "guven_skoru": 0, "neden": "Veri yok", "baskin_dayanak": "Veri yok"},
            "bir_yil": {"tahmin": "Veri yok", "guven_skoru": 0, "neden": "Veri yok", "baskin_dayanak": "Veri yok"},
            "analiz_dayanagi": "Model yaniti JSON formatinda alinamadi.",
        }


def ai_kart_html(baslik: str, veri: dict) -> str:
    guven = puan_sinirla(veri.get("guven_skoru", 0))
    return f"""
    <div class="ai-card">
        <div class="ai-card-top">
            <span>{escape(baslik)}</span>
            <strong>%{guven}</strong>
        </div>
        <h4>{escape(str(veri.get('tahmin') or 'Veri yok'))}</h4>
        <p>{escape(str(veri.get('neden') or 'Veri yok'))}</p>
        <small>Dayanak: {escape(str(veri.get('baskin_dayanak') or 'Veri yok'))}</small>
    </div>
    """


def ai_stratejik_analiz_goster(veri: dict) -> None:
    st.markdown("### AI Stratejik Analiz")
    st.caption("Analiz yalnizca butona bastiginizda calisir; normal sayfa acilisini yavaslatmaz.")

    if st.button("Yapay Zeka Analizini Baslat", type="primary", use_container_width=False):
        with st.spinner("AI stratejik analiz hazirlaniyor..."):
            emtialar = emtia_snapshot_getir(tuple(kritik_emtialari_sec(veri)))
            makro = makro_veri_getir(veri.get("ulke"))
            prompt = ai_prompt_hazirla(veri, emtialar, makro)
            try:
                sonuc = openai_analiz_iste(prompt)
            except Exception as hata:
                st.warning(str(hata))
                with st.expander("AI'ya gonderilecek prompt", expanded=False):
                    st.code(prompt, language="text")
                return

        st.markdown(
            """
            <style>
                .ai-grid {
                    display: grid;
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                    gap: 0.9rem;
                    margin-top: 0.8rem;
                }
                .ai-card {
                    background: rgba(15, 23, 42, 0.74);
                    border: 1px solid rgba(56, 189, 248, 0.24);
                    border-radius: 8px;
                    padding: 1rem;
                    min-height: 220px;
                }
                .ai-card-top {
                    display: flex;
                    justify-content: space-between;
                    gap: 0.75rem;
                    color: #cbd5e1;
                    font-size: 0.82rem;
                    font-weight: 800;
                }
                .ai-card-top strong {
                    color: #0f172a;
                    background: #67e8f9;
                    border-radius: 999px;
                    padding: 0.12rem 0.5rem;
                }
                .ai-card h4 {
                    color: #f8fafc;
                    margin: 0.8rem 0 0.55rem;
                    font-size: 1.05rem;
                }
                .ai-card p {
                    color: #dbeafe;
                    line-height: 1.48;
                    margin: 0 0 0.75rem;
                }
                .ai-card small {
                    color: #93c5fd;
                    font-weight: 800;
                }
                .ai-basis {
                    margin-top: 0.9rem;
                    padding: 0.85rem 1rem;
                    border-radius: 8px;
                    background: rgba(2, 6, 23, 0.44);
                    border: 1px solid rgba(148, 163, 184, 0.18);
                    color: #dbeafe;
                }
                @media (max-width: 768px) {
                    .ai-grid { grid-template-columns: 1fr; }
                }
            </style>
            """,
            unsafe_allow_html=True,
        )
        ai_html = "".join(
            [
                '<div class="ai-grid">',
                ai_kart_html("1 Haftalik", sonuc.get("bir_hafta", {})),
                ai_kart_html("1 Aylik", sonuc.get("bir_ay", {})),
                ai_kart_html("1 Yillik", sonuc.get("bir_yil", {})),
                "</div>",
                '<div class="ai-basis">',
                "<strong>Analiz Dayanagi</strong><br>",
                escape(str(sonuc.get("analiz_dayanagi") or "Veri yok")),
                "</div>",
            ]
        )
        ai_html = re.sub(r"\n\s+<", "\n<", ai_html).strip()
        st.markdown(ai_html, unsafe_allow_html=True)


def puan_sinirla(deger: float) -> int:
    if deger is None or pd.isna(deger) or not math.isfinite(float(deger)):
        return 0
    return int(max(0, min(100, round(deger))))


def ortalama(degerler: list[float | None]) -> float | None:
    temiz = [
        float(deger)
        for deger in degerler
        if deger is not None and not pd.isna(deger) and math.isfinite(float(deger))
    ]
    if not temiz:
        return None
    return sum(temiz) / len(temiz)


@st.cache_data(ttl=3600, show_spinner=False)
def temel_info_hizli_getir(ticker: str) -> dict:
    info = yf.Ticker(ticker).info
    return {
        "ticker": ticker.upper(),
        "shortName": info.get("shortName"),
        "longName": info.get("longName"),
        "sector": info.get("sector"),
        "marketCap": info.get("marketCap"),
        "currency": info.get("currency"),
        "exchange": info.get("exchange") or info.get("fullExchangeName") or "",
        "industry": info.get("industry"),
        "website": info.get("website"),
        "summary": info.get("longBusinessSummary"),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def temel_info_getir(ticker: str) -> dict:
    info = yf.Ticker(ticker).info
    fk, pd_dd = guvenilir_fk_pd_dd(ticker, info)
    return {
        "ticker": ticker.upper(),
        "shortName": info.get("shortName"),
        "longName": info.get("longName"),
        "sector": info.get("sector"),
        "marketCap": info.get("marketCap"),
        "currency": info.get("currency"),
        "trailingPE": fk,
        "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
        "targetMedianPrice": info.get("targetMedianPrice"),
        "priceToBook": pd_dd,
        "earningsGrowth": info.get("earningsGrowth"),
        "earningsQuarterlyGrowth": info.get("earningsQuarterlyGrowth"),
        "returnOnEquity": info.get("returnOnEquity"),
        "revenueGrowth": info.get("revenueGrowth"),
        "debtToEquity": info.get("debtToEquity"),
        "currentRatio": info.get("currentRatio"),
        "dividendYield": info.get("dividendYield"),
        "payoutRatio": info.get("payoutRatio"),
        "exchange": info.get("exchange") or info.get("fullExchangeName") or "",
        "industry": info.get("industry"),
        "website": info.get("website"),
        "summary": info.get("longBusinessSummary"),
    }


@st.cache_data(ttl=86400, show_spinner=False)
def bes_yillik_gecmis_ortalamalari(ticker: str) -> dict:
    try:
        hisse = yf.Ticker(ticker)
        finansallar = hisse.financials
        bilanco = hisse.balance_sheet
        roe_degerleri = []
        gelir_buyumeleri = []

        if not finansallar.empty and not bilanco.empty:
            net_kar = finansallar.loc["Net Income"] if "Net Income" in finansallar.index else pd.Series(dtype=float)
            gelir = finansallar.loc["Total Revenue"] if "Total Revenue" in finansallar.index else pd.Series(dtype=float)
            ozsermaye_satiri = None
            for aday in ["Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity"]:
                if aday in bilanco.index:
                    ozsermaye_satiri = bilanco.loc[aday]
                    break

            if ozsermaye_satiri is not None:
                for tarih in net_kar.index[:5]:
                    if tarih in ozsermaye_satiri.index and ozsermaye_satiri[tarih]:
                        roe_degerleri.append(float(net_kar[tarih]) / float(ozsermaye_satiri[tarih]))

            gelir = gelir.dropna()
            for i in range(min(5, len(gelir) - 1)):
                onceki = float(gelir.iloc[i + 1])
                if onceki:
                    gelir_buyumeleri.append((float(gelir.iloc[i]) - onceki) / onceki)

        return {
            "roe_5y": ortalama(roe_degerleri),
            "revenue_growth_5y": ortalama(gelir_buyumeleri),
        }
    except Exception:
        return {"roe_5y": None, "revenue_growth_5y": None}


def rakip_etiketi(info: dict) -> str:
    borsa = info.get("exchange") or "Borsa"
    return f"{borsa}:{info['ticker']}"


def metin_norm(metin: str | None) -> str:
    return (metin or "").strip().lower()


def endustri_uyumlu_mu(ana_endustri: str | None, aday_endustri: str | None) -> bool:
    ana = metin_norm(ana_endustri)
    aday = metin_norm(aday_endustri)
    if not ana or not aday:
        return False
    return ana == aday


def anahtar_kelime_uyumlu_mu(ticker: str, aday_info: dict) -> bool:
    anahtarlar = RAKIP_ANAHTAR_KELIMELERI.get(ticker.upper())
    if not anahtarlar:
        return True

    metin = " ".join(
        [
            metin_norm(aday_info.get("industry")),
            metin_norm(aday_info.get("sector")),
            metin_norm(aday_info.get("shortName")),
            metin_norm(aday_info.get("longName")),
        ]
    )
    return any(anahtar in metin for anahtar in anahtarlar)


@st.cache_data(ttl=3600, show_spinner=False)
def rakipleri_bul(
    ticker: str,
    sektor: str | None,
    endustri: str | None,
    piyasa_degeri: float | None,
    para_birimi: str | None,
) -> list[dict]:
    ticker = ticker.upper()
    oneri_listesi = RAKIP_ONERILERI.get(ticker, [])
    evren = [] if oneri_listesi else (BIST_EVRENI if ticker.endswith(".IS") else GLOBAL_EVRENI)
    adaylar = list(dict.fromkeys(oneri_listesi + evren))
    rakipler = []
    ana_piyasa_degeri_usd = piyasa_degerini_usd_cevir(piyasa_degeri, para_birimi)

    for aday in adaylar:
        if aday == ticker:
            continue
        try:
            info = temel_info_hizli_getir(aday)
        except Exception:
            continue

        aday_sektor = info.get("sector")
        aday_endustri = info.get("industry")
        aday_piyasa_degeri = info.get("marketCap")
        if not aday_piyasa_degeri:
            continue
        aday_piyasa_degeri_usd = piyasa_degerini_usd_cevir(aday_piyasa_degeri, info.get("currency"))

        sektor_uyumu = metin_norm(sektor) and metin_norm(aday_sektor) == metin_norm(sektor)
        endustri_uyumu = endustri_uyumlu_mu(endustri, aday_endustri)
        oneri_uyumu = aday in oneri_listesi
        if not endustri_uyumu and not oneri_uyumu:
            continue
        if not anahtar_kelime_uyumlu_mu(ticker, info):
            continue

        if ana_piyasa_degeri_usd and aday_piyasa_degeri_usd and ana_piyasa_degeri_usd > 0 and aday_piyasa_degeri_usd > 0:
            yakinlik = abs(math.log(aday_piyasa_degeri_usd / ana_piyasa_degeri_usd))
        else:
            yakinlik = 99
        info["market_cap_distance"] = yakinlik
        info["peer_rank_market_cap"] = aday_piyasa_degeri_usd or aday_piyasa_degeri
        info["peer_rank_industry"] = 0 if endustri_uyumu else 1
        info["peer_rank_recommended"] = 0 if oneri_uyumu else 1
        info["peer_rank_sector"] = 0 if sektor_uyumu else 1
        rakipler.append(info)
        if oneri_listesi and len(rakipler) >= 6:
            break

    rakipler = sorted(
        rakipler,
        key=lambda item: (
            item["peer_rank_industry"],
            item["peer_rank_recommended"],
            item["market_cap_distance"],
            -item.get("peer_rank_market_cap", 0),
        ),
    )
    mesafe_haritasi = {rakip["ticker"]: rakip.get("market_cap_distance", 99) for rakip in rakipler}
    secim_havuzu = [rakip["ticker"] for rakip in rakipler[:8]]
    detayli_rakipler = []
    for secilen in secim_havuzu:
        try:
            detay = temel_info_getir(secilen)
            detay["trailingPE"] = oran_temizle(detay.get("trailingPE"), "fk")
            detay["priceToBook"] = oran_temizle(detay.get("priceToBook"), "pd_dd")
            detay["dividendYield"] = oran_temizle(detay.get("dividendYield"), "temettu")
            detay["peer_data_score"] = sum(
                deger is not None
                for deger in [
                    detay.get("trailingPE"),
                    detay.get("priceToBook"),
                    detay.get("dividendYield"),
                ]
            )
            detay["market_cap_distance"] = mesafe_haritasi.get(secilen, 99)
            detayli_rakipler.append(detay)
        except Exception:
            continue
    detayli_rakipler = sorted(
        detayli_rakipler,
        key=lambda item: (
            -item.get("peer_data_score", 0),
            item.get("market_cap_distance", 99),
        ),
    )
    return detayli_rakipler[:3]


def eksik_mi(*degerler) -> bool:
    return any(deger is None or pd.isna(deger) for deger in degerler)


def hisse_puanla(
    info: dict,
    peer_pe_avg: float | None,
    peer_dividend_avg: float | None,
    gecmis_ortalamalari: dict | None = None,
) -> tuple[dict[str, int], dict[str, bool], dict[str, str]]:
    eksikler = {}
    aciklamalar = {}
    pe = info.get("trailingPE")
    if pe and peer_pe_avg and pe > 0:
        degerleme = 50 + ((peer_pe_avg - pe) / peer_pe_avg) * 55
        eksikler["Değerleme"] = False
    else:
        degerleme = 50
        eksikler["Değerleme"] = True
    aciklamalar["Değerleme"] = (
        f"Firmanın F/K oranı {oran_formatla(pe)}, rakip ortalaması {oran_formatla(peer_pe_avg)} ile karşılaştırıldı."
        if not eksikler["Değerleme"]
        else "F/K veya rakip ortalaması eksik olduğu için değerleme puanı veri yetersiz olarak işaretlendi."
    )

    earnings_growth = info.get("earningsGrowth")
    revenue_growth = info.get("revenueGrowth")
    gelecek_bilesenleri = []
    if earnings_growth is not None:
        gelecek_bilesenleri.append(50 + earnings_growth * 110)
    if revenue_growth is not None:
        gelecek_bilesenleri.append(50 + revenue_growth * 120)
    gelecek = ortalama(gelecek_bilesenleri) if gelecek_bilesenleri else 0
    eksikler["Gelecek"] = not gelecek_bilesenleri
    aciklamalar["Gelecek"] = (
        f"Kazanç büyümesi {yuzde_formatla(earnings_growth * 100) if earnings_growth is not None else 'Veri Yok'} ve gelir büyümesi {yuzde_formatla(revenue_growth * 100) if revenue_growth is not None else 'Veri Yok'} birlikte puanlandı."
        if not eksikler["Gelecek"]
        else "earningsGrowth ve revenueGrowth verileri bulunamadı."
    )

    gecmis_ortalamalari = gecmis_ortalamalari or {}
    roe = gecmis_ortalamalari.get("roe_5y")
    if roe is None:
        roe = info.get("returnOnEquity")
    gecmis_bilesenleri = []
    if roe is not None:
        gecmis_bilesenleri.append(50 + roe * 150)
    gecmis = ortalama(gecmis_bilesenleri) if gecmis_bilesenleri else 0
    eksikler["Geçmiş"] = not gecmis_bilesenleri
    aciklamalar["Geçmiş"] = (
        f"Son yıllar ROE ortalaması {yuzde_formatla(roe * 100)} baz alınarak hesaplandı."
        if not eksikler["Geçmiş"]
        else "Son 5 yıllık ROE veya returnOnEquity verisi bulunamadı."
    )

    debt_to_equity = info.get("debtToEquity")
    current_ratio = info.get("currentRatio")
    saglik_bilesenleri = []
    if debt_to_equity is not None:
        saglik_bilesenleri.append(100 - min(100, debt_to_equity / 2))
    if current_ratio is not None:
        saglik_bilesenleri.append(min(100, current_ratio / 2 * 100))
    saglik = ortalama(saglik_bilesenleri) if saglik_bilesenleri else 0
    eksikler["Sağlık"] = not saglik_bilesenleri
    aciklamalar["Sağlık"] = (
        f"Borç/özkaynak {oran_formatla(debt_to_equity)} ve cari oran {oran_formatla(current_ratio)} ile finansal dayanıklılık puanlandı."
        if not eksikler["Sağlık"]
        else "debtToEquity ve currentRatio verileri bulunamadı."
    )

    dividend_yield = info.get("dividendYield")
    if dividend_yield is not None and peer_dividend_avg is not None:
        if peer_dividend_avg > 0:
            temettu = 50 + ((dividend_yield - peer_dividend_avg) / peer_dividend_avg) * 55
        else:
            temettu = min(100, dividend_yield * 1200)
        eksikler["Temettü"] = False
    else:
        temettu = 50
        eksikler["Temettü"] = True
    aciklamalar["Temettü"] = (
        f"Temettü verimi {yuzde_formatla(dividend_yield * 100)}, rakip ortalaması {yuzde_formatla(peer_dividend_avg * 100)} ile kıyaslandı."
        if not eksikler["Temettü"]
        else "Temettü verimi veya sektör/rakip ortalaması eksik."
    )

    puanlar = {
        "Değerleme": puan_sinirla(degerleme),
        "Gelecek": puan_sinirla(gelecek),
        "Geçmiş": puan_sinirla(gecmis),
        "Sağlık": puan_sinirla(saglik),
        "Temettü": puan_sinirla(temettu),
    }
    return puanlar, eksikler, aciklamalar


def referans_puan_ortalamasi(rakip_puanlari: list[dict[str, int]]) -> dict[str, int]:
    if not rakip_puanlari:
        return {kriter: 0 for kriter in ["Değerleme", "Gelecek", "Geçmiş", "Sağlık", "Temettü"]}
    return {
        kriter: puan_sinirla(ortalama([puanlar[kriter] for puanlar in rakip_puanlari]) or 0)
        for kriter in rakip_puanlari[0]
    }


def eksik_kriterleri_birlestir(eksikler: dict[str, bool]) -> list[str]:
    return [kriter for kriter, eksik in eksikler.items() if eksik]


def analiz_motoru_calistir(veri: dict) -> dict:
    ana_info = {
        "ticker": veri["ticker"],
        "sector": veri["sektor"],
        "marketCap": veri["piyasa_degeri"],
        "trailingPE": oran_temizle(veri["fk"], "fk"),
        "currentPrice": veri["guncel_fiyat"],
        "targetMedianPrice": veri["hedef_fiyat"],
        "earningsGrowth": veri["kazanc_buyumesi_yillik"],
        "earningsQuarterlyGrowth": veri["kazanc_buyumesi"],
        "returnOnEquity": veri["ozsermaye_karliligi"],
        "revenueGrowth": veri["gelir_buyumesi"],
        "debtToEquity": veri["borc_ozsermaye"],
        "currentRatio": veri["cari_oran"],
        "dividendYield": oran_temizle(veri["temettu_verimi"], "temettu"),
        "payoutRatio": veri["payout_orani"],
        "exchange": veri["borsa"],
        "industry": veri["endustri"],
        "currency": veri["para_birimi"],
    }
    rakipler = rakipleri_bul(
        veri["ticker"],
        veri["sektor"],
        veri["endustri"],
        veri["piyasa_degeri"],
        veri["para_birimi"],
    )
    for rakip in rakipler:
        rakip["trailingPE"] = oran_temizle(rakip.get("trailingPE"), "fk")
        rakip["priceToBook"] = oran_temizle(rakip.get("priceToBook"), "pd_dd")
        rakip["dividendYield"] = oran_temizle(rakip.get("dividendYield"), "temettu")

    peer_pe_avg = ortalama([rakip.get("trailingPE") for rakip in rakipler])
    peer_pb_avg = ortalama([rakip.get("priceToBook") for rakip in rakipler])
    peer_dividend_avg = ortalama([rakip.get("dividendYield") for rakip in rakipler])
    ana_gecmis = {
        "roe_5y": veri["ozsermaye_karliligi"],
        "revenue_growth_5y": veri["gelir_buyumesi"],
    }
    hisse_puanlari, eksikler, aciklamalar = hisse_puanla(
        ana_info,
        peer_pe_avg,
        peer_dividend_avg,
        ana_gecmis,
    )

    rakip_puanlari = []
    for rakip in rakipler:
        rakip_gecmis = {
            "roe_5y": rakip.get("returnOnEquity"),
            "revenue_growth_5y": rakip.get("revenueGrowth"),
        }
        rakip_puan, _, _ = hisse_puanla(rakip, peer_pe_avg, peer_dividend_avg, rakip_gecmis)
        rakip_puanlari.append(rakip_puan)

    return {
        "hisse": hisse_puanlari,
        "referans": referans_puan_ortalamasi(rakip_puanlari),
        "rakipler": [rakip_etiketi(rakip) for rakip in rakipler],
        "ref_list": [rakip["ticker"] for rakip in rakipler],
        "eksikler": eksik_kriterleri_birlestir(eksikler),
        "aciklamalar": aciklamalar,
        "peer_pe_avg": peer_pe_avg,
        "peer_pb_avg": peer_pb_avg,
        "peer_dividend_avg": peer_dividend_avg,
        "competitors": {
            "tickers": [rakip_etiketi(rakip) for rakip in rakipler],
            "items": [
                {
                    "ticker": rakip_etiketi(rakip),
                    "name": rakip.get("longName") or rakip.get("shortName") or rakip["ticker"],
                    "website": rakip.get("website"),
                    "summary": rakip.get("summary"),
                    "fk": rakip.get("trailingPE"),
                    "pd_dd": rakip.get("priceToBook"),
                    "temettu": rakip.get("dividendYield"),
                }
                for rakip in rakipler
            ],
            "averages": {
                "fk": peer_pe_avg,
                "pd_dd": peer_pb_avg,
                "temettu": peer_dividend_avg,
            },
        },
    }


def finansal_oran_bileseni(veri: dict, analiz_sonucu: dict) -> None:
    competitors = analiz_sonucu.get("competitors", {})
    averages = competitors.get("averages", {})
    competitor_items = competitors.get("items", [])[:3]
    skorlar = analiz_sonucu.get("hisse", {})
    aciklamalar = analiz_sonucu.get("aciklamalar", {})

    def peer_label(peer: dict, index: int) -> str:
        label = peer.get("ticker") or f"Rakip {index + 1}"
        return label.split(":")[-1]

    def peer_summary(peer: dict) -> str:
        summary = peer.get("summary") or "Firma açıklaması bulunamadı."
        return summary[:220] + ("..." if len(summary) > 220 else "")

    def peer_header_html(index: int) -> str:
        if index >= len(competitor_items):
            return f"<div>Rakip {index + 1}</div>"

        peer = competitor_items[index]
        label = peer_label(peer, index)
        name = peer.get("name") or label
        website = peer.get("website")
        website_html = (
            f'<a href="{escape(website, quote=True)}" target="_blank" rel="noopener noreferrer">Resmi site</a>'
            if website
            else "<span>Web sitesi yok</span>"
        )
        return "".join(
            [
                '<div class="peer-head" tabindex="0">',
                escape(label),
                '<div class="peer-popover">',
                f"<strong>{escape(name)}</strong>",
                f"<p>{escape(peer_summary(peer))}</p>",
                website_html,
                "</div>",
                "</div>",
            ]
        )

    peer_headers = [peer_label(peer, index) for index, peer in enumerate(competitor_items)]

    oranlar = [
        {
            "key": "fk",
            "score_key": "Değerleme",
            "label": "F/K",
            "value_raw": oran_temizle(veri["fk"], "fk"),
            "value": oran_formatla(oran_temizle(veri["fk"], "fk")),
            "peer_raw": averages.get("fk"),
            "peer": oran_formatla(averages.get("fk")),
            "peer_values": [oran_formatla(oran_temizle(peer.get("fk"), "fk")) for peer in competitor_items],
            "meaning": "Fiyat/Kazanç oranı, yatırımcının şirket karının her 1 birimi için kaç birim fiyat ödediğini gösterir.",
            "direction": "Düşük F/K, rakiplere göre daha iskontolu değerlemeye işaret edebilir.",
        },
        {
            "key": "pd_dd",
            "score_key": "Değerleme",
            "label": "PD/DD",
            "value_raw": oran_temizle(veri["pd_dd"], "pd_dd"),
            "value": oran_formatla(oran_temizle(veri["pd_dd"], "pd_dd")),
            "peer_raw": averages.get("pd_dd"),
            "peer": oran_formatla(averages.get("pd_dd")),
            "peer_values": [oran_formatla(oran_temizle(peer.get("pd_dd"), "pd_dd")) for peer in competitor_items],
            "meaning": "Piyasa Değeri/Defter Değeri oranı, şirketin özkaynaklarına göre piyasada kaç kat değer gördüğünü gösterir.",
            "direction": "Düşük PD/DD, varlık bazlı değerleme açısından daha ucuz görünebilir.",
        },
        {
            "key": "temettu",
            "score_key": "Temettü",
            "label": "Temettü",
            "value_raw": oran_temizle(veri["temettu_verimi"], "temettu"),
            "value": yuzde_formatla(oran_temizle(veri["temettu_verimi"], "temettu") * 100)
            if oran_temizle(veri["temettu_verimi"], "temettu") is not None
            else "Veri yok",
            "peer_raw": averages.get("temettu"),
            "peer": yuzde_formatla(averages.get("temettu") * 100) if averages.get("temettu") is not None else "Veri yok",
            "peer_values": [
                yuzde_formatla(oran_temizle(peer.get("temettu"), "temettu") * 100)
                if oran_temizle(peer.get("temettu"), "temettu") is not None
                else "Veri yok"
                for peer in competitor_items
            ],
            "meaning": "Temettü verimi, yıllık temettünün hisse fiyatına oranını gösterir.",
            "direction": "Yüksek temettü verimi nakit getiri potansiyeli sunar; sürdürülebilirlik için payout oranı da izlenmelidir.",
        },
    ]

    rows = []
    for oran in oranlar:
        value_raw = oran["value_raw"]
        peer_raw = oran["peer_raw"]
        score_key = oran["score_key"]
        score = skorlar.get(score_key)
        score_text = f"{score}/100" if score is not None else "Veri yok"
        score_note = aciklamalar.get(score_key, "Skor açıklaması için yeterli veri bulunamadı.")
        peer_cells = oran["peer_values"][:3]
        while len(peer_cells) < 3:
            peer_cells.append("Veri yok")

        if value_raw is None or peer_raw is None or pd.isna(value_raw) or pd.isna(peer_raw):
            comparison = "Karşılaştırma için veri yetersiz."
            badge = "Veri Yetersiz"
        else:
            fark = float(value_raw) - float(peer_raw)
            if oran["key"] in ["fk", "pd_dd"]:
                daha_iyi = fark < 0
                badge = "İskontolu" if daha_iyi else "Primli"
            else:
                daha_iyi = fark > 0
                badge = "Üstünde" if daha_iyi else "Altında"
            comparison = f"Hisse değeri {oran['value']}; seçilen rakiplerin ortalaması {oran['peer']}. {badge} görünüm."

        peer_text = ", ".join(peer_headers) or "Veri Yok"
        rows.append(
            "".join(
                [
                    '<div class="ratio-row" tabindex="0">',
                    f'<div class="ratio-name">{escape(oran["label"])}</div>',
                    f'<div class="ratio-value">{escape(oran["value"])}</div>',
                    f'<div class="ratio-peer-cell">{escape(peer_cells[0])}</div>',
                    f'<div class="ratio-peer-cell">{escape(peer_cells[1])}</div>',
                    f'<div class="ratio-peer-cell">{escape(peer_cells[2])}</div>',
                    f'<div class="ratio-average">{escape(oran["peer"])}</div>',
                    '<div class="ratio-note">',
                    '<span class="ratio-badge-wrap" tabindex="0">',
                    f'<span class="ratio-badge">{escape(badge)}</span>',
                    '<div class="ratio-popover">',
                    f'<strong>{escape(oran["label"])} - {escape(badge)}</strong>',
                    f"<p>{escape(oran['meaning'])}</p>",
                    f"<p>{escape(comparison)}</p>",
                    f"<p>{escape(oran['direction'])}</p>",
                    f"<p><strong>{escape(score_key)} skoru:</strong> {escape(score_text)}</p>",
                    f"<p>{escape(score_note)}</p>",
                    f"<small>Rakipler: {escape(peer_text)}</small>",
                    "</div>",
                    "</span>",
                    "</div>",
                    "</div>",
                ]
            )
        )

    html = textwrap.dedent(
        f"""
        <style>
            .ratio-card {{
                background: rgba(15, 23, 42, 0.72);
                border: 1px solid rgba(148, 163, 184, 0.24);
                border-radius: 8px;
                overflow: visible;
                margin-top: 0.5rem;
            }}

            .ratio-head,
            .ratio-row {{
                display: grid;
                grid-template-columns:
                    minmax(78px, 0.75fr)
                    minmax(84px, 0.78fr)
                    repeat(3, minmax(82px, 0.78fr))
                    minmax(82px, 0.78fr)
                    minmax(96px, 0.9fr);
                gap: 0.65rem;
                align-items: center;
                padding: 0.85rem 1rem;
            }}

            .ratio-head {{
                color: #cbd5e1;
                font-size: 0.78rem;
                font-weight: 800;
                background: rgba(248, 250, 252, 0.06);
                border-bottom: 1px solid rgba(148, 163, 184, 0.18);
            }}

            .peer-head {{
                position: relative;
                display: inline-flex;
                width: fit-content;
                max-width: 100%;
                color: #dbeafe;
                border-bottom: 1px dotted rgba(219, 234, 254, 0.7);
                cursor: help;
                outline: none;
            }}

            .peer-popover {{
                display: none;
                position: absolute;
                z-index: 35;
                left: 0;
                top: calc(100% + 0.45rem);
                width: min(340px, 72vw);
                padding: 0.9rem;
                background: #f8fafc;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                box-shadow: 0 18px 46px rgba(0, 0, 0, 0.32);
            }}

            .peer-popover strong {{
                display: block;
                margin-bottom: 0.35rem;
                color: #0f172a;
            }}

            .peer-popover p {{
                margin: 0 0 0.55rem 0;
                color: #334155;
                line-height: 1.42;
                font-size: 0.86rem;
            }}

            .peer-popover a,
            .peer-popover span {{
                color: #0369a1;
                font-weight: 800;
                text-decoration: none;
            }}

            .peer-head:hover .peer-popover,
            .peer-head:focus .peer-popover,
            .peer-head:focus-within .peer-popover {{
                display: block;
            }}

            .ratio-row {{
                position: relative;
                border-bottom: 1px solid rgba(148, 163, 184, 0.14);
            }}

            .ratio-row:last-child {{ border-bottom: 0; }}

            .ratio-row:hover,
            .ratio-row:focus {{
                background: rgba(56, 189, 248, 0.08);
                outline: none;
            }}

            .ratio-name,
            .ratio-value,
            .ratio-peer-cell,
            .ratio-average {{
                color: #f8fafc;
                font-weight: 800;
            }}

            .ratio-peer-cell,
            .ratio-average {{
                color: #dbeafe;
                font-size: 0.92rem;
            }}

            .ratio-note {{
                display: flex;
                justify-content: center;
                align-items: center;
            }}

            .ratio-badge-wrap {{
                position: relative;
                display: inline-flex;
                align-items: center;
                outline: none;
            }}

            .ratio-badge {{
                font-size: 0.72rem;
                color: #0f172a;
                background: #f8fafc;
                border-radius: 999px;
                padding: 0.18rem 0.5rem;
                white-space: nowrap;
            }}

            .ratio-popover {{
                display: none;
                position: absolute;
                z-index: 30;
                right: 0;
                top: 50%;
                transform: translateY(-50%);
                width: min(390px, 82vw);
                padding: 0.9rem;
                background: #f8fafc;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                box-shadow: 0 18px 46px rgba(0, 0, 0, 0.32);
            }}

            .ratio-popover strong {{
                display: block;
                margin-bottom: 0.35rem;
                color: #0f172a;
            }}

            .ratio-popover p {{
                margin: 0 0 0.45rem 0;
                color: #334155;
                line-height: 1.42;
                font-size: 0.88rem;
            }}

            .ratio-popover small {{
                color: #64748b;
                font-weight: 700;
            }}

            .ratio-badge-wrap:hover .ratio-popover,
            .ratio-badge-wrap:focus .ratio-popover,
            .ratio-badge-wrap:focus-within .ratio-popover {{
                display: block;
            }}

            @media (max-width: 768px) {{
                .ratio-card {{
                    overflow-x: auto;
                }}

                .ratio-head,
                .ratio-row {{
                    min-width: 760px;
                    padding: 0.75rem;
                }}

                .ratio-popover {{
                    right: 0;
                    top: calc(100% + 0.35rem);
                    transform: none;
                    width: auto;
                }}
            }}
        </style>
        <div class="ratio-card">
            <div class="ratio-head">
                <div>Oran</div>
                <div>Hisse</div>
                {peer_header_html(0)}
                {peer_header_html(1)}
                {peer_header_html(2)}
                <div>Ort.</div>
                <div>Durum</div>
            </div>
            {''.join(rows)}
        </div>
        """
    )
    html = re.sub(r"\n\s+<", "\n<", html).strip()
    st.markdown(html, unsafe_allow_html=True)


with st.sidebar:
    st.title("Hisse Paneli")
    profil_senkronize()

    if st.session_state.ticker_secimi_bekleyen:
        st.session_state.ticker_secimi = st.session_state.ticker_secimi_bekleyen
        st.session_state.ticker_secimi_ana = st.session_state.ticker_secimi_bekleyen
        st.session_state.ticker_secimi_bekleyen = None

    sidebar_ticker = st.selectbox(
        "Hisse kodu",
        options=ONERILEN_HISSELER,
        index=None,
        accept_new_options=True,
        placeholder="Hisse seçiniz",
        key="ticker_secimi",
    )

    aktif_aday = str(sidebar_ticker).strip().upper() if sidebar_ticker else ""
    buton_col, favori_col = st.columns([0.78, 0.22])
    getir = buton_col.button("Verileri Getir", type="primary", use_container_width=True)

    if favori_col.button(
        "★" if aktif_aday in st.session_state.favoriler else "☆",
        help="Bu hisseyi favorilere ekle veya çıkar",
        use_container_width=True,
        disabled=not aktif_aday,
    ):
        favori_degistir(aktif_aday)
        st.rerun()

    if st.session_state.favoriler:
        with st.expander("Favoriler", expanded=False):
            st.caption("Favori hisseleriniz burada saklanır.")
            with st.container(height=240):
                for favori in st.session_state.favoriler[:20]:
                    ticker_satiri(favori, "favorite")

    with st.expander("Geçmiş", expanded=False):
        if st.session_state.hisse_gecmisi:
            st.caption("Son 20 hisse saklanır; liste uzadığında kaydırarak seçebilirsiniz.")
            with st.container(height=300):
                for kod in st.session_state.hisse_gecmisi:
                    ticker_satiri(kod, "history")
        else:
            st.caption("Aradığınız hisseler burada görünür.")

    st.divider()
    st.caption("BIST hisseleri için `.IS` uzantısını kullanın.")


mobil_gorunum = st.toggle(
    "Mobil görünüm",
    value=False,
    help="Telefon ekranında daha sıkı ve okunaklı bir düzen kullanır.",
)

st.title("Hisse Analiz Paneli")

st.markdown('<div class="mobile-picker">', unsafe_allow_html=True)
main_ticker = st.selectbox(
    "Hisse kodu",
    options=ONERILEN_HISSELER,
    index=None,
    accept_new_options=True,
    placeholder="Hisse seçiniz",
    key="ticker_secimi_ana",
)
st.markdown("</div>", unsafe_allow_html=True)

ticker = main_ticker or sidebar_ticker

if not ticker or not str(ticker).strip():
    st.info("Başlamak için üstteki alandan veya sol panelden bir hisse kodu girin.")
    st.stop()


aktif_ticker = str(ticker).strip().upper()
gecmise_ekle(aktif_ticker)

grafik_baslik = st.segmented_control(
    "Grafik dönemi",
    options=list(DONEMLER.keys()),
    default="1 Yıl",
    label_visibility="collapsed",
)
grafik_ayar = DONEMLER[grafik_baslik]

try:
    with st.spinner(f"{aktif_ticker} verileri alınıyor..."):
        veri = hisse_bilgisi_getir(
            aktif_ticker,
            grafik_ayar["period"],
            grafik_ayar["interval"],
        )
except Exception as hata:
    st.error("Veriler alınamadı. Hisse kodunu kontrol edip tekrar deneyin.")
    st.caption(str(hata))
    st.stop()


gecmis = veri["gecmis"]
if gecmis.empty:
    st.warning("Bu hisse için fiyat geçmişi bulunamadı.")
    st.stop()


para_birimi = veri["para_birimi"] or ""
usd_destekli = para_birimi in USD_CEVRIMLERI
usd_modu = bool(para_birimi and para_birimi != "USD" and usd_destekli)
kur = None
kur_serisi = None

if usd_modu:
    kur, kur_serisi = kur_verisi_getir(
        para_birimi,
        grafik_ayar["period"],
        grafik_ayar["interval"],
    )
    if kur is None:
        st.warning("USD dönüşümü için kur verisi alınamadı; değerler yerel para biriminde gösteriliyor.")
        usd_modu = False
elif para_birimi and para_birimi != "USD":
    st.caption(f"{para_birimi} için otomatik USD dönüşümü desteklenmediği için değerler yerel para biriminde gösteriliyor.")


guncel_fiyat = veri["guncel_fiyat"]
onceki_kapanis = veri["onceki_kapanis"]
temettu_tutari = veri["temettu_tutari"]
gosterim_para_birimi = "USD" if usd_modu else para_birimi

if usd_modu:
    guncel_fiyat = usd_degere_cevir(guncel_fiyat, kur, para_birimi)
    onceki_kapanis = usd_degere_cevir(onceki_kapanis, kur, para_birimi)
    temettu_tutari = usd_degere_cevir(temettu_tutari, kur, para_birimi)

degisim_orani = None
if guncel_fiyat is not None and onceki_kapanis:
    degisim_orani = ((guncel_fiyat - onceki_kapanis) / onceki_kapanis) * 100


st.subheader(veri["sirket_adi"])

metrik_1, metrik_2, metrik_3 = st.columns(1 if mobil_gorunum else 3)
metrik_1.metric(
    "Güncel Fiyat",
    sayi_formatla(guncel_fiyat, gosterim_para_birimi),
    delta=yuzde_formatla(degisim_orani) if degisim_orani is not None else None,
)
metrik_2.metric("Önceki Kapanış", sayi_formatla(onceki_kapanis, gosterim_para_birimi))
metrik_3.metric("Ticker", veri["ticker"])

with st.spinner("Rakipler ve finansal oranlar hesaplanıyor..."):
    analiz_sonucu = analiz_motoru_calistir(veri)

st.markdown("### Hisse Grafiği")
grafik_serisi = gecmis["Close"]
if usd_modu:
    grafik_serisi = usd_seriye_cevir(grafik_serisi, kur_serisi, para_birimi)

analist_tahminleri = analist_tahminleri_uret(veri, usd_modu, kur)

st.plotly_chart(
    grafik_olustur(
        grafik_serisi,
        gosterim_para_birimi,
        340 if mobil_gorunum else 440,
        analist_tahminleri,
    ),
    use_container_width=True,
    config={"displayModeBar": False, "scrollZoom": True},
)

analist_kaynaklari_goster(analist_tahminleri)

analist_beklentileri_goster(
    veri,
    guncel_fiyat,
    gosterim_para_birimi,
    usd_modu,
    kur,
    mobil_gorunum,
    analist_tahminleri,
)

ai_stratejik_analiz_goster(veri)

kritik_tarihler_goster(veri)

st.markdown("### Finansal Oranlar")
finansal_oran_bileseni(veri, analiz_sonucu)

temettu_df = temettu_gecmisi_getir(veri["ticker"])
temettu_kur_serisi = kur_serisi
if usd_modu:
    _, temettu_kur_serisi = kur_verisi_getir(para_birimi, "10y", "1d")
temettu_gecmisi_goster(temettu_df, para_birimi, usd_modu, temettu_kur_serisi)


with st.sidebar:
    st.toggle(
        "Şirket özetini göster",
        key="sirket_ozeti_goster",
        help="Bu tercih oturum boyunca hatırlanır.",
    )

    if st.session_state.sirket_ozeti_goster:
        with st.expander("Şirket Özeti", expanded=True):
            turkce_tab, ingilizce_tab = st.tabs(["Türkçe", "İngilizce"])
            with turkce_tab:
                st.write(turkce_ozet_getir(veri["ozet"]))
            with ingilizce_tab:
                st.write(veri["ozet"])
