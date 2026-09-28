"""İşlem günlüğü hesabı — ağ yok. Sayıyı betik hesaplar, gc-gunluk ajanı yorumlar."""
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import gunluk_hesap as g  # noqa: E402

BASLIK = "sembol,sinyal_tipi,giris_tarihi,giris,ilk_stop,cikis_tarihi,cikis,adet,cikis_sebebi,strateji_surumu,gercek_mi\n"


def _islem(**k):
    temel = {"sembol": "A", "sinyal_tipi": "DOKUNDU", "giris_tarihi": "2026-10-01", "giris": 100.0,
             "ilk_stop": 94.0, "cikis_tarihi": "2026-10-06", "cikis": 106.0, "adet": 10,
             "cikis_sebebi": "hedef", "strateji_surumu": "v1", "gercek_mi": False}
    return {**temel, **k}


class OkumaTesti(unittest.TestCase):
    def test_csv_okunur_ve_turler_cevrilir(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "islemler.csv"
            yol.write_text(BASLIK + "abc,ALTINA_GECTI,2026-10-01,100,94,2026-10-06,106,10,hedef,v1,evet\n",
                           encoding="utf-8")
            islemler = g.islemleri_oku(yol)
        self.assertEqual(islemler[0]["sembol"], "ABC")
        self.assertTrue(islemler[0]["gercek_mi"])
        self.assertEqual(islemler[0]["adet"], 10)

    def test_dosya_yoksa_bos(self):
        self.assertEqual(g.islemleri_oku(Path("/yok/islemler.csv")), [])


class HesapTesti(unittest.TestCase):
    def test_r_ve_net(self):
        s = g.islem_sonucu(_islem())
        self.assertAlmostEqual(s["r"], 1.0)                    # (106-100)/(100-94)
        self.assertAlmostEqual(s["net_usd"], 60.0 - 3.0)       # 2 emir × 1.5 USD
        self.assertAlmostEqual(s["net_r"], 57.0 / 60.0)
        self.assertEqual(s["isgunu"], 3)                        # 1 Eki Per → 6 Eki Sal

    def test_ozet_tiplere_ayrilir(self):
        islemler = [g.islem_sonucu(_islem()),
                    g.islem_sonucu(_islem(sinyal_tipi="ALTINA_GECTI", cikis=97.0, cikis_sebebi="stop"))]
        o = g.ozet(islemler)
        self.assertEqual(o["tum"]["islem"], 2)
        self.assertEqual(o["DOKUNDU"]["islem"], 1)
        self.assertEqual(o["ALTINA_GECTI"]["kazanma_orani"], 0.0)
        self.assertAlmostEqual(o["ALTINA_GECTI"]["en_buyuk_kayip_r"], -0.5)
        self.assertTrue(o["tum"]["orneklem_kucuk"])

    def test_bos_ozet(self):
        self.assertEqual(g.ozet([])["tum"], {"islem": 0, "orneklem_kucuk": True})


class KuralDisiTesti(unittest.TestCase):
    def test_sure_asimi(self):
        s = g.islem_sonucu(_islem(cikis_tarihi="2026-10-30", cikis_sebebi="sure"))
        self.assertTrue(any("süre" in x for x in g.kural_ihlalleri(s)))

    def test_stop_altinda_cikis(self):
        s = g.islem_sonucu(_islem(cikis=90.0, cikis_sebebi="stop"))
        self.assertTrue(any("stop altında" in x for x in g.kural_ihlalleri(s)))

    def test_stop_ustunde_zararla_elle_cikis(self):
        s = g.islem_sonucu(_islem(cikis=98.0, cikis_sebebi="elle"))
        self.assertTrue(any("tanımsız çıkış" in x for x in g.kural_ihlalleri(s)))

    def test_eksik_tip_ve_surum(self):
        s = g.islem_sonucu(_islem(sinyal_tipi="", strateji_surumu=""))
        ihlal = g.kural_ihlalleri(s)
        self.assertTrue(any("sinyal tipi" in x for x in ihlal))
        self.assertTrue(any("sürüm" in x for x in ihlal))

    def test_temiz_islem(self):
        self.assertEqual(g.kural_ihlalleri(g.islem_sonucu(_islem())), [])


class KarsilastirmaTesti(unittest.TestCase):
    def test_geri_testten_belirgin_kotu_isaretlenir(self):
        gercek = {"islem": 12, "beklenti_net_r": -0.4}
        test = {"islem": 500, "beklenti_net_r": 0.06}
        k = g.karsilastir(gercek, test)
        self.assertTrue(k["belirgin_kotu"])
        self.assertAlmostEqual(k["fark_r"], -0.46)

    def test_az_islemde_isaretlenmez(self):
        self.assertFalse(g.karsilastir({"islem": 3, "beklenti_net_r": -1.0}, {"islem": 500,
                                                                             "beklenti_net_r": 0.1})["belirgin_kotu"])


if __name__ == "__main__":
    unittest.main()
