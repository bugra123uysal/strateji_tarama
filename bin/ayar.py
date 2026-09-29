#!/usr/bin/env python3
"""Şirketin tek ayar dosyası — mesai, tavanlar, yollar, anahtarlar.

Bütün betikler buradan okur; hiçbir sayı ikinci bir yerde yazılmaz.
Anahtarlar repo kökündeki `.env` dosyasındadır (`.env.example` kopyası) ve git'e girmez.
"""
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Windows konsolu/Görev Zamanlayıcı cp1254 verir; özetlerdeki '→', '✅' gibi karakterler betiği
# UnicodeEncodeError ile çökertir. Bütün betikler bu dosyayı içe aktardığı için çıktı burada UTF-8'e alınır.
for _akim in (sys.stdout, sys.stderr):
    if hasattr(_akim, "reconfigure"):
        _akim.reconfigure(encoding="utf-8", errors="replace")

KOK = Path(__file__).resolve().parents[1]
TAKIMLAR = KOK / "takimlar"
ENV_DOSYASI = KOK / ".env"

# --- mesai (ANAYASA 4) -----------------------------------------------------
# gc-tarama kapanış koşusu 16:15 New York = yazın 23:15, kışın 00:15 TSİ → pencere gece yarısını geçer.
MESAI_BASLANGIC = 9   # dahil
MESAI_BITIS = 1       # hariç — ertesi gün 01:00'e kadar
MESAI_METNI = f"{MESAI_BASLANGIC:02d}:00-{MESAI_BITIS:02d}:00"

# --- tavanlar (ANAYASA 4) --------------------------------------------------
KOSU_BUTCESI_USD = 2.0          # tek koşunun para tavanı
KOSU_SURESI_SN = 15 * 60        # tek koşunun süre tavanı
KOSULAR_ARASI_DK = 0            # aynı takımın iki koşusu arası — 0: bekleme yok
GUNLUK_KOSU_TAVANI = 4          # takım başına gün
GUNLUK_MALIYET_TAVANI_USD = 10.0  # tüm şirket, gün
ES_ZAMANLI_TAVAN = 2            # dağıtıcının aynı anda başlattığı takım sayısı

# --- strateji ve risk (ANAYASA §7, §8 · sirket/STRATEJI-v3.md) --------------
# Bütün hesap betikleri (tarama_cek, geri_test, gunluk_hesap) bu değerleri buradan okur.
STRATEJI_SURUMU = "v3"
EVREN_PERF_Y_ESIGI = 30.0       # 1 yıllık performans > bu (%) — v2
V1_PERF_Y_ESIGI = 50.0          # v1 eşiği — yalnız panoda "v2 ile evrene girenler"i ayırmak için
# Takipçinin "Al + Güçlü al" filtresi `recommendation_mark` < bu. 2,5 değil: TradingView FTNT'yi (1,95)
# "Neutral" gösteriyor, takipçideki en yüksek not 1,625 (KLIC) — 2026-09-28'de takipçiyle karşılaştırıldı.
EVREN_ANALIST_UST = 1.8
PORTFOY = 50000.0               # USD — adet hesabının tek kaynağı
RISK_ORANI = 0.01               # işlem başı risk: portföyün %1'i
MAKS_ACIK_POZISYON = 5
MAKS_TOPLAM_RISK_ORANI = 0.05   # açık risk toplamı: portföyün %5'i
GUNLUK_UYGUN_ADAY = 3           # aynı gün en fazla bu kadar "işleme uygun"
KOMISYON_EMIR_USD = 1.5         # her emir (giriş ya da çıkış) için; gidiş-dönüş 3 USD
RSI_UZUNLUK = 14
BANT_UZUNLUK = 14
BANT_KAT = 2.0
BOLGE_ESIGI = 2.0               # dünkü mesafe (rsi − alt) ≤ bu değer → "bölgede"
ALTINA_BAKIS_BAR = 5            # son 5 barda mesafe < 0 olduysa ALTINA_GECTI
ATR_UZUNLUK = 14
STOP_ATR_KAT = 1.5
MAKS_STOP_YUZDE = 8.0
BILANCO_MIN_ISGUNU = 5          # bilançoya bundan AZ işlem günü kaldıysa elenir
MAKS_TUTMA_ISGUNU = 15
REJIM_SMA = 200
TREND_EMALARI = (50, 100, 200)  # panodaki trend kategorisi (bilgi etiketi, kural değil)
PIYASA_SAAT_DILIMI = "America/New_York"

# --- model köprüsü (docs/07-farkli-model.md) -------------------------------
# Varsayılan sağlayıcı Anthropic'tir. `takim.md`'de `saglayici: nim` yazan takım
# `bin/model_proxy.py`'nin ayağa kaldırdığı yerel LiteLLM proxy'sine yönlendirilir.
NIM_PROXY_URL = "http://127.0.0.1:4000"   # yalnız yerel — dışarı açık değil
NIM_YEREL_TOKEN = "sk-a-sirketi-yerel"    # yerel proxy'nin bearer token'ı (gizli değil)
LITELLM_SURUM = "1.101.0"                 # uvx ile sabitlenir; bkz. model_proxy.YASAKLI_SURUMLER

