#!/usr/bin/env python3
"""gc-tarama'nın veri betiği — deterministik, LLM çağırmaz. Panodaki her sayı buradan gelir.

Kullanım:
  python3 bin/tarama_cek.py --kapanis            # kapanmış günlük barla sinyal + çıkış kontrolü
  python3 bin/tarama_cek.py --acilis             # önceki kapanış adayları + açık pozisyonlar için premarket
  ek bayraklar: --kuru     (dosya yazmaz, özeti ekrana basar)
                --son-bar  (bugün bar yoksa da son kapanmış barla hesaplar — tatil/hafta sonu denemesi)

Çıktı: takimlar/gc-tarama/veri/YYYY-MM-DD.json (kapanış) · YYYY-MM-DD-acilis.json (açılış öncesi)
Çıkış kodu: 0 tamam ya da "yeni bar yok" · 1 veri hatası (pano yazılmamalı).
"""
import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import gc_hesap as h  # noqa: E402
import gc_veri as v  # noqa: E402

NY = ZoneInfo(ayar.PIYASA_SAAT_DILIMI)
VERI_DIZINI = ayar.KOK / "takimlar" / "gc-tarama" / "veri"
POZISYONLAR = ayar.KOK / "pozisyonlar.csv"
IZLEME_DOSYASI = ayar.KOK / "evren" / "izleme-listesi.txt"
POZISYON_KOLONLARI =["sembol", "giris_tarihi", "giris", "adet", "stop", "strateji_surumu"]
PIYASA_KAPANIS_SAATI = 16
ENDEKSLER = ("SPY", "QQQ")
GRAFIK_URL = "https://www.tradingview.com/chart/?symbol={}"


def y2(x):
    """JSON'a yazılan her ondalık 2 haneye yuvarlanır; pano bu değeri AYNEN kullanır."""
    return None if x is None or x != x else round(float(x), 2)


# --- pozisyonlar ----------------------------------------------------------------

def pozisyonlari_oku(yol=POZISYONLAR):
    if not Path(yol).is_file():
        return []
    with open(yol, encoding="utf-8-sig", newline="") as dosya:
        return [{"sembol": s["sembol"].strip().upper(),
                 "giris_tarihi": date.fromisoformat(s["giris_tarihi"].strip()),
                 "giris": float(s["giris"]), "adet": int(float(s["adet"])), "stop": float(s["stop"]),
                 "strateji_surumu": (s.get("strateji_surumu") or "").strip()}
                for s in csv.DictReader(dosya) if (s.get("sembol") or "").strip()]


def acik_risk_usd(pozisyonlar):
    """Stop girişin üstüne taşındıysa o pozisyonun riski 0'dır."""
    return sum(max(p["giris"] - p["stop"], 0.0) * p["adet"] for p in pozisyonlar)


def _bilanco(sembol, veri_tarihi, tv_tarihi=None):
    tarih = v.sonraki_bilanco(sembol, veri_tarihi)
    gun = h.isgunu_farki(veri_tarihi, tarih) if tarih else None
    supheli = bool(tarih and tv_tarihi and abs((date.fromisoformat(tv_tarihi) - tarih).days) > 1)
    return {"bilanco_tarihi": tarih.isoformat() if tarih else None, "bilanco_tv": tv_tarihi,
            "bilanco_isgunu": gun, "bilanco_supheli": supheli}


def pozisyon_satiri(poz, cer, veri_tarihi):
    son = cer.iloc[-1]
    bilanco = _bilanco(poz["sembol"], veri_tarihi)
    gecen = h.isgunu_farki(poz["giris_tarihi"], veri_tarihi)
    karar = h.cikis_kontrolu(poz, dusuk=son["Low"], rsi=son["rsi"], orta=son["orta"],
                             gecen_isgunu=gecen, bilanco_isgunu=bilanco["bilanco_isgunu"])
    risk = max(poz["giris"] - poz["stop"], 0.0) * poz["adet"]
    return {"sembol": poz["sembol"], "giris_tarihi": poz["giris_tarihi"].isoformat(),
            "giris": y2(poz["giris"]), "adet": poz["adet"], "stop": y2(poz["stop"]),
            "strateji_surumu": poz["strateji_surumu"], "kapanis": y2(son["Close"]), "dusuk": y2(son["Low"]),
            "rsi": y2(son["rsi"]), "orta": y2(son["orta"]), "gecen_isgunu": gecen,
            "kalan_isgunu": max(ayar.MAKS_TUTMA_ISGUNU - gecen, 0), "risk_usd": y2(risk),
            "kar_zarar_usd": y2((son["Close"] - poz["giris"]) * poz["adet"]),
            **bilanco, "karar": karar["karar"], "sebep": karar["sebep"]}


