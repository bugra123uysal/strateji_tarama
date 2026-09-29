"""Geri çekilme hesap modülünün testleri — ağ yok, para harcamaz.

RSI referansı: StockCharts "Relative Strength Index" ders notundaki örnek seri (Wilder yumuşatması,
ilk ortalama basit ortalama — TradingView `ta.rsi` ile aynı yöntem).
"""
import math
import sys
import unittest
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import gc_hesap as h  # noqa: E402

KAPANIS = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03,
           45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64, 46.21, 46.25, 45.71, 46.45,
           45.78, 45.35, 44.03, 44.18, 44.22, 44.57, 43.42, 42.66, 43.13]
BEKLENEN_RSI = [70.53, 66.32, 66.55, 69.41, 66.36, 57.97, 62.93, 63.26, 56.06, 62.38, 54.71,
                50.42, 39.99, 41.46, 41.87, 45.46, 37.30, 33.08, 37.77]


class RsiTesti(unittest.TestCase):
    def test_wilder_rsi_bilinen_seriyle_ayni(self):
        # Yayımlanmış tablo ara ortalamaları 2 haneye yuvarlayarak ilerler (0.24 / 0.10);
        # tam hassasiyetli hesap bu yüzden ±0.07 sapar. Yöntem hatası 1+ puan fark yaratırdı.
        rsi = h.rsi_wilder(pd.Series(KAPANIS), 14)
        self.assertTrue(rsi.iloc[:14].isna().all(), "ilk 14 bar tanımsız olmalı")
        for bulunan, beklenen in zip(rsi.iloc[14:], BEKLENEN_RSI):
            self.assertAlmostEqual(bulunan, beklenen, delta=0.1)

    def test_ilk_rsi_basit_ortalama_tohumuyla_tam_esit(self):
        degisim = [b - a for a, b in zip(KAPANIS, KAPANIS[1:15])]
        artis = sum(max(d, 0) for d in degisim) / 14
        dusus = sum(max(-d, 0) for d in degisim) / 14
        ikinci = KAPANIS[15] - KAPANIS[14]
        artis2 = (artis * 13 + max(ikinci, 0)) / 14
        dusus2 = (dusus * 13 + max(-ikinci, 0)) / 14
        rsi = h.rsi_wilder(pd.Series(KAPANIS), 14)
        self.assertAlmostEqual(rsi.iloc[14], 100 - 100 / (1 + artis / dusus), places=10)
        self.assertAlmostEqual(rsi.iloc[15], 100 - 100 / (1 + artis2 / dusus2), places=10)

    def test_hic_dusus_yoksa_rsi_100(self):
        rsi = h.rsi_wilder(pd.Series(np.arange(1.0, 31.0)), 14)
        self.assertEqual(rsi.iloc[-1], 100.0)

    def test_hic_yukselis_yoksa_rsi_0(self):
        rsi = h.rsi_wilder(pd.Series(np.arange(31.0, 1.0, -1)), 14)
        self.assertEqual(rsi.iloc[-1], 0.0)


class BantTesti(unittest.TestCase):
    def test_stdev_populasyon_ddof0(self):
        seri = pd.Series([2, 4, 4, 4, 5, 5, 7, 9], dtype=float)
        bant = h.rsi_bantlari(seri, uzunluk=8, kat=2.0)
        self.assertAlmostEqual(bant["orta"].iloc[-1], 5.0)
        self.assertAlmostEqual(bant["alt"].iloc[-1], 5.0 - 2 * 2.0)  # pop. std = 2
        self.assertAlmostEqual(bant["ust"].iloc[-1], 5.0 + 2 * 2.0)
        self.assertAlmostEqual(bant["mesafe"].iloc[-1], 9.0 - 1.0)

    def test_sabit_seride_bant_genisligi_sifir(self):
        bant = h.rsi_bantlari(pd.Series([50.0] * 20), uzunluk=14, kat=2.0)
        self.assertEqual(bant["alt"].iloc[-1], 50.0)
        self.assertEqual(bant["ust"].iloc[-1], 50.0)


