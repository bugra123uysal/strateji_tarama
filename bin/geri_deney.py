#!/usr/bin/env python3
"""Geri test DENEYLERİ — strateji kuralı değildir, karşılaştırmadır (ANAYASA §7: kural insanındır).

Kullanım: python3 bin/geri_deney.py [--yil 5] [--onbellek]
Çıktı:    geri-test/deney-YYYY-MM-DD.md (rapor) + .json (özet + işlemler)

Deney 1 — o günkü evren (hayatta kalma yanlılığını azaltmak):
  Havuz: bugünkü geniş evren (5 endeks, piyasa değeri > 2 milyar $). Her gün takipçinin fiyattan hesaplanabilen
  filtreleri yeniden uygulanır; sinyal yalnız hisse O GÜN filtreleri geçiyorsa sayılır:
  1Y performans > %30 · fiyat > EMA100, EMA200 (günlük) · fiyat > EMA50, EMA21 (haftalık) · 90g ort. hacim >
  10g ort. hacim · ADR > %3,5. Uygulanamayanlar: analist notu ve geçmiş piyasa değeri (geriye dönük veri yok).
  Kalan yanlılık: havuz bugün var olan hisselerdir; batan/listeden çıkan hisseler yoktur.
Deney 2 — çıkış varyantları (giriş, stop, eleme kuralları v3 ile aynı):
  mevcut      RSI > orta (kapanış) · stop · 15 işlem günü · bilanço öncesi son gün  (= geri_test.py)
  basabas_1r  mevcut + fiyat giriş + 1R'ye değdikten sonra stop girişe çekilir
  yarim_iz    RSI > orta'da yarısı satılır; kalan yarı: stop girişe çekilir, en yüksek − 1,5 × ATR ile iz sürer,
              en geç 30 işlem günü
  ust_bant    hedef RSI > üst bant (orta yerine)
"""
import json
import pickle
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import gc_hesap as h  # noqa: E402
import gc_veri as v  # noqa: E402
import geri_test as g  # noqa: E402

CIKTI_DIZINI = ayar.KOK / "geri-test"
ONBELLEK = CIKTI_DIZINI / "onbellek"
VARYANTLAR = ("mevcut", "basabas_1r", "yarim_iz", "ust_bant")
IZ_MAKS_ISGUNU = 2 * ayar.MAKS_TUTMA_ISGUNU
YIL_BAR = 252
ADR_BAR = 20
UYARI = ("Deney sonucudur, kural değildir. O günkü evren yanlılığı azaltır ama yok etmez: havuz bugün var olan "
         "hisselerdir; analist notu ve geçmiş piyasa değeri filtresi uygulanamadı.")


# --- deney 1: o günkü evren -------------------------------------------------------

def haftalik_ema(kapanis, n):
    """TradingView `EMA{n}|1W`'nin gün içindeki değeri: önceki haftaların EMA'sı + bu haftanın o günkü kapanışı.
    Cuma günü tam haftalık EMA'ya eşittir; hafta içi gelecek günlere bakmaz."""
    ema = kapanis.resample("W-FRI").last().ewm(span=n, adjust=False).mean()
    onceki = ema.shift(1)
    hafta_sonu = kapanis.index.to_period("W-FRI").end_time.normalize()
    alfa = 2 / (n + 1)
    return pd.Series(onceki.reindex(hafta_sonu).to_numpy() * (1 - alfa) + kapanis.to_numpy() * alfa,
                     index=kapanis.index)


def evren_maskesi(cer):
    """Her gün için: takipçinin fiyattan hesaplanabilen filtrelerini geçiyor mu? (bool Series, NaN → False)"""
    kapanis = cer["Close"]
    perf_y = (kapanis / kapanis.shift(YIL_BAR) - 1) * 100
    adr = ((cer["High"] / cer["Low"]).rolling(ADR_BAR).mean() - 1) * 100
    kosullar = [perf_y > ayar.EVREN_PERF_Y_ESIGI, kapanis > cer["ema100"], kapanis > cer["ema200"],
                kapanis > haftalik_ema(kapanis, 50), kapanis > haftalik_ema(kapanis, 21),
                cer["Volume"].rolling(90).mean() > cer["Volume"].rolling(10).mean(),
                adr > h.EVREN_ESIKLERI["adr_yuzde"]]
    return pd.concat(kosullar, axis=1).fillna(False).all(axis=1)


# --- deney 2: çıkış varyantları -----------------------------------------------------

