"""Windows konsol kodlaması (cp1254) ve ajanın 'hata' sonucunun korunması.

2026-09-28 16:00 açılış koşusu: Görev Zamanlayıcı altında stdout cp1254 idi, `tarama_cek.py`
özet satırındaki '→' karakterinde UnicodeEncodeError ile çöktü; kos.py ise ajanın yazdığı
`son_sonuc: hata`yı 'tamam' ile ezdi.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import kos  # noqa: E402


def _cp1254_ile_kostur(kod):
    ortam = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    ortam["PYTHONIOENCODING"] = "cp1254"
    return subprocess.run([sys.executable, "-c", kod], cwd=str(KOK / "bin"), capture_output=True,
                          env=ortam, timeout=60)


class KonsolKodlamasiTesti(unittest.TestCase):
    def test_cp1254_konsolda_ayar_iceren_betik_ok_karakterini_basabilir(self):
        sonuc = _cp1254_ile_kostur("import ayar; print('\\u00f6zet \\u2192 yaz\\u0131ld\\u0131 \\u2705')")
        self.assertEqual(sonuc.returncode, 0, sonuc.stderr.decode("utf-8", "replace"))
        self.assertIn("→", sonuc.stdout.decode("utf-8"))

    def test_claude_alt_sureci_utf8_ortamla_baslar(self):
        with mock.patch.object(kos.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            kos._claude_kos("istem", {}, "deneme", Path("/tmp/yok.md"))
        ortam = run.call_args.kwargs["env"]
        self.assertEqual(ortam["PYTHONIOENCODING"], "utf-8")

    def test_pythonutf8_alt_surece_gecmez(self):
        # PYTHONUTF8=1 → yfinance her sembolü 'possibly delisted' döndürdü (2026-09-28 19:04, 19:11)
        with mock.patch.dict(kos.os.environ, {"PYTHONUTF8": "1"}), \
                mock.patch.object(kos.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            kos._claude_kos("istem", {}, "deneme", Path("/tmp/yok.md"))
        self.assertNotIn("PYTHONUTF8", run.call_args.kwargs["env"])


class SonucKorumaTesti(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.kok = Path(self.gecici.name)
        self.kosu = self.kok / "kosu.md"
        self.kosu.write_text("## Bekçi\n", encoding="utf-8")
        self.zaman = "2026-09-28T16:00:02+03:00"

    def tearDown(self):
        self.gecici.cleanup()

    def _belirle(self, durum):
        ayar.durum_guncelle("deneme", durum, self.kok)
        asil = ayar.durum_oku
        with mock.patch.object(kos.ayar, "durum_oku", lambda t, kok=None: asil(t, self.kok)):
            return kos._sonuc_belirle({"hata": False}, "deneme", self.kosu, self.zaman)

    def test_ajan_bu_kosuda_hata_yazdiysa_hata_kalir(self):
        durum = {"son_kosu": self.zaman, "son_sonuc": "hata", "bekci": {"son_karar": "kabul"}}
        self.assertEqual(self._belirle(durum), "hata")

    def test_eski_kosunun_hatasi_bu_kosuyu_etkilemez(self):
        durum = {"son_kosu": "2026-09-27T23:15:00+03:00", "son_sonuc": "hata",
                 "bekci": {"son_karar": "kabul"}}
        self.assertEqual(self._belirle(durum), "tamam")

    def test_bekci_red_verdiyse_red(self):
        durum = {"son_kosu": self.zaman, "son_sonuc": "tamam", "bekci": {"son_karar": "red"}}
        self.assertEqual(self._belirle(durum), "red")


if __name__ == "__main__":
    unittest.main()
