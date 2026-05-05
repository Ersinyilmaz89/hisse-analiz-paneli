import json
import math
import sqlite3
import textwrap
from html import escape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

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

ANALIZ_EVRENI = sorted(
    set(
        ONERILEN_HISSELER
        + [
            "PATEK.IS", "MIATK.IS", "ASTOR.IS", "KONTR.IS", "CWENE.IS",
            "FROTO.IS", "TOASO.IS", "TTRAK.IS", "TCELL.IS", "TTKOM.IS",
            "SAHOL.IS", "MGROS.IS", "ULKER.IS", "PETKM.IS", "SASA.IS",
            "KRDMD.IS", "ISCTR.IS", "HALKB.IS", "VAKBN.IS", "ENKAI.IS",
            "KOZAL.IS", "PGSUS.IS", "DOAS.IS", "AEFES.IS", "CCOLA.IS",
            "ORCL", "ADBE", "CRM", "AVGO", "AMD", "INTC", "IBM",
            "NFLX", "DIS", "PYPL", "SHOP", "UBER", "ABNB", "JPM",
            "BAC", "WFC", "GS", "V", "MA", "XOM", "CVX", "SHEL",
            "BP", "KO", "PEP", "WMT", "COST", "HD", "NKE", "MCD",
        ]
    )
)

BIST_EVRENI = sorted([ticker for ticker in ANALIZ_EVRENI if ticker.endswith(".IS")])
GLOBAL_EVRENI = sorted([ticker for ticker in ANALIZ_EVRENI if not ticker.endswith(".IS")])

RAKIP_ONERILERI = {
    "AAPL": ["MSFT", "NVDA", "GOOGL", "META", "AMZN"],
    "MSFT": ["AAPL", "NVDA", "GOOGL", "ORCL", "ADBE"],
    "GOOGL": ["META", "AMZN", "MSFT", "AAPL", "NFLX"],
    "TUPRS.IS": ["PETKM.IS", "SASA.IS", "EREGL.IS", "KRDMD.IS", "FROTO.IS"],
    "THYAO.IS": ["PGSUS.IS", "TAVHL.IS", "DOAS.IS", "FROTO.IS", "TOASO.IS"],
    "ASELS.IS": ["KONTR.IS", "MIATK.IS", "PATEK.IS", "ASTOR.IS", "CWENE.IS"],
}

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