def _bilanco_cikisi(bilancolar, tarih):
    b = g._sonraki_bilanco(bilancolar, tarih)
    return b is not None and h.isgunu_farki(tarih, b) <= 1


def cikis_bacaklari(cer, giris_i, giris, stop, bilancolar, varyant):
    """Girişten sonraki çıkış(lar): [(indeks, fiyat, oran, sebep)], oranların toplamı 1. Veri biterse None."""
    tarihler = cer.index.date
    r = giris - stop
    hedef_kolon = "ust" if varyant == "ust_bant" else "orta"
    basabas = False
    for j in range(giris_i, len(cer)):
        s = cer.iloc[j]
        if s["Low"] <= stop:
            return [(j, min(s["Open"], stop), 1.0, "basabas" if basabas else "stop")]
        if s["rsi"] > s[hedef_kolon]:
            if varyant == "yarim_iz":
                kalan = _iz_bacagi(cer, giris_i, j, giris, stop, bilancolar)
                return None if kalan is None else [(j, s["Close"], 0.5, "hedef"), kalan]
            return [(j, s["Close"], 1.0, "hedef")]
        if j - giris_i >= ayar.MAKS_TUTMA_ISGUNU:
            return [(j, s["Close"], 1.0, "sure")]
        if _bilanco_cikisi(bilancolar, tarihler[j]):
            return [(j, s["Close"], 1.0, "bilanco")]
        if varyant == "basabas_1r" and not basabas and s["High"] >= giris + r:
            stop, basabas = max(stop, giris), True
    return None


def _iz_bacagi(cer, giris_i, hedef_j, giris, stop, bilancolar):
    """yarim_iz'in kalan yarısı: stop girişe çekilir, en yüksek − STOP_ATR_KAT × ATR ile yukarı taşınır."""
    tarihler = cer.index.date
    en_yuksek = cer["High"].iloc[giris_i:hedef_j + 1].max()
    iz = max(stop, giris, en_yuksek - ayar.STOP_ATR_KAT * cer["atr"].iloc[hedef_j])
    for j in range(hedef_j + 1, len(cer)):
        s = cer.iloc[j]
        if s["Low"] <= iz:
            return j, min(s["Open"], iz), 0.5, "iz"
        if j - giris_i >= IZ_MAKS_ISGUNU:
            return j, s["Close"], 0.5, "sure"
        if _bilanco_cikisi(bilancolar, tarihler[j]):
            return j, s["Close"], 0.5, "bilanco"
        en_yuksek = max(en_yuksek, s["High"])
        iz = max(iz, en_yuksek - ayar.STOP_ATR_KAT * s["atr"])
    return None


def islem_kaydi(giris, stop, adet, bacaklar):
    """Bacaklardan tek işlem: getiri ağırlıklı toplam; komisyon giriş + her çıkış bacağı."""
    r_birim = giris - stop
    brut_usd = sum(oran * adet * (fiyat - giris) for _, fiyat, oran, _ in bacaklar)
    net_usd = brut_usd - (1 + len(bacaklar)) * ayar.KOMISYON_EMIR_USD
    return {"getiri_yuzde": round(float(sum(o * (f / giris - 1) for _, f, o, _ in bacaklar) * 100), 4),
            "r": round(float(sum(o * (f - giris) for _, f, o, _ in bacaklar) / r_birim), 4),
            "net_usd": round(float(net_usd), 4), "net_r": round(float(net_usd / (adet * r_birim)), 4),
            "net_yuzde": round(float(net_usd / (adet * giris) * 100), 4),
            "sebep": "+".join(b[3] for b in bacaklar)}


class TembelBilanco:
    """Bilanço geçmişini yalnız bir sinyal rejim ve trend elemesini geçince indirir; diske önbellekler."""

    def __init__(self, sembol, onbellek):
        self.sembol, self.onbellek, self._liste = sembol, onbellek, None

    def _yukle(self):
        if self._liste is None:
            if self.sembol not in self.onbellek:
                self.onbellek[self.sembol] = [t.isoformat() for t in v.gecmis_bilancolar(self.sembol)]
            self._liste = [date.fromisoformat(t) for t in self.onbellek[self.sembol]]
        return self._liste

    def __iter__(self):
        return iter(self._yukle())

    def __bool__(self):
        return bool(self._yukle())


