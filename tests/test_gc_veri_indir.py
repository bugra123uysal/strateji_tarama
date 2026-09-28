"""barlari_indir: Yahoo toplu isteği kısınca (hepsi 'possibly delisted') yeniden dener — ağ yok."""
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import gc_veri as v  # noqa: E402


def _cerceve(semboller, dolu):
    """yfinance group_by='ticker' biçimi: (sembol, kolon) çok katmanlı kolonlar."""
    gunler = pd.date_range("2026-09-21", periods=5, freq="B")
    kolonlar = pd.MultiIndex.from_product([semboller, ["Open", "High", "Low", "Close", "Volume"]])
    deger = 1.0 if dolu else float("nan")
    return pd.DataFrame(deger, index=gunler, columns=kolonlar)


class YenidenDenemeTesti(unittest.TestCase):
    def _sahte_yf(self, yanitlar):
        cagrilar = []

        def download(semboller, **_):
            cagrilar.append(list(semboller))
            return _cerceve(list(semboller), yanitlar.pop(0))
        return types.SimpleNamespace(download=download), cagrilar

    def test_ilk_istek_bos_donerse_hatalilar_paketlerle_yeniden_denenir(self):
        yf, cagrilar = self._sahte_yf([False, True, True])
        semboller = [f"S{i}" for i in range(5)]
        with mock.patch.dict(sys.modules, {"yfinance": yf}), mock.patch.object(v.time, "sleep"), \
                mock.patch.object(v, "YENIDEN_PAKET", 3):
            barlar, hatali = v.barlari_indir(semboller)
        self.assertEqual(hatali, [])
        self.assertEqual(sorted(barlar), semboller)
        self.assertEqual([len(c) for c in cagrilar], [5, 3, 2])

    def test_yeniden_denemede_de_bossa_hatali_listelenir(self):
        yf, _ = self._sahte_yf([False, False])
        with mock.patch.dict(sys.modules, {"yfinance": yf}), mock.patch.object(v.time, "sleep"):
            barlar, hatali = v.barlari_indir(["SPY", "QQQ"])
        self.assertEqual(barlar, {})
        self.assertEqual(hatali, ["SPY", "QQQ"])

    def test_ilk_istek_tam_ise_yeniden_denenmez(self):
        yf, cagrilar = self._sahte_yf([True])
        with mock.patch.dict(sys.modules, {"yfinance": yf}), mock.patch.object(v.time, "sleep") as uyku:
            _, hatali = v.barlari_indir(["SPY", "QQQ"])
        self.assertEqual(hatali, [])
        self.assertEqual(len(cagrilar), 1)
        uyku.assert_not_called()


if __name__ == "__main__":
    unittest.main()