# --- adaylar --------------------------------------------------------------------

def son5(cer):
    return [{"tarih": t.date().isoformat(), "kapanis": y2(s["Close"]), "rsi": y2(s["rsi"]),
             "orta": y2(s["orta"]), "alt": y2(s["alt"]), "mesafe": y2(s["mesafe"])}
            for t, s in cer.tail(5).iterrows()]


def v2_ile_gelenler(evren):
    """v2 eşiğiyle evrene giren, v1 eşiğini (1Y > %50) geçemeyecek hisseler — 1Y performansa göre azalan."""
    bant = [e for e in evren if e.get("perf_y") is not None and e["perf_y"] <= ayar.V1_PERF_Y_ESIGI]
    return [{"sembol": e["sembol"], "perf_y": y2(e["perf_y"])}
            for e in sorted(bant, key=lambda e: e["perf_y"], reverse=True)]


def _trend(son):
    return h.trend_kategorisi(son["Close"], son["ema50"], son["ema100"], son["ema200"])


def trend_gruplari(evren, cerceveler):
    """Evren hisselerini trend kategorisine ayırır (bilgi, kural değil). Barı olmayan atlanır."""
    gruplar = {"GUCLU_TREND": [], "TREND": [], "DISI": []}
    for bilgi in evren:
        cer = cerceveler.get(bilgi["sembol"])
        if cer is None:
            continue
        k = _trend(cer.iloc[-1])
        gruplar[k["kategori"]].append(bilgi["sembol"] if k["kategori"] != "DISI"
                                      else {"sembol": bilgi["sembol"], "eksik": k["eksik"]})
    return gruplar


def aday_satiri(bilgi, cer, tip, veri_tarihi, bilanco=None):
    son, dun = cer.iloc[-1], cer.iloc[-2]
    trend = _trend(son)
    sv = h.seviyeler(son["Close"], son["atr"])
    tv = bilgi.get("tv_sembol") or bilgi["sembol"]
    return {"sembol": bilgi["sembol"], "tv_sembol": tv, "ad": bilgi.get("ad"), "sektor": bilgi.get("sektor"),
            "perf_y": y2(bilgi.get("perf_y")), "sinyal_tipi": tip, "kapanis": y2(son["Close"]), "rsi": y2(son["rsi"]), "dun_rsi": y2(dun["rsi"]),
            "orta": y2(son["orta"]), "alt": y2(son["alt"]), "ust": y2(son["ust"]),
            "dun_alt": y2(dun["alt"]), "dun_mesafe": y2(dun["mesafe"]), "mesafe": y2(son["mesafe"]),
            "atr": y2(son["atr"]), "giris": y2(sv["giris"]), "stop": y2(sv["stop"]),
            "stop_yuzde": y2(sv["stop_yuzde"]), "r": y2(sv["r"]), "adet": sv["adet"],
            "risk_usd": y2(sv["risk_usd"]), "iki_r": y2(sv["iki_r"]),
            "sma200_ustunde": bool(son["Close"] > son["sma200"]) if son["sma200"] == son["sma200"] else None,
            "ema50": y2(son["ema50"]), "ema100": y2(son["ema100"]), "ema200": y2(son["ema200"]),
            "trend_kategori": trend["kategori"], "trend_eksik": trend["eksik"],
            "cikis_kurali": f"RSI orta bandı geçince, en geç {ayar.MAKS_TUTMA_ISGUNU} işlem günü",
            "grafik": GRAFIK_URL.format(tv),
            "uyarilar": [u for u in [h.oynaklik_uyarisi(son["atr"], son["Close"])] if u],
            **(bilanco or _bilanco(bilgi["sembol"], veri_tarihi, bilgi.get("bilanco_tv")))}