def sembol_deneyi(sembol, cer, maske, spy_rejim, bilancolar, bas_tarih, varyant, sayac):
    """geri_test.sembol_islemleri ile aynı döngü + evren maskesi + çıkış varyantı."""
    islemler, i = [], 2
    tarihler = cer.index.date
    maske = maske.to_numpy()
    while i < len(cer) - 1:
        if tarihler[i] < bas_tarih or not maske[i] or not h.sinyal(cer, i)["var"]:
            i += 1
            continue
        tip = h.sinyal(cer, i)["tip"]
        son = cer.iloc[i]
        sv = h.seviyeler(son["Close"], son["atr"])
        trend = h.trend_kategorisi(son["Close"], son["ema50"], son["ema100"], son["ema200"])["kategori"]
        sebep = g.eleme_sebebi(cer, i, sv, trend, spy_rejim, bilancolar)
        if sebep:
            sayac[sebep] = sayac.get(sebep, 0) + 1
            i += 1
            continue
        giris = cer.iloc[i + 1]["Open"]
        bacaklar = cikis_bacaklari(cer, i + 1, giris, sv["stop"], bilancolar, varyant)
        if bacaklar is None:
            sayac["acik_kaldi"] = sayac.get("acik_kaldi", 0) + 1
            break
        j = bacaklar[-1][0]
        islemler.append({"sembol": sembol, "tip": tip, "trend": trend, "sinyal": tarihler[i].isoformat(),
                         "cikis_tarihi": tarihler[j].isoformat(), "giris": round(float(giris), 4),
                         **islem_kaydi(giris, sv["stop"], sv["adet"], bacaklar)})
        i = j + 1
    return islemler


# --- koşu ---------------------------------------------------------------------------

def _barlar(semboller, yil, onbellek_kullan):
    yol = ONBELLEK / f"barlar-{date.today().isoformat()}-{yil}y.pkl"
    if onbellek_kullan and yol.is_file():
        with open(yol, "rb") as dosya:
            return pickle.load(dosya)
    barlar, hatali = v.barlari_indir(semboller, yil=yil)
    ONBELLEK.mkdir(parents=True, exist_ok=True)
    with open(yol, "wb") as dosya:
        pickle.dump((barlar, hatali), dosya)
    return barlar, hatali


def _ozet(islemler):
    return {"tum": g.istatistik(islemler), **{t: g.istatistik([x for x in islemler if x["tip"] == t])
                                              for t in g.TIPLER}}


def calistir(yil=5, onbellek_kullan=False, bugun=None):
    bugun = bugun or date.today()
    takipci, kaynak, _ = v.evren_al()
    havuz = v.genis_evren()
    takipci_semboller = [e["sembol"] for e in takipci]
    havuz_semboller = sorted({e["sembol"] for e in havuz} | set(takipci_semboller))
    # +2 yıl: 1Y performans (252 bar) ve EMA200 ısınması başlangıçtan önce dolsun
    barlar, hatali = _barlar(havuz_semboller + ["SPY"], yil + 2, onbellek_kullan)
    spy = h.gosterge_cercevesi(barlar["SPY"])
    spy_rejim = {t.date(): h.rejim(s["Close"], s["sma200"]) for t, s in spy.iterrows()}
    bas_tarih = date(bugun.year - yil, bugun.month, min(bugun.day, 28))
    bilanco_yolu = ONBELLEK / "bilanco.json"
    bilanco_onbellek = json.loads(bilanco_yolu.read_text(encoding="utf-8")) if bilanco_yolu.is_file() else {}
    cerceveler = {s: h.gosterge_cercevesi(barlar[s]) for s in havuz_semboller if s in barlar}
    maskeler = {s: evren_maskesi(c) for s, c in cerceveler.items()}
    evrenler = {"bugunku": (takipci_semboller, lambda s: pd.Series(True, index=cerceveler[s].index)),
                "o_gunku": (havuz_semboller, lambda s: maskeler[s])}
    sonuc = {}
    try:
        for evren_adi, (semboller, maske_al) in evrenler.items():
            for varyant in VARYANTLAR:
                islemler, sayac = [], {}
                for s in semboller:
                    if s in cerceveler:
                        islemler += sembol_deneyi(s, cerceveler[s], maske_al(s), spy_rejim,
                                                  TembelBilanco(s, bilanco_onbellek), bas_tarih, varyant, sayac)
                sonuc[f"{evren_adi}/{varyant}"] = {"ozet": _ozet(islemler), "elenen": sayac,
                                                   "sembol_sayisi": len({x["sembol"] for x in islemler}),
                                                   "islemler": islemler}
                print(f"  {evren_adi}/{varyant}: {len(islemler)} işlem", flush=True)
    finally:
        bilanco_yolu.write_text(json.dumps(bilanco_onbellek), encoding="utf-8")
    gunluk_evren = pd.concat(maskeler.values(), axis=1).fillna(False).sum(axis=1)
    gunluk_evren = gunluk_evren[gunluk_evren.index.date >= bas_tarih]
    return {"tarih": bugun.isoformat(), "strateji_surumu": ayar.STRATEJI_SURUMU, "uyari": UYARI,
            "donem": f"{bas_tarih.isoformat()} → {bugun.isoformat()}", "takipci_kaynagi": kaynak,
            "takipci_sayisi": len(takipci_semboller), "havuz_sayisi": len(havuz_semboller),
            "verisi_yok": hatali,
            "o_gunku_evren": {"ortalama": round(float(gunluk_evren.mean()), 1),
                              "en_az": int(gunluk_evren.min()), "en_cok": int(gunluk_evren.max())},
            "deneyler": sonuc}