DB_PATH = Path("data") / "profiles.db"
DEMO_PROFILLER = ["Joker1", "Joker2"]


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

        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        #MainMenu,
        header,
        footer {
            visibility: hidden !important;
            height: 0 !important;
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
        }
    </style>
    """,
    unsafe_allow_html=True,
)


if "hisse_gecmisi" not in st.session_state:
    st.session_state.hisse_gecmisi = []

if "favoriler" not in st.session_state:
    st.session_state.favoriler = []

if "profil_email" not in st.session_state:
    st.session_state.profil_email = DEMO_PROFILLER[0]

if "aktif_profil" not in st.session_state:
    st.session_state.aktif_profil = None

if "ticker_secimi" not in st.session_state:
    st.session_state.ticker_secimi = None

if "ticker_secimi_bekleyen" not in st.session_state:
    st.session_state.ticker_secimi_bekleyen = None

if "sirket_ozeti_goster" not in st.session_state:
    st.session_state.sirket_ozeti_goster = True

if "Ref_List" not in st.session_state:
    st.session_state.Ref_List = []


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
    profil = (st.session_state.profil_email or DEMO_PROFILLER[0]).strip().lower()
    if st.session_state.aktif_profil != profil:
        st.session_state.aktif_profil = profil
        st.session_state.favoriler = favorileri_yukle(profil)


@st.cache_data(ttl=300, show_spinner=False)
def hisse_bilgisi_getir(ticker: str, period: str, interval: str) -> dict:
    hisse = yf.Ticker(ticker)
    info = hisse.info
    gecmis = hisse.history(period=period, interval=interval)

    return {
        "ticker": ticker.upper(),
        "sirket_adi": info.get("longName") or info.get("shortName") or ticker.upper(),
        "guncel_fiyat": info.get("currentPrice") or info.get("regularMarketPrice"),
        "onceki_kapanis": info.get("previousClose"),
        "fk": info.get("trailingPE"),
        "pd_dd": info.get("priceToBook"),
        "temettu_verimi": info.get("dividendYield"),
        "temettu_tutari": info.get("dividendRate"),
        "payout_orani": info.get("payoutRatio"),
        "hedef_fiyat": info.get("targetMedianPrice"),
        "kazanc_buyumesi": info.get("earningsQuarterlyGrowth"),
        "kazanc_buyumesi_yillik": info.get("earningsGrowth"),
        "ozsermaye_karliligi": info.get("returnOnEquity"),
        "gelir_buyumesi": info.get("revenueGrowth"),
        "borc_ozsermaye": info.get("debtToEquity"),
        "cari_oran": info.get("currentRatio"),
        "sektor": info.get("sector"),
        "endustri": info.get("industry"),
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


def gecmise_ekle(ticker: str) -> None:
    ticker = ticker.upper()
    mevcut = [kod for kod in st.session_state.hisse_gecmisi if kod != ticker]
    st.session_state.hisse_gecmisi = [ticker, *mevcut][:20]


def favori_degistir(ticker: str) -> None:
    ticker = ticker.upper()
    profil = st.session_state.aktif_profil or DEMO_PROFILLER[0].lower()
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


def grafik_olustur(grafik_serisi: pd.Series, para_birimi: str, yukseklik: int) -> go.Figure:
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
def temel_info_getir(ticker: str) -> dict:
    info = yf.Ticker(ticker).info
    return {
        "ticker": ticker.upper(),
        "sector": info.get("sector"),
        "marketCap": info.get("marketCap"),
        "trailingPE": info.get("trailingPE"),
        "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
        "targetMedianPrice": info.get("targetMedianPrice"),
        "priceToBook": info.get("priceToBook"),
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


@st.cache_data(ttl=3600, show_spinner=False)
def rakipleri_bul(ticker: str, sektor: str | None, endustri: str | None, piyasa_degeri: float | None) -> list[dict]:
    ticker = ticker.upper()
    evren = BIST_EVRENI if ticker.endswith(".IS") else GLOBAL_EVRENI
    adaylar = list(dict.fromkeys(RAKIP_ONERILERI.get(ticker, []) + evren + ANALIZ_EVRENI))
    rakipler = []

    for aday in adaylar:
        if aday == ticker:
            continue
        try:
            info = temel_info_getir(aday)
        except Exception:
            continue

        aday_sektor = info.get("sector")
        aday_endustri = info.get("industry")
        aday_piyasa_degeri = info.get("marketCap")
        if not aday_piyasa_degeri:
            continue

        sektor_uyumu = sektor and aday_sektor and aday_sektor.lower() == sektor.lower()
        endustri_uyumu = endustri and aday_endustri and aday_endustri.lower() == endustri.lower()
        oneri_uyumu = aday in RAKIP_ONERILERI.get(ticker, [])
        if not sektor_uyumu and not endustri_uyumu and not oneri_uyumu:
            continue

        if piyasa_degeri and aday_piyasa_degeri and piyasa_degeri > 0 and aday_piyasa_degeri > 0:
            yakinlik = abs(math.log(aday_piyasa_degeri / piyasa_degeri))
        else:
            yakinlik = 99
        info["market_cap_distance"] = yakinlik
        info["peer_rank_market_cap"] = aday_piyasa_degeri
        rakipler.append(info)

    rakipler = sorted(
        rakipler,
        key=lambda item: (
            0 if item.get("industry", "").lower() == (endustri or "").lower() else 1,
            -item.get("peer_rank_market_cap", 0),
            item["market_cap_distance"],
        ),
    )
    return rakipler[:3]


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
        "trailingPE": veri["fk"],
        "currentPrice": veri["guncel_fiyat"],
        "targetMedianPrice": veri["hedef_fiyat"],
        "earningsGrowth": veri["kazanc_buyumesi_yillik"],
        "earningsQuarterlyGrowth": veri["kazanc_buyumesi"],
        "returnOnEquity": veri["ozsermaye_karliligi"],
        "revenueGrowth": veri["gelir_buyumesi"],
        "debtToEquity": veri["borc_ozsermaye"],
        "currentRatio": veri["cari_oran"],
        "dividendYield": veri["temettu_verimi"],
        "payoutRatio": veri["payout_orani"],
        "exchange": veri["borsa"],
        "industry": veri["endustri"],
    }
    rakipler = rakipleri_bul(veri["ticker"], veri["sektor"], veri["endustri"], veri["piyasa_degeri"])
    peer_pe_avg = ortalama([rakip.get("trailingPE") for rakip in rakipler])
    peer_pb_avg = ortalama([rakip.get("priceToBook") for rakip in rakipler])
    peer_dividend_avg = ortalama([rakip.get("dividendYield") for rakip in rakipler])
    ana_gecmis = bes_yillik_gecmis_ortalamalari(veri["ticker"])
    hisse_puanlari, eksikler, aciklamalar = hisse_puanla(
        ana_info,
        peer_pe_avg,
        peer_dividend_avg,
        ana_gecmis,
    )

    rakip_puanlari = []
    for rakip in rakipler:
        rakip_gecmis = bes_yillik_gecmis_ortalamalari(rakip["ticker"])
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
            "averages": {
                "fk": peer_pe_avg,
                "pd_dd": peer_pb_avg,
                "temettu": peer_dividend_avg,
            },
        },
    }


def radar_chart_olustur(puanlar: dict[str, int], referans_puanlar: dict[str, int], rakipler: list[str], mobil: bool) -> go.Figure:
    kategoriler = list(puanlar.keys())
    degerler = list(puanlar.values())
    referans_degerler = [referans_puanlar.get(kategori, 0) for kategori in kategoriler]
    kapali_kategoriler = [*kategoriler, kategoriler[0]]
    kapali_degerler = [*degerler, degerler[0]]
    kapali_referans_degerler = [*referans_degerler, referans_degerler[0]]
    rakip_metni = f"Kıyaslanan Rakipler: {', '.join(rakipler) if rakipler else 'Veri Yok'}"

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=kapali_referans_degerler,
            theta=kapali_kategoriler,
            fill="toself",
            fillcolor="rgba(56, 189, 248, 0.16)",
            line={"color": "rgba(56, 189, 248, 0.72)", "width": 2},
            name="Referans",
            customdata=[rakip_metni] * len(kapali_kategoriler),
            hovertemplate="%{customdata}<br>%{theta}: %{r}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=kapali_degerler,
            theta=kapali_kategoriler,
            fill="toself",
            fillcolor="rgba(255, 70, 85, 0.28)",
            line={"color": "#ff4655", "width": 3},
            marker={"size": 7, "color": "#ffffff", "line": {"color": "#ff4655", "width": 2}},
            name="Hisse",
            hovertemplate="%{theta}: %{r}<extra></extra>",
        )
    )
    fig.update_layout(
        height=340 if mobil else 420,
        margin={"l": 10, "r": 10, "t": 16, "b": 16},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.03,
            "xanchor": "right",
            "x": 1,
            "font": {"color": "#f8fafc"},
        },
        polar={
            "bgcolor": "rgba(15, 23, 42, 0.46)",
            "radialaxis": {
                "visible": False,
                "range": [0, 100],
                "showticklabels": False,
                "showline": False,
                "gridcolor": "rgba(148, 163, 184, 0.18)",
            },
            "angularaxis": {
                "showline": False,
                "gridcolor": "rgba(148, 163, 184, 0.18)",
                "tickfont": {"color": "#f8fafc", "size": 13},
            },
        },
        font={"color": "#f8fafc"},
    )
    return fig


def finansal_oran_bileseni(veri: dict, competitors: dict) -> None:
    averages = competitors.get("averages", {})
    competitor_text = ", ".join(competitors.get("tickers", [])) or "Veri Yok"

    oranlar = [
        {
            "key": "fk",
            "label": "F/K",
            "value_raw": veri["fk"],
            "value": oran_formatla(veri["fk"]),
            "peer_raw": averages.get("fk"),
            "peer": oran_formatla(averages.get("fk")),
            "meaning": "Fiyat/Kazanç oranı, yatırımcının şirket karının her 1 birimi için kaç birim fiyat ödediğini gösterir.",
            "direction": "Düşük F/K, rakiplere göre daha iskontolu değerlemeye işaret edebilir.",
        },
        {
            "key": "pd_dd",
            "label": "PD/DD",
            "value_raw": veri["pd_dd"],
            "value": oran_formatla(veri["pd_dd"]),
            "peer_raw": averages.get("pd_dd"),
            "peer": oran_formatla(averages.get("pd_dd")),
            "meaning": "Piyasa Değeri/Defter Değeri oranı, şirketin özkaynaklarına göre piyasada kaç kat değer gördüğünü gösterir.",
            "direction": "Düşük PD/DD, varlık bazlı değerleme açısından daha ucuz görünebilir.",
        },
        {
            "key": "temettu",
            "label": "Temettü",
            "value_raw": veri["temettu_verimi"],
            "value": yuzde_formatla(veri["temettu_verimi"] * 100) if veri["temettu_verimi"] is not None else "Veri yok",
            "peer_raw": averages.get("temettu"),
            "peer": yuzde_formatla(averages.get("temettu") * 100) if averages.get("temettu") is not None else "Veri yok",
            "meaning": "Temettü verimi, yıllık temettünün hisse fiyatına oranını gösterir.",
            "direction": "Yüksek temettü verimi nakit getiri potansiyeli sunar; sürdürülebilirlik için payout oranı da izlenmelidir.",
        },
    ]

    rows = []
    for oran in oranlar:
        value_raw = oran["value_raw"]
        peer_raw = oran["peer_raw"]
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
            comparison = f"Hisse değeri {oran['value']}; rakip ortalaması {oran['peer']}. {badge} görünüm."

        rows.append(
            "".join(
                [
                    '<div class="ratio-row" tabindex="0">',
                    f'<div class="ratio-name">{escape(oran["label"])}</div>',
                    '<div class="ratio-value">',
                    escape(oran["value"]),
                    f'<span class="ratio-badge">{escape(badge)}</span>',
                    "</div>",
                    '<div class="ratio-popover">',
                    f'<strong>{escape(oran["label"])}</strong>',
                    f"<p>{escape(oran['meaning'])}</p>",
                    f"<p>{escape(comparison)}</p>",
                    f"<p>{escape(oran['direction'])}</p>",
                    f"<small>Rakipler: {escape(competitor_text)}</small>",
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
                grid-template-columns: minmax(96px, 0.7fr) minmax(140px, 1fr);
                gap: 0.75rem;
                align-items: center;
                padding: 0.85rem 1rem;
            }}

            .ratio-head {{
                color: #cbd5e1;
                font-size: 0.82rem;
                font-weight: 800;
                background: rgba(248, 250, 252, 0.06);
                border-bottom: 1px solid rgba(148, 163, 184, 0.18);
            }}

            .ratio-row {{
                position: relative;
                border-bottom: 1px solid rgba(148, 163, 184, 0.14);
                cursor: help;
            }}

            .ratio-row:last-child {{ border-bottom: 0; }}

            .ratio-row:hover,
            .ratio-row:focus {{
                background: rgba(56, 189, 248, 0.08);
                outline: none;
            }}

            .ratio-name {{
                color: #f8fafc;
                font-weight: 800;
            }}

            .ratio-value {{
                color: #f8fafc;
                font-weight: 700;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.75rem;
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
                left: min(52%, 280px);
                top: 50%;
                transform: translateY(-50%);
                width: min(360px, 82vw);
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

            .ratio-row:hover .ratio-popover,
            .ratio-row:focus .ratio-popover {{
                display: block;
            }}

            @media (max-width: 768px) {{
                .ratio-head,
                .ratio-row {{
                    grid-template-columns: 0.8fr 1fr;
                    padding: 0.75rem;
                }}

                .ratio-popover {{
                    left: 0.5rem;
                    right: 0.5rem;
                    top: calc(100% + 0.35rem);
                    transform: none;
                    width: auto;
                }}
            }}
        </style>
        <div class="ratio-card">
            <div class="ratio-head">
                <div>Oran</div>
                <div>Değer</div>
            </div>
            {''.join(rows)}
        </div>
        """
    )
    st.markdown(html, unsafe_allow_html=True)


