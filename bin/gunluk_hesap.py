#!/usr/bin/env python3
"""İşlem günlüğü hesabı — gc-gunluk'un sayıları. LLM çağırmaz.

Kullanım: python3 bin/gunluk_hesap.py [--hafta YYYY-Www]
Girdi:  islemler.csv (kapanmış işlemler) — kolonlar:
        sembol, sinyal_tipi, giris_tarihi, giris, ilk_stop, cikis_tarihi, cikis, adet, cikis_sebebi,
        strateji_surumu, gercek_mi
        (`ilk_stop` R hesabı için şarttır: R = (çıkış − giriş) ÷ (giriş − ilk stop))
        geri-test/*.json — en yeni geriye dönük test özeti (karşılaştırma için)
Çıktı:  takimlar/gc-gunluk/veri/YYYY-Www.json
"""
import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import gc_hesap as h  # noqa: E402

ISLEMLER = ayar.KOK / "islemler.csv"
GERI_TEST = ayar.KOK / "geri-test"
VERI_DIZINI = ayar.KOK / "takimlar" / "gc-gunluk" / "veri"
KOLONLAR = ["sembol", "sinyal_tipi", "giris_tarihi", "giris", "ilk_stop", "cikis_tarihi", "cikis", "adet",
            "cikis_sebebi", "strateji_surumu", "gercek_mi"]
GECERLI_SEBEPLER = {"stop", "hedef", "sure", "bilanco"}
STOP_TOLERANSI = 0.005        # stop'un %0,5'ten fazla altında çıkış → gap ya da stop aşağı çekildi
KUCUK_ORNEKLEM = 30           # bundan az işlem → "karar için erken"
KARSILASTIRMA_MIN_ISLEM = 10  # geri testle kıyas için en az bu kadar gerçek/kâğıt işlem
BELIRGIN_KOTU_R = 0.2         # net beklenti geri testten bu kadar R düşükse en üste yazılır
TIPLER = (h.SINYAL_DOKUNDU, h.SINYAL_ALTINA)
EVET = {"evet", "true", "1", "e", "yes", "gercek", "gerçek"}


def islemleri_oku(yol=ISLEMLER):
    if not Path(yol).is_file():
        return []
    with open(yol, encoding="utf-8-sig", newline="") as dosya:
        return [{"sembol": s["sembol"].strip().upper(), "sinyal_tipi": (s.get("sinyal_tipi") or "").strip(),
                 "giris_tarihi": s["giris_tarihi"].strip(), "giris": float(s["giris"]),
                 "ilk_stop": float(s["ilk_stop"]), "cikis_tarihi": s["cikis_tarihi"].strip(),
                 "cikis": float(s["cikis"]), "adet": int(float(s["adet"])),
                 "cikis_sebebi": (s.get("cikis_sebebi") or "").strip().lower(),
                 "strateji_surumu": (s.get("strateji_surumu") or "").strip(),
                 "gercek_mi": (s.get("gercek_mi") or "").strip().lower() in EVET}
                for s in csv.DictReader(dosya) if (s.get("sembol") or "").strip()]


def islem_sonucu(islem):
    """Tek işlemin R, net USD ve süre hesabı — yeni sözlük döner."""
    risk = islem["giris"] - islem["ilk_stop"]
    brut = (islem["cikis"] - islem["giris"]) * islem["adet"]
    net = brut - 2 * ayar.KOMISYON_EMIR_USD
    return {**islem, "r": (islem["cikis"] - islem["giris"]) / risk if risk > 0 else None,
            "net_usd": net, "net_r": net / (risk * islem["adet"]) if risk > 0 and islem["adet"] else None,
            "getiri_yuzde": (islem["cikis"] / islem["giris"] - 1) * 100,
            "isgunu": h.isgunu_farki(date.fromisoformat(islem["giris_tarihi"]),
                                     date.fromisoformat(islem["cikis_tarihi"]))}


def kural_ihlalleri(s):
    ihlal = []
    if s["r"] is None:
        ihlal.append("ilk stop girişin altında değil — R hesaplanamaz")
    if s["isgunu"] > ayar.MAKS_TUTMA_ISGUNU:
        ihlal.append(f"süre aşıldı ({s['isgunu']} > {ayar.MAKS_TUTMA_ISGUNU} işlem günü)")
    if s["cikis"] < s["ilk_stop"] * (1 - STOP_TOLERANSI):
        ihlal.append("stop altında çıkış (gap ya da stop aşağı çekildi)")
    if s["cikis_sebebi"] not in GECERLI_SEBEPLER:
        ihlal.append(f"tanımsız çıkış sebebi: '{s['cikis_sebebi'] or 'boş'}' (stop/hedef/sure/bilanco)")
    if s["sinyal_tipi"] not in TIPLER:
        ihlal.append("sinyal tipi eksik ya da tanımsız")
    if not s["strateji_surumu"]:
        ihlal.append("strateji sürümü yazılmamış")
    return ihlal


