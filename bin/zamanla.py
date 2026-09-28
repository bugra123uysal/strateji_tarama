#!/usr/bin/env python3
"""Zamanlayıcı — Windows Görev Zamanlayıcı + New York saatine bakan tetik. LLM çağırmaz.

Neden böyle: Görev Zamanlayıcı yalnız yerel saati bilir. Türkiye yaz/kış saati uygulamaz (UTC+3), ABD uygular.
16:15 New York yazın 23:15, kışın 00:15 TSİ'dir. Görev iki olası TSİ saatinin İKİSİNDE de tetiklenir;
`--tik` o an New York saatine bakar, doğru pencerede değilse hiçbir şey yapmaz, aynı gün aynı görevi ikinci
kez koşturmaz. Bilgisayar kapalıyken kaçan tetik açılışta koşar (StartWhenAvailable) — pencere hâlâ açıksa.

Kullanım:
  python3 bin/zamanla.py --goster        # tetik saatleri ve yaz/kış TSİ karşılıkları (hiçbir şey kurmaz)
  python3 bin/zamanla.py --kur           # Windows görevlerini kur (GeriCekilme\\gc-tarama, GeriCekilme\\gc-gunluk)
  python3 bin/zamanla.py --kaldir        # görevleri sil
  python3 bin/zamanla.py --durum         # kurulu görevler
  python3 bin/zamanla.py --tik           # görevlerin çağırdığı giriş: New York saatine göre gc-tarama
  python3 bin/zamanla.py --gunluk        # görevlerin çağırdığı giriş: gc-gunluk
"""
import json
import subprocess
import sys
import tempfile
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import gc_hesap as h  # noqa: E402

NY = ZoneInfo(ayar.PIYASA_SAAT_DILIMI)
TSI = ZoneInfo("Europe/Istanbul")
KLASOR = "GeriCekilme"
KAYIT = ayar.KOK / "sirket-log" / "tetik.json"

# New York saatine göre pencereler: [başlangıç, bitiş). Başlangıç = asıl koşu saati.
PENCERELER = {"acilis": (time(9, 0), time(9, 30)),      # premarket; açılıştan (09:30) önce bitmeli
              "kapanis": (time(16, 15), time(23, 59))}  # kapanmış bar; gece yarısına kadar telafi
# Görev Zamanlayıcı tetikleri (TSİ): her New York saati için yaz (EDT) ve kış (EST) karşılığı.
TSI_TETIKLER = sorted({(datetime.combine(g, bas, NY).astimezone(TSI)).strftime("%H:%M")
                       for bas, _ in PENCERELER.values() for g in (date(2026, 7, 1), date(2026, 12, 1))})
GUNLUK_TETIK = ("MON", "09:30")                          # gc-gunluk: pazartesi 09:30 TSİ


def ny_gorevi(simdi):
    """`simdi` (zaman dilimli) anında New York'ta hangi gc-tarama görevi koşmalı? Yoksa None."""
    ny = simdi.astimezone(NY)
    if not h.isgunu_mu(ny.date()):
        return None
    for gorev, (bas, son) in PENCERELER.items():
        if bas <= ny.time() < son:
            return gorev
    return None


