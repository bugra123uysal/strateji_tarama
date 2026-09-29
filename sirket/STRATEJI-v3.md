# STRATEJİ v3 — Güçlü Hissede Geri Çekilme

> İnsanındır (ANAYASA §7). Ajan değiştiremez, esnetemez; kural önerisi yalnızca `defter.md`'ye yazılır.
> Kural değişirse bu dosya değişmez — `STRATEJI-v4.md` açılır.
> **v2'den farkı (2026-09-29, insan kararı):** elemeye **trend koşulu** eklendi — sinyal gününde günlük
> fiyat > EMA200 ve EMA50 > EMA200 değilse aday elenir. Fiyat > EMA100 ise "GÜÇLÜ TREND", değilse "TREND"
> olarak gösterilir; ikisi de uygun olabilir. Evren, giriş sinyali, seviye ve çıkış kuralları v2 ile aynı.
> (v2'nin v1'den farkı: evren "…cuma cevik_üzerine_deneme" takipçisi, 1 yıllık performans > %30.)

### Evren (hangi hisseler)
Kaynak: TradingView hisse takipçisi **Nasıl Başarılı Trader Olursun? cuma cevik_üzerine_deneme**
- Adres: https://www.tradingview.com/screener/hcMDHuqR/
- v1'in kaynağı olan "…cuma cevik" (https://www.tradingview.com/screener/1wmjOyDZ/) artık KULLANILMAZ.
- Takipçideki filtreler değişirse bu dosya değişmez; yeni sürüm (v4) açılır.

Takipçinin filtreleri (2026-09-28'de takipçiden okundu; o gün 66 hisse):
- Ülke: ABD. Endeksler: S&P 500, Nasdaq 100, Dow Jones Industrial Average, Nasdaq Composite, Russell 2000
- Piyasa değeri > 2 milyar $
- Analist notu: "Al" veya "Güçlü al"
- 1 yıllık performans > %30
- Fiyat > EMA100 ve Fiyat > EMA200 (günlük)
- Fiyat > EMA50 ve Fiyat > EMA21 (haftalık)
- 90 günlük ortalama hacim > 10 günlük ortalama hacim
- ADR > %3,5

Uygulama notu (kural değil): takipçinin "Al / Güçlü al" filtresi ücretsiz uç noktada okunamıyor; betik
`recommendation_mark` < 1,8 kullanır (`bin/ayar.py` → `EVREN_ANALIST_UST`, takipçiyle karşılaştırılarak bulundu).
Kalan tek-tük fark gün içi sınır değerlerinden gelir; bkz. `kasa/decisions/2026-09-28-strateji-v2.md`.

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
- **Trend (v3):** sinyal gününün kapanışında günlük fiyat > EMA200 VE EMA50 > EMA200 değilse elenir ("trend dışı").
  EMA(kapanış, n), TradingView `ta.ema` gibi üstel (alfa = 2/(n+1)). Fiyat > EMA100 ise aday "GÜÇLÜ TREND",
  değilse "TREND · EMA100 altı" olarak işaretlenir — ikisi de uygun olabilir, fark yalnız gösterilir.
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
v3 kâğıt işlem dönemindedir; 8 haftalık kâğıt işlem şartı v3 için baştan başlar. Gerçek para, geriye
dönük test ve kâğıt işlemler pozitif beklenti gösterdikten sonra ve insan kararıyla kullanılır.
`DOKUNDU` tipi insan kararıyla tutuldu (2026-09-29); v2 geri testinde trend içinde bile sıfıra yakındı —
kâğıt işlemde `ALTINA_GECTI`'den ayrı ölçülür.