def _tv_bilanco(bilgi, veri_tarihi):
    """Gözlem listesi için ucuz yol: bilanço tarihi TradingView'dan (yfinance çağrısı yok)."""
    tarih = bilgi.get("bilanco_tv")
    gun = h.isgunu_farki(veri_tarihi, date.fromisoformat(tarih)) if tarih else None
    return {"bilanco_tarihi": tarih, "bilanco_tv": tarih, "bilanco_isgunu": gun, "bilanco_supheli": False,
            "bilanco_kaynagi": "tradingview"}


def gozlem_listesi(genis, evren_semboller, cerceveler, veri_tarihi, rejim_):
    """Kural dışı gözlem: sinyal veren ama takipçi evreninde olmayan hisseler. Hiçbiri 'uygun' olamaz."""
    sonuc = []
    for bilgi in genis:
        cer = cerceveler.get(bilgi["sembol"])
        if bilgi["sembol"] in evren_semboller or cer is None:
            continue
        s = h.sinyal(cer)
        if not s["var"]:
            continue
        satir = aday_satiri(bilgi, cer, s["tip"], veri_tarihi, _tv_bilanco(bilgi, veri_tarihi))
        takilma = h.evren_takilmalari(bilgi["filtre_alanlari"]) or ["takipçi dışı (nedeni belirsiz)"]
        sonuc.append({**satir, "durum": "gozlem", "takildigi_filtreler": takilma,
                      "strateji_notlari": h.strateji_notlari(satir, rejim_)})
    tip_sirasi = {h.SINYAL_ALTINA: 0, h.SINYAL_DOKUNDU: 1}
    return sorted(sonuc, key=lambda a: (len(a["takildigi_filtreler"]) + len(a["strateji_notlari"]),
                                        tip_sirasi[a["sinyal_tipi"]], a["stop_yuzde"]))


def yakin_listesi(evren, cerceveler):
    """Evrende, bugün alt bant bölgesinde ama henüz dönmemiş — yarın sinyal verebilir."""
    sonuc = []
    for bilgi in evren:
        cer = cerceveler.get(bilgi["sembol"])
        if cer is None or not h.yakin_sinyal(cer):
            continue
        son = cer.iloc[-1]
        tv = bilgi.get("tv_sembol") or bilgi["sembol"]
        sonuc.append({"sembol": bilgi["sembol"], "kapanis": y2(son["Close"]), "rsi": y2(son["rsi"]),
                      "alt": y2(son["alt"]), "mesafe": y2(son["mesafe"]), "grafik": GRAFIK_URL.format(tv)})
    return sorted(sonuc, key=lambda a: a["mesafe"])


def izleme_oku(yol=IZLEME_DOSYASI):
    """İnsanın TradingView izleme listesinin kopyası. (liste adı, [{sembol, tv_sembol}]) döner.
    `# liste: <ad>` satırı adı verir; diğer `#` satırları ve boş satırlar atlanır. Dosya yoksa (None, [])."""
    if not Path(yol).is_file():
        return None, []
    ad, semboller = None, []
    for satir in Path(yol).read_text(encoding="utf-8-sig").splitlines():
        satir = satir.strip()
        if satir.lower().startswith("# liste:"):
            ad = satir.split(":", 1)[1].strip()
        elif satir and not satir.startswith("#"):
            tv = satir.upper()
            semboller.append({"sembol": tv.split(":")[-1], "tv_sembol": tv})
    return ad, semboller


