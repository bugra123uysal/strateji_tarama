# GERİ ÇEKİLME ŞİRKETİ — KURULUM PROMPTU (v1)

Bu klasör, selmakcby/a-sirketi iskeletinden klonlandı. Burada TEK BİR STRATEJİ için yeni bir şirket kuracağız: "Güçlü Hissede Geri Çekilme". Bu şirkette başka strateji olmayacak. Kırılım stratejim ayrı bir şirkette yaşıyor; ona hiçbir şekilde dokunma.

Çalışma ortamım Windows. a-sirketi macOS için yazılmış (`bin/kos.py` POSIX `fcntl` kullanıyor, `bin/zamanla.py` launchd kuruyor). Her şeyi WSL (Ubuntu) içinde çalışacak şekilde kur. Zamanlayıcı için launchd yerine Windows Görev Zamanlayıcı'dan `wsl` komutunu çağıran bir kurulum yaz ya da WSL içinde cron kullan; hangisini seçtiğini ve nedenini bana söyle.

Önce bu promptun tamamını oku, sonra `ANAYASA.md`, `sirket/AJAN-KIMLIGI.md`, `docs/05-yeni-takim.md` ve `takimlar/_iskelet/` dosyalarını oku. Mevcut üç takım (x-icerik, youtube-analiz, twitter-icerik) bu şirkette gereksiz; onları sil ya da devre dışı bırak ve testleri buna göre güncelle. Her adımdan sonra kısa bir özet ver ve bir sonraki adıma geçmeden onayımı bekle.

---

## TEMEL İLKE: SAYIYI KOD HESAPLAR, AJAN YORUMLAR

RSI, Bollinger, ATR, stop, pozisyon adedi gibi hiçbir sayıyı yapay zekâ ajanı hesaplamaz. Tüm hesaplar deterministik Python betiklerinde yapılır ve JSON'a yazılır. Ajan yalnızca bu JSON'u okur, haberleri araştırır, kuralları uygular ve panoyu yazar. Panodaki her sayı `veri/*.json` içinde birebir bulunmalıdır (ANAYASA §2: kaynaksız sayı yok).

---

## ADIM 1 · ANAYASA'YA EKLENECEK MADDELER

Mevcut beş maddeyi koru, şu maddeleri ekle:

**§6 · Emir düğmesi insanın.** Hiçbir takım aracı kuruma bağlanamaz, emir gönderemez, TradingView'da alarm ya da çizim oluşturamaz. Çıktı bir panodur; alım satım kararını ve emri insan verir. Panoda "al" emri kipi kullanılmaz; "kurala uyan aday" denir.

**§7 · Strateji insanın ve sürümlüdür.** Stratejinin kuralları `sirket/STRATEJI-v1.md` dosyasındadır. Ajan bu kuralları değiştiremez, esnetemez, "bu sefer istisna" yapamaz. Kural önerisi yalnızca `defter.md` dosyasına yazılır. Kural değişirse yeni dosya açılır (v2) ve her çıktıda hangi sürümün kullanıldığı yazar.

**§8 · Risk tavanları.** İşlem başı risk portföyün %1'i. Aynı anda en fazla 5 açık pozisyon. Toplam açık risk portföyün %5'ini geçemez. Aynı gün en fazla 3 yeni aday "işleme uygun" işaretlenir. Bu tavanlar betikte uygulanır, ajan yalnızca raporlar.

---

## ADIM 2 · STRATEJİ DOSYASI: `sirket/STRATEJI-v1.md`

Bu içeriği birebir yaz:

### Evren (hangi hisseler)
Kaynak: TradingView hisse takipçisi **Nasıl Başarılı Trader Olursun? cuma cevik**
- Adres: https://www.tradingview.com/screener/1wmjOyDZ/
- Hesapta aynı filtrelere sahip bir kopyası daha var ("…cuma cevik_üzerine_deneme"). O kopya KULLANILMAZ; tek kaynak yukarıdaki takipçidir.
- Takipçideki filtreler değişirse bu dosya da güncellenir ve strateji sürümü artar (v2).

Takipçinin filtreleri:
- Ülke: ABD. Endeksler: S&P 500, Nasdaq 100, Dow Jones Industrial Average, Nasdaq Composite, Russell 2000
- Piyasa değeri > 2 milyar $
- Analist notu: "Al" veya "Güçlü al"
- 1 yıllık performans > %50
- Fiyat > EMA100 ve Fiyat > EMA200 (günlük)
- Fiyat > EMA50 ve Fiyat > EMA21 (haftalık)
- 90 günlük ortalama hacim > 10 günlük ortalama hacim
- ADR > %3,5