class AtrTesti(unittest.TestCase):
    def test_sabit_aralikta_atr_araliga_esit(self):
        n = 30
        df = pd.DataFrame({"High": [11.0] * n, "Low": [9.0] * n, "Close": [10.0] * n})
        self.assertAlmostEqual(h.atr_wilder(df, 14).iloc[-1], 2.0)

    def test_bosluk_gerceek_araliga_dahil(self):
        df = pd.DataFrame({"High": [11.0, 16.0], "Low": [9.0, 14.0], "Close": [10.0, 15.0]})
        tr = h.gercek_aralik(df)
        self.assertEqual(tr.iloc[1], 6.0)  # max(16-14, |16-10|, |14-10|)


def _bant_cercevesi(rsi, alt):
    rsi = pd.Series(rsi, dtype=float)
    alt = pd.Series(alt, dtype=float)
    return pd.DataFrame({"rsi": rsi, "orta": alt + 10, "alt": alt, "ust": alt + 20, "mesafe": rsi - alt})


class SinyalTesti(unittest.TestCase):
    def test_dokundu_sinyali(self):
        # dün mesafe 1.5 (≤ 2), dün dip, bugün yukarı; son 5 barda mesafe hiç < 0 değil
        cer = _bant_cercevesi([40, 38, 36, 33, 31.5, 34], [30, 30, 30, 30, 30, 30])
        s = h.sinyal(cer)
        self.assertTrue(s["var"])
        self.assertEqual(s["tip"], "DOKUNDU")

    def test_altina_gecti_sinyali(self):
        cer = _bant_cercevesi([40, 35, 28, 29, 29, 31], [30, 30, 30, 30, 30, 30])
        s = h.sinyal(cer)
        self.assertTrue(s["var"])
        self.assertEqual(s["tip"], "ALTINA_GECTI")

    def test_bolge_disinda_sinyal_yok(self):
        cer = _bant_cercevesi([40, 38, 36, 35, 33, 36], [30, 30, 30, 30, 30, 30])  # dün mesafe 3
        self.assertFalse(h.sinyal(cer)["var"])

    def test_donus_yoksa_sinyal_yok(self):
        cer = _bant_cercevesi([40, 38, 36, 33, 31.5, 31.0], [30, 30, 30, 30, 30, 30])  # bugün düşüyor
        self.assertFalse(h.sinyal(cer)["var"])

    def test_dun_dip_degilse_sinyal_yok(self):
        cer = _bant_cercevesi([40, 38, 36, 31, 31.5, 33], [30, 30, 30, 30, 30, 30])  # dün yükselmişti
        self.assertFalse(h.sinyal(cer)["var"])

    def test_esik_tam_2_bolgede_sayilir(self):
        cer = _bant_cercevesi([40, 38, 36, 34, 32, 33], [30, 30, 30, 30, 30, 30])
        self.assertTrue(h.sinyal(cer)["var"])


class SeviyeTesti(unittest.TestCase):
    def test_seviyeler(self):
        sv = h.seviyeler(giris=100.0, atr=4.0, portfoy=2500.0)
        self.assertAlmostEqual(sv["stop"], 94.0)
        self.assertAlmostEqual(sv["r"], 6.0)
        self.assertAlmostEqual(sv["stop_yuzde"], 6.0)
        self.assertEqual(sv["adet"], 4)  # floor(25 / 6)
        self.assertAlmostEqual(sv["iki_r"], 112.0)
        self.assertAlmostEqual(sv["risk_usd"], 24.0)

    def test_adet_asagi_yuvarlanir_ve_sifir_olabilir(self):
        sv = h.seviyeler(giris=1000.0, atr=20.0, portfoy=2500.0)  # R = 30 > 25
        self.assertEqual(sv["adet"], 0)


def _aday(sembol, stop_yuzde, adet=5, r=5.0, bilanco_isgunu=None):
    return {"sembol": sembol, "stop_yuzde": stop_yuzde, "adet": adet, "r": r,
            "risk_usd": adet * r, "bilanco_isgunu": bilanco_isgunu}


