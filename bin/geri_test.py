#!/usr/bin/env python3
"""Geriye dönük test — `bin/gc_hesap.py`'nin AYNI fonksiyonlarıyla. LLM çağırmaz.

Kullanım: python3 bin/geri_test.py [--yil 5]
Çıktı:    geri-test/YYYY-MM-DD.md (rapor) + geri-test/YYYY-MM-DD.json (ham işlemler + özet)

Uygulanan kurallar (sirket/STRATEJI-v3.md): sinyal, rejim (SPY ≥ SMA200), bilanço < 5 işlem günü,
stop > %8, adet ≥ 1; giriş ertesi gün AÇILIŞTA (açılış stop altındaysa işlem yok), çıkış: stop
(gap'te açılış fiyatı), RSI > orta (kapanış), 15 işlem günü (kapanış), bilanço öncesi son gün (kapanış).
Uygulanmayanlar: günlük 3 aday, 5 açık pozisyon ve %5 toplam risk tavanı — her sinyal ayrı işlem sayılır.
Komisyon: emir başına ayar.KOMISYON_EMIR_USD (gidiş-dönüş 2×), adet ayar.PORTFOY ile sabit (bileşik değil).
"""
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import gc_hesap as h  # noqa: E402
import gc_veri as v  # noqa: E402

CIKTI_DIZINI = ayar.KOK / "geri-test"
UYARI = ("Bu evren bugünün güçlü hisselerinden oluşur; geçmiş sonuç hayatta kalma yanlılığı "
         "nedeniyle olduğundan iyi görünür.")
TIPLER = (h.SINYAL_DOKUNDU, h.SINYAL_ALTINA)


def _sonraki_bilanco(bilancolar, gun):
    return next((b for b in bilancolar if b >= gun), None)


def _cikis(cer, giris_i, stop, bilancolar):
    """Girişten sonra ilk çıkış: (indeks, fiyat, sebep) ya da veri biterse None."""
    tarihler = cer.index.date
    for j in range(giris_i, len(cer)):
        s = cer.iloc[j]
        if s["Low"] <= stop:
            return j, min(s["Open"], stop), "stop"
        if s["rsi"] > s["orta"]:
            return j, s["Close"], "hedef"
        if j - giris_i >= ayar.MAKS_TUTMA_ISGUNU:
            return j, s["Close"], "sure"
        b = _sonraki_bilanco(bilancolar, tarihler[j])
        if b is not None and h.isgunu_farki(tarihler[j], b) <= 1:
            return j, s["Close"], "bilanco"
    return None


def eleme_sebebi(cer, i, sv, trend, spy_rejim, bilancolar):
    """i. bardaki sinyal neden işleme dönüşmez? None = dönüşür. Bilanço listesine yalnız rejim ve trend
    geçildikten sonra bakılır (geri_deney tembel yükler)."""
    tarih = cer.index[i].date()
    if spy_rejim.get(tarih) != "YESIL":
        return "rejim"
    if trend == "DISI":
        return "trend_disi"
    b = _sonraki_bilanco(bilancolar, tarih)
    if b is not None and h.isgunu_farki(tarih, b) < ayar.BILANCO_MIN_ISGUNU:
        return "bilanco"
    if sv["stop_yuzde"] > ayar.MAKS_STOP_YUZDE:
        return "stop_genis"
    if sv["adet"] < 1:
        return "adet_sifir"
    if cer.iloc[i + 1]["Open"] <= sv["stop"]:
        return "gap"
    return None


def sembol_islemleri(sembol, cer, spy_rejim, bilancolar, bas_tarih, sayac):
    islemler, i = [], 2
    tarihler = cer.index.date
    while i < len(cer) - 1:
        if tarihler[i] < bas_tarih or not h.sinyal(cer, i)["var"]:
            i += 1
            continue
        tip = h.sinyal(cer, i)["tip"]
        son = cer.iloc[i]
        sv = h.seviyeler(son["Close"], son["atr"])
        trend = h.trend_kategorisi(son["Close"], son["ema50"], son["ema100"], son["ema200"])["kategori"]
        sebep = eleme_sebebi(cer, i, sv, trend, spy_rejim, bilancolar)
        if sebep:
            sayac[sebep] = sayac.get(sebep, 0) + 1
            i += 1
            continue
        if not bilancolar:
            sayac["bilanco_bilinmiyor"] = sayac.get("bilanco_bilinmiyor", 0) + 1
        giris = cer.iloc[i + 1]["Open"]
        cikis = _cikis(cer, i + 1, sv["stop"], bilancolar)
        if cikis is None:
            sayac["acik_kaldi"] = sayac.get("acik_kaldi", 0) + 1
            break
        j, fiyat, neden = cikis
        adet, risk_birimi = sv["adet"], giris - sv["stop"]
        net_usd = (fiyat - giris) * adet - 2 * ayar.KOMISYON_EMIR_USD
        islemler.append({"sembol": sembol, "tip": tip, "trend": trend, "sinyal": tarihler[i].isoformat(),
                         "giris_tarihi": tarihler[i + 1].isoformat(), "cikis_tarihi": tarihler[j].isoformat(),
                         "giris": round(float(giris), 4), "stop": round(float(sv["stop"]), 4),
                         "cikis": round(float(fiyat), 4), "adet": adet, "sebep": neden,
                         "getiri_yuzde": round(float((fiyat / giris - 1) * 100), 4),
                         "r": round(float((fiyat - giris) / risk_birimi), 4),
                         "net_usd": round(float(net_usd), 4),
                         "net_r": round(float(net_usd / (adet * risk_birimi)), 4),
                         "net_yuzde": round(float(net_usd / (adet * giris) * 100), 4)})
        i = j + 1
    return islemler


