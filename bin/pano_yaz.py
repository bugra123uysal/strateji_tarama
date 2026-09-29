#!/usr/bin/env python3
"""gc-tarama panosu — veri JSON'u + ajanın not dosyasından tek dosyalık HTML üretir. LLM çağırmaz.

Kullanım: python3 bin/pano_yaz.py [--tarih YYYY-MM-DD] [--kontrol]
  --tarih    hangi kapanış verisi (varsayılan: en yenisi)
  --kontrol  yalnız not dosyasını denetler; sorun varsa listeler ve 1 döner

Girdi:  takimlar/gc-tarama/veri/<tarih>.json          (tarama_cek --kapanis)
        takimlar/gc-tarama/veri/*-acilis.json          (varsa, kaynak_kapanis bu tarihse)
        takimlar/gc-tarama/notlar/<tarih>.json         (ajan: haber, bayrak, sektör — SAYI HESAPLAMAZ)
Çıktı:  takimlar/gc-tarama/cikti/<tarih>-pano.html ve cikti/pano.html (her zaman en güncel)

Panodaki her hesaplanmış sayı veri JSON'undan AYNEN alınır; ajan yalnızca metin not verir.
"""
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402

TAKIM = ayar.KOK / "takimlar" / "gc-tarama"
VERI, NOTLAR, CIKTI = TAKIM / "veri", TAKIM / "notlar", TAKIM / "cikti"
ETIKETLER = {"✅", "🟡", "⛔"}
GOZLEM_GORUNUR = 15
UYARI_ALT = "Bu pano bir kural uygulayıcısıdır, yatırım tavsiyesi değildir. Emir düğmesi insandadır."
TIP_ETIKETI = {"DOKUNDU": "DOKUNDU", "ALTINA_GECTI": "ALTINA GEÇTİ"}


def e(x):
    return html.escape("–" if x is None else str(x))


def guvenli_url(url):
    return url if isinstance(url, str) and url.startswith(("https://", "http://")) else None


# --- girdi -------------------------------------------------------------------

def veri_dosyasi(tarih=None):
    dosyalar = sorted(VERI.glob("????-??-??.json"))
    if tarih:
        yol = VERI / f"{tarih}.json"
        if not yol.is_file():
            raise FileNotFoundError(f"veri yok: {yol.name}")
        return yol
    if not dosyalar:
        raise FileNotFoundError("hiç kapanış verisi yok — önce tarama_cek --kapanis")
    return dosyalar[-1]


def acilis_verisi(kapanis_adi):
    for yol in sorted(VERI.glob("*-acilis.json"), reverse=True):
        veri = json.loads(yol.read_text(encoding="utf-8"))
        if veri.get("kaynak_kapanis") == kapanis_adi:
            return veri
    return None


def notlari_oku(tarih):
    yol = NOTLAR / f"{tarih}.json"
    return json.loads(yol.read_text(encoding="utf-8")) if yol.is_file() else {}


def not_sorunlari(notlar):
    """Bekçiden önce ucuz denetim: her haber iddiası etiketli ve kaynaklı mı, en fazla 2 kaynak mı."""
    sorunlar = []
    for bolum in ("adaylar", "gozlem", "pozisyonlar"):
        for sembol, n in (notlar.get(bolum) or {}).items():
            haberler = n.get("haber") or []
            if len(haberler) > 2:
                sorunlar.append(f"{bolum}/{sembol}: {len(haberler)} haber (en fazla 2)")
            for i, hb in enumerate(haberler, 1):
                if hb.get("etiket") not in ETIKETLER:
                    sorunlar.append(f"{bolum}/{sembol} haber {i}: etiket ✅/🟡/⛔ değil")
                if hb.get("etiket") != "⛔" and not guvenli_url(hb.get("kaynak")):
                    sorunlar.append(f"{bolum}/{sembol} haber {i}: kaynak bağlantısı yok")
    return sorunlar


# --- parçalar ------------------------------------------------------------------

def cip(metin, tur):
    return f'<span class="cip cip-{tur}">{e(metin)}</span>'


