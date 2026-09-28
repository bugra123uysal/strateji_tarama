"""Zamanlayıcı — New York saatine göre karar, yaz/kış kayması, tekrar engeli. Ağ yok, görev kurmaz."""
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import zamanla as z  # noqa: E402

TSI = ZoneInfo("Europe/Istanbul")


def tsi(*a):
    return datetime(*a, tzinfo=TSI)


class NyKarariTesti(unittest.TestCase):
    def test_yaz_saatinde_kapanis_2315_tsi(self):
        self.assertEqual(z.ny_gorevi(tsi(2026, 10, 30, 23, 15)), "kapanis")   # 16:15 EDT

    def test_kis_saatinde_2315_tsi_erken_0015_dogru(self):
        self.assertIsNone(z.ny_gorevi(tsi(2026, 11, 2, 23, 15)))              # 15:15 EST — piyasa açık
        self.assertEqual(z.ny_gorevi(tsi(2026, 11, 3, 0, 15)), "kapanis")     # 16:15 EST (Pazartesi)

    def test_acilis_yazin_1600_kisin_1700(self):
        self.assertEqual(z.ny_gorevi(tsi(2026, 10, 30, 16, 0)), "acilis")
        self.assertIsNone(z.ny_gorevi(tsi(2026, 10, 30, 17, 0)))              # 10:00 EDT — piyasa açık
        self.assertIsNone(z.ny_gorevi(tsi(2026, 11, 2, 16, 0)))               # 08:00 EST — erken
        self.assertEqual(z.ny_gorevi(tsi(2026, 11, 2, 17, 0)), "acilis")

    def test_mart_gecisi(self):
        self.assertEqual(z.ny_gorevi(tsi(2027, 3, 13, 0, 15)), "kapanis")     # Cuma 12 Mart 16:15 EST
        self.assertEqual(z.ny_gorevi(tsi(2027, 3, 15, 23, 15)), "kapanis")    # Pzt 15 Mart 16:15 EDT

    def test_hafta_sonu_ve_tatil_bos(self):
        self.assertIsNone(z.ny_gorevi(tsi(2026, 9, 27, 23, 15)))              # Pazar
        self.assertIsNone(z.ny_gorevi(tsi(2026, 11, 26, 16, 0)))              # Şükran Günü

    def test_tetik_saatleri_dort_tane(self):
        self.assertEqual(z.TSI_TETIKLER, ["00:15", "16:00", "17:00", "23:15"])


class TikTesti(unittest.TestCase):
    def test_ayni_gun_ikinci_tetik_kosturmaz(self):
        cagrilar = []
        with tempfile.TemporaryDirectory() as d:
            kayit = Path(d) / "tetik.json"
            ilk = z.tik(tsi(2026, 10, 30, 23, 15), kostur=cagrilar.append, yol=kayit)
            ikinci = z.tik(tsi(2026, 10, 31, 0, 15), kostur=cagrilar.append, yol=kayit)  # aynı NY günü, 17:15
        self.assertEqual(ilk[0], "kostu")
        self.assertEqual(ikinci[0], "tekrar")
        self.assertEqual(cagrilar, [["gc-tarama", "--gorev", "kapanis"]])

    def test_pencere_disi_hicbir_sey_yapmaz(self):
        cagrilar = []
        with tempfile.TemporaryDirectory() as d:
            sonuc = z.tik(tsi(2026, 11, 2, 23, 15), kostur=cagrilar.append, yol=Path(d) / "t.json")
        self.assertEqual(sonuc[0], "bos")
        self.assertEqual(cagrilar, [])

    def test_mesai_disi_telafi_kaydi_dusmez_ertesi_tetik_kosar(self):
        # Yazın 16:15 NY = 23:15 TSİ; bilgisayar 02:00 TSİ'de açıldı → NY 19:00, pencere açık ama mesai kapalı.
        # kos.py koşuyu atlayacağı için kayıt düşülmemeli, yoksa o günün kapanış koşusu kaybolur.
        cagrilar = []
        with tempfile.TemporaryDirectory() as d:
            kayit = Path(d) / "tetik.json"
            gece = z.tik(tsi(2026, 10, 31, 2, 0), kostur=cagrilar.append, yol=kayit)
            self.assertFalse(kayit.exists())
        self.assertEqual(gece[0], "bos")
        self.assertEqual(cagrilar, [])


class GorevXmlTesti(unittest.TestCase):
    def test_gorevler_dogru_argumanla_ve_kacan_tetigi_telafi_eder(self):
        g = z.gorevler()
        tarama, gunluk = g[f"{z.KLASOR}\\gc-tarama"], g[f"{z.KLASOR}\\gc-gunluk"]
        for saat in z.TSI_TETIKLER:
            self.assertIn(f"T{saat}:00", tarama)
        self.assertIn("--tik", tarama)
        self.assertIn("<StartWhenAvailable>true</StartWhenAvailable>", tarama)
        self.assertIn("<Monday />", gunluk)
        self.assertIn("T09:30:00", gunluk)
        self.assertIn("--gunluk", gunluk)


if __name__ == "__main__":
    unittest.main()
