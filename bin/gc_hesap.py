#!/usr/bin/env python3
"""Geri çekilme stratejisinin ortak hesap modülü — deterministik, LLM çağırmaz, ağa çıkmaz.

`bin/tarama_cek.py` (günlük tarama) ve `bin/geri_test.py` (geriye dönük test) AYNI fonksiyonları
buradan çağırır; hesap kopyalanmaz. Kurallar: `sirket/STRATEJI-v3.md`. Sabitler: `bin/ayar.py`.

Gösterge tanımları TradingView ile aynıdır:
- RSI: `ta.rsi` — Wilder yumuşatması (RMA, alpha = 1/n), ilk değer ilk n değişimin basit ortalaması.
- stdev: `ta.stdev` — POPÜLASYON standart sapması (ddof=0).
- ATR: `ta.atr` — gerçek aralığın RMA'sı.
"""
import math
import sys
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402

SINYAL_DOKUNDU = "DOKUNDU"
SINYAL_ALTINA = "ALTINA_GECTI"


# --- göstergeler ---------------------------------------------------------------

def rma(seri, n):
    """TradingView `ta.rma`: ilk değer ilk n geçerli değerin basit ortalaması, sonra Wilder."""
    degerler = seri.to_numpy(dtype=float)
    sonuc = np.full(len(degerler), np.nan)
    gecerli = np.flatnonzero(~np.isnan(degerler))
    if len(gecerli) < n:
        return pd.Series(sonuc, index=seri.index)
    bas = gecerli[0]
    tohum = bas + n - 1
    sonuc[tohum] = degerler[bas:tohum + 1].mean()
    for i in range(tohum + 1, len(degerler)):
        sonuc[i] = (sonuc[i - 1] * (n - 1) + degerler[i]) / n
    return pd.Series(sonuc, index=seri.index)