def istatistik(islemler):
    if not islemler:
        return {"islem": 0}
    g = np.array([x["getiri_yuzde"] for x in islemler])
    kazanc, kayip = g[g > 0], g[g <= 0]
    sebepler = {}
    for x in islemler:
        sebepler[x["sebep"]] = sebepler.get(x["sebep"], 0) + 1
    return {"islem": len(islemler), "kazanma_orani": round(len(kazanc) / len(g) * 100, 2),
            "ort_kazanc_yuzde": round(float(kazanc.mean()), 2) if len(kazanc) else None,
            "ort_kayip_yuzde": round(float(kayip.mean()), 2) if len(kayip) else None,
            "beklenti_yuzde": round(float(g.mean()), 2),
            "beklenti_net_yuzde": round(float(np.mean([x["net_yuzde"] for x in islemler])), 2),
            "beklenti_r": round(float(np.mean([x["r"] for x in islemler])), 3),
            "beklenti_net_r": round(float(np.mean([x["net_r"] for x in islemler])), 3),
            "en_buyuk_kayip_yuzde": round(float(g.min()), 2),
            "toplam_net_usd": round(float(sum(x["net_usd"] for x in islemler)), 2),
            "cikis_sebepleri": sebepler}


TREND_GRUPLARI = {"filtresiz": None, "trend_kosulu": ("GUCLU_TREND", "TREND"),
                  "guclu_trend": ("GUCLU_TREND",), "trend_disi": ("DISI",)}
TREND_ETIKETI = {"filtresiz": "Filtresiz (hepsi)", "trend_kosulu": "Trend koşulu (EMA50>EMA200, fiyat>EMA200)",
                 "guclu_trend": "Güçlü trend (+ fiyat>EMA100)", "trend_disi": "Trend dışı"}


def trend_kirilimi(islemler):
    """Sinyal günündeki EMA trend kategorisine göre istatistik — kural değil, karşılaştırma."""
    sonuc = {}
    for ad, kategoriler in TREND_GRUPLARI.items():
        grup = [x for x in islemler if kategoriler is None or x["trend"] in kategoriler]
        sonuc[ad] = {"tum": istatistik(grup), **{t: istatistik([x for x in grup if x["tip"] == t]) for t in TIPLER}}
    return sonuc


def calistir(yil=5, bugun=None):
    bugun = bugun or date.today()
    evren, kaynak, uyari = v.evren_al()
    semboller = [e["sembol"] for e in evren]
    barlar, hatali = v.barlari_indir(semboller + ["SPY"], yil=yil + 1)  # +1 yıl: SMA200 ısınması
    spy = h.gosterge_cercevesi(barlar["SPY"])
    spy_rejim = {t.date(): h.rejim(s["Close"], s["sma200"]) for t, s in spy.iterrows()}
    bas_tarih = date(bugun.year - yil, bugun.month, min(bugun.day, 28))
    islemler, sayac, bilancosuz = [], {}, []
    for sembol in semboller:
        if sembol not in barlar:
            continue
        bilancolar = v.gecmis_bilancolar(sembol)
        if not bilancolar:
            bilancosuz.append(sembol)
        cer = h.gosterge_cercevesi(barlar[sembol])
        islemler += sembol_islemleri(sembol, cer, spy_rejim, bilancolar, bas_tarih, sayac)
    ozet = {"tum": istatistik(islemler), **{t: istatistik([x for x in islemler if x["tip"] == t]) for t in TIPLER}}
    return {"tarih": bugun.isoformat(), "strateji_surumu": ayar.STRATEJI_SURUMU, "uyari": UYARI,
            "donem": f"{bas_tarih.isoformat()} → {bugun.isoformat()}", "evren_kaynagi": kaynak,
            "evren_uyarisi": uyari, "evren_sayisi": len(semboller), "verisi_yok": hatali,
            "bilanco_verisi_yok": bilancosuz, "portfoy_usd": ayar.PORTFOY,
            "komisyon_emir_usd": ayar.KOMISYON_EMIR_USD, "elenen_sinyaller": sayac,
            "ozet": ozet, "trend_kirilimi": trend_kirilimi(islemler), "islemler": islemler}


