"""tarama_cek ve geri_test'in ağa çıkmayan parçaları — ağ yok, para harcamaz."""
import sys
import tempfile
import unittest
import unittest.mock
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import geri_test as g  # noqa: E402
import tarama_cek as t  # noqa: E402


class AcilisIsaretiTesti(unittest.TestCase):
    def test_stop_altinda_gap(self):
        self.assertEqual(t.acilis_isareti(93.0, stop=94.0, iki_r=112.0), "GAP — girilmez")

    def test_iki_r_ustunde_kacti(self):
        self.assertEqual(t.acilis_isareti(113.0, stop=94.0, iki_r=112.0), "kaçtı — kovalanmaz")

    def test_arada_normal(self):
        self.assertEqual(t.acilis_isareti(101.0, stop=94.0, iki_r=112.0), "normal")

    def test_fiyat_yoksa_soyler(self):
        self.assertEqual(t.acilis_isareti(None, stop=94.0, iki_r=112.0), "premarket fiyatı yok")


class V2IleGelenTesti(unittest.TestCase):
    def test_yalniz_v1_esigini_gecemeyenler_performansa_gore_sirali(self):
        evren = [{"sembol": "MU", "perf_y": 565.27}, {"sembol": "TARS", "perf_y": 35.664},
                 {"sembol": "SDRL", "perf_y": 46.6}, {"sembol": "FIVE", "perf_y": 50.0},
                 {"sembol": "CSV", "perf_y": None}]
        self.assertEqual(t.v2_ile_gelenler(evren),
                         [{"sembol": "FIVE", "perf_y": 50.0}, {"sembol": "SDRL", "perf_y": 46.6},
                          {"sembol": "TARS", "perf_y": 35.66}])


class TrendGruplariTesti(unittest.TestCase):
    def test_evren_uc_gruba_ayrilir_verisi_olmayan_atlanir(self):
        def cer(kapanis, e50, e100, e200):
            return pd.DataFrame({"Close": [kapanis], "ema50": [e50], "ema100": [e100], "ema200": [e200]})
        evren = [{"sembol": s} for s in ("A", "B", "C", "YOK")]
        cerceveler = {"A": cer(110, 105, 100, 90), "B": cer(98, 105, 100, 90), "C": cer(110, 80, 100, 90)}
        self.assertEqual(t.trend_gruplari(evren, cerceveler),
                         {"GUCLU_TREND": ["A"], "TREND": ["B"],
                          "DISI": [{"sembol": "C", "eksik": ["EMA50 ≤ EMA200"]}]})


