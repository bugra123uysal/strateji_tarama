#!/usr/bin/env python3
"""Geri çekilme şirketinin veri katmanı — ağa çıkan her şey burada, hesap burada değil.

- Evren: TradingView tarayıcı uç noktası (resmi değil, bozulabilir) → yedek: `evren/cuma-cevik.csv`
- Günlük barlar ve bilanço tarihi: yfinance
- Premarket fiyatı: TradingView tarayıcı uç noktası

Kolon adları `scanner.tradingview.com/america/metainfo` ile doğrulandı (2026-09-27). TradingView
bilinmeyen kolona hata vermez, sessizce boş döner — yeni kolon eklemeden önce metainfo'ya bak.
"""
import csv
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402

TARAYICI_URL = "https://scanner.tradingview.com/america/scan"
EVREN_CSV = ayar.KOK / "evren" / "cuma-cevik.csv"
ZAMAN_ASIMI_SN = 30
YENIDEN_BEKLEME_SN = 20   # Yahoo kısıtlaması geçsin diye yeniden denemeden önce
YENIDEN_PAKET = 100       # yeniden denemede tek istekteki sembol sayısı

# "Nasıl Başarılı Trader Olursun? cuma cevik_üzerine_deneme" takipçisinin filtreleri (sirket/STRATEJI-v3.md → Evren)
ENDEKSLER = ["SYML:SP;SPX", "SYML:NASDAQ;NDX", "SYML:DJ;DJI", "SYML:NASDAQ;IXIC", "SYML:TVC;RUT"]
# Takipçinin kullandığı `analyst_rating` alanı ücretsiz uç noktada boş döner; `recommendation_mark`
# eşiği takipçiyle karşılaştırılarak bulundu (bkz. ayar.EVREN_ANALIST_UST).
EVREN_FILTRESI = [
    {"left": "type", "operation": "in_range", "right": ["stock", "dr"]},
    {"left": "market_cap_basic", "operation": "greater", "right": 2e9},
    {"left": "recommendation_mark", "operation": "less", "right": ayar.EVREN_ANALIST_UST},
    {"left": "Perf.Y", "operation": "greater", "right": ayar.EVREN_PERF_Y_ESIGI},
    {"left": "close", "operation": "greater", "right": "EMA100"},
    {"left": "close", "operation": "greater", "right": "EMA200"},
    {"left": "close", "operation": "greater", "right": "EMA50|1W"},
    {"left": "close", "operation": "greater", "right": "EMA21|1W"},
    {"left": "average_volume_90d_calc", "operation": "greater", "right": "average_volume_10d_calc"},
    {"left": "ADRP", "operation": "greater", "right": 3.5},   # ADR yüzde; `ADR` kolonu dolar cinsinden
]
EVREN_KOLONLARI = ["name", "exchange", "description", "sector", "earnings_release_next_date", "Perf.Y"]


class VeriHatasi(Exception):
    pass


# --- evren -------------------------------------------------------------------

def _tarayici(govde):
    try:
        yanit = requests.post(TARAYICI_URL, json=govde, timeout=ZAMAN_ASIMI_SN)
        yanit.raise_for_status()
        veri = yanit.json()
    except (requests.RequestException, ValueError) as exc:
        raise VeriHatasi(f"tarayıcı uç noktası: {type(exc).__name__}: {exc}") from exc
    if veri.get("error"):
        raise VeriHatasi(f"tarayıcı uç noktası hata döndü: {veri['error']}")
    return veri.get("data") or []


def _unix_tarih(deger):
    if not deger:
        return None
    return datetime.fromtimestamp(int(deger), tz=timezone.utc).date().isoformat()