def izleme_listesi(izleme, evren_semboller, cerceveler, veri_tarihi, rejim_):
    """İzleme listesindeki her hisse stratejinin hesabından geçer (bilgi — 'uygun' kararı ana listededir).
    durum: SINYAL (giriş sinyali) · YAKIN (bölgede, dönüş bekliyor) · YOK · VERI_YOK. Sinyaller üstte."""
    sonuc = []
    for bilgi in izleme:
        cer = cerceveler.get(bilgi["sembol"])
        if cer is None:
            sonuc.append({**bilgi, "durum": "VERI_YOK", "grafik": GRAFIK_URL.format(bilgi["tv_sembol"])})
            continue
        s = h.sinyal(cer)
        durum = "SINYAL" if s["var"] else "YAKIN" if h.yakin_sinyal(cer) else "YOK"
        satir = aday_satiri(bilgi, cer, s["tip"], veri_tarihi, _bilanco(bilgi["sembol"], veri_tarihi))
        evrende = bilgi["sembol"] in evren_semboller
        notlar = h.strateji_notlari(satir, rejim_) + ([] if evrende else ["takipçi evreninde değil"])
        sonuc.append({**satir, "durum": durum, "evrende": evrende, "strateji_notlari": notlar})
    sira = {"SINYAL": 0, "YAKIN": 1, "YOK": 2, "VERI_YOK": 3}
    return sorted(sonuc, key=lambda a: (sira[a["durum"]], a.get("mesafe") if a.get("mesafe") is not None else 1e9))


def _genis_evren_guvenli():
    try:
        return v.genis_evren(), None
    except v.VeriHatasi as exc:
        return [], f"gözlem listesi kurulamadı: {exc}"


# --- kapanış koşusu --------------------------------------------------------------

def _kapanmis_barlar(barlar, simdi_ny):
    """Piyasa kapanmadan çekilen bugünkü yarım bar atılır — sinyal yalnız kapanmış bara göre."""
    bugun = simdi_ny.date()
    if simdi_ny.hour >= PIYASA_KAPANIS_SAATI:
        return barlar
    return {s: df[df.index.date < bugun] for s, df in barlar.items()}


def _rejim_bilgisi(barlar):
    sonuc = {}
    for sembol in ENDEKSLER:
        cer = h.gosterge_cercevesi(barlar[sembol])
        son = cer.iloc[-1]
        sonuc[sembol] = {"kapanis": y2(son["Close"]), "sma200": y2(son["sma200"]),
                         "rejim": h.rejim(son["Close"], son["sma200"])}
    return sonuc