def kayit_oku(yol=KAYIT):
    try:
        return json.loads(Path(yol).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def tik(simdi=None, kostur=None, yol=KAYIT):
    """Tetik girişi. (sonuç, açıklama) döner; aynı New York gününde aynı görev bir kez koşar."""
    simdi = simdi or datetime.now(timezone.utc)
    gorev = ny_gorevi(simdi)
    ny = simdi.astimezone(NY)
    if gorev is None:
        return "bos", f"New York {ny:%a %H:%M} — pencere dışı ya da tatil"
    if not ayar.mesaide_mi(simdi.astimezone(TSI)):
        # kos.py mesai dışında koşuyu atlar; kayıt düşülürse o günün görevi sessizce kaybolur
        return "bos", f"New York {ny:%a %H:%M} — {gorev} penceresi açık ama TSİ mesai dışı ({ayar.MESAI_METNI})"
    anahtar = f"{ny.date().isoformat()}:{gorev}"
    kayit = kayit_oku(yol)
    if anahtar in kayit:
        return "tekrar", f"{anahtar} zaten koştu ({kayit[anahtar]})"
    Path(yol).parent.mkdir(parents=True, exist_ok=True)
    Path(yol).write_text(json.dumps({**kayit, anahtar: simdi.astimezone(TSI).isoformat(timespec="seconds")},
                                    ensure_ascii=False, indent=1), encoding="utf-8")
    (kostur or _kostur)(["gc-tarama", "--gorev", gorev])
    return "kostu", f"{anahtar} başlatıldı"


def _kostur(argv):
    subprocess.run([sys.executable, str(ayar.KOK / "bin" / "kos.py"), *argv], cwd=str(ayar.KOK), check=False)


# --- Windows Görev Zamanlayıcı --------------------------------------------------

def _gorev_xml(aciklama, tetikler, arguman):
    tetik_xml = "".join(tetikler)
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>{aciklama}</Description></RegistrationInfo>
  <Triggers>{tetik_xml}</Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec><Command>"{sys.executable}"</Command><Arguments>"{ayar.KOK / 'bin' / 'zamanla.py'}" {arguman}</Arguments>
      <WorkingDirectory>{ayar.KOK}</WorkingDirectory></Exec>
  </Actions>
</Task>
"""


def _gunluk_tetik(saat):
    return (f"<CalendarTrigger><StartBoundary>2026-01-01T{saat}:00</StartBoundary>"
            f"<ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger>")


def gorevler():
    gun, saat = GUNLUK_TETIK
    haftalik = (f"<CalendarTrigger><StartBoundary>2026-01-05T{saat}:00</StartBoundary><ScheduleByWeek>"
                f"<DaysOfWeek><Monday /></DaysOfWeek><WeeksInterval>1</WeeksInterval></ScheduleByWeek></CalendarTrigger>")
    return {
        f"{KLASOR}\\gc-tarama": _gorev_xml(
            "gc-tarama: 09:00 ve 16:15 New York — TSİ karşılıkları yaz/kış için ikişer tetik, "
            "karar zamanla.py --tik'te", [_gunluk_tetik(s) for s in TSI_TETIKLER], "--tik"),
        f"{KLASOR}\\gc-gunluk": _gorev_xml("gc-gunluk: pazartesi 09:30 TSİ", [haftalik], "--gunluk"),
    }


def _schtasks(*argv):
    return subprocess.run(["schtasks", *argv], capture_output=True, text=True, encoding="mbcs", errors="replace")


def kur():
    for ad, xml in gorevler().items():
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-16") as dosya:
            dosya.write(xml)
        sonuc = _schtasks("/Create", "/TN", ad, "/XML", dosya.name, "/F")
        Path(dosya.name).unlink(missing_ok=True)
        print(f"{ad}: {'kuruldu' if sonuc.returncode == 0 else 'HATA — ' + (sonuc.stderr or sonuc.stdout).strip()}")


def kaldir():
    for ad in gorevler():
        sonuc = _schtasks("/Delete", "/TN", ad, "/F")
        print(f"{ad}: {'silindi' if sonuc.returncode == 0 else 'yok'}")


def durum():
    for ad in gorevler():
        sonuc = _schtasks("/Query", "/TN", ad, "/FO", "LIST")
        print(sonuc.stdout.strip() if sonuc.returncode == 0 else f"{ad}: kurulu değil")


def goster(bugun=None):
    """Yaz/kış geçişinde New York saatlerinin TSİ karşılığı ve hangi tetiğin koşacağı."""
    bugun = bugun or datetime.now(TSI).date()
    ornekler = [date(2026, 10, 30), date(2026, 11, 2), date(2027, 3, 12), date(2027, 3, 15), bugun]
    print(f"Tetikler (TSİ, her gün): {', '.join(TSI_TETIKLER)} · gc-gunluk: pazartesi {GUNLUK_TETIK[1]} TSİ\n")
    print("New York günü    | açılış 09:00 NY → TSİ | kapanış 16:15 NY → TSİ | TSİ tetiklerinde karar")
    for gun in ornekler:
        ac = datetime.combine(gun, PENCERELER["acilis"][0], NY).astimezone(TSI)
        kp = datetime.combine(gun, PENCERELER["kapanis"][0], NY).astimezone(TSI)
        kararlar = []
        for s in TSI_TETIKLER:
            saat, dakika = map(int, s.split(":"))
            an = datetime.combine(gun + timedelta(days=1 if saat < 9 else 0), time(saat, dakika), TSI)
            kararlar.append(f"{s}→{ny_gorevi(an) or '-'}")
        print(f"{gun} {gun:%a}   | {ac:%H:%M} ({ac:%d.%m})         | {kp:%H:%M} ({kp:%d.%m})          | "
              + " ".join(kararlar))


def main(argv):
    komutlar = {"--goster": goster, "--kur": kur, "--kaldir": kaldir, "--durum": durum}
    for bayrak, is_ in komutlar.items():
        if bayrak in argv:
            is_()
            return 0
    if "--tik" in argv:
        sonuc, aciklama = tik()
        print(f"tetik: {sonuc} — {aciklama}")
        return 0
    if "--gunluk" in argv:
        _kostur(["gc-gunluk"])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
