"""Pano üreticisi — ağ yok. Sayılar veri JSON'undan aynen gelir, ajan notu yalnız metindir."""
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import pano_yaz as p  # noqa: E402


def _aday(sembol="URGN", durum="uygun", **k):
    return {"sembol": sembol, "tv_sembol": f"NASDAQ:{sembol}", "ad": "Ad", "sektor": "Sektör",
            "sinyal_tipi": "DOKUNDU", "kapanis": 41.35, "rsi": 40.53, "alt": 37.47, "giris": 41.35,
            "stop": 38.36, "stop_yuzde": 7.23, "r": 2.99, "adet": 167, "iki_r": 47.33,
            "cikis_kurali": "RSI orta bandı geçince, en geç 15 işlem günü",
            "grafik": f"https://www.tradingview.com/chart/?symbol=NASDAQ:{sembol}", "uyarilar": [],
            "bilanco_tarihi": "2026-11-05", "bilanco_isgunu": 29, "bilanco_supheli": False,
            "durum": durum, "sebep": None if durum == "uygun" else "bilanço yakın", **k}


def _veri(adaylar=(), rejim="YESIL"):
    r = {"kapanis": 700.0, "sma200": 650.0, "rejim": rejim}
    return {"tarih": "2026-09-28", "veri_kapanisi": "2026-09-28", "uretim": "x", "strateji_surumu": "v1",
            "donem": "kâğıt işlem", "portfoy_usd": 50000.0,
            "tavanlar": {"maks_acik_pozisyon": 5, "gunluk_uygun": 3},
            "evren": {"kaynak": "tarayici", "uyari": None, "sayi": 52},
            "rejim": {"SPY": r, "QQQ": r}, "rejim_karari": rejim, "pozisyonlar": [], "pozisyon_verisi_yok": [],
            "acik_pozisyon_sayisi": 0, "acik_risk_usd": 0.0, "acik_risk_yuzde": 0.0,
            "sinyal_sayisi": len(adaylar), "adaylar": list(adaylar), "yakin": [],
            "gozlem": {"aciklama": "KURAL DIŞI", "genis_evren_sayisi": 0, "uyari": None, "adaylar": []}}


class NotDenetimiTesti(unittest.TestCase):
    def test_etiketsiz_ve_kaynaksiz_haber_yakalanir(self):
        notlar = {"adaylar": {"X": {"haber": [{"iddia": "a", "etiket": "?", "kaynak": "https://x"},
                                             {"iddia": "b", "etiket": "✅", "kaynak": ""}]}}}
        sorunlar = p.not_sorunlari(notlar)
        self.assertEqual(len(sorunlar), 2)

    def test_uc_kaynak_fazla(self):
        haber = [{"iddia": "a", "etiket": "🟡", "kaynak": "https://x"}] * 3
        self.assertTrue(p.not_sorunlari({"gozlem": {"X": {"haber": haber}}}))

    def test_dogrulanamayan_kaynaksiz_olabilir(self):
        self.assertEqual(p.not_sorunlari({"adaylar": {"X": {"haber": [{"iddia": "a", "etiket": "⛔"}]}}}), [])


class IzlemeBolumuTesti(unittest.TestCase):
    def _izleme(self):
        return {"liste": "bolingir e değenler", "kaynak": "evren/izleme-listesi.txt", "adaylar": [
            _aday("FIVE", durum="SINYAL", sinyal_tipi="ALTINA_GECTI", trend_kategori="GUCLU_TREND", trend_eksik=[],
                  mesafe=-1.2, evrende=False, strateji_notlari=["takipçi evreninde değil"]),
            _aday("NRIX", durum="YAKIN", sinyal_tipi=None, mesafe=0.8, evrende=True, strateji_notlari=[]),
            {"sembol": "URGN", "tv_sembol": "NASDAQ:URGN", "durum": "VERI_YOK",
             "grafik": "https://www.tradingview.com/chart/?symbol=NASDAQ:URGN"}]}

    def test_ayri_bolumde_liste_adi_ve_durumlar(self):
        metin = p.sayfa({**_veri(), "izleme": self._izleme()}, None, {})
        self.assertIn("İzleme listesi", metin)
        self.assertIn("bolingir e değenler", metin)
        self.assertIn("SİNYAL · ALTINA GEÇTİ", metin)
        self.assertIn("YARIN OLABİLİR", metin)
        self.assertIn("veri alınamadı", metin)
        self.assertIn("takipçi evreninde değil", metin)

    def test_sinyaller_ustte(self):
        metin = p.izleme_bolumu({"izleme": self._izleme()})
        self.assertLess(metin.index("FIVE"), metin.index("NRIX"))
        self.assertLess(metin.index("NRIX"), metin.index("URGN"))

    def test_eski_veride_bolum_yok(self):
        self.assertEqual(p.izleme_bolumu(_veri()), "")