class AdaySecimiTesti(unittest.TestCase):
    def test_en_kucuk_stoplu_uc_aday_uygun_kalanlar_yedek(self):
        adaylar = [_aday(s, y) for s, y in [("A", 5), ("B", 3), ("C", 7), ("D", 4), ("E", 6)]]
        sonuc = h.aday_sec(adaylar, rejim="YESIL", acik_sayi=0, acik_risk_usd=0.0, portfoy=2500.0)
        durum = {a["sembol"]: a["durum"] for a in sonuc}
        self.assertEqual(durum, {"B": "uygun", "D": "uygun", "A": "uygun", "E": "yedek", "C": "yedek"})

    def test_kirmizi_rejimde_hic_uygun_yok(self):
        sonuc = h.aday_sec([_aday("A", 3)], rejim="KIRMIZI", acik_sayi=0, acik_risk_usd=0.0,
                           portfoy=2500.0)
        self.assertEqual(sonuc[0]["durum"], "elendi")
        self.assertIn("rejim", sonuc[0]["sebep"])

    def test_bilanco_yakin_ve_genis_stop_elenir(self):
        adaylar = [_aday("A", 3, bilanco_isgunu=4), _aday("B", 9), _aday("C", 3, bilanco_isgunu=5)]
        durum = {a["sembol"]: (a["durum"], a.get("sebep")) for a in
                 h.aday_sec(adaylar, "YESIL", 0, 0.0, 2500.0)}
        self.assertEqual(durum["A"][0], "elendi")
        self.assertIn("bilanço", durum["A"][1])
        self.assertEqual(durum["B"][0], "elendi")
        self.assertIn("%8", durum["B"][1])
        self.assertEqual(durum["C"][0], "uygun")

    def test_adet_sifirsa_elenir(self):
        sonuc = h.aday_sec([_aday("A", 3, adet=0)], "YESIL", 0, 0.0, 2500.0)
        self.assertEqual(sonuc[0]["durum"], "elendi")

    def test_bilinmeyen_bilanco_elemez_ama_isaretler(self):
        sonuc = h.aday_sec([_aday("A", 3, bilanco_isgunu=None)], "YESIL", 0, 0.0, 2500.0)
        self.assertEqual(sonuc[0]["durum"], "uygun")

    def test_bes_acik_pozisyonda_yeni_uygun_yok(self):
        sonuc = h.aday_sec([_aday("A", 3)], "YESIL", acik_sayi=5, acik_risk_usd=0.0, portfoy=2500.0)
        self.assertEqual(sonuc[0]["durum"], "elendi")
        self.assertIn("risk tavanı", sonuc[0]["sebep"])

    def test_toplam_risk_tavani_asilamaz(self):
        # açık risk 105 USD (%4,2); 25 USD'lik aday 130 > 125 → sığmaz
        sonuc = h.aday_sec([_aday("A", 3, adet=5, r=5.0)], "YESIL", acik_sayi=3,
                           acik_risk_usd=105.0, portfoy=2500.0)
        self.assertEqual(sonuc[0]["durum"], "elendi")

    def test_girdi_listesi_degismez(self):
        adaylar = [_aday("A", 3)]
        h.aday_sec(adaylar, "YESIL", 0, 0.0, 2500.0)
        self.assertNotIn("durum", adaylar[0])

    def test_v3_trend_disi_elenir_sebep_sadece_trend_kosulu(self):
        aday = {**_aday("A", 3), "trend_kategori": "DISI", "trend_eksik": ["fiyat ≤ EMA100", "EMA50 ≤ EMA200"]}
        sonuc = h.aday_sec([aday], "YESIL", 0, 0.0, 2500.0)
        self.assertEqual(sonuc[0]["durum"], "elendi")
        self.assertEqual(sonuc[0]["sebep"], "trend dışı (EMA50 ≤ EMA200)")

    def test_v3_ema100_altindaki_trend_uygun_kalir(self):
        aday = {**_aday("A", 3), "trend_kategori": "TREND", "trend_eksik": ["fiyat ≤ EMA100"]}
        self.assertEqual(h.aday_sec([aday], "YESIL", 0, 0.0, 2500.0)[0]["durum"], "uygun")

    def test_v3_trend_bilgisi_yoksa_elemez(self):
        # eski çağıranlar (trend alanı yok) davranış değiştirmesin
        self.assertEqual(h.aday_sec([_aday("A", 3)], "YESIL", 0, 0.0, 2500.0)[0]["durum"], "uygun")


GECEN_ALAN = {"market_cap_basic": 5e9, "recommendation_mark": 1.4, "Perf.Y": 80.0, "close": 100.0,
              "EMA100": 90.0, "EMA200": 80.0, "EMA50|1W": 85.0, "EMA21|1W": 95.0,
              "average_volume_90d_calc": 2e6, "average_volume_10d_calc": 1e6, "ADRP": 4.2}


