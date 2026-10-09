# Defter — gc-tarama

> Ajan yazar, insan okur. Her koşudan en fazla bir ders. Yeni ders üste.

## Dersler
- 2026-10-09 (kapanış): 3 uygun, 2 yedek, 10 elendi; 5 adayın hiçbirinde düşüşü açıklayan haber çıkmadı (haber_yok). Uyarılı gözlem ARX'te
  yine imzalı nakit devralma anlaşması çıktı (🟡) — düşük ATR uyarısı = M&A dersi tekrar etti. TER/SANM/GH bilanço tarihleri kaynaklar
  arasında tutmuyor, şirket duyurusu bulunamadı; TER'de `bilanco_dogrulama` not düşülerek insana bırakıldı. 7 arama.
- 2026-10-07 (kapanış): 3 uygun, 2 yedek, 1 elendi; aday haberlerinde kırmızı bayrak bulunamadı. Uyarılı üç gözlemin (TECH, ATKR, MKTX)
  üçünde de imzalı nakit devralma çıktı (🟡) — aynı ders dördüncü koşuda tekrar etti. Yetenek önerisi: `kaynak-dogrulama` →
  ## Öğrenilenler'e "düşük oynaklık uyarısı = önce M&A araması, sembol başına 1 arama" eklensin. Bilanço tarihleri kaynaklar arasında
  tutmuyor (IMAX, MAN): ikincil takvim yetmez, yatırımcı ilişkileri sayfası açılmalı.
- 2026-10-06 (kapanış): Uygun/yedek aday yoktu (1 sinyal CHRN elendi). Düşük oynaklık uyarılı iki gözlemin (LXP, ITGR) ikisinde de
  imzalı nakit devralma anlaşması çıktı (🟡; birincil sayfa açılmadı) — 28 Eylül LNTH dersinin devamı. Sembol başına tek arama yetti (2 arama).
- 2026-10-05 (kapanış): uyarılı üç gözlemin (TECH, ATKR, CBZ) üçünde de imzalı nakit devralma anlaşması çıktı (şirket/alıcı duyurusu
  ve SEC 8-K birincil, ✅); tek MAN adayında düşüş sebebi bulunamadı, bilanço tarihi şirket duyurusuyla doğrulandı. 4 arama yetti.
  SOXL fundamentals 404 yine kritik değil.
- 2026-10-05 (açılış): Açılış koşusunda 5 adayın 3'ünde (IMAX, GH, NEO) gece yeni haber çıkmadı; TGTX'te hukuk bürosu incelemesi
  duyurusu, ADPT'de yönetici Form 144 bildirimi çıktı — ikisi de 🟡 ve şirketin kendi açıklaması değil. Aday başına tek arama
  yetti (5 arama). Not dosyasını elle yazarken `python3 <geçici betik>` onaylanmadı; bu ortamda notlar doğrudan Write ile güncellenmeli.
- 2026-10-02 (kapanış): Uygun/yedek 5 adayın 4'ünde (GH, TGTX, ADPT, NEO) düşüşü açıklayan haber çıkmadı; IMAX'ta sebep sektörel
  (sinema hisseleri birlikte düştü). RNW uyarılı gözleminde yine imzalı devralma anlaşması çıktı. 8 aramalık bütçe bilanço
  doğrulamasına yetmedi (IMAX/TGTX için tarih duyurusu yok, NEO aranmadı); sıra: haber → uyarılı gözlem → bilanço.
- 2026-10-01 (kapanış): MKTX uyarılı gözlemde yine ICE nakit devralma anlaşması çıktı (30 Eylül dersinin devamı). SSRM bilanço
  tarihi şüpheli ve resmi duyuru yok: arama özeti "bekleniyor" diyor, `bilanco_dogrulama` null bırakıldı.
- 2026-09-30 (kapanış): Düşük oynaklık uyarılı 5 gözlemin 5'inde (LNTH, LXP, TECH, CBZ, ITGR) imzalı nakit devralma
  anlaşması çıktı; sembol başına tek arama ("<şirket> definitive agreement acquire 2026") yetiyor. Aynı ders 28, 29 ve 30 Eylül'de
  üç koşudur tekrarlandı → koşu kaydına `kaynak-dogrulama` için yetenek önerisi yazıldı.