def rejim_cipi(ad, r):
    tur = {"YESIL": "yesil", "KIRMIZI": "kirmizi"}.get(r["rejim"], "gri")
    return (f'<span class="cip cip-{tur}">{e(ad)} {e(r["rejim"])}'
            f'<small>{e(r["kapanis"])} / SMA200 {e(r["sma200"])}</small></span>')


def ust_serit(v, acilis):
    rejim = " ".join(rejim_cipi(ad, r) for ad, r in v["rejim"].items())
    gelen = v["evren"].get("v2_ile_gelen")
    evren = f'{v["evren"]["sayi"]}' + (f' ({len(gelen)} v2 ile gelen)' if gelen is not None else "")
    olcu = [("evren", evren), ("sinyal", v["sinyal_sayisi"]),
            ("açık pozisyon", f'{v["acik_pozisyon_sayisi"]}/{v["tavanlar"]["maks_acik_pozisyon"]}'),
            ("açık risk", f'{v["acik_risk_usd"]} USD (%{v["acik_risk_yuzde"]})')]
    kutular = "".join(f'<div class="olcu"><b>{e(d)}</b><span>{e(k)}</span></div>' for k, d in olcu)
    uyari = f'<p class="uyari">⚠ {e(v["evren"]["uyari"])}</p>' if v["evren"].get("uyari") else ""
    return f"""<header class="serit">
  <div class="baslik"><h1>Geri Çekilme Panosu</h1>
    <p>{e(v["tarih"])} · veri: <b>{e(v["veri_kapanisi"])}</b> kapanışı · strateji <b>{e(v["strateji_surumu"])}</b>
    — {e(v["donem"])} dönemi · portföy {e(v["portfoy_usd"])} USD</p></div>
  <div class="rejim">{rejim}</div>
  <div class="olculer">{kutular}</div>{uyari}
</header>{acilis_bolumu(acilis)}"""


def acilis_bolumu(a):
    if not a:
        return ""
    satirlar = "".join(
        f'<tr><td>{e(x["sembol"])}</td><td>{e(x["durum"])}</td><td class="s">{e(x["premarket_fiyat"])}</td>'
        f'<td class="s">{e(x["premarket_degisim_yuzde"])}</td><td class="s">{e(x["stop"])}</td>'
        f'<td class="s">{e(x["iki_r"])}</td><td>{isaret_cipi(x["isaret"])}</td></tr>'
        for x in a["adaylar"])
    poz = "".join(f'<li>{e(p["sembol"])}: premarket {e(p["premarket_fiyat"])} · stop {e(p["stop"])} · '
                  f'{isaret_cipi(p["isaret"])}</li>' for p in a["pozisyonlar"])
    return f"""<section class="acilis"><h2>Açılış öncesi güncellemesi <small>{e(a["uretim"])}</small></h2>
  <table><thead><tr><th>Sembol</th><th>Durum</th><th>Premarket</th><th>Değişim %</th><th>Stop</th><th>2R</th>
  <th>İşaret</th></tr></thead><tbody>{satirlar or '<tr><td colspan="7">aday yok</td></tr>'}</tbody></table>
  {f'<ul>{poz}</ul>' if poz else ''}</section>"""


def isaret_cipi(isaret):
    tur = "kirmizi" if "GAP" in isaret else "sari" if "kaçtı" in isaret else "gri" if "yok" in isaret else "yesil"
    return cip(isaret, tur)