class GozlemTesti(unittest.TestCase):
    def test_butun_filtreleri_gecen_takilmaz(self):
        self.assertEqual(h.evren_takilmalari(GECEN_ALAN), [])

    def test_ema200_altinda_ve_perf_dusuk_takilir(self):
        alan = {**GECEN_ALAN, "EMA200": 120.0, "Perf.Y": 10.0}
        self.assertEqual(h.evren_takilmalari(alan), ["1 yıllık performans ≤ %30", "fiyat ≤ EMA200 (günlük)"])

    def test_analist_notu_takipcinin_al_esigiyle_ayni(self):
        # FTNT 1,95 → TradingView "Neutral" (2026-09-28); takipçideki en yüksek not 1,625 (KLIC)
        self.assertIn("analist notu Al/Güçlü al değil",
                      h.evren_takilmalari({**GECEN_ALAN, "recommendation_mark": 1.945652}))
        self.assertEqual(h.evren_takilmalari({**GECEN_ALAN, "recommendation_mark": 1.625}), [])

    def test_eksik_veri_takilma_sayilir(self):
        self.assertIn("ADR ≤ %3,5", h.evren_takilmalari({**GECEN_ALAN, "ADRP": None}))

    def test_girdi_degismez(self):
        alan = dict(GECEN_ALAN)
        h.evren_takilmalari(alan)
        self.assertEqual(alan, GECEN_ALAN)

    def test_strateji_notlari_hepsini_sayar(self):
        aday = {**_aday("A", 9.5, adet=0, bilanco_isgunu=2), "sma200_ustunde": False}
        notlar = h.strateji_notlari(aday, "KIRMIZI")
        self.assertEqual(len(notlar), 5)

    def test_strateji_notlari_v3_trend_disini_sayar(self):
        aday = {**_aday("A", 3), "trend_kategori": "DISI", "trend_eksik": ["EMA50 ≤ EMA200"]}
        self.assertIn("trend dışı (EMA50 ≤ EMA200)", h.strateji_notlari(aday, "YESIL"))

    def test_yakin_sinyal_bolgede_donus_yok(self):
        cer = _bant_cercevesi([40, 38, 36, 34, 33, 31.5], [30] * 6)  # bugün mesafe 1.5, düşüyor
        self.assertTrue(h.yakin_sinyal(cer))

    def test_sinyal_varsa_yakin_degil(self):
        cer = _bant_cercevesi([40, 38, 36, 33, 31.5, 34], [30] * 6)
        self.assertFalse(h.yakin_sinyal(cer))


class CikisTesti(unittest.TestCase):
    def _poz(self, **k):
        return {"sembol": "X", "giris": 100.0, "stop": 94.0, **k}

    def test_stopa_gelirse_cik(self):
        c = h.cikis_kontrolu(self._poz(), dusuk=93.5, rsi=40, orta=45, gecen_isgunu=3, bilanco_isgunu=None)
        self.assertEqual(c["karar"], "CIK")
        self.assertIn("stop", c["sebep"])

    def test_rsi_orta_bandi_gecince_cik(self):
        c = h.cikis_kontrolu(self._poz(), dusuk=99, rsi=50, orta=45, gecen_isgunu=3, bilanco_isgunu=None)
        self.assertEqual(c["karar"], "CIK")
        self.assertIn("orta", c["sebep"])

    def test_sure_dolunca_cik(self):
        c = h.cikis_kontrolu(self._poz(), dusuk=99, rsi=40, orta=45, gecen_isgunu=15, bilanco_isgunu=None)
        self.assertEqual(c["karar"], "CIK")
        self.assertIn("15", c["sebep"])

    def test_bilanco_oncesi_son_gun_cik(self):
        c = h.cikis_kontrolu(self._poz(), dusuk=99, rsi=40, orta=45, gecen_isgunu=3, bilanco_isgunu=1)
        self.assertEqual(c["karar"], "CIK")
        self.assertIn("bilanço", c["sebep"])

    def test_kosul_yoksa_tut(self):
        c = h.cikis_kontrolu(self._poz(), dusuk=99, rsi=40, orta=45, gecen_isgunu=3, bilanco_isgunu=10)
        self.assertEqual(c["karar"], "TUT")