def kapanis(simdi_ny, son_bar=False):
    """Kapanış verisini kurar. (veri sözlüğü | None, mesaj) döner; None = yeni bar yok."""
    evren, kaynak, uyari = v.evren_al()
    genis, genis_uyari = _genis_evren_guvenli()
    pozisyonlar = pozisyonlari_oku()
    izleme_adi, izleme = izleme_oku()
    istenen = sorted({e["sembol"] for e in evren} | {g["sembol"] for g in genis}
                     | {p["sembol"] for p in pozisyonlar} | {i["sembol"] for i in izleme} | set(ENDEKSLER))
    barlar, hatali = v.barlari_indir(istenen)
    if any(s not in barlar for s in ENDEKSLER):
        raise v.VeriHatasi("SPY/QQQ verisi alınamadı — rejim hesaplanamaz")
    barlar = _kapanmis_barlar(barlar, simdi_ny)
    veri_tarihi = barlar["SPY"].index[-1].date()
    if not son_bar and veri_tarihi != simdi_ny.date():
        return None, f"yeni bar yok (son kapanış {veri_tarihi}, New York bugün {simdi_ny.date()})"
    cerceveler, bayat = {}, []
    for sembol, df in barlar.items():
        df = df[df.index.date <= veri_tarihi]
        if df.empty or df.index[-1].date() != veri_tarihi:
            bayat.append(sembol)
            continue
        cerceveler[sembol] = h.gosterge_cercevesi(df)
    rejimler = _rejim_bilgisi({s: barlar[s] for s in ENDEKSLER})
    ham_adaylar, gostergeler = [], {}
    for bilgi in evren:
        cer = cerceveler.get(bilgi["sembol"])
        if cer is None:
            continue
        s = h.sinyal(cer)
        gostergeler[bilgi["sembol"]] = {"sinyal": s["tip"], "son5": son5(cer)}
        if s["var"]:
            ham_adaylar.append(aday_satiri(bilgi, cer, s["tip"], veri_tarihi))
    poz_satirlari = [pozisyon_satiri(p, cerceveler[p["sembol"]], veri_tarihi)
                     for p in pozisyonlar if p["sembol"] in cerceveler]
    poz_eksik = [p["sembol"] for p in pozisyonlar if p["sembol"] not in cerceveler]
    risk = acik_risk_usd(pozisyonlar)
    adaylar = h.aday_sec(ham_adaylar, rejimler["SPY"]["rejim"], len(pozisyonlar), risk)
    sira = {"uygun": 0, "yedek": 1, "elendi": 2}
    adaylar = sorted(adaylar, key=lambda a: (sira[a["durum"]], a["stop_yuzde"]))
    veri = {
        "mod": "kapanis", "tarih": simdi_ny.date().isoformat(), "uretim": simdi_ny.isoformat(timespec="seconds"),
        "veri_kapanisi": veri_tarihi.isoformat(), "strateji_surumu": ayar.STRATEJI_SURUMU,
        "donem": "kâğıt işlem", "portfoy_usd": ayar.PORTFOY,
        "tavanlar": {"islem_risk_usd": y2(ayar.PORTFOY * ayar.RISK_ORANI),
                     "toplam_risk_usd": y2(ayar.PORTFOY * ayar.MAKS_TOPLAM_RISK_ORANI),
                     "maks_acik_pozisyon": ayar.MAKS_ACIK_POZISYON, "gunluk_uygun": ayar.GUNLUK_UYGUN_ADAY,
                     "maks_stop_yuzde": ayar.MAKS_STOP_YUZDE},
        "evren": {"kaynak": kaynak, "uyari": uyari, "sayi": len(evren),
                  "semboller": [e["sembol"] for e in evren], "hatali": sorted(set(hatali) | set(bayat)),
                  "perf_y_esigi": ayar.EVREN_PERF_Y_ESIGI, "v1_perf_y_esigi": ayar.V1_PERF_Y_ESIGI,
                  "v2_ile_gelen": v2_ile_gelenler(evren), "trend": trend_gruplari(evren, cerceveler)},
        "rejim": rejimler, "rejim_karari": rejimler["SPY"]["rejim"],
        "pozisyonlar": sorted(poz_satirlari, key=lambda p: p["karar"] != "CIK"),
        "pozisyon_verisi_yok": poz_eksik,
        "acik_pozisyon_sayisi": len(pozisyonlar), "acik_risk_usd": y2(risk),
        "acik_risk_yuzde": y2(risk / ayar.PORTFOY * 100),
        "sinyal_sayisi": len(ham_adaylar),
        "ozet": {d: sum(a["durum"] == d for a in adaylar) for d in ("uygun", "yedek", "elendi")},
        "adaylar": adaylar,
        "gozlem": {"aciklama": "KURAL DIŞI — takipçi evreni dışında sinyal verenler; bilgi amaçlı, işleme uygun değil",
                   "genis_evren_sayisi": len(genis), "uyari": genis_uyari,
                   "adaylar": gozlem_listesi(genis, {e["sembol"] for e in evren}, cerceveler, veri_tarihi,
                                             rejimler["SPY"]["rejim"])},
        "yakin": yakin_listesi(evren, cerceveler),
        "izleme": {"liste": izleme_adi, "kaynak": IZLEME_DOSYASI.relative_to(ayar.KOK).as_posix(),
                   "adaylar": izleme_listesi(izleme, {e["sembol"] for e in evren}, cerceveler, veri_tarihi,
                                             rejimler["SPY"]["rejim"])},
        "gostergeler": gostergeler,
    }
    return veri, "tamam"


# --- açılış öncesi koşusu ----------------------------------------------------------

def son_kapanis_dosyasi(dizin=VERI_DIZINI):
    dosyalar = sorted(p for p in Path(dizin).glob("????-??-??.json"))
    if not dosyalar:
        raise v.VeriHatasi("önceki kapanış koşusunun veri dosyası yok")
    return dosyalar[-1]