def haber_blogu(n):
    if not n:
        return '<p class="not bos">Haber notu henüz yazılmadı.</p>'
    parca = []
    if n.get("kirmizi_bayrak"):
        parca.append(f'<p class="bayrak">KIRMIZI BAYRAK — {e(n["kirmizi_bayrak"])}</p>')
    if n.get("bilanco_insan_onayi"):
        parca.append('<p class="bayrak">Bilanço yakın — elenmeli, insan onayı</p>')
    for hb in n.get("haber") or []:
        url = guvenli_url(hb.get("kaynak"))
        kaynak = f' <a href="{e(url)}" target="_blank" rel="noopener">kaynak</a>' if url else ""
        parca.append(f'<p class="not">{e(hb.get("etiket"))} {e(hb.get("iddia"))}{kaynak}</p>')
    if n.get("haber_yok"):
        parca.append('<p class="not">Belirgin haber bulunamadı.</p>')
    if isinstance(n.get("bilanco_dogrulama"), str):  # ajan bazen düz metin yazar — çökme, aynen göster
        parca.append(f'<p class="not">Bilanço doğrulama: {e(n["bilanco_dogrulama"])}</p>')
    elif n.get("bilanco_dogrulama"):
        b = n["bilanco_dogrulama"]
        url = guvenli_url(b.get("kaynak"))
        parca.append(f'<p class="not">Bilanço doğrulama: {e(b.get("tarih"))} {e(b.get("not") or "")}'
                     + (f' <a href="{e(url)}" target="_blank" rel="noopener">kaynak</a>' if url else "") + "</p>")
    if n.get("sektor"):
        parca.append(f'<p class="not sektor">Sektör: {e(n["sektor"])}</p>')
    return "".join(parca)


def bilanco_metni(a):
    if not a.get("bilanco_tarihi"):
        return '<b class="dikkat">bilinmiyor — elle kontrol et</b>'
    ek = " · kaynaklar farklı!" if a.get("bilanco_supheli") else ""
    return f'{e(a["bilanco_tarihi"])} ({e(a["bilanco_isgunu"])} işlem günü){e(ek)}'


TREND_ETIKETI = {"GUCLU_TREND": ("GÜÇLÜ TREND", "yesil"), "TREND": ("TREND · EMA100 altı", "sari")}


def trend_cipi(a):
    """Eski veri dosyasında (trend alanı yok) boş."""
    kategori = a.get("trend_kategori")
    if kategori is None:
        return ""
    if kategori in TREND_ETIKETI:
        return cip(*TREND_ETIKETI[kategori])
    return cip("trend dışı: " + ", ".join(a.get("trend_eksik") or []), "gri")


def ema_metni(a):
    if a.get("ema50") is None:
        return ""
    return f'<p class="kural">EMA50 {e(a["ema50"])} · EMA100 {e(a["ema100"])} · EMA200 {e(a["ema200"])}</p>'


def v2_bandi_cipi(a, esik):
    """Aday yalnız v2 eşiğiyle evrende ise (1Y ≤ v1 eşiği) işaret; eski veri dosyasında esik None → boş."""
    if esik is None or a.get("perf_y") is None or a["perf_y"] > esik:
        return ""
    return cip(f'v2 bandı · 1Y %{a["perf_y"]}', "sari")


def aday_karti(a, n, sinif="", v1_esigi=None):
    tip = TIP_ETIKETI.get(a["sinyal_tipi"], a["sinyal_tipi"])
    uyarilar = "".join(f'<p class="bayrak">{e(u)}</p>' for u in a.get("uyarilar") or [])
    alanlar = [("Kapanış", a["kapanis"]), ("RSI / alt bant", f'{a["rsi"]} / {a["alt"]}'),
               ("Giriş ref.", a["giris"]), ("Stop", f'{a["stop"]} (%{a["stop_yuzde"]})'), ("R", a["r"]),
               ("Adet", a["adet"]), ("2R", a["iki_r"])]
    izgara = "".join(f'<div><span>{e(k)}</span><b>{e(d)}</b></div>' for k, d in alanlar)
    return f"""<article class="kart {sinif}">
  <div class="kart-ust"><h3>{e(a["sembol"])}</h3>{cip(tip, "tip-" + a["sinyal_tipi"].lower())}{trend_cipi(a)}{v2_bandi_cipi(a, v1_esigi)}
    <a class="grafik" href="{e(guvenli_url(a["grafik"]) or '#')}" target="_blank" rel="noopener">grafik ↗</a></div>
  <p class="ad">{e(a.get("ad") or "")} · {e(a.get("sektor") or "")}</p>
  <div class="izgara">{izgara}</div>{ema_metni(a)}
  <p class="kural">Çıkış: {e(a["cikis_kurali"])} · Bilanço: {bilanco_metni(a)}</p>
  {uyarilar}{haber_blogu(n)}
</article>"""


