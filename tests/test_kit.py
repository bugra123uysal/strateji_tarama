"""Kitin kendi testleri — ağ yok, claude çağrısı yok, para harcamaz.

python3 -m unittest discover -s tests
"""
import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import bekci  # noqa: E402
import dagitici  # noqa: E402
import gunluk  # noqa: E402
import kos  # noqa: E402

TAKIM_MD = """---
name: {ad}
description: {ad} takımı — test.
model: sonnet
tools: [Read, Write]
gerekli_anahtarlar: []
butce_usd: 2
---

# {ad}
"""


GERCEK_TAKIMLAR = sorted(y.parent.name for y in (KOK / "takimlar").glob("*/takim.md")
                         if not y.parent.name.startswith("_"))
TEST_ZINCIRI = [{"ad": "a-den-b-ye", "desen": re.compile(r"^a-(.+)$"), "takim": "takim-b",
                 "id": "b-{0}", "not": "takim-a maddesi bitti; takim-b devralsın"}]


def ilk_gercek_takim(test):
    """Repodaki ilk gerçek takım; henüz takım kurulmadıysa testi atlar."""
    if not GERCEK_TAKIMLAR:
        test.skipTest("repoda henüz takım yok")
    return GERCEK_TAKIMLAR[0]


def sahte_kok(tmp, takimlar=("takim-a", "takim-b")):
    """Geçici dizinde takimlar/<t>/{takim.md,durum.json,kosu/} olan minik bir repo."""
    kok = Path(tmp) / "kok"
    for ad in takimlar:
        dizin = kok / "takimlar" / ad
        (dizin / "kosu").mkdir(parents=True)
        (dizin / "takim.md").write_text(TAKIM_MD.format(ad=ad), encoding="utf-8")
        (dizin / "durum.json").write_text(json.dumps(
            {"takim": ad, "son_kosu": None, "son_sonuc": None, "kuyruk": [],
             "bekci": {"son_karar": None, "red_sayisi_7g": 0}, "defter_son_ders": None,
             "sayaclar": {}}, ensure_ascii=False), encoding="utf-8")
    return kok