class PozisyonTesti(unittest.TestCase):
    def test_csv_okunur_ve_acik_risk_hesaplanir(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "pozisyonlar.csv"
            yol.write_text("sembol,giris_tarihi,giris,adet,stop,strateji_surumu\n"
                           "abc,2026-09-21,100,4,94,v1\n"
                           "XYZ,2026-09-22,50,10,51,v1\n", encoding="utf-8")
            poz = t.pozisyonlari_oku(yol)
        self.assertEqual([p["sembol"] for p in poz], ["ABC", "XYZ"])
        self.assertEqual(poz[0]["giris_tarihi"], date(2026, 9, 21))
        self.assertAlmostEqual(t.acik_risk_usd(poz), 24.0)  # XYZ stop girişin üstünde → risk 0

    def test_dosya_yoksa_bos_liste(self):
        self.assertEqual(t.pozisyonlari_oku(Path("/yok/pozisyonlar.csv")), [])


class KapanmisBarTesti(unittest.TestCase):
    def test_piyasa_acikken_bugunku_yarim_bar_atilir(self):
        from datetime import datetime
        idx = pd.DatetimeIndex(["2026-09-24", "2026-09-25"])
        barlar = {"SPY": pd.DataFrame({"Close": [1.0, 2.0]}, index=idx)}
        gun_ici = datetime(2026, 9, 25, 11, 0, tzinfo=t.NY)
        aksam = datetime(2026, 9, 25, 16, 15, tzinfo=t.NY)
        self.assertEqual(len(t._kapanmis_barlar(barlar, gun_ici)["SPY"]), 1)
        self.assertEqual(len(t._kapanmis_barlar(barlar, aksam)["SPY"]), 2)


def _cerceve(kapanis, dusuk=None, acilis=None, rsi=None, orta=None):
    n = len(kapanis)
    return pd.DataFrame({"Open": acilis or kapanis, "High": kapanis, "Low": dusuk or kapanis, "Close": kapanis,
                         "rsi": rsi or [40.0] * n, "orta": orta or [50.0] * n},
                        index=pd.bdate_range("2026-01-05", periods=n))


class GeriTestCikisTesti(unittest.TestCase):
    def test_stop_gapte_acilistan_cikar(self):
        cer = _cerceve([100, 100, 90], dusuk=[99, 99, 88], acilis=[100, 100, 91])
        self.assertEqual(g._cikis(cer, 1, stop=95.0, bilancolar=[]), (2, 91, "stop"))

    def test_rsi_orta_ustunde_hedef(self):
        cer = _cerceve([100, 101, 103], rsi=[40, 45, 55], orta=[50, 50, 50])
        self.assertEqual(g._cikis(cer, 1, stop=95.0, bilancolar=[]), (2, 103, "hedef"))

    def test_on_bes_gunde_sure(self):
        cer = _cerceve([100.0] * 20)
        j, _, sebep = g._cikis(cer, 1, stop=95.0, bilancolar=[])
        self.assertEqual((j, sebep), (16, "sure"))

    def test_bilanco_oncesi_son_gun(self):
        cer = _cerceve([100.0] * 10)
        bilanco = cer.index[4].date()
        j, _, sebep = g._cikis(cer, 1, stop=95.0, bilancolar=[bilanco])
        self.assertEqual((j, sebep), (3, "bilanco"))

    def test_veri_biterse_none(self):
        self.assertIsNone(g._cikis(_cerceve([100.0] * 5), 1, stop=95.0, bilancolar=[]))


class IstatistikTesti(unittest.TestCase):
    def test_ozet_degerleri(self):
        islemler = [{"getiri_yuzde": 4.0, "net_yuzde": 3.5, "r": 1.0, "net_r": 0.9, "net_usd": 22.0, "sebep": "hedef"},
                    {"getiri_yuzde": -2.0, "net_yuzde": -2.5, "r": -0.5, "net_r": -0.6, "net_usd": -15.0, "sebep": "stop"}]
        o = g.istatistik(islemler)
        self.assertEqual(o["islem"], 2)
        self.assertEqual(o["kazanma_orani"], 50.0)
        self.assertEqual(o["beklenti_yuzde"], 1.0)
        self.assertEqual(o["en_buyuk_kayip_yuzde"], -2.0)
        self.assertEqual(o["toplam_net_usd"], 7.0)
        self.assertEqual(o["cikis_sebepleri"], {"hedef": 1, "stop": 1})

    def test_bos_liste(self):
        self.assertEqual(g.istatistik([]), {"islem": 0})

    def test_rapor_uyari_ile_baslar(self):
        sonuc = {"strateji_surumu": "v1", "tarih": "2026-09-27", "uyari": g.UYARI, "donem": "x",
                 "evren_sayisi": 1, "evren_kaynagi": "csv", "portfoy_usd": 2500.0, "komisyon_emir_usd": 1.5,
                 "ozet": {"tum": {"islem": 0}, "DOKUNDU": {"islem": 0}, "ALTINA_GECTI": {"islem": 0}},
                 "elenen_sinyaller": {}, "bilanco_verisi_yok": [], "verisi_yok": []}
        metin = g.rapor_metni(sonuc)
        self.assertIn("hayatta kalma yanlılığı", metin.splitlines()[2])


class GeriTestV3TrendElemesiTesti(unittest.TestCase):
    def test_trend_disi_sinyal_islem_olmaz_sayilir(self):
        cer = _cerceve([100.0] * 30)
        cer = cer.assign(ema50=90.0, ema100=95.0, ema200=99.0, atr=2.0, Open=100.0)  # EMA50 < EMA200
        sayac = {}
        with unittest.mock.patch.object(g.h, "sinyal", return_value={"var": True, "tip": "DOKUNDU"}):
            islemler = g.sembol_islemleri("X", cer, {d: "YESIL" for d in cer.index.date}, [], cer.index[0].date(),
                                          sayac)
        self.assertEqual(islemler, [])
        self.assertGreater(sayac.get("trend_disi", 0), 0)


class TrendKirilimiTesti(unittest.TestCase):
    """Geri testte EMA trend koşulu ile / olmadan — kural değil, karşılaştırma."""

    def _islem(self, trend, tip, getiri):
        return {"trend": trend, "tip": tip, "getiri_yuzde": getiri, "net_yuzde": getiri, "r": getiri,
                "net_r": getiri, "net_usd": getiri, "sebep": "hedef"}

    def test_kirilim_filtreli_ve_filtresiz(self):
        islemler = [self._islem("GUCLU_TREND", "DOKUNDU", 2.0), self._islem("TREND", "ALTINA_GECTI", 1.0),
                    self._islem("DISI", "DOKUNDU", -3.0)]
        k = g.trend_kirilimi(islemler)
        self.assertEqual(k["filtresiz"]["tum"]["islem"], 3)
        self.assertEqual(k["trend_kosulu"]["tum"]["islem"], 2)       # GÜÇLÜ TREND + TREND
        self.assertEqual(k["guclu_trend"]["tum"]["islem"], 1)
        self.assertEqual(k["trend_disi"]["tum"]["islem"], 1)
        self.assertEqual(k["trend_kosulu"]["DOKUNDU"]["islem"], 1)
        self.assertEqual(k["trend_disi"]["tum"]["beklenti_yuzde"], -3.0)

    def test_rapora_trend_tablosu_eklenir(self):
        sonuc = {"strateji_surumu": "v2", "tarih": "2026-09-28", "uyari": g.UYARI, "donem": "x",
                 "evren_sayisi": 1, "evren_kaynagi": "tarayici", "portfoy_usd": 50000.0, "komisyon_emir_usd": 1.5,
                 "ozet": {"tum": {"islem": 0}, "DOKUNDU": {"islem": 0}, "ALTINA_GECTI": {"islem": 0}},
                 "trend_kirilimi": g.trend_kirilimi([self._islem("DISI", "DOKUNDU", -3.0)]),
                 "elenen_sinyaller": {}, "bilanco_verisi_yok": [], "verisi_yok": []}
        metin = g.rapor_metni(sonuc)
        self.assertIn("EMA trend koşulu ile / olmadan", metin)
        self.assertIn("| Trend dışı | Tümü | 1 |", metin)


def _gosterge_cercevesi(n=5, mesafe=1.0):
    return pd.DataFrame({"Close": 100.0, "Low": 99.0, "rsi": 35.0, "orta": 45.0, "alt": 34.0, "ust": 56.0,
                         "mesafe": mesafe, "atr": 2.0, "sma200": 90.0, "ema50": 95.0, "ema100": 97.0,
                         "ema200": 92.0}, index=pd.bdate_range("2026-09-21", periods=n))


class IzlemeListesiTesti(unittest.TestCase):
    def test_dosya_okunur_yorum_ve_bos_satir_atlanir(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "izleme.txt"
            yol.write_text("# liste: bolingir e değenler\n# açıklama\n\nNASDAQ:FIVE\n urgn \n", encoding="utf-8")
            ad, semboller = t.izleme_oku(yol)
        self.assertEqual(ad, "bolingir e değenler")
        self.assertEqual(semboller, [{"sembol": "FIVE", "tv_sembol": "NASDAQ:FIVE"},
                                     {"sembol": "URGN", "tv_sembol": "URGN"}])

    def test_dosya_yoksa_bos(self):
        self.assertEqual(t.izleme_oku(Path("yok/izleme.txt")), (None, []))

    def _satirlar(self, sinyal, yakin=False, evren=()):
        izleme = [{"sembol": "FIVE", "tv_sembol": "NASDAQ:FIVE"}, {"sembol": "URGN", "tv_sembol": "NASDAQ:URGN"}]
        bilanco = {"bilanco_tarihi": "2026-12-03", "bilanco_tv": None, "bilanco_isgunu": 46, "bilanco_supheli": False}
        with unittest.mock.patch.object(t.h, "sinyal", return_value=sinyal), \
                unittest.mock.patch.object(t.h, "yakin_sinyal", return_value=yakin), \
                unittest.mock.patch.object(t, "_bilanco", return_value=bilanco):
            return t.izleme_listesi(izleme, set(evren), {"FIVE": _gosterge_cercevesi()}, date(2026, 9, 25), "YESIL")

    def test_sinyal_veren_strateji_seviyeleriyle_gelir(self):
        five, urgn = self._satirlar({"var": True, "tip": "ALTINA_GECTI"})
        self.assertEqual((five["durum"], five["sinyal_tipi"]), ("SINYAL", "ALTINA_GECTI"))
        self.assertEqual((five["stop"], five["trend_kategori"]), (97.0, "GUCLU_TREND"))
        self.assertIn("takipçi evreninde değil", five["strateji_notlari"])
        self.assertEqual(urgn, {"sembol": "URGN", "tv_sembol": "NASDAQ:URGN", "durum": "VERI_YOK",
                                "grafik": t.GRAFIK_URL.format("NASDAQ:URGN")})

    def test_bolgede_donus_bekleyen_yakin(self):
        five = self._satirlar({"var": False, "tip": None}, yakin=True, evren={"FIVE"})[0]
        self.assertEqual((five["durum"], five["sinyal_tipi"]), ("YAKIN", None))
        self.assertNotIn("takipçi evreninde değil", five["strateji_notlari"])
        self.assertTrue(five["evrende"])

    def test_sinyal_yok(self):
        self.assertEqual(self._satirlar({"var": False, "tip": None})[0]["durum"], "YOK")


if __name__ == "__main__":
    unittest.main()


class Adim4Testi(unittest.TestCase):
    def test_mesai_gece_yarisini_gecer(self):
        import ayar
        from datetime import datetime
        self.assertTrue(ayar.mesaide_mi(datetime(2026, 11, 3, 0, 15)), "kışın 00:15 TSİ kapanış koşusu")
        self.assertTrue(ayar.mesaide_mi(datetime(2026, 9, 28, 23, 15)))
        self.assertTrue(ayar.mesaide_mi(datetime(2026, 9, 28, 16, 0)))
        self.assertFalse(ayar.mesaide_mi(datetime(2026, 9, 28, 3, 0)))

    def test_gorev_isteme_girer(self):
        import kos
        metin = kos.istem("takim-a", {"description": "x"}, KOK / "takimlar/takim-a/kosu/x.md",
                          "2026-09-28 23:15", gorev="kapanis")
        self.assertIn("Bu koşunun görevi: **kapanis**", metin)
        self.assertEqual(kos._gorev(["gc-tarama", "--gorev", "acilis"]), "acilis")
        self.assertIsNone(kos._gorev(["gc-tarama"]))

    def test_dusuk_oynaklik_uyarisi(self):
        import gc_hesap as h
        self.assertIn("satın alma", h.oynaklik_uyarisi(0.66, 99.74))
        self.assertIsNone(h.oynaklik_uyarisi(2.0, 41.35))


class AjanOzetiTesti(unittest.TestCase):
    def test_ozet_kucuk_ve_uyarili_gozlemi_tasir(self):
        gozlem = [{"sembol": f"G{i}", "uyarilar": ["düşük oynaklık"] if i == 9 else [],
                   "takildigi_filtreler": ["x"]} for i in range(12)]
        veri = {"tarih": "2026-09-28", "veri_kapanisi": "2026-09-28", "strateji_surumu": "v1",
                "rejim_karari": "YESIL", "evren": {"kaynak": "tarayici", "uyari": None, "sayi": 52},
                "sinyal_sayisi": 2, "ozet": {"uygun": 1, "yedek": 0, "elendi": 1},
                "adaylar": [{"sembol": "A", "durum": "uygun", "sebep": None},
                            {"sembol": "B", "durum": "elendi", "sebep": "bilanço yakın"}],
                "pozisyonlar": [], "gozlem": {"adaylar": gozlem}, "gostergeler": {"A": {"son5": []}}}
        o = t.ajan_ozeti(veri)
        self.assertEqual([a["sembol"] for a in o["adaylar"]], ["A"])
        self.assertEqual(o["elenen"], [{"sembol": "B", "sebep": "bilanço yakın"}])
        self.assertEqual([a["sembol"] for a in o["gozlem_incelenecek"]], ["G0", "G1", "G2", "G3", "G4", "G9"])
        self.assertNotIn("gostergeler", o)
        self.assertEqual(o["gozlem_toplam"], 12)