ENV_SATIRI = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def claude_yolu():
    """`claude` çalıştırılabilirinin tam yolu. Windows'ta npm kısa yolu `claude.cmd`'dir; CreateProcess
    uzantısız adı bulamaz, `shutil.which` PATHEXT ile bulur. İstem bu yüzden argv ile değil stdin ile gider
    (cmd.exe çok satırlı argümanı bozar)."""
    return shutil.which("claude") or "claude"


def simdi_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


# --- anahtarlar ------------------------------------------------------------

def env_yukle(yol=None):
    """`.env` dosyasını sözlük olarak okur; `export` ve tırnak toleranslı. Yoksa boş sözlük."""
    try:
        satirlar = Path(yol or ENV_DOSYASI).read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    sonuc = {}
    for satir in satirlar:
        if satir.lstrip().startswith("#"):
            continue
        eslesme = ENV_SATIRI.match(satir)
        if eslesme:
            sonuc[eslesme.group(1)] = eslesme.group(2).strip("'\"")
    return sonuc


def ortam_yukle(yol=None):
    """`.env` içeriğini ortama yazar. **Proje `.env`'i kazanır**: kabukta aynı adla tanımlı bir
    değişken varsa üzerine yazılır — izleyici `.env`'e ne yazdıysa onu görür. `.env`'de geçmeyen
    değişkenlere dokunulmaz. Ortamın kopyasını döner."""
    for anahtar, deger in env_yukle(yol).items():
        os.environ[anahtar] = deger
    return dict(os.environ)


def eksik_anahtarlar(gerekli, ortam=None):
    ortam = ortam if ortam is not None else os.environ
    return [a for a in gerekli if not ortam.get(a)]


# --- mesai -----------------------------------------------------------------

def mesaide_mi(simdi=None):
    an = simdi or datetime.now()
    if MESAI_BITIS > MESAI_BASLANGIC:
        return MESAI_BASLANGIC <= an.hour < MESAI_BITIS
    return an.hour >= MESAI_BASLANGIC or an.hour < MESAI_BITIS  # gece yarısını geçen pencere


def sonraki_mesai(simdi=None):
    an = simdi or datetime.now()
    aday = an.replace(hour=MESAI_BASLANGIC, minute=0, second=0, microsecond=0)
    return aday if aday > an else aday + timedelta(days=1)


# --- takim.md frontmatter --------------------------------------------------

def _deger(ham):
    ham = ham.strip()
    if ham.startswith("[") and ham.endswith("]"):
        ic = ham[1:-1].strip()
        return [p.strip().strip("'\"") for p in ic.split(",")] if ic else []
    return ham.strip("'\"")


def frontmatter(metin):
    """Basit YAML frontmatter: `anahtar: değer` ve `[a, b]` listeleri. (fm, gövde) döner."""
    if not metin.startswith("---"):
        return {}, metin
    parcalar = metin.split("---", 2)
    if len(parcalar) < 3:
        return {}, metin
    fm = {}
    for satir in parcalar[1].splitlines():
        if ":" not in satir or satir.lstrip().startswith("#"):
            continue
        anahtar, ham = satir.split(":", 1)
        fm[anahtar.strip()] = _deger(ham)
    return fm, parcalar[2].lstrip("\n")


def takim_bilgisi(takim, kok=None):
    """`takimlar/<takim>/takim.md` frontmatter'ı; dosya yoksa None."""
    yol = Path(kok or KOK) / "takimlar" / takim / "takim.md"
    if not yol.is_file():
        return None
    fm, _ = frontmatter(yol.read_text(encoding="utf-8"))
    return fm


# --- durum.json ------------------------------------------------------------

def durum_yolu(takim, kok=None):
    return Path(kok or KOK) / "takimlar" / takim / "durum.json"


def durum_oku(takim, kok=None):
    try:
        return json.loads(durum_yolu(takim, kok).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def durum_guncelle(takim, yama, kok=None):
    """Yeni sözlük yazar (immutable birleştirme); yazılan durumu döner."""
    yol = durum_yolu(takim, kok)
    yeni = {**durum_oku(takim, kok), **yama}
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(yeni, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return yeni


def ozet(simdi=None):
    """`python3 bin/ayar.py` çıktısı — üç satır. Önce `.env` yüklenir."""
    ortam_yukle()
    an = simdi or datetime.now().astimezone()
    durum = "içinde" if mesaide_mi(an) else "dışında"
    return "\n".join([
        f"{an:%Y-%m-%d %H:%M} — mesai {durum} ({MESAI_METNI}), sonraki açılış {sonraki_mesai(an):%a %H:%M}",
        f"tavanlar: koşu {KOSU_BUTCESI_USD} USD / {KOSU_SURESI_SN // 60} dk · "
        f"takım günde {GUNLUK_KOSU_TAVANI} koşu · arası {KOSULAR_ARASI_DK} dk · "
        f"şirket günde {GUNLUK_MALIYET_TAVANI_USD} USD",
        f".env: {'var' if Path(ENV_DOSYASI).exists() else 'yok'}",
    ])


if __name__ == "__main__":
    print(ozet())