class TakvimTesti(unittest.TestCase):
    def test_nyse_tatilleri_2026(self):
        tatiller = h.nyse_tatilleri(2026)
        for gun in (date(2026, 1, 1), date(2026, 4, 3), date(2026, 7, 3), date(2026, 11, 26),
                    date(2026, 12, 25), date(2026, 6, 19), date(2026, 9, 7)):
            self.assertIn(gun, tatiller)

    def test_isgunu_farki_tatili_ve_haftasonunu_atlar(self):
        # Cuma 2 Eki 2026 → Perşembe 8 Eki 2026: Pzt, Sal, Çar, Per = 4 işlem günü
        self.assertEqual(h.isgunu_farki(date(2026, 10, 2), date(2026, 10, 8)), 4)
        # 25 Kasım Çar → 27 Kasım Cum: 26'sı Şükran Günü
        self.assertEqual(h.isgunu_farki(date(2026, 11, 25), date(2026, 11, 27)), 1)


class HesaplaTesti(unittest.TestCase):
    def test_hesapla_sayilari_yuvarlanmis_ve_tam_dondurur(self):
        n = 60
        kapanis = 100 + np.sin(np.arange(n) / 3.0) * 5
        df = pd.DataFrame({"Open": kapanis, "High": kapanis + 1, "Low": kapanis - 1, "Close": kapanis},
                          index=pd.bdate_range("2026-01-02", periods=n))
        sonuc = h.gosterge_cercevesi(df)
        for kolon in ("rsi", "orta", "alt", "ust", "mesafe", "atr", "sma200"):
            self.assertIn(kolon, sonuc.columns)
        self.assertFalse(math.isnan(sonuc["rsi"].iloc[-1]))


class TrendKategorisiTesti(unittest.TestCase):
    """Bilgi etiketi (kural değil): fiyat > EMA200, tercihen > EMA100, ve EMA50 > EMA200 (günlük)."""

    def test_uc_kosul_da_tamam_guclu_trend(self):
        k = h.trend_kategorisi(kapanis=110, ema50=105, ema100=100, ema200=90)
        self.assertEqual(k["kategori"], "GUCLU_TREND")
        self.assertEqual(k["eksik"], [])

    def test_ema100_altinda_ama_digerleri_tamam_trend(self):
        k = h.trend_kategorisi(kapanis=98, ema50=105, ema100=100, ema200=90)
        self.assertEqual(k["kategori"], "TREND")
        self.assertEqual(k["eksik"], ["fiyat ≤ EMA100"])

    def test_ema50_ema200_altinda_kategori_disi(self):
        k = h.trend_kategorisi(kapanis=110, ema50=88, ema100=100, ema200=90)
        self.assertEqual(k["kategori"], "DISI")
        self.assertEqual(k["eksik"], ["EMA50 ≤ EMA200"])

    def test_fiyat_ema200_altinda_kategori_disi(self):
        k = h.trend_kategorisi(kapanis=85, ema50=95, ema100=100, ema200=90)
        self.assertEqual(k["kategori"], "DISI")
        self.assertIn("fiyat ≤ EMA200", k["eksik"])

    def test_eksik_veri_kategori_disi(self):
        self.assertEqual(h.trend_kategorisi(110, float("nan"), 100, 90)["kategori"], "DISI")

    def test_gosterge_cercevesi_ema_kolonlari_ustel(self):
        # EMA(kapanış, n): alfa = 2/(n+1), özyinelemeli (TradingView ta.ema) — sabit seride değer sabittir
        df = pd.DataFrame({"Open": 10.0, "High": 11.0, "Low": 9.0, "Close": 10.0, "Volume": 1},
                          index=pd.date_range("2024-01-01", periods=300, freq="B"))
        cer = h.gosterge_cercevesi(df)
        for kolon in ("ema50", "ema100", "ema200"):
            self.assertAlmostEqual(cer[kolon].iloc[-1], 10.0)
        artan = df.assign(Close=np.arange(300, dtype=float))
        son = h.gosterge_cercevesi(artan).iloc[-1]
        self.assertGreater(son["ema50"], son["ema100"])
        self.assertGreater(son["ema100"], son["ema200"])


if __name__ == "__main__":
    unittest.main()