def evren_tarayicidan():
    govde = {"symbols": {"symbolset": ENDEKSLER}, "columns": EVREN_KOLONLARI,
             "filter": EVREN_FILTRESI, "range": [0, 1000],
             "sort": {"sortBy": "name", "sortOrder": "asc"}}
    satirlar = _tarayici(govde)
    if not satirlar:
        raise VeriHatasi("tarayıcı uç noktası boş liste döndü — filtre ya da kolon adı bozulmuş olabilir")
    return [{"sembol": d[0], "borsa": d[1], "ad": d[2], "sektor": d[3],
             "bilanco_tv": _unix_tarih(d[4]), "tv_sembol": s, "perf_y": d[5]}
            for s, d in ((x["s"], x["d"]) for x in satirlar)]


def evren_csvden(yol=EVREN_CSV):
    """Takipçiden 'Sonuçları CSV olarak indir' ile alınan dosya. İlk kolon sembol ya da BORSA:SEMBOL."""
    if not Path(yol).is_file():
        raise VeriHatasi(f"yedek evren dosyası yok: {Path(yol).name}")
    with open(yol, encoding="utf-8-sig", newline="") as dosya:
        okuyucu = csv.DictReader(dosya)
        kolon = next((k for k in okuyucu.fieldnames or [] if k.strip().lower() in ("symbol", "ticker", "sembol")),
                     (okuyucu.fieldnames or [None])[0])
        evren = []
        for satir in okuyucu:
            ham = (satir.get(kolon) or "").strip()
            if not ham:
                continue
            borsa, _, sembol = ham.rpartition(":")
            evren.append({"sembol": sembol, "borsa": borsa or None, "ad": satir.get("Description"),
                          "sektor": satir.get("Sector"), "bilanco_tv": None,
                          "tv_sembol": ham if borsa else None, "perf_y": None})
    if not evren:
        raise VeriHatasi("yedek evren dosyası boş")
    return evren


def evren_al():
    """(evren, kaynak, uyarı). Önce uç nokta; hata olursa CSV. İkisi de yoksa VeriHatasi."""
    try:
        return evren_tarayicidan(), "tarayici", None
    except VeriHatasi as ilk:
        try:
            return evren_csvden(), "csv", f"uç nokta kullanılamadı, CSV'ye düşüldü: {ilk}"
        except VeriHatasi as ikinci:
            raise VeriHatasi(f"{ilk} · {ikinci}") from ikinci


# Gözlem listesi (kural dışı) için geniş evren: aynı endeksler + piyasa değeri > 2 milyar $, başka filtre yok.
# Filtre kolonları her sembol için döner; hangi filtreye takıldığını `gc_hesap.evren_takilmalari` bulur.
GENIS_KOLONLAR = ["name", "exchange", "description", "sector", "earnings_release_next_date",
                  "market_cap_basic", "recommendation_mark", "Perf.Y", "close", "EMA100", "EMA200",
                  "EMA50|1W", "EMA21|1W", "average_volume_90d_calc", "average_volume_10d_calc", "ADRP"]


def genis_evren():
    govde = {"symbols": {"symbolset": ENDEKSLER}, "columns": GENIS_KOLONLAR,
             "filter": EVREN_FILTRESI[:2], "range": [0, 3000],
             "sort": {"sortBy": "name", "sortOrder": "asc"}}
    satirlar = _tarayici(govde)
    if not satirlar:
        raise VeriHatasi("geniş evren sorgusu boş döndü")
    sonuc = []
    for s, d in ((x["s"], x["d"]) for x in satirlar):
        alan = dict(zip(GENIS_KOLONLAR, d))
        sonuc.append({"sembol": alan["name"], "borsa": alan["exchange"], "ad": alan["description"],
                      "sektor": alan["sector"], "bilanco_tv": _unix_tarih(alan["earnings_release_next_date"]),
                      "tv_sembol": s, "filtre_alanlari": {k: alan[k] for k in GENIS_KOLONLAR[5:]}})
    return sonuc