- 2026-09-30 (açılış): `--acilis` bu ortamda temiz çalıştı (28 Eylül'deki `cp1254` çökmesi tekrarlamadı). Bir aday için
  premarket fiyatı boş geldi (BLTE) — betik bunu "premarket fiyatı yok" diye işaretliyor, elle doldurma. Açılış koşusunda
  yeni haber çoğunlukla şirketin kendi bülteni oluyor: bunu ✅ ile önceki 🟡 aktarım satırının yerine koy (aday başına 2 kaynak sınırı).
  Arama özetinde geçen bir bilanço tarihi sayfa açılıp doğrulanmadıkça `bilanco_dogrulama`'ya yazılmadı.
- 2026-09-29 (kapanış): gözlem uyarısı ("düşük oynaklık — satın alma anlaşması olabilir") 28 Eylül dersini bir kez daha
  doğruladı: RNW ve MKTX'in ikisinde de imzalı nakit devralma anlaşması bulundu; uyarılı gözlemlerde önce M&A aranınca
  iki aramada kırmızı bayrak çıkıyor. Bilanço tarihi şüpheli iki adayda (BLTE, SSRM) şirket takvimi henüz yayımlanmamıştı;
  `bilanco_dogrulama: null` bırakıldı, tahmin edilmedi. Yfinance SOXL için fundamentals 404 verdi (kapanış yine de bitti).
  Sektör satırı: altın madencisi adayda sektörel düşüş günü aday-özgü sebep sayılmamalı, sektör satırında yazılmalı.
- 2026-09-28 (kapanış, devam koşusu): şema uyumsuzluğu bekçiden önce yakalandı — `bilanco_dogrulama` düz metin
  yazılmıştı; doğrulama birincil kaynaktan yapılamadıysa alan `{tarih,kaynak,not}` sözlüğü ya da `null` olmalı.
  Ayrıca haber iddialarına üçüncü taraf gelir/EBITDA/anlaşma tutarı koymak (§2) önceki bekçi reddiyle aynı desen;
  haber satırı sayı taşımadan, yalnız olgu ve etiketle yazılmalı. Bütçe tavanına çarpan koşuda önce notların
  şeması ve sektör satırı yazılmalı, arama sırası: aday haberi → sektör → gözlem.
- 2026-09-28 (kapanış, DENEME KOŞUSU 6, `--son-bar`, piyasa açıkken prova): kök sebep düzeltmesi doğrulandı.
  `bin/kos.py` artık `PYTHONUTF8` ortam değişkenini set ETMİYOR (`ortam.pop("PYTHONUTF8", None)`) — kullanıcı
  yolundaki 'Ğ' karakteri PYTHONUTF8=1 ile birlikte yfinance'ın (curl tabanlı) her sembolü boş döndürmesine
  sebep oluyormuş. Bu koşuda `tarama_cek.py --kapanis --son-bar` çıkış kodu 0 ile temiz bitti, toplu
  "possibly delisted" hatası (4. ve 5. deneme koşularında görülen) TEKRARLAMADI: evren 58, sinyal 1, uygun 1
  (FIVE). Sonraki koşularda da tekrarlamazsa kök sebep kesinleşmiş sayılabilir; `engel_tekrar` bu koşuda
  `durum.json`'da temizlendi.
- 2026-09-28 (kapanış, DENEME KOŞUSU 5, `--son-bar`, piyasa açıkken prova): 4. koşudan sonra
  `bin/gc_veri.py`'ye eklenen düzeltme (hatalı sembolleri 20 sn bekleyip 100'lük paketlerle yeniden
  deneme) sorunu çözmedi — aynı toplu "possibly delisted" hatası tekrarladı, bu sefer MSFT, NFLX,
  AMZN, LOW, ASML gibi hiçbir şekilde delisted olmayan büyük şirketler de dahil binlerce sembolde.
  Bu, art arda 2. koşuda (4. ve 5. deneme) aynı hata; yeniden deneme mantığı eklenmiş olsa bile
  sorun sürüyor — bu bir gerçek toplu borsa çıkışı değil, yfinance/Yahoo tarafında kalıcı bir engelleme
  ya da IP/oran sınırlaması gibi okunuyor (kanıtlanmadı, yorum). **Patrona bildir**: aynı hata art arda
  tekrarlıyor ve denenen düzeltme işe yaramadı; veri kaynağı gözden geçirilmeli (örn. farklı sağlayıcı,
  API anahtarlı istek, ya da daha uzun bekleme/daha küçük paket denemesi).
- 2026-09-28 (kapanış, DENEME KOŞUSU 4): `tarama_cek.py --kapanis --son-bar` çıkış kodu 1 ile bitti —
  evrendeki hemen hemen tüm semboller (SPY/QQQ dahil) için yfinance "possibly delisted; no price data found"
  hatası döndü, betik SPY/QQQ rejim verisini kuramadığı için `VeriHatasi("SPY/QQQ verisi alınamadı — rejim
  hesaplanamaz")` fırlattı (`bin/tarama_cek.py:184`). Binlerce sembolün aynı anda "delisted" görünmesi gerçek
  bir toplu borsa çıkışı değil; veri sağlayıcısı kaynaklı bir arıza ya da oran sınırlaması gibi okunuyor
  (kanıtlanmadı, yorum). Aynı gün içinde art arda 4. deneme koşusuydu — çok sayıda ardışık geniş evren
  indirmesi sağlayıcıyı sınırlamış olabilir. Bir sonraki koşuda aynı hata tekrarlarsa patrona bildirilmeli.
- 2026-09-28 (açılış): `tarama_cek.py --acilis`, Windows konsolunun `cp1254` kod sayfasında özet
  satırındaki `→` karakteriyle `UnicodeEncodeError` verip çöküyor; hata dosya yazımından ÖNCE oluşuyor,
  yani veri dosyası hiç üretilmiyor. Bu ortamda düzeltme (betikte `PYTHONIOENCODING` ya da `→`→`->`)
  yapılmadan açılış koşuları hep "hata" ile kapanacak — üç koşu üst üste tekrarlarsa patrona bildir.
- 2026-09-28: Veri JSON'undaki "düşük oynaklık — satın alma anlaşması olabilir" uyarısı gerçek bir sinyal: LNTH'de Curium satın alma anlaşması (Ağustos 2026) fiyatı sabitlemiş. Bu uyarıyı taşıyan adaylarda önce M&A/birleşme haberi aranmalı — bulununca kırmızı_bayrak alanına yazılmalı (RSI/bant sinyali geçersizleşir).

## Kural önerileri (insana)
- 2026-10-08 (kapanış): uyarılı gözlem adayında (CZR, düşük ATR) satın alma haberi ilk aramada bulundu; ATR uyarısı yine M&A işaretiydi. tarama_cek.py SOXL için 404 verdi ama koşu tamamlandı (uyarı, hata değil).