def pozisyon_bolumu(v, notlar):
    if not v["pozisyonlar"]:
        bos = "Açık pozisyon yok." + (f' Verisi alınamayan: {e(", ".join(v["pozisyon_verisi_yok"]))}'
                                      if v.get("pozisyon_verisi_yok") else "")
        return f'<section><h2>Açık pozisyonlar ve çıkış kontrolü</h2><p class="bos">{bos}</p></section>'
    satirlar = "".join(
        f'<tr class="{"cik" if p["karar"] == "CIK" else ""}"><td>{e(p["sembol"])}</td><td>{e(p["karar"])}</td>'
        f'<td>{e(p["sebep"] or "")}</td><td class="s">{e(p["giris"])}</td><td class="s">{e(p["kapanis"])}</td>'
        f'<td class="s">{e(p["stop"])}</td><td class="s">{e(p["adet"])}</td><td class="s">{e(p["rsi"])} / '
        f'{e(p["orta"])}</td><td class="s">{e(p["gecen_isgunu"])}</td><td class="s">{e(p["kar_zarar_usd"])}</td>'
        f'<td>{e(p["bilanco_tarihi"] or "bilinmiyor")}</td></tr>' for p in v["pozisyonlar"])
    return f"""<section><h2>Açık pozisyonlar ve çıkış kontrolü</h2><div class="kaydir"><table><thead><tr>
  <th>Sembol</th><th>Karar</th><th>Sebep</th><th>Giriş</th><th>Kapanış</th><th>Stop</th><th>Adet</th>
  <th>RSI / orta</th><th>Gün</th><th>K/Z USD</th><th>Bilanço</th></tr></thead><tbody>{satirlar}</tbody></table></div>
</section>"""


def aday_bolumleri(v, notlar):
    n = notlar.get("adaylar") or {}
    uygun = [a for a in v["adaylar"] if a["durum"] == "uygun"]
    yedek = [a for a in v["adaylar"] if a["durum"] == "yedek"]
    elendi = [a for a in v["adaylar"] if a["durum"] == "elendi"]
    kirmizi = v["rejim_karari"] != "YESIL"
    esik = v["evren"].get("v1_perf_y_esigi")
    bas = "İşleme uygun adaylar" + (" — rejim KIRMIZI, liste yalnız bilgi" if kirmizi else "")
    govde = "".join(aday_karti(a, n.get(a["sembol"]), "uygun", esik) for a in uygun) or \
        '<p class="bos buyuk">Bugün kurala uyan aday yok.</p>'
    parca = [f'<section><h2>{e(bas)} <small>en fazla {v["tavanlar"]["gunluk_uygun"]}</small></h2>'
             f'<div class="kartlar">{govde}</div></section>']
    if yedek:
        parca.append('<section><h2>Yedekler <small>kurala uyan, günlük sınıra takılan</small></h2><div class="kartlar">'
                     + "".join(aday_karti(a, n.get(a["sembol"]), "yedek", esik) for a in yedek) + "</div></section>")
    satir = "".join(f'<li><b>{e(a["sembol"])}</b> {e(TIP_ETIKETI.get(a["sinyal_tipi"]))} — {e(a["sebep"])}'
                    f' · <a href="{e(a["grafik"])}" target="_blank" rel="noopener">grafik</a></li>' for a in elendi)
    parca.append(f'<section><h2>Elenenler <small>sinyal verdi, kurala takıldı</small></h2>'
                 f'<ul class="liste">{satir or "<li>yok</li>"}</ul></section>')
    return "".join(parca)


def yakin_bolumu(v):
    satir = "".join(f'<li><b>{e(y["sembol"])}</b> kapanış {e(y["kapanis"])} · RSI {e(y["rsi"])} · alt {e(y["alt"])}'
                    f' · mesafe {e(y["mesafe"])} · <a href="{e(y["grafik"])}" target="_blank" rel="noopener">grafik</a>'
                    f'</li>' for y in v.get("yakin") or [])
    return (f'<section><h2>Yarın sinyal verebilir <small>evrende, alt bant bölgesinde, dönüş yok</small></h2>'
            f'<ul class="liste">{satir or "<li>yok</li>"}</ul></section>')