ETIKET = {"tum": "İkisi (tümü)", h.SINYAL_DOKUNDU: "DOKUNDU", h.SINYAL_ALTINA: "ALTINA_GECTI"}


def rapor_metni(s):
    satirlar = [f"# Geriye dönük test — strateji {s['strateji_surumu']} — {s['tarih']}", "",
                f"> **{s['uyari']}**", "",
                f"- Dönem: {s['donem']} · evren: {s['evren_sayisi']} sembol ({s['evren_kaynagi']})",
                f"- Portföy {s['portfoy_usd']:.0f} USD, işlem başı risk %{ayar.RISK_ORANI * 100:g}, "
                f"komisyon emir başı {s['komisyon_emir_usd']} USD (gidiş-dönüş {2 * s['komisyon_emir_usd']} USD)",
                "- Uygulanmayan: günlük 3 aday, 5 açık pozisyon ve %5 toplam risk tavanı "
                "(her sinyal ayrı işlem sayıldı)", "",
                "| Sinyal tipi | İşlem | Kazanma % | Ort. kazanç % | Ort. kayıp % | Beklenti % | "
                "Beklenti % (komisyon sonrası) | Beklenti R (net) | En büyük kayıp % | Toplam net USD |",
                "|---|---|---|---|---|---|---|---|---|---|"]
    for anahtar in ("tum", *TIPLER):
        o = s["ozet"][anahtar]
        if not o["islem"]:
            satirlar.append(f"| {ETIKET[anahtar]} | 0 | – | – | – | – | – | – | – | – |")
            continue
        satirlar.append(f"| {ETIKET[anahtar]} | {o['islem']} | {o['kazanma_orani']} | {o['ort_kazanc_yuzde']} | "
                        f"{o['ort_kayip_yuzde']} | {o['beklenti_yuzde']} | {o['beklenti_net_yuzde']} | "
                        f"{o['beklenti_net_r']} | {o['en_buyuk_kayip_yuzde']} | {o['toplam_net_usd']} |")
    if s.get("trend_kirilimi"):
        satirlar += ["", "## EMA trend koşulu ile / olmadan (sinyal günündeki günlük EMA'lar)", "",
                     "Trend koşulu: fiyat > EMA200 ve EMA50 > EMA200; \"güçlü trend\" ayrıca fiyat > EMA100. "
                     "v3'te trend dışı sinyal elenir (\"trend_disi\" elenenlerde sayılır), bu yüzden o grup boştur.",
                     "",
                     "| Grup | Tip | İşlem | Kazanma % | Beklenti % (net) | Beklenti R (net) | Toplam net USD |",
                     "|---|---|---|---|---|---|---|"]
        for grup, istat in s["trend_kirilimi"].items():
            for anahtar in ("tum", *TIPLER):
                o = istat[anahtar]
                tip = "Tümü" if anahtar == "tum" else ETIKET[anahtar]
                satirlar.append(f"| {TREND_ETIKETI[grup]} | {tip} | {o['islem']} | {o.get('kazanma_orani', '–')} | "
                                f"{o.get('beklenti_net_yuzde', '–')} | {o.get('beklenti_net_r', '–')} | "
                                f"{o.get('toplam_net_usd', '–')} |")
    satirlar += ["", "## Çıkış sebepleri", ""]
    for anahtar in ("tum", *TIPLER):
        satirlar.append(f"- {ETIKET[anahtar]}: {s['ozet'][anahtar].get('cikis_sebepleri', {})}")
    satirlar += ["", "## Elenen sinyaller (işleme dönüşmeyen)", "", f"- {s['elenen_sinyaller']}",
                 f"- Bilanço geçmişi alınamayan semboller (bilanço kuralı uygulanamadı): "
                 f"{', '.join(s['bilanco_verisi_yok']) or 'yok'}",
                 f"- Fiyat verisi alınamayan: {', '.join(s['verisi_yok']) or 'yok'}", ""]
    return "\n".join(satirlar)


def main(argv):
    yil = int(argv[argv.index("--yil") + 1]) if "--yil" in argv else 5
    try:
        sonuc = calistir(yil)
    except v.VeriHatasi as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1
    CIKTI_DIZINI.mkdir(exist_ok=True)
    (CIKTI_DIZINI / f"{sonuc['tarih']}.json").write_text(
        json.dumps(sonuc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metin = rapor_metni(sonuc)
    (CIKTI_DIZINI / f"{sonuc['tarih']}.md").write_text(metin, encoding="utf-8")
    print(metin)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