class SayfaTesti(unittest.TestCase):
    def test_sayilar_json_dan_aynen(self):
        metin = p.sayfa(_veri([_aday()]), None, {})
        for sayi in ("41.35", "38.36", "7.23", "2.99", "167", "47.33", "40.53 / 37.47"):
            self.assertIn(sayi, metin)
        self.assertIn("v1", metin)
        self.assertIn(p.UYARI_ALT, metin)

    def test_bos_gun_acikca_yazilir(self):
        self.assertIn("Bugün kurala uyan aday yok.", p.sayfa(_veri(), None, {}))

    def test_kirmizi_rejim_basligi(self):
        self.assertIn("rejim KIRMIZI", p.sayfa(_veri(rejim="KIRMIZI"), None, {}))

    def test_haber_metni_kacislanir_ve_js_baglantisi_atilir(self):
        notlar = {"adaylar": {"URGN": {"haber": [{"iddia": "<script>alert(1)</script>", "etiket": "✅",
                                                   "kaynak": "javascript:alert(1)"}]}}}
        metin = p.sayfa(_veri([_aday()]), None, notlar)
        self.assertNotIn("<script>alert", metin)
        self.assertIn("&lt;script&gt;", metin)
        self.assertNotIn("javascript:", metin)

    def test_elenen_tek_satir_sebepli(self):
        metin = p.sayfa(_veri([_aday("ABC", durum="elendi")]), None, {})
        self.assertIn("<b>ABC</b>", metin)
        self.assertIn("bilanço yakın", metin)

    def test_bilanco_dogrulama_duz_metin_de_olabilir(self):
        # 2026-09-28 23:15 koşusu: ajan alanı sözlük yerine metin yazdı, pano çöktü
        notlar = {"adaylar": {"URGN": {"bilanco_dogrulama": "TipRanks tahmini: 2026-12-01 <b>"}}}
        metin = p.sayfa(_veri([_aday()]), None, notlar)
        self.assertIn("Bilanço doğrulama: TipRanks tahmini: 2026-12-01 &lt;b&gt;", metin)

    def test_bilinmeyen_bilanco(self):
        metin = p.sayfa(_veri([_aday(bilanco_tarihi=None, bilanco_isgunu=None)]), None, {})
        self.assertIn("bilinmiyor — elle kontrol et", metin)

    def test_acilis_bolumu_ust_seritte(self):
        acilis = {"uretim": "09:00", "adaylar": [{"sembol": "URGN", "durum": "uygun", "premarket_fiyat": 37.0,
                                                   "premarket_degisim_yuzde": -10.5, "stop": 38.36, "iki_r": 47.33,
                                                   "isaret": "GAP — girilmez"}], "pozisyonlar": []}
        metin = p.sayfa(_veri([_aday()]), acilis, {})
        self.assertIn("Açılış öncesi güncellemesi", metin)
        self.assertLess(metin.index("Açılış öncesi"), metin.index("İşleme uygun adaylar"))
        self.assertIn("GAP — girilmez", metin)


class V2EvrenTesti(unittest.TestCase):
    """v2 eşiği (1Y > %30) ile evrene giren, v1'de (1Y > %50) olmayacak hisseler panoda görünür."""

    def _v2_veri(self, adaylar=()):
        veri = _veri(adaylar)
        veri["evren"] = {**veri["evren"], "perf_y_esigi": 30.0, "v1_perf_y_esigi": 50.0,
                         "v2_ile_gelen": [{"sembol": "SDRL", "perf_y": 46.6}, {"sembol": "TARS", "perf_y": 35.66}]}
        return veri

    def test_v2_ile_gelenler_bolumu_ve_ust_serit_sayisi(self):
        metin = p.sayfa(self._v2_veri(), None, {})
        self.assertIn("v2 ile evrene girenler", metin)
        for parca in ("SDRL", "46.6", "TARS", "35.66"):
            self.assertIn(parca, metin)
        self.assertIn("v2 ile gelen", metin)
        self.assertIn("1Y performans &gt; %30.0 — toplam 52 hisse, üst sınır yok", metin)

    def test_v2_bandindaki_aday_kartinda_isaret(self):
        metin = p.sayfa(self._v2_veri([_aday("SDRL", perf_y=46.6)]), None, {})
        self.assertIn("v2 bandı · 1Y %46.6", metin)

    def test_v1_esigini_gecen_adayda_isaret_yok(self):
        metin = p.sayfa(self._v2_veri([_aday("MU", perf_y=565.27)]), None, {})
        self.assertNotIn("v2 bandı", metin)

    def test_eski_veri_dosyasi_bozulmaz(self):
        metin = p.sayfa(_veri([_aday()]), None, {})
        self.assertNotIn("v2 ile evrene girenler", metin)
        self.assertNotIn("Trend kategorisi", metin)


class TrendKategorisiPanoTesti(unittest.TestCase):
    def _veri(self, adaylar=()):
        veri = _veri(adaylar)
        veri["evren"] = {**veri["evren"], "trend": {
            "GUCLU_TREND": ["MU", "SNDK"], "TREND": ["FIVE"],
            "DISI": [{"sembol": "XYZ", "eksik": ["EMA50 ≤ EMA200"]}]}}
        return veri

    def test_evren_uc_gruba_ayrilir(self):
        metin = p.sayfa(self._veri(), None, {})
        self.assertIn("Trend kategorisi", metin)
        for parca in ("MU", "SNDK", "FIVE", "XYZ", "EMA50 ≤ EMA200"):
            self.assertIn(parca, metin)
        self.assertLess(metin.index("MU"), metin.index("FIVE"))

    def test_aday_kartinda_trend_cipi_ve_ema_degerleri(self):
        aday = _aday(trend_kategori="GUCLU_TREND", trend_eksik=[], ema50=40.12, ema100=38.5, ema200=33.07)
        metin = p.sayfa(self._veri([aday]), None, {})
        self.assertIn("GÜÇLÜ TREND", metin)
        for sayi in ("40.12", "38.5", "33.07"):
            self.assertIn(sayi, metin)

    def test_kategori_disi_adayda_sebep_gorunur(self):
        aday = _aday(trend_kategori="DISI", trend_eksik=["EMA50 ≤ EMA200"], ema50=30.0, ema100=38.5, ema200=33.0)
        metin = p.sayfa(self._veri([aday]), None, {})
        self.assertIn("trend dışı: EMA50 ≤ EMA200", metin)


if __name__ == "__main__":
    unittest.main()