IZLEME_DURUMU = {"SINYAL": ("SİNYAL", "yesil"), "YAKIN": ("YARIN OLABİLİR", "sari"), "YOK": ("sinyal yok", "gri")}


def izleme_satiri(a):
    grafik = f'<a class="grafik" href="{e(guvenli_url(a["grafik"]) or "#")}" target="_blank" rel="noopener">grafik ↗</a>'
    if a["durum"] == "VERI_YOK":
        return (f'<article class="gozlem-satir"><div class="kart-ust"><h3>{e(a["sembol"])}</h3>'
                f'{cip("veri alınamadı", "kirmizi")}{grafik}</div></article>')
    metin, renk = IZLEME_DURUMU[a["durum"]]
    if a.get("sinyal_tipi"):
        metin += " · " + TIP_ETIKETI.get(a["sinyal_tipi"], a["sinyal_tipi"])
    notlar = "".join(cip(t, "sari") for t in a.get("strateji_notlari") or [])
    evren = cip("evrende", "yesil") if a.get("evrende") else ""
    uyarilar = "".join(f'<p class="bayrak">{e(u)}</p>' for u in a.get("uyarilar") or [])
    return f"""<article class="gozlem-satir izleme-{e(a["durum"].lower())}">
  <div class="kart-ust"><h3>{e(a["sembol"])}</h3>{cip(metin, renk)}{trend_cipi(a)}{evren}{grafik}</div>
  <p class="sayilar">kapanış {e(a["kapanis"])} · RSI {e(a["rsi"])} / alt {e(a["alt"])} · mesafe {e(a.get("mesafe"))}
  · stop {e(a["stop"])} (%{e(a["stop_yuzde"])}) · R {e(a["r"])} · adet {e(a["adet"])} · 2R {e(a["iki_r"])}
  · bilanço {bilanco_metni(a)}</p>
  <div class="etiketler">{notlar}</div>{uyarilar}
</article>"""


def izleme_bolumu(v):
    iz = v.get("izleme")
    if not iz:  # izleme alanı olmayan eski veri dosyası
        return ""
    adaylar = iz.get("adaylar") or []
    sira = {"SINYAL": 0, "YAKIN": 1, "YOK": 2, "VERI_YOK": 3}
    govde = "".join(izleme_satiri(a) for a in sorted(adaylar, key=lambda a: sira.get(a["durum"], 9)))
    return f"""<section class="izleme"><h2>İzleme listesi — {e(iz.get("liste") or "adsız")}
  <small>{len(adaylar)} hisse · strateji hesabı</small></h2>
  <p class="aciklama">TradingView izleme listenin kopyası ({e(iz.get("kaynak"))}). Her hisse aynı sinyal, trend, bilanço
  ve stop kurallarından geçer. Sarı etiketler kurala takıldığı yerlerdir. "İşleme uygun" kararı yalnız yukarıdaki
  aday listesinde verilir.</p>
  {govde or '<p class="bos">liste boş</p>'}</section>"""


def v2_evren_bolumu(v):
    ev = v["evren"]
    gelen = ev.get("v2_ile_gelen")
    if gelen is None:  # v2 öncesi veri dosyası
        return ""
    satir = "".join(f'<li><b>{e(g["sembol"])}</b> 1Y %{e(g["perf_y"])}</li>' for g in gelen)
    return (f'<section><h2>v2 ile evrene girenler <small>{len(gelen)} hisse</small></h2>'
            f'<p class="aciklama">Evren: 1Y performans &gt; %{e(ev["perf_y_esigi"])} — toplam {e(ev["sayi"])} hisse, '
            f'üst sınır yok. Aşağıdakiler bunların alt kümesi: 1Y performansı %{e(ev["v1_perf_y_esigi"])} ve altında '
            f'olduğu için v1 eşiğinde (&gt; %{e(ev["v1_perf_y_esigi"])}) evrende olmazdı.</p>'
            f'<ul class="liste sutun">{satir or "<li>yok</li>"}</ul></section>')