### Giriş sinyali (RSI Bollinger — alt banda değen VEYA altına geçen)
- `rsi` = RSI(kapanış, 14), Wilder yumuşatması (TradingView `ta.rsi` ile aynı)
- `orta` = SMA(rsi, 14)
- `alt` = orta − 2 × stdev(rsi, 14). stdev, TradingView `ta.stdev` gibi POPÜLASYON standart sapması (ddof=0) olmalı
- `ust` = orta + 2 × stdev(rsi, 14)
- `mesafe` = rsi − alt (negatif ise RSI bandın altında)
- **Koşul 1 — bölgede:** dünkü kapanışta `mesafe` ≤ 2,0 RSI puanı. Bu, hem alt çizgiye değmeyi/yaklaşmayı hem de altına geçmeyi kapsar.
- **Koşul 2 — dönüş:** bugün `rsi` > dünkü `rsi` VE dünkü `rsi` ≤ önceki günün `rsi`'si (dün bir dip oluştu, bugün yukarı döndü)
- **Sinyal tipi:** son 5 barda `mesafe` < 0 olmuşsa `ALTINA_GECTI`, olmamışsa `DOKUNDU`. İki tip panoda ayrı gösterilir ve günlükte ayrı ölçülür.
- Sinyal yalnızca kapanmış günlük bara göre hesaplanır.

### Eleme (sinyal var ama işleme uygun değil)
- Piyasa rejimi: SPY kapanışı SMA200'ün altındaysa rejim KIRMIZI olur; o gün hiçbir aday "işleme uygun" olamaz, liste yalnızca bilgi amaçlı gösterilir
- Bilanço tarihine 5 işlem gününden az kaldıysa elenir
- Stop mesafesi girişin %8'inden fazlaysa elenir
- Aynı gün 3'ten fazla uygun aday varsa stop mesafesi (%) en küçük olan 3'ü seçilir, diğerleri "yedek" olarak gösterilir
- Açık pozisyon sayısı 5 ise ya da toplam açık risk %5'e ulaştıysa yeni aday "uygun" olamaz

### Seviyeler
- Giriş referansı: sinyal gününün kapanışı (gerçek giriş ertesi gün açılışta, insan tarafından)
- Stop: giriş − 1,5 × ATR(14). Stop sadece yukarı taşınır, asla aşağı çekilmez
- R (risk birimi) = giriş − stop
- Adet = aşağı yuvarla((PORTFOY × 0,01) ÷ R). PORTFOY değeri `bin/ayar.py` içinde tek yerde durur
- 2R seviyesi = giriş + 2 × R (bilgi amaçlı)

### Çıkış
- Stop seviyesine gelirse çık
- Günlük kapanışta RSI, `orta` bandın üstüne çıkarsa çık (asıl hedef)
- 15 işlem günü içinde ne stop ne hedef olduysa çık
- Bilanço açıklanmadan önceki son işlem gününde pozisyonu kapat

### Bu sürümün durumu
v1 henüz geriye dönük testten geçmedi. `DOKUNDU` sinyal tipi hiç test edilmedi. Bu yüzden v1'in ilk 8 haftası kâğıt üzerinde (paper) işlemdir; gerçek para, geriye dönük test ve kâğıt işlemler pozitif beklenti gösterdikten sonra ve insan kararıyla kullanılır.

---

## ADIM 3 · VERİ BETİĞİ: `bin/tarama_cek.py`

LLM çağırmayan, deterministik bir Python betiği yaz. Görevleri:

1. **Evreni al.** TradingView tarayıcı uç noktasına (scanner.tradingview.com/america/scan) Python `requests` ile POST at ve evren filtrelerini uygula. Bu uç nokta resmi değildir ve bozulabilir. Bu yüzden şu yedek yolu da yaz: uç nokta hata verirse `evren/cuma-cevik.csv` dosyasını oku (bu dosyayı ben "Nasıl Başarılı Trader Olursun? cuma cevik" takipçisinin menüsünden "Sonuçları CSV olarak indir" ile indirip koyacağım). Hangi yolun kullanıldığı JSON'a yazılsın.
   **Doğrulama:** İlk kurulumda uç noktadan gelen sembol listesini bana göster. Ben takipçiyle karşılaştıracağım; sayı ve semboller birebir tutmuyorsa (birkaç sembollük farklar dahil) filtreleri takipçiyle eşleşene kadar düzelt. Filtre kolon adlarını tahmin etme: TradingView bilinmeyen kolona hata vermez, sessizce boş döner ve filtre çalışmıyormuş gibi görünür.
