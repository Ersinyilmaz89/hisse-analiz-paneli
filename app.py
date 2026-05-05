import json
import sqlite3
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

        .block-container { padding-top: 2rem; }

        h1, h2, h3 { letter-spacing: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


if "hisse_gecmisi" not in st.session_state:
    st.session_state.hisse_gecmisi = []

if "favoriler" not in st.session_state:
    st.session_state.favoriler = []

if "profil_email" not in st.session_state:
    st.session_state.profil_email = "demo@local"

if "aktif_profil" not in st.session_state:
    st.session_state.aktif_profil = None

if "ticker_secimi" not in st.session_state:
    st.session_state.ticker_secimi = None

if "ticker_secimi_bekleyen" not in st.session_state:
    st.session_state.ticker_secimi_bekleyen = None

if "sirket_ozeti_goster" not in st.session_state:
    st.session_state.sirket_ozeti_goster = True


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
    profil = (st.session_state.profil_email or "demo@local").strip().lower()
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
    profil = st.session_state.aktif_profil or "demo@local"
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


def grafik_olustur(grafik_serisi: pd.Series, para_birimi: str) -> go.Figure:
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
        height=440,
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


with st.sidebar:
    st.title("Hisse Paneli")
    st.text_input(
        "Profil",
        key="profil_email",
        placeholder="ornek@email.com",
        help="Şimdilik deneme profili. Google girişinde bu alan Google e-postasıyla otomatik dolacak.",
    )
    profil_senkronize()

    if st.session_state.ticker_secimi_bekleyen:
        st.session_state.ticker_secimi = st.session_state.ticker_secimi_bekleyen
        st.session_state.ticker_secimi_bekleyen = None

    st.caption(f"Aktif profil: `{st.session_state.aktif_profil}`")

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

metrik_1, metrik_2, metrik_3 = st.columns(3)
metrik_1.metric(
    "Güncel Fiyat",
    sayi_formatla(guncel_fiyat, gosterim_para_birimi),
    delta=yuzde_formatla(degisim_orani) if degisim_orani is not None else None,
)
metrik_2.metric("Önceki Kapanış", sayi_formatla(onceki_kapanis, gosterim_para_birimi))
metrik_3.metric("Ticker", veri["ticker"])


finansal_oranlar = pd.DataFrame(
    [
        {
            "Oran": "F/K",
            "Değer": oran_formatla(veri["fk"]),
            "Açıklama": "Hisse fiyatının hisse başına kara bölünmesi.",
        },
        {
            "Oran": "PD/DD",
            "Değer": oran_formatla(veri["pd_dd"]),
            "Açıklama": "Piyasa değerinin defter değerine oranı.",
        },
        {
            "Oran": "Temettü Verimi",
            "Değer": yuzde_formatla(veri["temettu_verimi"] * 100)
            if veri["temettu_verimi"] is not None
            else "Veri yok",
            "Açıklama": "Yıllık temettünün hisse fiyatına oranıdır. Para birimi değişse de yüzde oran aynı kalır.",
        },
        {
            "Oran": "Yıllık Temettü",
            "Değer": sayi_formatla(temettu_tutari, gosterim_para_birimi),
            "Açıklama": "Yahoo Finance tarafından bildirilen yıllık hisse başı temettü tutarı.",
        },
    ]
)

st.markdown("### Hisse Grafiği")
grafik_serisi = gecmis["Close"]
if usd_modu:
    grafik_serisi = usd_seriye_cevir(grafik_serisi, kur_serisi, para_birimi)

st.plotly_chart(
    grafik_olustur(grafik_serisi, gosterim_para_birimi),
    use_container_width=True,
    config={"displayModeBar": False, "scrollZoom": True},
)

st.markdown("### Finansal Oranlar")
st.dataframe(finansal_oranlar, hide_index=True, use_container_width=True)


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