def trend_bolumu(v):
    t = v["evren"].get("trend")
    if t is None:  # trend alanı olmayan eski veri dosyası
        return ""

    def liste(semboller):
        return "".join(f"<li><b>{e(s)}</b></li>" for s in semboller) or "<li>yok</li>"

    disi = "".join(f'<li><b>{e(d["sembol"])}</b> <small>{e(", ".join(d["eksik"]))}</small></li>'
                   for d in t["DISI"]) or "<li>yok</li>"
    return f"""<section><h2>Trend kategorisi <small>evren · günlük EMA · v3 kuralı</small></h2>
  <p class="aciklama">Kural (v3): sinyal günü fiyat &gt; EMA200 ve EMA50 &gt; EMA200 değilse aday elenir (trend dışı).
  GÜÇLÜ TREND: fiyat EMA100'ün de üstünde. TREND: fiyat EMA100'ün altında — ikisi de uygun olabilir.
  Takipçi fiyat &gt; EMA100/EMA200'ü zaten şart koşar; EMA50 &gt; EMA200 takipçide yoktur.</p>
  <h3 class="alt-baslik">{cip("GÜÇLÜ TREND", "yesil")} {len(t["GUCLU_TREND"])} hisse</h3>
  <ul class="liste sutun">{liste(t["GUCLU_TREND"])}</ul>
  <h3 class="alt-baslik">{cip("TREND · EMA100 altı", "sari")} {len(t["TREND"])} hisse</h3>
  <ul class="liste sutun">{liste(t["TREND"])}</ul>
  <h3 class="alt-baslik">{cip("trend dışı", "gri")} {len(t["DISI"])} hisse</h3>
  <ul class="liste">{disi}</ul></section>"""


def gozlem_satiri(a, n):
    etiketler = "".join(cip(t, "gri") for t in a["takildigi_filtreler"])
    notlar = "".join(cip(t, "sari") for t in a["strateji_notlari"])
    uyarilar = "".join(f'<p class="bayrak">{e(u)}</p>' for u in a.get("uyarilar") or [])
    return f"""<article class="gozlem-satir">
  <div class="kart-ust"><h3>{e(a["sembol"])}</h3>{cip(TIP_ETIKETI.get(a["sinyal_tipi"]), "tip-" + a["sinyal_tipi"].lower())}
  {trend_cipi(a)}<span class="kucuk">{e(a.get("sektor") or "")}</span>
  <a class="grafik" href="{e(guvenli_url(a["grafik"]) or '#')}" target="_blank" rel="noopener">grafik ↗</a></div>
  <p class="sayilar">kapanış {e(a["kapanis"])} · RSI {e(a["rsi"])} / alt {e(a["alt"])} · stop {e(a["stop"])}
  (%{e(a["stop_yuzde"])}) · R {e(a["r"])} · adet {e(a["adet"])} · 2R {e(a["iki_r"])} · bilanço {bilanco_metni(a)}</p>
  <div class="etiketler">{etiketler}{notlar}</div>{uyarilar}{haber_blogu(n) if n else ""}
</article>"""


def gozlem_bolumu(v, notlar):
    g = v.get("gozlem") or {}
    adaylar = g.get("adaylar") or []
    n = notlar.get("gozlem") or {}
    ilk = "".join(gozlem_satiri(a, n.get(a["sembol"])) for a in adaylar[:GOZLEM_GORUNUR])
    kalan = adaylar[GOZLEM_GORUNUR:]
    devam = (f'<details><summary>{len(kalan)} hisse daha</summary>'
             + "".join(gozlem_satiri(a, n.get(a["sembol"])) for a in kalan) + "</details>") if kalan else ""
    uyari = f'<p class="uyari">⚠ {e(g["uyari"])}</p>' if g.get("uyari") else ""
    return f"""<section class="gozlem"><h2>Gözlem listesi — KURAL DIŞI
  <small>geniş evren {e(g.get("genis_evren_sayisi"))} · sinyal {len(adaylar)}</small></h2>
  <p class="aciklama">{e(g.get("aciklama"))}. En az filtreye takılan üstte. Bu listeden hiçbir hisse "uygun" değildir.</p>
  {uyari}{ilk or '<p class="bos">yok</p>'}{devam}</section>"""