def _yuvarla(x, hane=3):
    return None if x is None else round(float(x), hane)


def istatistik(sonuclar):
    if not sonuclar:
        return {"islem": 0, "orneklem_kucuk": True}
    r = np.array([s["r"] for s in sonuclar if s["r"] is not None])
    net_r = [s["net_r"] for s in sonuclar if s["net_r"] is not None]
    kazanc, kayip = r[r > 0], r[r <= 0]
    return {"islem": len(sonuclar), "orneklem_kucuk": len(sonuclar) < KUCUK_ORNEKLEM,
            "kazanma_orani": _yuvarla(len(kazanc) / len(r) * 100, 2) if len(r) else None,
            "ort_kazanc_r": _yuvarla(kazanc.mean()) if len(kazanc) else None,
            "ort_kayip_r": _yuvarla(kayip.mean()) if len(kayip) else None,
            "beklenti_r": _yuvarla(r.mean()) if len(r) else None,
            "beklenti_net_r": _yuvarla(np.mean(net_r)) if net_r else None,
            "en_buyuk_kayip_r": _yuvarla(r.min()) if len(r) else None,
            "toplam_net_usd": _yuvarla(sum(s["net_usd"] for s in sonuclar), 2)}


def ozet(sonuclar):
    return {"tum": istatistik(sonuclar),
            **{t: istatistik([s for s in sonuclar if s["sinyal_tipi"] == t]) for t in TIPLER},
            "gercek": istatistik([s for s in sonuclar if s["gercek_mi"]]),
            "kagit": istatistik([s for s in sonuclar if not s["gercek_mi"]])}


def karsilastir(gercek, test):
    """Gerçek/kâğıt net beklenti (R) ile geri testinkini kıyaslar; eşikler bu dosyanın başında."""
    if not test or not test.get("islem") or gercek.get("beklenti_net_r") is None:
        return {"fark_r": None, "belirgin_kotu": False}
    fark = round(gercek["beklenti_net_r"] - test["beklenti_net_r"], 3)
    return {"fark_r": fark, "belirgin_kotu": gercek["islem"] >= KARSILASTIRMA_MIN_ISLEM and fark < -BELIRGIN_KOTU_R}


def son_geri_test(dizin=GERI_TEST):
    dosyalar = sorted(Path(dizin).glob("????-??-??.json"))
    if not dosyalar:
        return None, None
    veri = json.loads(dosyalar[-1].read_text(encoding="utf-8"))
    return dosyalar[-1].name, veri.get("ozet")


def hafta_kimligi(gun):
    yil, hafta, _ = gun.isocalendar()
    return f"{yil}-W{hafta:02d}"


def hesapla(bugun=None):
    bugun = bugun or datetime.now().date()
    sonuclar = [islem_sonucu(i) for i in islemleri_oku()]
    ihlaller = [{"sembol": s["sembol"], "giris_tarihi": s["giris_tarihi"], "ihlaller": kural_ihlalleri(s)}
                for s in sonuclar if kural_ihlalleri(s)]
    oz = ozet(sonuclar)
    test_adi, test_ozet = son_geri_test()
    kiyas = {anahtar: karsilastir(oz[anahtar], (test_ozet or {}).get(anahtar)) for anahtar in ("tum", *TIPLER)}
    return {"hafta": hafta_kimligi(bugun), "tarih": bugun.isoformat(), "strateji_surumu": ayar.STRATEJI_SURUMU,
            "islem_dosyasi_var": ISLEMLER.is_file(), "ozet": oz, "kural_disi": ihlaller,
            "geri_test": {"dosya": test_adi, "ozet": {k: (test_ozet or {}).get(k) for k in ("tum", *TIPLER)}},
            "karsilastirma": kiyas, "esikler": {"kucuk_orneklem": KUCUK_ORNEKLEM,
                                                "karsilastirma_min_islem": KARSILASTIRMA_MIN_ISLEM,
                                                "belirgin_kotu_r": BELIRGIN_KOTU_R},
            "islemler": [{k: (_yuvarla(v) if isinstance(v, float) else v) for k, v in s.items()} for s in sonuclar]}


def main(argv):
    try:
        sonuc = hesapla()
    except (KeyError, ValueError) as exc:
        print(f"HATA: islemler.csv okunamadı — {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if "--hafta" in argv:
        sonuc = {**sonuc, "hafta": argv[argv.index("--hafta") + 1]}
    VERI_DIZINI.mkdir(parents=True, exist_ok=True)
    yol = VERI_DIZINI / f"{sonuc['hafta']}.json"
    yol.write_text(json.dumps(sonuc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    t = sonuc["ozet"]["tum"]
    print(f"hafta {sonuc['hafta']} · işlem {t['islem']} · kural dışı {len(sonuc['kural_disi'])} · "
          f"geri test {sonuc['geri_test']['dosya'] or 'yok'} · yazıldı: {yol.relative_to(ayar.KOK).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