class AyarTesti(unittest.TestCase):
    def test_env_yukle_export_ve_tirnak_tolere_eder(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / ".env"
            yol.write_text("export A=1\nB=\"iki\"\n# yorum\nC='üç'\nBOS=\n", encoding="utf-8")
            self.assertEqual(ayar.env_yukle(yol), {"A": "1", "B": "iki", "C": "üç", "BOS": ""})

    def test_eksik_anahtarlar(self):
        self.assertEqual(ayar.eksik_anahtarlar(["A", "B"], {"A": "1"}), ["B"])
        self.assertEqual(ayar.eksik_anahtarlar([], {}), [])

    def test_mesai_penceresi(self):
        gunduz = datetime(2026, 9, 11, 12, 0)
        gece = datetime(2026, 9, 11, 3, 0)
        self.assertTrue(ayar.mesaide_mi(gunduz))
        self.assertFalse(ayar.mesaide_mi(gece))
        self.assertEqual(ayar.sonraki_mesai(gece).hour, ayar.MESAI_BASLANGIC)

    def test_frontmatter_liste_ayristirir(self):
        fm, govde = ayar.frontmatter(TAKIM_MD.format(ad="takim-a"))
        self.assertEqual(fm["name"], "takim-a")
        self.assertEqual(fm["tools"], ["Read", "Write"])
        self.assertEqual(fm["butce_usd"], "2")
        self.assertTrue(govde.startswith("# takim-a"))

    def test_gercek_takimlarin_frontmatteri_okunur(self):
        for ad in GERCEK_TAKIMLAR:
            fm = ayar.takim_bilgisi(ad)
            self.assertIsNotNone(fm, ad)
            self.assertEqual(fm["name"], ad)
            self.assertIsInstance(fm["tools"], list)


class KuruKosuTesti(unittest.TestCase):
    def test_kos_kuru_calisir_ve_hicbir_dosyaya_yazmaz(self):
        for ad in GERCEK_TAKIMLAR:
            oncesi = json.loads((KOK / "takimlar" / ad / "durum.json").read_text(encoding="utf-8"))
            kayitlar = sorted((KOK / "takimlar" / ad / "kosu").glob("*.md"))
            yakala = io.StringIO()
            with redirect_stdout(yakala):
                kod = kos.main([ad, "--kuru"])
            self.assertEqual(kod, 0, ad)
            self.assertIn("kuru koşu", yakala.getvalue())
            self.assertIn("claude çağrılmadı", yakala.getvalue())
            sonrasi = json.loads((KOK / "takimlar" / ad / "durum.json").read_text(encoding="utf-8"))
            self.assertEqual(oncesi, sonrasi, f"{ad}: kuru koşu durum.json'u değiştirdi")
            self.assertEqual(sorted((KOK / "takimlar" / ad / "kosu").glob("*.md")), kayitlar)

    def test_istem_anayasayi_ve_kosu_kaydini_soyler(self):
        ad = ilk_gercek_takim(self)
        fm = ayar.takim_bilgisi(ad)
        metin = kos.istem(ad, fm, KOK / f"takimlar/{ad}/kosu/x.md", "2026-09-11T12:00:00+02:00")
        self.assertIn("ANAYASA.md", metin)
        self.assertIn("kurallar.md", metin)
        self.assertIn("SIRKET_KOSU", metin)
        self.assertIn("<kaynak>", metin)


class KimlikIstemiTesti(unittest.TestCase):
    """Koşu istemi: kimlik → ANAYASA → AJAN-KIMLIGI → kurallar → takim.md sırası."""

    def _istem(self, takim=None, fm=None):
        takim = takim or ilk_gercek_takim(self)
        return kos.istem(takim, fm if fm is not None else {},
                         KOK / f"takimlar/{takim}/kosu/2026-09-11-1200.md", "2026-09-11 12:00")

    def test_istemin_ilk_satiri_kimlik(self):
        metin = self._istem()
        self.assertTrue(metin.startswith(f"Sen `{GERCEK_TAKIMLAR[0]}` ajanısın."), metin[:80])
        self.assertIn("bir çalışansın", metin.splitlines()[0])
        self.assertIn("bir yapay zekâ ajanısın", metin.splitlines()[0])
        self.assertIn("Mesleğin:", metin.splitlines()[0])

    def test_istem_kimlik_dosyasini_okuma_sirasina_koyar(self):
        metin = self._istem()
        self.assertIn("sirket/AJAN-KIMLIGI.md", metin)
        self.assertLess(metin.index("ANAYASA.md"), metin.index("sirket/AJAN-KIMLIGI.md"))
        self.assertLess(metin.index("sirket/AJAN-KIMLIGI.md"), metin.index(f"takimlar/{GERCEK_TAKIMLAR[0]}/kurallar.md"))

    def test_istem_meslegi_takim_md_den_okur(self):
        """fm boş gelse bile description takim.md'den tamamlanır."""
        metin = self._istem()
        aciklama = ayar.takim_bilgisi(GERCEK_TAKIMLAR[0])["description"]
        self.assertIn(aciklama[:40], metin)

    def test_istem_yetenek_satiri_ekler(self):
        metin = self._istem("deney", {"description": "deneme takımı — test.",
                                      "skills": ["kaynak-dogrulama", "zincir-yazimi"]})
        self.assertIn("Yeteneklerin: `skills/kaynak-dogrulama/SKILL.md`, `skills/zincir-yazimi/SKILL.md`", metin)
        self.assertIn("ilgili adımda oku ve uygula", metin)

    def test_istem_skillleri_takim_md_den_tamamlar(self):
        metin = self._istem()
        for ad in ayar.takim_bilgisi(GERCEK_TAKIMLAR[0]).get("skills") or []:
            self.assertIn(f"`skills/{ad}/SKILL.md`", metin)

    def test_istem_skills_yoksa_yetenek_satiri_yok(self):
        metin = self._istem("yok-boyle-takim", {"description": "x", "skills": []})
        self.assertNotIn("Yeteneklerin:", metin)

    def test_istem_kendini_gelistirme_cumlesi(self):
        metin = self._istem()
        self.assertIn("kendini geliştir", metin)
        self.assertIn("defter.md", metin)

    def test_kuru_kosu_kimlik_satirini_basar(self):
        ad = ilk_gercek_takim(self)
        yakala = io.StringIO()
        with redirect_stdout(yakala):
            kos.main([ad, "--kuru"])
        cikti = yakala.getvalue()
        self.assertIn(f"kimlik (istemin ilk satırı): Sen `{ad}` ajanısın.", cikti)
        self.assertIn("yetenekler:", cikti)

    def test_dagitici_kuru_calisir_ve_kuyruga_yazmaz(self):
        oncesi = {ad: (KOK / f"takimlar/{ad}/durum.json").read_text(encoding="utf-8")
                  for ad in GERCEK_TAKIMLAR}
        yakala = io.StringIO()
        with redirect_stdout(yakala):
            kod = dagitici.main(["--kuru"])
        self.assertEqual(kod, 0)
        self.assertIn("dağıtıcı", yakala.getvalue())
        self.assertIn("kuru koşu", yakala.getvalue())
        for ad, metin in oncesi.items():
            self.assertEqual(metin, (KOK / f"takimlar/{ad}/durum.json").read_text(encoding="utf-8"))

    def test_kosu_yolu_tarihli(self):
        yol = kos.kosu_yolu("takim-a", "2026-09-11T12:05:00+02:00", kok="/x")
        self.assertEqual(yol.as_posix(), "/x/takimlar/takim-a/kosu/2026-09-11-1205.md")

    def test_sonucu_cozumle(self):
        iyi = kos.sonucu_cozumle(json.dumps({"result": "bitti", "total_cost_usd": 0.12,
                                             "num_turns": 3, "is_error": False}))
        self.assertEqual(iyi["maliyet"], 0.12)
        self.assertFalse(iyi["hata"])
        self.assertTrue(kos.sonucu_cozumle("json değil")["hata"])


@mock.patch.object(dagitici, "ZINCIR", TEST_ZINCIRI)
class ZincirTesti(unittest.TestCase):
    def test_a_tamam_olunca_b_kuyruguna_is_duser(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            ayar.durum_guncelle("takim-a", {"kuyruk": [
                {"id": "a-1234", "durum": "tamam", "not": "bitti"}]}, kok)
            yazilan = dagitici.zinciri_isle(kok, "takim-a")
            self.assertEqual([z["id"] for z in yazilan], ["b-1234"])
            kuyruk = ayar.durum_oku("takim-b", kok)["kuyruk"]
            self.assertEqual(kuyruk[0]["id"], "b-1234")
            self.assertEqual(kuyruk[0]["durum"], "bekliyor")

    def test_zincir_iki_kez_calisinca_tekrar_yazmaz(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            ayar.durum_guncelle("takim-a", {"kuyruk": [{"id": "a-7", "durum": "tamam"}]}, kok)
            dagitici.zinciri_isle(kok, "takim-a")
            self.assertEqual(dagitici.zinciri_isle(kok, "takim-a"), [])
            self.assertEqual(len(ayar.durum_oku("takim-b", kok)["kuyruk"]), 1)

    def test_bekleyen_madde_zincire_girmez(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            ayar.durum_guncelle("takim-a", {"kuyruk": [{"id": "a-9", "durum": "bekliyor"}]}, kok)
            self.assertEqual(dagitici.zinciri_isle(kok, "takim-a"), [])


class TavanTesti(unittest.TestCase):
    SIMDI = datetime.fromisoformat("2026-09-11T15:00:00+02:00")

    def _bekleyen_kok(self, tmp):
        kok = sahte_kok(tmp)
        ayar.durum_guncelle("takim-a", {"kuyruk": [{"id": "a-1", "durum": "bekliyor"}]}, kok)
        return kok

    def test_bos_kuyruk_kosmaz(self):
        with tempfile.TemporaryDirectory() as tmp:
            kossun, sebep = dagitici.tetik_karari(sahte_kok(tmp), "takim-a", self.SIMDI)
            self.assertFalse(kossun)
            self.assertIn("bekleyen madde yok", sebep)

    def test_bekleyen_madde_kosturur(self):
        with tempfile.TemporaryDirectory() as tmp:
            kossun, _ = dagitici.tetik_karari(self._bekleyen_kok(tmp), "takim-a", self.SIMDI)
            self.assertTrue(kossun)

    def test_mesai_disi_bekletir(self):
        with tempfile.TemporaryDirectory() as tmp:
            gece = self.SIMDI.replace(hour=3)
            kossun, sebep = dagitici.tetik_karari(self._bekleyen_kok(tmp), "takim-a", gece)
            self.assertFalse(kossun)
            self.assertIn("mesai dışı", sebep)

    def test_kosular_arasi_bekleme_kurali(self):
        # Varsayılan ayar 0 (bekleme yok); kural mantığı ayar 30'a çekilerek sınanır.
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(ayar, "KOSULAR_ARASI_DK", 30):
            kok = self._bekleyen_kok(tmp)
            yeni = self.SIMDI - timedelta(minutes=10)
            ayar.durum_guncelle("takim-a", {"son_kosu": yeni.isoformat()}, kok)
            kossun, sebep = dagitici.tetik_karari(kok, "takim-a", self.SIMDI)
            self.assertFalse(kossun)
            self.assertIn("30 dk", sebep)

    def test_bekleme_sifirsa_hemen_kosar(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(ayar, "KOSULAR_ARASI_DK", 0):
            kok = self._bekleyen_kok(tmp)
            yeni = self.SIMDI - timedelta(minutes=1)
            ayar.durum_guncelle("takim-a", {"son_kosu": yeni.isoformat()}, kok)
            kossun, _ = dagitici.tetik_karari(kok, "takim-a", self.SIMDI)
            self.assertTrue(kossun)

    def test_gunluk_kosu_tavani(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = self._bekleyen_kok(tmp)
            for saat in range(ayar.GUNLUK_KOSU_TAVANI):
                (kok / "takimlar/takim-a/kosu" / f"2026-09-11-{saat:02d}00.md").write_text("x")
            kossun, sebep = dagitici.tetik_karari(kok, "takim-a", self.SIMDI)
            self.assertFalse(kossun)
            self.assertIn("günlük koşu tavanı", sebep)

    def test_gunluk_maliyet_tavani(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = self._bekleyen_kok(tmp)
            (kok / "takimlar/takim-b/kosu/2026-09-11-0900.md").write_text(
                "- maliyet: 10.50 USD · tur: 3\n", encoding="utf-8")
            kossun, sebep = dagitici.tetik_karari(kok, "takim-a", self.SIMDI)
            self.assertFalse(kossun)
            self.assertIn("günlük bütçe", sebep)


class BekciTesti(unittest.TestCase):
    def test_on_kontrol_anahtar_desenlerini_yakalar(self):
        self.assertEqual(bekci.on_kontrol("anahtar sk-abc123def burada"), ["OpenAI anahtarı"])
        self.assertEqual(bekci.on_kontrol("AIzaSyD-abcdefghij"), ["Google anahtarı"])
        self.assertEqual(bekci.on_kontrol("ghp_abcdef123456"), ["GitHub token"])
        self.assertEqual(bekci.on_kontrol("12345678:AAEabcdefghijklmnopqrstuvwx-yz"),
                         ["Telegram bot token"])
        self.assertIn("e-posta adresi", bekci.on_kontrol("gönderen: biri@marka.com"))

    def test_on_kontrol_temiz_metni_gecirir(self):
        self.assertEqual(bekci.on_kontrol("3 link okundu, 2 tablo yazıldı, 1 ⛔ çıktı"), [])

    def test_bos_kosu_kaydi_red(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            (kok / "ANAYASA.md").write_text("1. Yayın düğmesi insanın.", encoding="utf-8")
            kosu = kok / "takimlar/takim-a/kosu/2026-09-11-1200.md"
            kosu.write_text("   \n", encoding="utf-8")
            karar = bekci.denetle(kok, "takim-a", kosu)
            self.assertEqual(karar["karar"], "red")
            self.assertIn("boş", karar["gerekce"])
            self.assertEqual(ayar.durum_oku("takim-a", kok)["bekci"]["son_karar"], "red")

    def test_anahtar_sizan_kosu_llm_cagirmadan_red(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            kosu = kok / "takimlar/takim-a/kosu/2026-09-11-1200.md"
            kosu.write_text("# Koşu\nAPIFY_TOKEN=sk-gizli123456 ile çektim\n", encoding="utf-8")
            with mock.patch.object(bekci, "openai_sor") as sahte_openai, \
                 mock.patch.object(bekci, "haiku_sor") as sahte_haiku:
                karar = bekci.denetle(kok, "takim-a", kosu)
            sahte_openai.assert_not_called()
            sahte_haiku.assert_not_called()
            self.assertEqual(karar["karar"], "red")
            self.assertIn("## Bekçi", kosu.read_text(encoding="utf-8"))

    def test_haiku_yedegi_ayni_aile_uyarisi_yazar(self):
        yanit = json.dumps({"result": '{"karar":"kabul","gerekce":"temiz","ihlal_edilen_kural":null}'})
        with mock.patch.object(bekci.subprocess, "run",
                               return_value=mock.Mock(stdout=yanit, returncode=0)):
            karar = bekci.haiku_sor("istem")
        self.assertEqual(karar["karar"], "kabul")
        self.assertIn(bekci.AYNI_AILE_UYARISI, karar["gerekce"])

    def test_madde_3_gerekceli_red_gecersiz(self):
        red = {"karar": "red", "gerekce": "ANAYASA madde 3: denetleyen aynı aileden",
               "ihlal_edilen_kural": "3"}
        self.assertEqual(bekci.gecersiz_gerekceyi_ayikla(red)["karar"], "kabul")

    def test_icerik_gerekceli_red_korunur(self):
        red = {"karar": "red", "gerekce": "kaynaksız sayı: '8 bin abone'", "ihlal_edilen_kural": "2"}
        self.assertEqual(bekci.gecersiz_gerekceyi_ayikla(red)["karar"], "red")

    def test_haiku_yedeginin_ayni_aile_notu_redi_gecersiz_kilmaz(self):
        # 17 Eyl 2026: yedek bekçinin "[bekçi aynı aileden — uyarı]" öneki filtreye takılıp
        # haklı bir içerik red'ini kabule çeviriyordu.
        red = {"karar": "red",
               "gerekce": f"[{bekci.AYNI_AILE_UYARISI}] tema toplamı 45, yorum 50 — sayılar tutarsız",
               "ihlal_edilen_kural": "Kurallar — sayılar tam ve tutarlı olmalı"}
        self.assertEqual(bekci.gecersiz_gerekceyi_ayikla(red)["karar"], "red")


class BelgeTutarliligiTesti(unittest.TestCase):
    def test_env_ornegi_ile_readme_ayni_anahtarlari_sayiyor(self):
        ornek = ayar.env_yukle(KOK / ".env.example")
        self.assertTrue(ornek, ".env.example okunamadı")
        readme = (KOK / "README.md").read_text(encoding="utf-8")
        for anahtar in ornek:
            self.assertIn(anahtar, readme, f"{anahtar} .env.example'da var ama README'de yok")

    def test_env_orneginde_gercek_deger_yok(self):
        for anahtar, deger in ayar.env_yukle(KOK / ".env.example").items():
            self.assertEqual(deger, "", f"{anahtar} .env.example'da dolu!")

    def test_repoda_sizmis_anahtar_yok(self):
        desenler = [re.compile(p) for p in
                    (r"\bsk-[A-Za-z0-9]{20,}", r"\bAIza[0-9A-Za-z_-]{30,}",
                     r"\bgh[pousr]_[A-Za-z0-9]{30,}", r"\b\d{9,}:[A-Za-z0-9_-]{30,}")]
        atla = {".git", "__pycache__", "kosu", "cikti", "gelen", "veri"}
        for yol in KOK.rglob("*"):
            if not yol.is_file() or yol.name == "test_kit.py" or set(yol.parts) & atla:
                continue
            if yol.suffix not in (".py", ".md", ".json", ".sh", ".example", ".gitignore", ""):
                continue
            metin = yol.read_text(encoding="utf-8", errors="ignore")
            for desen in desenler:
                self.assertIsNone(desen.search(metin), f"{yol.name}: anahtara benzeyen metin")

    def test_gitignore_env_i_kapsiyor(self):
        satirlar = (KOK / ".gitignore").read_text(encoding="utf-8").splitlines()
        for beklenen in (".env", "takimlar/*/kosu/", "takimlar/*/cikti/", "takimlar/*/gelen/",
                         "takimlar/*/veri/", "__pycache__/", "*.jsonl"):
            self.assertIn(beklenen, satirlar)

    def test_stop_hook_bekciyi_cagiriyor(self):
        ayarlar = json.loads((KOK / ".claude/settings.json").read_text(encoding="utf-8"))
        komutlar = [h["command"] for madde in ayarlar["hooks"]["Stop"] for h in madde["hooks"]]
        self.assertTrue(any("bekci.py" in k for k in komutlar))
        self.assertEqual(list(ayarlar["hooks"]), ["Stop"])


MESAI_ICI = datetime(2026, 9, 11, 10, 0).astimezone()


GUN = "2026-09-11"
KOSU_METNI = """# Koşu — {takim} — {gun}

- model: sonnet · bütçe: 2 USD

iş yapıldı.

---
- maliyet: {maliyet} USD · tur: 7 · hata: {hata}


## Bekçi
- karar: **{karar}**
- gerekçe: {gerekce}
- ihlal edilen kural: -
"""


def _kosu_yaz(kok, takim, saat, maliyet="0.500", hata="False", karar="kabul", gerekce="temiz"):
    yol = Path(kok) / "takimlar" / takim / "kosu" / f"{GUN}-{saat}.md"
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(KOSU_METNI.format(takim=takim, gun=GUN, maliyet=maliyet, hata=hata,
                                     karar=karar, gerekce=gerekce), encoding="utf-8")
    return yol


class GunlukRaporTesti(unittest.TestCase):
    def test_kosu_oku_ozet_ve_bekci_kararini_ayiklar(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            kosu = gunluk.kosu_oku(_kosu_yaz(kok, "takim-a", "0930", maliyet="1.250", karar="red"))
        self.assertEqual((kosu["gun"], kosu["saat"]), (GUN, "09:30"))
        self.assertEqual((kosu["maliyet"], kosu["tur"], kosu["hata"]), (1.25, 7, False))
        self.assertEqual((kosu["bekci"], kosu["atlandi"]), ("red", None))

    def test_kosu_oku_atlanan_kosuyu_tanir(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            yol = Path(kok) / "takimlar/takim-a/kosu" / f"{GUN}-0300.md"
            yol.write_text("# Koşu\n\n**Atlandı:** mesai dışı (09:00-23:00); kuyrukta bekler\n",
                           encoding="utf-8")
            kosu = gunluk.kosu_oku(yol)
        self.assertIn("mesai dışı", kosu["atlandi"])
        self.assertEqual((kosu["maliyet"], kosu["bekci"]), (0.0, "-"))

    def test_gunun_kosulari_gune_gore_suzup_saate_gore_sirali_doner(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            _kosu_yaz(kok, "takim-a", "1400")
            _kosu_yaz(kok, "takim-b", "0930")
            (Path(kok) / "takimlar/takim-a/kosu/2026-09-10-1000.md").write_text("dün", encoding="utf-8")
            kosular = gunluk.gunun_kosulari(kok, GUN)
        self.assertEqual([(k["saat"], k["takim"]) for k in kosular],
                         [("09:30", "takim-b"), ("14:00", "takim-a")])

    def test_bekci_telemetrisi_gune_gore_suzulur_bozuk_satir_atlanir(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            (Path(kok) / gunluk.TELEMETRI).write_text(
                json.dumps({"zaman": f"{GUN}T09:30:00+03:00", "takim": "takim-a", "karar": "red"}) + "\n"
                + "{bozuk json\n"
                + json.dumps({"zaman": "2026-09-10T09:30:00+03:00", "takim": "takim-a", "karar": "kabul"}) + "\n",
                encoding="utf-8")
            kararlar = gunluk.gunun_bekci_kararlari(kok, GUN)
        self.assertEqual([k["karar"] for k in kararlar], ["red"])

    def test_aksam_raporu_kosulari_kararlari_ve_dikkati_yazar(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            _kosu_yaz(kok, "takim-a", "0930", maliyet="1.250", karar="red", gerekce="kaynak yok")
            (Path(kok) / gunluk.TELEMETRI).write_text(
                json.dumps({"zaman": f"{GUN}T09:45:00+03:00", "takim": "takim-a", "karar": "red",
                            "gerekce": "kaynak yok", "ihlal_edilen_kural": "kaynak"},
                           ensure_ascii=False) + "\n", encoding="utf-8")
            metin = gunluk.aksam_raporu(kok, MESAI_ICI)
        self.assertIn("Akşam denetimi", metin)
        self.assertIn("Bugünün koşuları (1)", metin)
        self.assertIn("**red 1**", metin)
        self.assertIn("⛔ `takim-a` 09:30 — bekçi **red**", metin)
        self.assertIn(f"/ {ayar.GUNLUK_MALIYET_TAVANI_USD:.0f} USD", metin)

    def test_temiz_gunde_uydurma_uyari_yok(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            _kosu_yaz(kok, "takim-a", "0930")
            metin = gunluk.aksam_raporu(kok, MESAI_ICI)
        self.assertIn("temiz gün, işaretlenecek bir şey yok", metin)
        self.assertNotIn("⛔", metin)

    def test_sabah_raporu_dagitici_kararlarini_tasir(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            dagitici.kuyruga_yaz(kok, "takim-a", "a-1", "test maddesi")
            dagitim = dagitici.dagit(kok, MESAI_ICI, kuru=True)
            metin = gunluk.sabah_raporu(kok, MESAI_ICI, dagitim)
        self.assertIn("Sabah raporu", metin)
        self.assertIn("| takim-a | KOŞ |", metin)
        self.assertIn("| takim-b | BEKLE |", metin)
        self.assertIn("Dün (2026-09-10)", metin)

    def test_sabah_kuru_kosu_hicbir_takimi_baslatmaz(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            dagitici.kuyruga_yaz(kok, "takim-a", "a-1", "test maddesi")
            with mock.patch.object(dagitici, "_kostur") as sahte:
                gunluk.sabah(kok, MESAI_ICI, kuru=True)
            sahte.assert_not_called()
            self.assertFalse((Path(kok) / gunluk.RAPOR_DIZINI).exists())

    def test_haftalik_is_yalniz_pazartesi_kuyruga_duser(self):
        haftalik = [{"takim": "takim-a", "gun": 0, "id": "hf-{hafta}", "not": "haftalık iş"}]
        with tempfile.TemporaryDirectory() as d, mock.patch.object(gunluk, "HAFTALIK", haftalik):
            kok = sahte_kok(d, takimlar=("takim-a",))
            sali = gunluk.haftalik_kuyruk(kok, datetime(2026, 9, 15, 9, 0).astimezone())
            pazartesi = gunluk.haftalik_kuyruk(kok, datetime(2026, 9, 14, 9, 0).astimezone())
            tekrar = gunluk.haftalik_kuyruk(kok, datetime(2026, 9, 14, 9, 30).astimezone())
            kuyruk = ayar.durum_oku("takim-a", kok)["kuyruk"]
        self.assertEqual(sali, [])
        self.assertEqual([h["id"] for h in pazartesi], ["hf-2026-W38"])
        self.assertEqual(tekrar, [], "aynı haftanın maddesi ikinci kez yazılmamalı")
        self.assertEqual([(o["id"], o["durum"]) for o in kuyruk], [("hf-2026-W38", "bekliyor")])

    def test_hafta_kimligi_iso(self):
        self.assertEqual(gunluk.hafta_kimligi(datetime(2026, 9, 14, 9, 0)), "2026-W38")

    def test_haftalik_is_olmayan_gunde_rapor_bunu_soyler(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            metin = gunluk.sabah_raporu(kok, MESAI_ICI, {"zincir": [], "kararlar": []})
        self.assertIn("bugün (Cuma) haftalık iş yok", metin)

    def test_rapor_dosyaya_yazilir(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            yol = gunluk.yaz(kok, "aksam", gunluk.aksam_raporu(kok, MESAI_ICI), MESAI_ICI)
        self.assertEqual(yol.name, f"{GUN}-aksam.md")
        self.assertIn(gunluk.RAPOR_DIZINI, yol.as_posix())


if __name__ == "__main__":
    unittest.main()