# --- sayfa ---------------------------------------------------------------------

CSS = """
:root{--zemin:#0d0f12;--yuzey:#151a20;--yuzey2:#1c232b;--cizgi:#2a333d;--metin:#e6e9ee;--soluk:#8b95a3;
--yesil:#3fcf8e;--kirmizi:#ff5d5d;--sari:#f2b84b;--mor:#b48cff;--mavi:#6cb6ff;
--mono:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;
--sans:"Segoe UI",system-ui,-apple-system,Roboto,sans-serif}
*{box-sizing:border-box}html,body{margin:0;background:var(--zemin);color:var(--metin);font:15px/1.5 var(--sans)}
main{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:1.5rem;margin:0;letter-spacing:.02em}h2{font-size:1.05rem;margin:28px 0 10px;text-transform:uppercase;
letter-spacing:.08em;color:var(--soluk)}h2 small,h1 small{font-weight:400;text-transform:none;letter-spacing:0;margin-left:8px}
h3{margin:0;font:700 1.25rem var(--mono)}a{color:var(--mavi)}small{color:var(--soluk)}
.serit{background:linear-gradient(135deg,#17202a,#10151b);border:1px solid var(--cizgi);border-radius:14px;padding:18px;
display:grid;gap:14px}.baslik p{margin:4px 0 0;color:var(--soluk)}.baslik b{color:var(--metin)}
.rejim{display:flex;gap:8px;flex-wrap:wrap}.olculer{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px}
.olcu{background:var(--yuzey2);border-radius:10px;padding:10px 12px}.olcu b{display:block;font:700 1.2rem var(--mono)}
.olcu span{color:var(--soluk);font-size:.8rem}
.cip{display:inline-flex;gap:6px;align-items:baseline;padding:3px 10px;border-radius:999px;font:600 .78rem var(--mono);
border:1px solid currentColor;margin:2px 4px 2px 0}.cip small{font-weight:400}
.cip-yesil{color:var(--yesil)}.cip-kirmizi{color:var(--kirmizi)}.cip-sari{color:var(--sari)}.cip-gri{color:var(--soluk)}
.cip-tip-altina_gecti{color:var(--mor)}.cip-tip-dokundu{color:var(--mavi)}
.kartlar{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.kart{background:var(--yuzey);border:1px solid var(--cizgi);border-left:4px solid var(--yesil);border-radius:12px;padding:16px;
transition:transform .15s ease,border-color .15s ease}.kart:hover{transform:translateY(-2px);border-color:#3a4652}
.kart.yedek{border-left-color:var(--sari)}.kart-ust{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.grafik{margin-left:auto;font-size:.85rem;text-decoration:none;border:1px solid var(--cizgi);padding:2px 8px;border-radius:8px}
.grafik:hover,.grafik:focus{border-color:var(--mavi);outline:none}
.ad{color:var(--soluk);margin:4px 0 10px;font-size:.85rem}
.izgara{display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:8px}
.izgara div{background:var(--yuzey2);border-radius:8px;padding:6px 8px}.izgara span{display:block;color:var(--soluk);font-size:.72rem}
.izgara b{font:600 .95rem var(--mono);font-variant-numeric:tabular-nums}
.kural{font-size:.85rem;color:var(--soluk)}.not{margin:6px 0;font-size:.9rem}.not.bos{color:var(--soluk);font-style:italic}
.bayrak{margin:6px 0;padding:6px 10px;border-radius:8px;background:#3a1618;color:#ffb3b3;font-weight:600;font-size:.85rem}
.dikkat{color:var(--sari)}.uyari{color:var(--sari);margin:0}
table{width:100%;border-collapse:collapse;font-size:.85rem}th,td{padding:7px 8px;border-bottom:1px solid var(--cizgi);text-align:left}
th{color:var(--soluk);font-weight:500}.s{font-family:var(--mono);text-align:right}tr.cik td{color:var(--kirmizi);font-weight:600}
.kaydir{overflow-x:auto}.acilis{background:var(--yuzey);border:1px solid var(--sari);border-radius:12px;padding:6px 14px 12px;margin-top:14px}
.liste{padding-left:18px}.liste li{margin:4px 0}.liste.sutun{columns:4 150px;column-gap:18px}
.alt-baslik{font:600 .9rem var(--sans);margin:14px 0 4px;color:var(--soluk)}.bos{color:var(--soluk)}.bos.buyuk{font-size:1.1rem;padding:18px;
background:var(--yuzey);border-radius:12px;border:1px dashed var(--cizgi)}
.gozlem{border:1px dashed var(--mor);border-radius:14px;padding:4px 16px 16px;margin-top:30px;
background:repeating-linear-gradient(135deg,transparent 0 14px,rgba(180,140,255,.03) 14px 28px)}
.gozlem h2{color:var(--mor)}.aciklama{color:var(--soluk);font-size:.85rem}
.gozlem-satir{background:var(--yuzey);border-radius:10px;padding:10px 12px;margin:8px 0}
.sayilar{font:.82rem var(--mono);color:#c9d1db;margin:6px 0}.etiketler{display:flex;flex-wrap:wrap}.kucuk{color:var(--soluk);font-size:.8rem}
details summary{cursor:pointer;color:var(--mor);margin:10px 0}
.izleme{border:1px solid var(--mavi);border-radius:14px;padding:4px 16px 16px;margin-top:30px}.izleme h2{color:var(--mavi)}
.izleme-sinyal{border-left:4px solid var(--yesil)}.izleme-yakin{border-left:4px solid var(--sari)}
footer{margin:34px 0 10px;padding-top:14px;border-top:1px solid var(--cizgi);color:var(--soluk);font-size:.85rem}
@media (max-width:600px){main{padding:12px}.kartlar{grid-template-columns:1fr}h3{font-size:1.1rem}}
"""