2. **Günlük barları çek.** Evrendeki semboller + SPY + QQQ için `yfinance` ile son 2 yılın günlük verisini TEK bir toplu `download` çağrısıyla indir. ~60 sembol için limit sorunu olmaz; yine de hata alan sembolleri listele ve atla.
3. **Hesapla:** her sembol için rsi, orta, alt, ust, mesafe, sinyal (var/yok), sinyal tipi, ATR(14), stop, stop %, R, adet, 2R seviyesi, SMA200 üstünde mi, son kapanış.
4. **Bilanço tarihi:** yfinance'ten bir sonraki bilanço tarihini al; alınamazsa `null` yaz ve panoda "bilinmiyor — elle kontrol et" göster. Tahmin etme.
5. **Rejim:** SPY ve QQQ için kapanış, SMA200, rejim (YESIL/KIRMIZI).
6. **Açık pozisyonları izle:** `pozisyonlar.csv` dosyasını oku (kolonlar: sembol, giris_tarihi, giris, adet, stop, strateji_surumu). Her pozisyon için bugünkü çıkış kontrolünü yap: stop'a geldi mi, RSI orta bandı geçti mi, kaç işlem günü oldu, bilanço yaklaşıyor mu. Çıkış koşulu varsa `CIK` ve sebebini yaz.
7. **Risk tavanlarını uygula:** açık pozisyon sayısı, toplam açık risk, günlük 3 aday sınırı.
8. Çıktı: `takimlar/gc-tarama/veri/YYYY-MM-DD.json`. Her adayda: sembol, sinyal tipi, tüm sayılar, uygun/elendi/yedek durumu ve eleme sebebi.

`bin/geri_test.py`: AYNI hesaplama fonksiyonlarını kullanan (kopya kod değil, ortak modül) bir geriye dönük test betiği yaz. Evrendeki semboller için son 5 yılı test etsin ve sinyal tipine göre (DOKUNDU / ALTINA_GECTI / ikisi) işlem sayısı, kazanma oranı, ortalama kazanç, ortalama kayıp, beklenti (işlem başı ortalama % getiri), en büyük kayıp ve komisyon sonrası sonucu versin. Raporun başına şu uyarıyı yaz: "Bu evren bugünün güçlü hisselerinden oluşur; geçmiş sonuç hayatta kalma yanlılığı nedeniyle olduğundan iyi görünür."

Testler: RSI ve Bollinger hesabını bilinen bir örnek seriyle doğrulayan birim testler yaz. SNDK için hesapladığın son 5 günlük rsi/orta/alt değerlerini bana göster; TradingView'daki grafiğimle karşılaştıracağım.

---

## ADIM 4 · TAKIM: `gc-tarama`

`bin/takim-olustur.sh gc-tarama` ile oluştur ve `takim.md` dosyasını doldur:

