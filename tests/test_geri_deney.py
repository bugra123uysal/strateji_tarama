"""Geri test deneyleri — ağ yok. O günkü evren maskesi ve çıkış varyantları."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import geri_deney as d  # noqa: E402
import geri_test as g  # noqa: E402


def _cer(kapanis, dusuk=None, yuksek=None, acilis=None, rsi=None, orta=None, ust=None, atr=2.0):
    n = len(kapanis)
    return pd.DataFrame({"Open": acilis or kapanis, "High": yuksek or kapanis, "Low": dusuk or kapanis,
                         "Close": kapanis, "rsi": rsi or [40.0] * n, "orta": orta or [50.0] * n,
                         "ust": ust or [60.0] * n, "atr": atr},
                        index=pd.bdate_range("2026-01-05", periods=n))


class HaftalikEmaTesti(unittest.TestCase):
    def test_hafta_ici_gun_ileriye_bakmaz(self):
        kapanis = pd.Series(np.arange(1.0, 31.0), index=pd.bdate_range("2026-01-05", periods=30))
        tam = d.haftalik_ema(kapanis, 3)
        kesik = d.haftalik_ema(kapanis.iloc[:12], 3)   # 12. gün çarşamba: sonraki günler yok
        self.assertAlmostEqual(tam.iloc[11], kesik.iloc[11])

    def test_cuma_degeri_haftalik_ema_ile_ayni(self):
        kapanis = pd.Series(np.arange(1.0, 31.0), index=pd.bdate_range("2026-01-05", periods=30))
        haftalik = kapanis.resample("W-FRI").last().ewm(span=3, adjust=False).mean()
        gunluk = d.haftalik_ema(kapanis, 3)
        self.assertAlmostEqual(gunluk.loc["2026-01-23"], haftalik.loc["2026-01-23"])


class EvrenMaskesiTesti(unittest.TestCase):
    def _cerceve(self, n=300, egim=0.5, aralik=0.05, hacim_artar=False):
        kapanis = pd.Series(100 + egim * np.arange(n), index=pd.bdate_range("2025-01-01", periods=n))
        hacim = np.linspace(2e6, 1e6, n) if not hacim_artar else np.linspace(1e6, 2e6, n)
        df = pd.DataFrame({"Open": kapanis, "High": kapanis * (1 + aralik), "Low": kapanis, "Close": kapanis,
                           "Volume": hacim})
        return df.assign(ema100=kapanis.ewm(span=100, adjust=False).mean(),
                         ema200=kapanis.ewm(span=200, adjust=False).mean())

    def test_guclu_yukselen_hisse_evrende(self):
        self.assertTrue(d.evren_maskesi(self._cerceve()).iloc[-1])

    def test_ilk_yil_bilinmez(self):
        self.assertFalse(d.evren_maskesi(self._cerceve()).iloc[200])  # 252 bar yok → 1Y performans NaN

    def test_dusuk_adr_elenir(self):
        self.assertFalse(d.evren_maskesi(self._cerceve(aralik=0.01)).iloc[-1])

    def test_artan_kisa_hacim_elenir(self):
        self.assertFalse(d.evren_maskesi(self._cerceve(hacim_artar=True)).iloc[-1])

    def test_zayif_performans_elenir(self):
        self.assertFalse(d.evren_maskesi(self._cerceve(egim=0.05)).iloc[-1])


class CikisVaryantiTesti(unittest.TestCase):
    def test_mevcut_geri_test_ile_ayni(self):
        ornekler = [_cer([100, 100, 90], dusuk=[99, 99, 88], acilis=[100, 100, 91]),
                    _cer([100, 101, 103], rsi=[40, 45, 55], orta=[50, 50, 50]),
                    _cer([100.0] * 20)]
        for cer in ornekler:
            beklenen = g._cikis(cer, 1, stop=95.0, bilancolar=[])
            bacak = d.cikis_bacaklari(cer, 1, 100.0, 95.0, [], "mevcut")
            self.assertEqual([(b[0], b[1], b[3]) for b in bacak], [beklenen])
            self.assertEqual(bacak[0][2], 1.0)

    def test_basabas_1r_sonrasi_stop_girise_cekilir(self):
        # giriş 100, stop 95 (R=5); 2. bar 105'e dokunur; 3. bar 99'a düşer → mevcut devam, başa baş 100'den çıkar
        cer = _cer([100, 100, 104, 99, 99], yuksek=[100, 100, 105, 100, 100], dusuk=[100, 100, 103, 99, 99])
        self.assertEqual(d.cikis_bacaklari(cer, 1, 100.0, 95.0, [], "basabas_1r"), [(3, 99.0, 1.0, "basabas")])

    def test_ust_bant_hedefi(self):
        cer = _cer([100, 101, 103, 106], rsi=[40, 45, 55, 65], orta=[50] * 4, ust=[60] * 4)
        self.assertEqual(d.cikis_bacaklari(cer, 1, 100.0, 95.0, [], "ust_bant"), [(3, 106.0, 1.0, "hedef")])

    def test_yarim_iz_iki_bacak(self):
        # 2. barda hedef (yarısı 103); kalan iz stopla taşınır: en yüksek 120, ATR 2 → iz 117; 5. bar 116'ya düşer
        cer = _cer([100, 101, 103, 115, 118, 116], rsi=[40, 45, 55, 60, 65, 60], orta=[50] * 6,
                   yuksek=[100, 101, 103, 116, 120, 118], dusuk=[100, 101, 103, 114, 117, 116])
        self.assertEqual(d.cikis_bacaklari(cer, 1, 100.0, 95.0, [], "yarim_iz"),
                         [(2, 103.0, 0.5, "hedef"), (5, 116.0, 0.5, "iz")])

    def test_yarim_iz_hedefsiz_stop_tek_bacak(self):
        cer = _cer([100, 100, 90], dusuk=[99, 99, 88], acilis=[100, 100, 91])
        self.assertEqual(d.cikis_bacaklari(cer, 1, 100.0, 95.0, [], "yarim_iz"), [(2, 91.0, 1.0, "stop")])

    def test_veri_biterse_none(self):
        self.assertIsNone(d.cikis_bacaklari(_cer([100.0] * 5), 1, 100.0, 95.0, [], "ust_bant"))


class IslemKaydiTesti(unittest.TestCase):
    def test_iki_bacakli_islem_uc_komisyon(self):
        kayit = d.islem_kaydi(100.0, 95.0, 10, [(2, 110.0, 0.5, "hedef"), (5, 120.0, 0.5, "iz")])
        self.assertEqual(kayit["getiri_yuzde"], 15.0)
        self.assertEqual(kayit["r"], 3.0)
        self.assertEqual(kayit["net_usd"], 150.0 - 3 * d.ayar.KOMISYON_EMIR_USD)
        self.assertEqual(kayit["sebep"], "hedef+iz")


if __name__ == "__main__":
    unittest.main()