def sayfa(v, acilis, notlar):
    genel = f'<p class="not">{e(notlar["genel"])}</p>' if notlar.get("genel") else ""
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Geri Çekilme Panosu {e(v["veri_kapanisi"])}</title>
<style>{CSS}</style></head><body><main>
{ust_serit(v, acilis)}{genel}
{pozisyon_bolumu(v, notlar.get("pozisyonlar") or {})}
{aday_bolumleri(v, notlar)}
{yakin_bolumu(v)}
{izleme_bolumu(v)}
{trend_bolumu(v)}
{v2_evren_bolumu(v)}
{gozlem_bolumu(v, notlar)}
<footer>{e(UYARI_ALT)}<br>Strateji {e(v["strateji_surumu"])} · veri {e(v["uretim"])} · evren kaynağı {e(v["evren"]["kaynak"])}</footer>
</main></body></html>
"""


def main(argv):
    tarih = argv[argv.index("--tarih") + 1] if "--tarih" in argv else None
    try:
        yol = veri_dosyasi(tarih)
    except FileNotFoundError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1
    v = json.loads(yol.read_text(encoding="utf-8"))
    notlar = notlari_oku(yol.stem)
    sorunlar = not_sorunlari(notlar)
    for s in sorunlar:
        print(f"not sorunu: {s}")
    if "--kontrol" in argv:
        return 1 if sorunlar else 0
    metin = sayfa(v, acilis_verisi(yol.name), notlar)
    CIKTI.mkdir(parents=True, exist_ok=True)
    arsiv = CIKTI / f"{yol.stem}-pano.html"
    for hedef in (arsiv, CIKTI / "pano.html"):
        hedef.write_text(metin, encoding="utf-8")
    print(f"yazıldı: {arsiv.relative_to(ayar.KOK).as_posix()} ve cikti/pano.html")
    return 1 if sorunlar else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