def acilis_isareti(fiyat, stop, iki_r):
    if fiyat is None:
        return "premarket fiyatı yok"
    if fiyat < stop:
        return "GAP — girilmez"
    if fiyat > iki_r:
        return "kaçtı — kovalanmaz"
    return "normal"


def acilis(simdi_ny):
    kaynak = son_kapanis_dosyasi()
    onceki = json.loads(kaynak.read_text(encoding="utf-8"))
    adaylar = [a for a in onceki["adaylar"] if a["durum"] in ("uygun", "yedek")]
    pozisyonlar = pozisyonlari_oku()
    fiyatlar = v.premarket_cek([a["sembol"] for a in adaylar] + [p["sembol"] for p in pozisyonlar])
    satirlar = []
    for a in adaylar:
        pm = fiyatlar.get(a["sembol"], {})
        satirlar.append({"sembol": a["sembol"], "durum": a["durum"], "stop": a["stop"], "iki_r": a["iki_r"],
                         "premarket_fiyat": y2(pm.get("premarket_fiyat")),
                         "premarket_degisim_yuzde": y2(pm.get("premarket_degisim")),
                         "isaret": acilis_isareti(pm.get("premarket_fiyat"), a["stop"], a["iki_r"])})
    poz = []
    for p in pozisyonlar:
        pm = fiyatlar.get(p["sembol"], {})
        fiyat = pm.get("premarket_fiyat")
        poz.append({"sembol": p["sembol"], "stop": y2(p["stop"]), "premarket_fiyat": y2(fiyat),
                    "premarket_degisim_yuzde": y2(pm.get("premarket_degisim")),
                    "isaret": ("premarket fiyatı yok" if fiyat is None else
                               "GAP — stop altında açılış olabilir" if fiyat < p["stop"] else "normal")})
    return {"mod": "acilis", "tarih": simdi_ny.date().isoformat(),
            "uretim": simdi_ny.isoformat(timespec="seconds"), "kaynak_kapanis": kaynak.name,
            "veri_kapanisi": onceki["veri_kapanisi"], "strateji_surumu": onceki["strateji_surumu"],
            "adaylar": satirlar, "pozisyonlar": poz}, "tamam"


# --- giriş noktası ---------------------------------------------------------------

AJAN_GOZLEM_ILK = 5
ADAY_ALANLARI = ("sembol", "ad", "sektor", "sinyal_tipi", "durum", "sebep", "uyarilar", "bilanco_tarihi",
                 "bilanco_tv", "bilanco_isgunu", "bilanco_supheli", "stop_yuzde")


def ajan_ozeti(veri):
    """gc-tarama ajanının okuduğu küçük dosya: yalnız haber araştırmasına gereken alanlar.
    Tam veri (göstergeler, 100+ gözlem) pano içindir; ajanın okuması maliyeti katlar."""
    gozlem = veri["gozlem"]["adaylar"]
    secilen = [a for i, a in enumerate(gozlem) if i < AJAN_GOZLEM_ILK or a.get("uyarilar")]
    return {"mod": "kapanis", "tarih": veri["tarih"], "veri_kapanisi": veri["veri_kapanisi"],
            "strateji_surumu": veri["strateji_surumu"], "rejim_karari": veri["rejim_karari"],
            "evren": {k: veri["evren"][k] for k in ("kaynak", "uyari", "sayi")},
            "sinyal_sayisi": veri["sinyal_sayisi"], "ozet": veri["ozet"],
            "adaylar": [{k: a.get(k) for k in ADAY_ALANLARI} for a in veri["adaylar"] if a["durum"] != "elendi"],
            "elenen": [{"sembol": a["sembol"], "sebep": a["sebep"]} for a in veri["adaylar"] if a["durum"] == "elendi"],
            "pozisyonlar": [{k: p.get(k) for k in ("sembol", "karar", "sebep", "bilanco_tarihi")}
                            for p in veri["pozisyonlar"]],
            "gozlem_incelenecek": [{k: a.get(k) for k in (*ADAY_ALANLARI, "takildigi_filtreler")} for a in secilen],
            "gozlem_toplam": len(gozlem)}


