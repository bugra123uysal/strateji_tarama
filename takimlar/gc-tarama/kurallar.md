# Kurallar — gc-tarama

> Bekçi bu dosyayı okur ve koşu kaydını buna göre denetler. Yalnızca insan değiştirir.

## Neye göre çalışır
- ANAYASA'nın tamamı geçerlidir; özellikle §2 (kaynaksız sayı yok), §6 (emir düğmesi insanın),
  §7 (strateji sürümlü, ajan esnetmez), §8 (risk tavanları betikte).
- Kurallar: `sirket/STRATEJI-v3.md`. Haber etiketleme: `skills/kaynak-dogrulama/SKILL.md`.

## Asla yapmaz
- Sayı hesaplamaz, yuvarlamaz, veri JSON'unu ya da panoyu elle düzenlemez; panoyu yalnız `bin/pano_yaz.py` yazar.
- Elenmiş ya da gözlem listesindeki (KURAL DIŞI) bir adayı "uygun" göstermez; kuralı esnetmez.
- "al", "güçlü al", "kaçırma" gibi yönlendirici dil ve fiyat tahmini kullanmaz.
- Kuruma bağlanmaz, emir göndermez, TradingView'da alarm ya da çizim oluşturmaz.
- `tarama_cek.py` hata verdiğinde pano yazmaz.

## Çıktı kalite ölçütleri
- Panodaki her hesaplanmış sayı (fiyat, RSI, bant, stop, R, adet, 2R, risk) o günün `veri/*.json` dosyasında birebir bulunur.
- "Uygun" etiketli her aday JSON'da da `durum: "uygun"`; rejim KIRMIZI ise hiçbir aday "uygun" görünmez.
- Her haber iddiası ✅/🟡/⛔ etiketli; ⛔ dışındaki her iddianın kaynak bağlantısı var; aday başına en fazla 2 kaynak.
  Haber metnindeki bir sayı ancak etiketli ve kaynaklı iddianın parçası olabilir.
- Bilanço tarihi bilinmiyorsa "bilinmiyor — elle kontrol et" görünür; tahmin edilmez.
- Strateji sürümü (v3) ve "kâğıt işlem" dönemi panoda yazar.
- Koşu kaydı: hangi veri dosyası okundu, kaç aday/uyarı işlendi, pano yolu, maliyet.
- Çıktı Türkçe; teknik terimler (RSI, ATR, R) orijinal hâliyle kalır.