def rapor_metni(s):
    satirlar = [f"# Geri test deneyleri — strateji {s['strateji_surumu']} — {s['tarih']}", "",
                f"> **{s['uyari']}**", "",
                f"- Dönem: {s['donem']}",
                f"- Bugünkü evren: takipçinin bugünkü {s['takipci_sayisi']} hissesi ({s['takipci_kaynagi']}) — "
                f"eski yöntem, hayatta kalma yanlılıklı",
                f"- O günkü evren: {s['havuz_sayisi']} hisselik havuzdan her gün filtreyi geçenler — günde ortalama "
                f"{s['o_gunku_evren']['ortalama']} (en az {s['o_gunku_evren']['en_az']}, "
                f"en çok {s['o_gunku_evren']['en_cok']})",
                "- Giriş, stop, rejim, trend, bilanço ve stop genişliği elemeleri v3 ile aynı; günlük 3 aday ve "
                "pozisyon tavanları uygulanmadı (her sinyal ayrı işlem)", "",
                "## Özet — net beklenti (R, komisyon sonrası)", "",
                "| Evren | Çıkış | İşlem | Kazanma % | Ort. kazanç % | Ort. kayıp % | Beklenti R (net) | "
                "DOKUNDU R | ALTINA_GECTI R | En büyük kayıp % | Toplam net USD |",
                "|---|---|---|---|---|---|---|---|---|---|---|"]
    for ad, deney in s["deneyler"].items():
        evren, varyant = ad.split("/")
        o, dok, alt = deney["ozet"]["tum"], deney["ozet"][h.SINYAL_DOKUNDU], deney["ozet"][h.SINYAL_ALTINA]
        if not o["islem"]:
            satirlar.append(f"| {evren} | {varyant} | 0 | – | – | – | – | – | – | – | – |")
            continue
        satirlar.append(f"| {evren} | {varyant} | {o['islem']} | {o['kazanma_orani']} | {o['ort_kazanc_yuzde']} | "
                        f"{o['ort_kayip_yuzde']} | **{o['beklenti_net_r']}** | {dok.get('beklenti_net_r', '–')} | "
                        f"{alt.get('beklenti_net_r', '–')} | {o['en_buyuk_kayip_yuzde']} | {o['toplam_net_usd']} |")
    satirlar += ["", "## Çıkış sebepleri", ""]
    for ad, deney in s["deneyler"].items():
        satirlar.append(f"- {ad}: {deney['ozet']['tum'].get('cikis_sebepleri', {})}")
    satirlar += ["", "## Elenen sinyaller", ""]
    for ad, deney in s["deneyler"].items():
        satirlar.append(f"- {ad}: {deney['elenen']}")
    satirlar += ["", f"- Fiyat verisi alınamayan: {len(s['verisi_yok'])} sembol", ""]
    return "\n".join(satirlar)


def main(argv):
    yil = int(argv[argv.index("--yil") + 1]) if "--yil" in argv else 5
    try:
        sonuc = calistir(yil, onbellek_kullan="--onbellek" in argv)
    except v.VeriHatasi as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1
    CIKTI_DIZINI.mkdir(exist_ok=True)
    (CIKTI_DIZINI / f"deney-{sonuc['tarih']}.json").write_text(
        json.dumps(sonuc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    metin = rapor_metni(sonuc)
    (CIKTI_DIZINI / f"deney-{sonuc['tarih']}.md").write_text(metin, encoding="utf-8")
    print(metin)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
