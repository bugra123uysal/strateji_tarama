"""Obsidian kasası — yalnız bu stratejinin üç klasörü, sağlıklı bağlantılar."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
KASA = KOK / "kasa"
IZINLI_KLASORLER = {"decisions", "sessions", "concepts", "_schema", ".obsidian"}
IZINLI_TURLER = {"decision", "session", "concept"}


class KasaTesti(unittest.TestCase):
    def test_yalniz_izinli_klasorler(self):
        klasorler = {p.name for p in KASA.iterdir() if p.is_dir()}
        self.assertLessEqual(klasorler, IZINLI_KLASORLER, klasorler - IZINLI_KLASORLER)

    def test_her_not_izinli_turde(self):
        for yol in [*KASA.glob("decisions/*.md"), *KASA.glob("sessions/*.md"), *KASA.glob("concepts/*.md")]:
            with self.subTest(not_=yol.name):
                ilk = yol.read_text(encoding="utf-8").split("---")[1]
                tur = next(s.split(":", 1)[1].strip() for s in ilk.splitlines() if s.startswith("type:"))
                self.assertIn(tur, IZINLI_TURLER)
                self.assertIn(yol.parent.name.rstrip("s"), tur + "s")

    def test_kasa_denetimi_gecer(self):
        sonuc = subprocess.run([sys.executable, str(KOK / "bin/kasa_lint.py"), str(KASA), "--exclude", "CLAUDE.md",
                                "--exclude", "log.md", "--fail-under", "90"],
                               capture_output=True, text=True, encoding="utf-8",
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(sonuc.returncode, 0, sonuc.stdout[-800:] + sonuc.stderr[-800:])


if __name__ == "__main__":
    unittest.main()