def yaz(veri, dizin=VERI_DIZINI):
    ek = "-acilis" if veri["mod"] == "acilis" else ""
    yol = Path(dizin) / f"{veri['tarih']}{ek}.json"
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(veri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if veri["mod"] == "kapanis":
        (Path(dizin) / f"{veri['tarih']}-ajan.json").write_text(
            json.dumps(ajan_ozeti(veri), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return yol


def ozet_satirlari(veri):
    if veri["mod"] == "acilis":
        return [f"açılış öncesi · kaynak {veri['kaynak_kapanis']} · {len(veri['adaylar'])} aday · "
                f"{len(veri['pozisyonlar'])} pozisyon"] + \
               [f"  {a['sembol']}: premarket {a['premarket_fiyat']} → {a['isaret']}" for a in veri["adaylar"]]
    e = veri["evren"]
    satirlar = [f"kapanış {veri['veri_kapanisi']} · evren {e['sayi']} ({e['kaynak']}) · "
                f"rejim SPY {veri['rejim']['SPY']['rejim']} / QQQ {veri['rejim']['QQQ']['rejim']} · "
                f"sinyal {veri['sinyal_sayisi']} · uygun {veri['ozet']['uygun']} · yedek {veri['ozet']['yedek']} · "
                f"elendi {veri['ozet']['elendi']} · açık pozisyon {veri['acik_pozisyon_sayisi']} "
                f"(risk {veri['acik_risk_usd']} USD)"]
    if e["uyari"]:
        satirlar.append(f"  uyarı: {e['uyari']}")
    if e["hatali"]:
        satirlar.append(f"  verisi alınamayan/bayat: {', '.join(e['hatali'])}")
    satirlar += [f"  {a['sembol']} {a['sinyal_tipi']} → {a['durum']}" + (f" ({a['sebep']})" if a["sebep"] else "")
                 for a in veri["adaylar"]]
    g = veri["gozlem"]
    satirlar.append(f"gözlem (kural dışı): geniş evren {g['genis_evren_sayisi']} · sinyal {len(g['adaylar'])}"
                    + (f" · uyarı: {g['uyari']}" if g["uyari"] else ""))
    uyarili = [a["sembol"] for a in g["adaylar"] if a.get("uyarilar")]
    satirlar.append(f"  ilk 5: {', '.join(a['sembol'] for a in g['adaylar'][:5]) or '-'}"
                    f" · uyarılı: {', '.join(uyarili) or '-'} · tam liste veri JSON'unda")
    satirlar.append(f"yarın sinyal verebilir (bölgede, dönüş yok): "
                    f"{', '.join(y['sembol'] for y in veri['yakin']) or 'yok'}")
    iz = veri.get("izleme") or {}
    if iz.get("adaylar"):
        satirlar.append(f"izleme listesi ({iz['liste'] or iz['kaynak']}): "
                        + ", ".join(f"{a['sembol']} {a['durum']}" + (f"/{a['sinyal_tipi']}" if a.get("sinyal_tipi") else "")
                                    for a in iz["adaylar"]))
    return satirlar


def main(argv):
    if not ({"--kapanis", "--acilis"} & set(argv)):
        print(__doc__)
        return 2
    simdi_ny = datetime.now(NY)
    try:
        veri, mesaj = acilis(simdi_ny) if "--acilis" in argv else kapanis(simdi_ny, "--son-bar" in argv)
    except v.VeriHatasi as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1
    if veri is None:
        print(f"YENİ BAR YOK — {mesaj}. Koşu erken biter.")
        return 0
    # Önce dosya: özet basılırken bir sorun çıksa da veri kaybolmasın
    yazilan = None if "--kuru" in argv else yaz(veri)
    print("\n".join(ozet_satirlari(veri)))
    if yazilan is None:
        print("→ --kuru: dosya yazılmadı.")
    else:
        print(f"yazıldı: {yazilan.relative_to(ayar.KOK).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