def rsi_wilder(kapanis, n=ayar.RSI_UZUNLUK):
    degisim = kapanis.astype(float).diff()
    artis = rma(degisim.clip(lower=0).where(degisim.notna()), n)
    dusus = rma((-degisim).clip(lower=0).where(degisim.notna()), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        rsi = 100 - 100 / (1 + artis / dusus)
    rsi = rsi.where(dusus != 0, 100.0).where(artis != 0, 0.0)
    return rsi.where(artis.notna())


def rsi_bantlari(rsi, uzunluk=ayar.BANT_UZUNLUK, kat=ayar.BANT_KAT):
    orta = rsi.rolling(uzunluk).mean()
    sapma = rsi.rolling(uzunluk).std(ddof=0)
    alt = orta - kat * sapma
    return pd.DataFrame({"rsi": rsi, "orta": orta, "alt": alt, "ust": orta + kat * sapma,
                         "mesafe": rsi - alt})


def gercek_aralik(df):
    onceki = df["Close"].shift(1)
    return pd.concat([df["High"] - df["Low"], (df["High"] - onceki).abs(), (df["Low"] - onceki).abs()],
                     axis=1).max(axis=1, skipna=True)


def atr_wilder(df, n=ayar.ATR_UZUNLUK):
    return rma(gercek_aralik(df), n)


def gosterge_cercevesi(df):
    """OHLC çerçevesine rsi/orta/alt/ust/mesafe/atr/sma200/ema50/ema100/ema200 kolonları eklenmiş YENİ çerçeve.
    EMA: alfa = 2/(n+1), özyinelemeli (TradingView `ta.ema`); 2 yıllık veride başlangıç etkisi sönmüş olur."""
    bant = rsi_bantlari(rsi_wilder(df["Close"]))
    emalar = {f"ema{n}": df["Close"].ewm(span=n, adjust=False).mean() for n in ayar.TREND_EMALARI}
    return df.assign(**{k: bant[k] for k in bant.columns},
                     atr=atr_wilder(df),
                     sma200=df["Close"].rolling(ayar.REJIM_SMA).mean(),
                     **emalar)


# --- trend kategorisi (bilgi etiketi, kural değil) -------------------------------

def trend_kategorisi(kapanis, ema50, ema100, ema200):
    """GUCLU_TREND: fiyat > EMA200 ve > EMA100 ve EMA50 > EMA200 · TREND: EMA100 dışında hepsi ·
    DISI: gerisi. `eksik` sağlanmayan koşulları sayar. Eksik veri (NaN/None) koşulu sağlamaz."""
    def ustunde(a, b):
        return a is not None and b is not None and a == a and b == b and a > b

    eksik = [etiket for tamam, etiket in ((ustunde(kapanis, ema200), "fiyat ≤ EMA200"),
                                          (ustunde(kapanis, ema100), "fiyat ≤ EMA100"),
                                          (ustunde(ema50, ema200), "EMA50 ≤ EMA200")) if not tamam]
    kategori = "GUCLU_TREND" if not eksik else "TREND" if eksik == ["fiyat ≤ EMA100"] else "DISI"
    return {"kategori": kategori, "eksik": eksik}


# --- sinyal ve seviyeler -------------------------------------------------------

def sinyal(cer, i=None):
    """`cer`'in i. barında (varsayılan: son kapanmış bar) giriş sinyali var mı?

    Koşul 1: dünkü mesafe ≤ BOLGE_ESIGI. Koşul 2: bugün rsi > dün rsi ve dün rsi ≤ önceki gün rsi.
    Tip: son ALTINA_BAKIS_BAR barda (bugün dahil) mesafe < 0 olduysa ALTINA_GECTI, yoksa DOKUNDU."""
    i = len(cer) - 1 if i is None else i
    if i < 2:
        return {"var": False, "tip": None}
    rsi = cer["rsi"].to_numpy()
    mesafe = cer["mesafe"].to_numpy()
    if any(math.isnan(x) for x in (rsi[i], rsi[i - 1], rsi[i - 2], mesafe[i - 1])):
        return {"var": False, "tip": None}
    bolgede = mesafe[i - 1] <= ayar.BOLGE_ESIGI
    dondu = rsi[i] > rsi[i - 1] and rsi[i - 1] <= rsi[i - 2]
    if not (bolgede and dondu):
        return {"var": False, "tip": None}
    pencere = mesafe[max(0, i - ayar.ALTINA_BAKIS_BAR + 1):i + 1]
    tip = SINYAL_ALTINA if np.nanmin(pencere) < 0 else SINYAL_DOKUNDU
    return {"var": True, "tip": tip}


def seviyeler(giris, atr, portfoy=ayar.PORTFOY):
    stop = giris - ayar.STOP_ATR_KAT * atr
    r = giris - stop
    adet = math.floor((portfoy * ayar.RISK_ORANI) / r) if r > 0 else 0
    return {"giris": giris, "stop": stop, "r": r, "stop_yuzde": r / giris * 100,
            "adet": adet, "risk_usd": adet * r, "iki_r": giris + 2 * r}


def aday_sec(adaylar, rejim, acik_sayi, acik_risk_usd, portfoy=ayar.PORTFOY):
    """Sinyal veren adaylara eleme ve risk tavanlarını uygular. Girdiye dokunmaz; her adayın
    kopyasına `durum` (uygun | yedek | elendi) ve `sebep` ekleyip yeni liste döner."""
    sonuc, aday_havuzu = [], []
    for aday in adaylar:
        sebep = _eleme_sebebi(aday, rejim)
        if sebep:
            sonuc.append({**aday, "durum": "elendi", "sebep": sebep})
        else:
            aday_havuzu.append(aday)
    risk_tavani = portfoy * ayar.MAKS_TOPLAM_RISK_ORANI
    sayi, risk = acik_sayi, acik_risk_usd
    secilen = 0
    for aday in sorted(aday_havuzu, key=lambda a: a["stop_yuzde"]):
        if secilen >= ayar.GUNLUK_UYGUN_ADAY:
            sonuc.append({**aday, "durum": "yedek", "sebep": f"günlük {ayar.GUNLUK_UYGUN_ADAY} aday sınırı"})
            continue
        if sayi + 1 > ayar.MAKS_ACIK_POZISYON or risk + aday["risk_usd"] > risk_tavani + 1e-9:
            sonuc.append({**aday, "durum": "elendi",
                          "sebep": (f"risk tavanı (açık {sayi}/{ayar.MAKS_ACIK_POZISYON} pozisyon, "
                                    f"açık risk {risk:.2f}/{risk_tavani:.2f} USD)")})
            continue
        sonuc.append({**aday, "durum": "uygun", "sebep": None})
        sayi, risk, secilen = sayi + 1, risk + aday["risk_usd"], secilen + 1
    return sonuc


def trend_disi_sebebi(aday):
    """v3: sinyal gününde fiyat > EMA200 ve EMA50 > EMA200 değilse sebep metni; değilse None.
    Fiyat ≤ EMA100 tek başına elemez (TREND olarak uygun kalır). Trend alanı yoksa elemez."""
    if aday.get("trend_kategori") != "DISI":
        return None
    kosul = [x for x in aday.get("trend_eksik") or [] if x != "fiyat ≤ EMA100"]
    return f"trend dışı ({', '.join(kosul)})"


def _eleme_sebebi(aday, rejim):
    if rejim != "YESIL":
        return "rejim kırmızı (SPY < SMA200) — yalnızca bilgi"
    trend = trend_disi_sebebi(aday)
    if trend:
        return trend
    gun = aday.get("bilanco_isgunu")
    if gun is not None and gun < ayar.BILANCO_MIN_ISGUNU:
        return f"bilanço yakın ({gun} işlem günü < {ayar.BILANCO_MIN_ISGUNU})"
    if aday["stop_yuzde"] > ayar.MAKS_STOP_YUZDE:
        return f"stop mesafesi %{aday['stop_yuzde']:.2f} > %{ayar.MAKS_STOP_YUZDE:g}"
    if aday["adet"] < 1:
        return "adet < 1 (tek hisse bile işlem başı risk tavanını aşar)"
    return None


# --- gözlem listesi (kural dışı, yalnız bilgi) ----------------------------------

EVREN_ESIKLERI = {"piyasa_degeri": 2e9, "analist_ust": ayar.EVREN_ANALIST_UST,
                  "perf_y": ayar.EVREN_PERF_Y_ESIGI, "adr_yuzde": 3.5}


def evren_takilmalari(alan):
    """Takipçi filtrelerinden hangilerine takıldığını döner (boş liste = evrende olmalı).
    `alan`: gc_veri.GENIS_KOLONLAR'ın filtre alanları. Eksik veri de takılma sayılır."""
    def eksik(*anahtarlar):
        return any(alan.get(k) is None for k in anahtarlar)

    sonuc = []
    if eksik("market_cap_basic") or alan["market_cap_basic"] <= EVREN_ESIKLERI["piyasa_degeri"]:
        sonuc.append("piyasa değeri ≤ 2 milyar $")
    if eksik("recommendation_mark") or alan["recommendation_mark"] >= EVREN_ESIKLERI["analist_ust"]:
        sonuc.append("analist notu Al/Güçlü al değil")
    if eksik("Perf.Y") or alan["Perf.Y"] <= EVREN_ESIKLERI["perf_y"]:
        sonuc.append(f"1 yıllık performans ≤ %{EVREN_ESIKLERI['perf_y']:g}")
    for kolon, etiket in (("EMA100", "fiyat ≤ EMA100 (günlük)"), ("EMA200", "fiyat ≤ EMA200 (günlük)"),
                          ("EMA50|1W", "fiyat ≤ EMA50 (haftalık)"), ("EMA21|1W", "fiyat ≤ EMA21 (haftalık)")):
        if eksik("close", kolon) or alan["close"] <= alan[kolon]:
            sonuc.append(etiket)
    if eksik("average_volume_90d_calc", "average_volume_10d_calc") or \
            alan["average_volume_90d_calc"] <= alan["average_volume_10d_calc"]:
        sonuc.append("90g ort. hacim ≤ 10g ort. hacim")
    if eksik("ADRP") or alan["ADRP"] <= EVREN_ESIKLERI["adr_yuzde"]:
        sonuc.append("ADR ≤ %3,5")
    return sonuc


def strateji_notlari(aday, rejim_):
    """Gözlem adayı için strateji kurallarından ihlal edilenlerin TAMAMI (eleme gibi ilkinde durmaz)."""
    notlar = []
    if rejim_ != "YESIL":
        notlar.append("rejim kırmızı")
    if trend_disi_sebebi(aday):
        notlar.append(trend_disi_sebebi(aday))
    gun = aday.get("bilanco_isgunu")
    if gun is not None and gun < ayar.BILANCO_MIN_ISGUNU:
        notlar.append(f"bilanço yakın ({gun} işlem günü)")
    if aday["stop_yuzde"] > ayar.MAKS_STOP_YUZDE:
        notlar.append(f"stop %{aday['stop_yuzde']:.2f} > %{ayar.MAKS_STOP_YUZDE:g}")
    if aday["adet"] < 1:
        notlar.append("adet < 1")
    if aday.get("sma200_ustunde") is False:
        notlar.append("fiyat SMA200 altında")
    return notlar


DUSUK_OYNAKLIK_ATR_YUZDE = 1.0


def oynaklik_uyarisi(atr, kapanis):
    """ATR kapanışın %1'inden küçükse fiyat bir satın alma anlaşmasına sabitlenmiş olabilir
    (ör. LNTH, 2026-09-25: nakit teklif 102,50 $, ATR %0,66). Kural değil, uyarıdır."""
    if not atr or not kapanis or atr != atr:
        return None
    oran = atr / kapanis * 100
    if oran < DUSUK_OYNAKLIK_ATR_YUZDE:
        return (f"düşük oynaklık (ATR %{oran:.2f} < %{DUSUK_OYNAKLIK_ATR_YUZDE:g}) — "
                f"satın alma anlaşması / sabitlenmiş fiyat olabilir, haberi kontrol et")
    return None


def yakin_sinyal(cer, i=None):
    """Bugün bölgede (mesafe ≤ eşik) ama sinyal yok → yarın dönüşle sinyal verebilir."""
    i = len(cer) - 1 if i is None else i
    mesafe = cer["mesafe"].iloc[i]
    return bool(mesafe == mesafe and mesafe <= ayar.BOLGE_ESIGI and not sinyal(cer, i)["var"])


def cikis_kontrolu(poz, dusuk, rsi, orta, gecen_isgunu, bilanco_isgunu):
    """Açık pozisyon için bugünkü kapanmış bara göre çıkış kararı: {karar: CIK|TUT, sebep}."""
    sebepler = []
    if dusuk <= poz["stop"]:
        sebepler.append(f"stop seviyesine geldi (düşük {dusuk:.2f} ≤ stop {poz['stop']:.2f})")
    if rsi > orta:
        sebepler.append(f"RSI orta bandın üstünde ({rsi:.2f} > {orta:.2f}) — hedef")
    if gecen_isgunu >= ayar.MAKS_TUTMA_ISGUNU:
        sebepler.append(f"süre doldu ({gecen_isgunu} ≥ {ayar.MAKS_TUTMA_ISGUNU} işlem günü)")
    if bilanco_isgunu is not None and bilanco_isgunu <= 1:
        sebepler.append("bilanço öncesi son işlem günü")
    if sebepler:
        return {"karar": "CIK", "sebep": "; ".join(sebepler)}
    return {"karar": "TUT", "sebep": None}


def rejim(kapanis, sma200):
    if kapanis is None or sma200 is None or math.isnan(sma200):
        return "BILINMIYOR"
    return "YESIL" if kapanis >= sma200 else "KIRMIZI"


# --- NYSE takvimi ---------------------------------------------------------------

def _paskalya(yil):
    a, b, c = yil % 19, yil // 100, yil % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    hh = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - hh - k) % 7
    m = (a + 11 * hh + 22 * l_) // 451
    ay = (hh + l_ - 7 * m + 114) // 31
    gun = ((hh + l_ - 7 * m + 114) % 31) + 1
    return date(yil, ay, gun)


def _nci_gun(yil, ay, haftagunu, n):
    """Ayın n. <haftagunu>'sü (0=Pzt); n=-1 son."""
    if n > 0:
        ilk = date(yil, ay, 1)
        return ilk + timedelta(days=(haftagunu - ilk.weekday()) % 7 + 7 * (n - 1))
    son = date(yil + (ay == 12), ay % 12 + 1, 1) - timedelta(days=1)
    return son - timedelta(days=(son.weekday() - haftagunu) % 7)


def _gozlenen(gun):
    if gun.weekday() == 5:
        return gun - timedelta(days=1)
    if gun.weekday() == 6:
        return gun + timedelta(days=1)
    return gun


@lru_cache(maxsize=None)
def nyse_tatilleri(yil):
    """NYSE tam gün tatilleri (yarım günler işlem günü sayılır)."""
    gunler = {
        _nci_gun(yil, 1, 0, 3),                     # Martin Luther King
        _nci_gun(yil, 2, 0, 3),                     # Başkanlar Günü
        _paskalya(yil) - timedelta(days=2),         # Kutsal Cuma
        _nci_gun(yil, 5, 0, -1),                    # Anma Günü
        _gozlenen(date(yil, 7, 4)),                 # Bağımsızlık
        _nci_gun(yil, 9, 0, 1),                     # İşçi Bayramı
        _nci_gun(yil, 11, 3, 4),                    # Şükran Günü
        _gozlenen(date(yil, 12, 25)),               # Noel
    }
    yilbasi = date(yil, 1, 1)
    if yilbasi.weekday() != 5:                      # Cumartesiye düşen yılbaşı ertelenmez
        gunler.add(_gozlenen(yilbasi))
    if yil >= 2022:
        gunler.add(_gozlenen(date(yil, 6, 19)))     # Juneteenth
    return frozenset(gunler)


def _tatil_listesi(bas, son):
    return [g for y in range(bas.year, son.year + 1) for g in nyse_tatilleri(y)]


def isgunu_mu(gun):
    return gun.weekday() < 5 and gun not in nyse_tatilleri(gun.year)


def isgunu_farki(bas, son):
    """(bas, son] aralığındaki NYSE işlem günü sayısı. son < bas ise negatif değil 0."""
    if son <= bas:
        return 0
    return int(np.busday_count(bas + timedelta(days=1), son + timedelta(days=1),
                               holidays=_tatil_listesi(bas, son)))
