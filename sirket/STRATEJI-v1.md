# STRATEJİ v1 — Güçlü Hissede Geri Çekilme

> İnsanındır (ANAYASA §7). Ajan değiştiremez, esnetemez; kural önerisi yalnızca `defter.md`'ye yazılır.
> Kural değişirse bu dosya değişmez — `STRATEJI-v2.md` açılır.

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