with st.sidebar:
    st.title("Hisse Paneli")
    st.selectbox(
        "Profil",
        options=DEMO_PROFILLER,
        index=0,
        key="profil_email",
        help="Şimdilik iki demo profil. Her profil kendi favori listesini ayrı tutar.",
    )
    profil_senkronize()

    if st.session_state.ticker_secimi_bekleyen:
        st.session_state.ticker_secimi = st.session_state.ticker_secimi_bekleyen
        st.session_state.ticker_secimi_bekleyen = None

    st.caption(f"Aktif profil: `{st.session_state.profil_email}`")

    ticker = st.selectbox(
        "Hisse kodu",
        options=ONERILEN_HISSELER,
        index=None,
        accept_new_options=True,
        placeholder="Hisse seçiniz",
        key="ticker_secimi",
    )

    aktif_aday = str(ticker).strip().upper() if ticker else ""
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

if not ticker or not str(ticker).strip():
    st.info("Başlamak için sol taraftan bir hisse kodu girin.")
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
usd_modu = False
kur = None
kur_serisi = None

if para_birimi and para_birimi != "USD" and usd_destekli:
    usd_modu = st.toggle(
        "USD bazında hesapla",
        value=False,
        help="Fiyat ve grafik değerlerini ilgili kurla USD'ye çevirir. F/K ve PD/DD gibi oranlar yapısı gereği değişmez.",
    )

