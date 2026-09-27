"""Kurulumun kendi testleri — ağ yok, claude çağrısı yok, para harcamaz.

Kapsam: `.env` önceliği, bekçinin geçersiz OpenAI anahtarında Haiku yedeğine düşmesi,
`bin/takim-olustur.sh` uyarıları, Windows'ta da çalışan repo kilidi ve `.gitignore`.

python3 -m unittest discover -s tests
"""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import bekci  # noqa: E402
import kos  # noqa: E402


def _http_hatasi(kod):
    return urllib.error.HTTPError("https://ornek", kod, "hata", {}, None)


# --- .env kabuğu ezer --------------------------------------------------------

class EnvOnceligiTesti(unittest.TestCase):
    def test_ortam_yukle_kabuktaki_degeri_ezer(self):
        """Proje `.env`'i kazanır: izleyici .env'e ne yazdıysa onu görür."""
        with tempfile.TemporaryDirectory() as d:
            env = Path(d) / ".env"
            env.write_text("OPENAI_API_KEY=dosyadan\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "kabuktan"}, clear=False):
                ayar.ortam_yukle(env)
                self.assertEqual(os.environ["OPENAI_API_KEY"], "dosyadan")

    def test_env_de_olmayan_degisken_ortamda_kalir(self):
        with tempfile.TemporaryDirectory() as d:
            env = Path(d) / ".env"
            env.write_text("OPENAI_API_KEY=dosyadan\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"BASKA_DEGISKEN": "dokunma"}, clear=False):
                ayar.ortam_yukle(env)
                self.assertEqual(os.environ["BASKA_DEGISKEN"], "dokunma")


# --- K5 · bekçi yedeği -------------------------------------------------------

class BekciYedegiTesti(unittest.TestCase):
    def test_openai_401_atlandi_gerekcesi_verir(self):
        with mock.patch.object(bekci.urllib.request, "urlopen", side_effect=_http_hatasi(401)):
            karar = bekci.openai_sor("sk-gecersiz", "istem")
        self.assertEqual(karar["karar"], "atlandi")
        self.assertIn("openai 401", karar["gerekce"])

    def test_gecersiz_anahtar_haiku_yedegine_duser(self):
        yedek = {"karar": "kabul", "gerekce": "[bekçi aynı aileden — uyarı] temiz",
                 "ihlal_edilen_kural": None}
        with mock.patch.object(bekci, "openai_sor",
                               return_value={"karar": "atlandi", "gerekce": "openai 401",
                                             "ihlal_edilen_kural": None}), \
             mock.patch.object(bekci, "haiku_sor", return_value=yedek) as sahte_haiku:
            karar = bekci.llm_karari("sk-gecersiz", "istem")
        sahte_haiku.assert_called_once()
        self.assertEqual(karar["karar"], "kabul")
        self.assertIn("openai 401 → haiku yedeği", karar["gerekce"])

    def test_ag_hatasi_da_yedege_duser(self):
        with mock.patch.object(bekci, "openai_sor",
                               return_value={"karar": "atlandi", "gerekce": "openai ulaşılamadı: URLError",
                                             "ihlal_edilen_kural": None}), \
             mock.patch.object(bekci, "haiku_sor",
                               return_value={"karar": "red", "gerekce": "boş", "ihlal_edilen_kural": "x"}):
            karar = bekci.llm_karari("sk-gecersiz", "istem")
        self.assertEqual(karar["karar"], "red")
        self.assertIn("haiku yedeği", karar["gerekce"])

    def test_calisan_anahtar_yedege_dusmez(self):
        with mock.patch.object(bekci, "openai_sor",
                               return_value={"karar": "kabul", "gerekce": "temiz",
                                             "ihlal_edilen_kural": None}), \
             mock.patch.object(bekci, "haiku_sor") as sahte_haiku:
            karar = bekci.llm_karari("sk-gecerli", "istem")
        sahte_haiku.assert_not_called()
        self.assertEqual(karar["gerekce"], "temiz")

    def test_denetle_gecersiz_anahtarla_atlandi_birakmaz(self):
        with tempfile.TemporaryDirectory() as d:
            kok = Path(d)
            (kok / "takimlar" / "deneme" / "kosu").mkdir(parents=True)
            kosu = kok / "takimlar" / "deneme" / "kosu" / "2026-09-15.md"
            kosu.write_text("# Koşu\n\nİki dosya okundu, bir çıktı yazıldı.\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-gecersiz"}), \
                 mock.patch.object(bekci.urllib.request, "urlopen", side_effect=_http_hatasi(401)), \
                 mock.patch.object(bekci, "haiku_sor",
                                   return_value={"karar": "kabul", "gerekce": "temiz",
                                                 "ihlal_edilen_kural": None}):
                karar = bekci.denetle(kok, "deneme", kosu)
        self.assertEqual(karar["karar"], "kabul")
        self.assertIn("openai 401 → haiku yedeği", karar["gerekce"])


# --- K6 · takim-olustur.sh ---------------------------------------------------

def _betik_kokunu_kur(hedef):
    (hedef / "bin").mkdir(parents=True)
    shutil.copy2(KOK / "bin" / "takim-olustur.sh", hedef / "bin" / "takim-olustur.sh")
    shutil.copytree(KOK / "takimlar" / "_iskelet", hedef / "takimlar" / "_iskelet")
    return hedef / "bin" / "takim-olustur.sh"


class TakimOlusturTesti(unittest.TestCase):
    def test_argumansiz_cagri_temiz_turkce_mesaj_ve_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            betik = _betik_kokunu_kur(Path(d))
            sonuc = subprocess.run(["bash", str(betik)], capture_output=True, text=True,
                                   encoding="utf-8")
        self.assertEqual(sonuc.returncode, 2)
        self.assertIn("takım adı gerekli", sonuc.stderr)
        self.assertNotIn("parameter", sonuc.stderr.lower())

    def test_kurulan_takim_skills_uyarisi_basar(self):
        with tempfile.TemporaryDirectory() as d:
            betik = _betik_kokunu_kur(Path(d))
            sonuc = subprocess.run(["bash", str(betik), "deneme"], capture_output=True, text=True,
                                   encoding="utf-8")
        self.assertEqual(sonuc.returncode, 0, sonuc.stderr)
        self.assertIn("skills:", sonuc.stdout)
        self.assertIn("testler kırmızı", sonuc.stdout)



# --- repo kilidi (Windows + POSIX) -------------------------------------------

class RepoKilidiTesti(unittest.TestCase):
    def test_ikinci_kilit_birincisi_birakilana_kadar_bekler(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / ".kos.lock"
            sira = []
            ikinci_basladi = threading.Event()

            def ikinci():
                ikinci_basladi.set()
                with kos.repo_kilidi(yol):
                    sira.append("ikinci")

            with kos.repo_kilidi(yol):
                is_parcacigi = threading.Thread(target=ikinci)
                is_parcacigi.start()
                ikinci_basladi.wait(2)
                is_parcacigi.join(0.5)
                self.assertTrue(is_parcacigi.is_alive(), "ikinci koşu kilidi beklemeliydi")
                sira.append("birinci")
            is_parcacigi.join(15)
            self.assertEqual(sira, ["birinci", "ikinci"])


class GitignoreTesti(unittest.TestCase):
    def test_gitignore_olmayan_klasoru_saymaz(self):
        satirlar = (KOK / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("sirket-log/", satirlar)
        self.assertNotIn("sirket/log/", satirlar, "kodda `sirket/log/` diye bir dizin yok")
        kod = "\n".join(y.read_text(encoding="utf-8") for y in (KOK / "bin").glob("*.py"))
        self.assertNotIn("sirket/log", kod)


if __name__ == "__main__":
    unittest.main()