- **description:** Geri çekilme şirketinin tarama takımı olarak veri betiğinin ürettiği JSON'u okuyup adayların haberlerini araştırmak ve kuralları uygulayan günlük panoyu yazmak; al-sat kararı vermek değil.
- **model:** sonnet · **butce_usd:** 1
- **tools:** Read, Write, Glob, Grep, WebSearch, WebFetch, Bash(python3 bin/tarama_cek.py *)
- **Ne zaman koşar:** Pazartesi–Cuma, günde İKİ kez. Saatler ABD saatine (America/New_York) göre kurulur ki yaz/kış saati değişince elle kaydırmak gerekmesin:
  - **Kapanış koşusu — 16:15 New York** (yaz saatinde 23:15, Kasım'dan sonra 00:15 TSİ): kapanmış günlük barla sinyalleri hesaplar, yarının aday listesini ve açık pozisyonların çıkış kontrolünü yazar.
  - **Açılış öncesi koşusu — 09:00 New York** (yaz saatinde 16:00, Kasım'dan sonra 17:00 TSİ): YENİ SİNYAL HESAPLAMAZ. Bir önceki kapanış koşusunun adaylarını alır, premarket fiyatını ve gece gelen haberleri kontrol eder, panoyu günceller.
  - Gün içinde (açılış ile kapanış arasında) tarama YAPILMAZ: sinyal kapanmış günlük bara göre tanımlıdır; gün içi yarım barda RSI sürekli değişir, sinyal görünüp kaybolur.
  - `bin/ayar.py` içindeki mesai penceresini bu iki koşuyu kapsayacak şekilde değiştir (kapanış koşusu kışın 00:15 TSİ'ye düşer). Bu değişikliği ANAYASA §4'e not olarak işle.
  - ABD tatil günlerinde betik "yeni bar yok" der ve koşu erken biter.

**Kapanış koşusu adımları:**
1. `python3 bin/tarama_cek.py --kapanis` çalıştır. Hata olursa koşuyu hata olarak kapat, pano yazma.
2. Bugünün `veri/*.json` dosyasını oku.
3. "Uygun" ve "yedek" her aday için:
   - **Haber:** son 5 günde düşüşün sebebi olabilecek haber var mı? En fazla 2 kaynak, her iddia ✅/🟡/⛔ etiketli. Sebep-sonuç ilişkisi uydurma; bulamazsan "belirgin haber bulunamadı" yaz.
   - **Bilanço tarihi doğrulama:** JSON'daki tarih `null` ya da şüpheliyse şirketin yatırımcı ilişkileri sayfasından veya güvenilir bir takvimden doğrula ve kaynağıyla yaz. Doğrulanan tarih 5 işlem gününden yakınsa adayı "elenmeli — insan onayı" olarak işaretle (kuralı kendin uygulamazsın, insana gösterirsin).
   - **Kırmızı bayrak:** düşüş şirkete özgü ağır bir olaydan mı (bilanço hayal kırıklığı, rehberlik düşürme, dava, muhasebe sorunu, hisse satışı/sulandırma)? Varsa "KIRMIZI BAYRAK" notu ekle. Bu bir geri çekilme değil, hikâye değişimi olabilir.
   - **Sektör bağlamı:** aynı gün sektördeki diğer hisseler de düştü mü (piyasa geneli mi, şirkete özel mi)? Tek satır.
4. Haber ve bayraklar kural sonucunu DEĞİŞTİRMEZ; yalnızca not olarak eklenir. Kararı insan verir.
5. Panoyu yaz (Adım 5).
6. `durum.json` güncelle, `defter.md`'ye en fazla bir ders, koşu kaydını yaz.

**Açılış öncesi koşusu adımları:**
1. `python3 bin/tarama_cek.py --acilis` çalıştır: yalnızca önceki kapanış koşusunun adayları ve açık pozisyonlar için premarket fiyatını çeker (TradingView tarayıcı uç noktasında `premarket_close`, `premarket_change` kolonları). Yeni sinyal hesaplamaz.
2. Premarket fiyatı stop seviyesinin altındaysa adayı "GAP — girilmez" olarak işaretle. Premarket fiyatı 2R seviyesinin üstündeyse "kaçtı — kovalanmaz" olarak işaretle. Bu kontroller betikte yapılır.
3. Gece gelen yeni haberleri kontrol et (yalnızca adaylar ve açık pozisyonlar için).
4. Panonun üst şeridine "Açılış öncesi güncellemesi" bölümünü ekle; kapanış koşusunun geri kalanını değiştirme.
5. Koşu kaydını yaz.

**Asla:** sayı hesaplamaz ya da yuvarlamaz (JSON'daki değeri aynen yazar), kuralı esnetmez, "güçlü al", "kaçırma" gibi yönlendirici dil kullanmaz, elenmiş adayı haber güzel diye uygun yapmaz, fiyat tahmini yapmaz.

`kurallar.md` (bekçi bunu okur):
- Panodaki her sayı o günün `veri/*.json` dosyasında birebir bulunmalı
- "Uygun" etiketli her aday JSON'da da "uygun" olmalı
- Rejim KIRMIZI ise hiçbir aday "uygun" görünmemeli
- Her haber iddiası etiketli ve kaynaklı olmalı
- Strateji sürümü (v1) panoda yazmalı

---

## ADIM 5 · PANO: `takimlar/gc-tarama/cikti/`

Her koşuda iki dosya: `YYYY-MM-DD-pano.html` (arşiv) ve `pano.html` (her zaman en güncel; bunu tarayıcıda yer imi olarak açacağım). Tek dosya, dış bağımlılık yok, koyu tema, telefonda da okunur.

Panonun bölümleri, yukarıdan aşağıya:

1. **Üst şerit:** tarih, veri hangi kapanışa ait, strateji sürümü (v1 — kâğıt işlem dönemi), SPY ve QQQ rejim çipleri (YEŞİL/KIRMIZI), evrendeki hisse sayısı, bugünkü sinyal sayısı, açık pozisyon sayısı ve toplam açık risk.
2. **Açık pozisyonlar ve çıkış kontrolü:** her pozisyon bir satır; `CIK` olanlar en üstte, kırmızı, sebebiyle.
3. **İşleme uygun adaylar (en fazla 3):** her aday bir kart:
   sembol · sinyal tipi rozeti (DOKUNDU / ALTINA GEÇTİ) · kapanış · RSI ve alt bant değeri · giriş referansı · stop (ve %) · R · adet · 2R seviyesi · çıkış kuralı ("RSI orta bandı geçince, en geç 15 işlem günü") · bilanço tarihi · haber notu (etiketli) · TradingView grafik bağlantısı (tradingview.com/chart/?symbol=BORSA:SEMBOL)
4. **Yedekler:** kurala uyan ama günlük 3 sınırına takılanlar.
5. **Elenenler:** sinyal verdi ama elendi; tek satır ve sebep (bilanço yakın, stop %8'den geniş, rejim kırmızı, risk tavanı).
6. **Alt bilgi:** "Bu pano bir kural uygulayıcısıdır, yatırım tavsiyesi değildir. Emir düğmesi insandadır."

Hiç sinyal yoksa bunu açıkça yaz: "Bugün kurala uyan aday yok." Boş gün de bir sonuçtur.

---

## ADIM 6 · TAKIM: `gc-gunluk`

- **Ne zaman koşar:** her pazartesi 09:30.
- **Girdi:** `islemler.csv` (kapanmış işlemlerim; kolonlar: sembol, sinyal_tipi, giris_tarihi, giris, cikis_tarihi, cikis, adet, cikis_sebebi, strateji_surumu, gercek_mi) ve son geriye dönük test raporu.
- **Hesabı betik yapar:** `bin/gunluk_hesap.py` yaz. Toplam ve sinyal tipine göre işlem sayısı, kazanma oranı, ortalama kazanç/kayıp (R cinsinden), beklenti, en büyük kayıp, kurala uymayan işlemler (stop aşağı çekilmiş, süre aşılmış vb.).
- **Ajan:** sayıları yorumlar ve `cikti/YYYY-Www-gunluk.md` yazar. Gerçek sonuçlar geriye dönük testten belirgin şekilde kötüyse bunu en üstte yazar. İşlem sayısı 30'dan azsa "örneklem küçük, karar için erken" der. Kural değişikliği önerirse yalnızca `defter.md`'ye yazar.

---

## ADIM 7 · OBSIDIAN HAFIZASI (claude-obsidian-kit)

selmakcby/claude-obsidian-kit'i bu şirkete bağla. Kasa (vault) klasörü `kasa/`. Sadece şunları tut:
- `decisions/`: strateji sürüm kararları (v1 neden böyle, v2'ye neden geçildi)
- `sessions/`: her haftanın `gc-gunluk` özeti
- `concepts/`: RSI Bollinger, geri çekilme, risk birimi (R) gibi kavram notları

Kasaya teknik analiz kitabı, formasyon rehberi ya da başka stratejilerin notlarını koyma. Bu şirketin hafızası yalnızca bu stratejiye aittir.

---

## ADIM 8 · KURU KOŞU, TEST VE ZAMANLAMA

1. `python3 -m unittest discover -s tests` yeşil olmalı
2. `python3 bin/geri_test.py` çalıştır ve sonucu bana göster. Beklenti negatifse DUR ve bana söyle; şirketi zamanlamaya bağlamadan önce kararı ben vereceğim
3. `python3 bin/kos.py gc-tarama --kuru`, sonra gerçek bir koşu. Oluşan `pano.html`'in yolunu ver
4. Her şey doğruysa zamanlayıcıyı kur: hafta içi 16:15 New York (kapanış koşusu) ve 09:00 New York (açılış öncesi koşusu) gc-tarama; pazartesi 09:30 TSİ gc-gunluk. Zamanlayıcının New York saatine göre çalıştığını, yaz/kış saati geçişinde TSİ karşılığının kaydığını test et ve bana göster
5. Maliyeti raporla: bir gc-tarama koşusu kaç USD tuttu

Bitince bana şunları ver: oluşturulan dosyaların listesi, geriye dönük test özeti (sinyal tipine göre), ilk panonun yolu ve kurulumda bilmem gereken riskler.