if usd_modu:
    kur, kur_serisi = kur_verisi_getir(
        para_birimi,
        grafik_ayar["period"],
        grafik_ayar["interval"],
    )
    if kur is None:
        st.warning("USD dönüşümü için kur verisi alınamadı; değerler yerel para biriminde gösteriliyor.")
        usd_modu = False


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

st.markdown("### Hisse Analizi")
with st.spinner("Rakipler ve finansal skorlar hesaplanıyor..."):
    analiz_sonucu = analiz_motoru_calistir(veri)
st.session_state.Ref_List = analiz_sonucu["ref_list"]

st.plotly_chart(
    radar_chart_olustur(
        analiz_sonucu["hisse"],
        analiz_sonucu["referans"],
        analiz_sonucu["rakipler"],
        mobil_gorunum,
    ),
    use_container_width=True,
    config={"displayModeBar": False, "scrollZoom": False},
)
st.caption(
    "Ref_List: "
    + (", ".join(analiz_sonucu["rakipler"]) if analiz_sonucu["rakipler"] else "Veri Yok")
)
if analiz_sonucu["eksikler"]:
    st.warning("Veri Yetersiz: " + ", ".join(analiz_sonucu["eksikler"]))

st.markdown("#### Neden ve Nasıl?")
for kategori, puan in analiz_sonucu["hisse"].items():
    with st.container(border=True):
        st.markdown(f"**{kategori}: {puan}**")
        st.caption(analiz_sonucu["aciklamalar"].get(kategori, "Açıklama üretilemedi."))

finansal_oranlar = pd.DataFrame(
    [
        {
            "Oran": "F/K",
            "Değer": oran_formatla(veri["fk"]),
        },
        {
            "Oran": "PD/DD",
            "Değer": oran_formatla(veri["pd_dd"]),
        },
        {
            "Oran": "Temettü Verimi",
            "Değer": yuzde_formatla(veri["temettu_verimi"] * 100)
            if veri["temettu_verimi"] is not None
            else "Veri yok",
        },
        {
            "Oran": "Yıllık Temettü",
            "Değer": sayi_formatla(temettu_tutari, gosterim_para_birimi),
        },
    ]
)

st.markdown("### Hisse Grafiği")
grafik_serisi = gecmis["Close"]
if usd_modu:
    grafik_serisi = usd_seriye_cevir(grafik_serisi, kur_serisi, para_birimi)

st.plotly_chart(
    grafik_olustur(grafik_serisi, gosterim_para_birimi, 340 if mobil_gorunum else 440),
    use_container_width=True,
    config={"displayModeBar": False, "scrollZoom": True},
)

st.markdown("### Finansal Oranlar")
finansal_oran_bileseni(veri, analiz_sonucu["competitors"])


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