def premarket_cek(semboller):
    """{sembol: {premarket_fiyat, premarket_degisim, bilanco_tv, tv_sembol}} — yalnız birincil listeleme."""
    if not semboller:
        return {}
    govde = {"markets": ["america"], "columns": ["name", "premarket_close", "premarket_change",
                                                  "earnings_release_next_date"],
             "filter": [{"left": "name", "operation": "in_range", "right": sorted(set(semboller))},
                        {"left": "is_primary", "operation": "equal", "right": True}],
             "range": [0, 200]}
    return {d[0]: {"premarket_fiyat": d[1], "premarket_degisim": d[2], "bilanco_tv": _unix_tarih(d[3]),
                   "tv_sembol": s}
            for s, d in ((x["s"], x["d"]) for x in _tarayici(govde))}


# --- yfinance ------------------------------------------------------------------

def yf_sembol(sembol):
    return sembol.replace(".", "-").replace("/", "-")


def barlari_indir(semboller, yil=2):
    """{sembol: OHLCV DataFrame} ve hatalı sembol listesi. Önce TEK toplu indirme; Yahoo isteği kısarsa
    (2026-09-28 19:04: SPY dahil her sembol 'possibly delisted') hatalılar bir kez, bekleyip küçük
    paketlerle yeniden denenir. Fiyatlar TradingView grafiğindeki gibi bölünmeye göre düzeltilmiş,
    temettüye göre düzeltilmemiştir (auto_adjust=False)."""
    barlar, hatali = _indir(list(semboller), yil)
    if not hatali:
        return barlar, hatali
    time.sleep(YENIDEN_BEKLEME_SN)
    kalan = []
    for i in range(0, len(hatali), YENIDEN_PAKET):
        yeni, bos = _indir(hatali[i:i + YENIDEN_PAKET], yil)
        barlar.update(yeni)
        kalan.extend(bos)
    return barlar, kalan


def _indir(semboller, yil):
    import yfinance as yf

    eslem = {yf_sembol(s): s for s in semboller}
    ham = yf.download(list(eslem), period=f"{yil}y", interval="1d", auto_adjust=False,
                      group_by="ticker", progress=False, threads=True)
    barlar, hatali = {}, []
    for yfs, sembol in eslem.items():
        try:
            df = ham[yfs] if len(eslem) > 1 else ham
            df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
        except KeyError:
            df = pd.DataFrame()
        if df.empty:
            hatali.append(sembol)
            continue
        barlar[sembol] = df.set_axis(pd.DatetimeIndex(df.index).tz_localize(None).normalize(), axis=0)
    return barlar, hatali


def sonraki_bilanco(sembol, bugun):
    """yfinance'ten bugünden sonraki (bugün dahil) ilk bilanço tarihi; alınamazsa None — tahmin yok."""
    import yfinance as yf

    try:
        takvim = yf.Ticker(yf_sembol(sembol)).calendar or {}
    except ImportError as exc:  # kurulum eksiği sessizce "bilinmiyor"a dönmesin
        raise VeriHatasi(f"yfinance bağımlılığı eksik: {exc}") from exc
    except Exception:  # yfinance ağ/ayrıştırma hataları çeşitlidir; sonuç "bilinmiyor" — panoda görünür
        return None
    tarihler = takvim.get("Earnings Date") or []
    gelecek = sorted(t for t in tarihler if isinstance(t, date) and t >= bugun)
    return gelecek[0] if gelecek else None


def gecmis_bilancolar(sembol, adet=60):
    """Geriye dönük test için geçmiş bilanço tarihleri (date listesi); alınamazsa boş liste."""
    import yfinance as yf

    try:
        tablo = yf.Ticker(yf_sembol(sembol)).get_earnings_dates(limit=adet)
    except ImportError as exc:  # ör. lxml yoksa bütün test bilançosuz koşardı
        raise VeriHatasi(f"yfinance bağımlılığı eksik: {exc}") from exc
    except Exception:  # yfinance ağ/ayrıştırma hataları çeşitlidir; test "bilanço bilinmiyor" sayar
        return []
    if tablo is None or tablo.empty:
        return []
    return sorted({pd.Timestamp(t).date() for t in tablo.index})
