# Kurallar — gc-gunluk

> Bekçi bu dosyayı okur ve koşu kaydını buna göre denetler. Yalnızca insan değiştirir.

## Neye göre çalışır
- ANAYASA'nın tamamı geçerlidir; özellikle §2 (kaynaksız sayı yok) ve §7 (kural önerisi yalnız defterde).
- Yorum ölçüsü: `skills/gunluk-yorumu/SKILL.md`.

## Asla yapmaz
- Sayı hesaplamaz, yuvarlamaz; `islemler.csv` ya da veri JSON'unu değiştirmez.
- Kural değişikliğini notta önermez ya da uygulamaz; öneri yalnız `defter.md`'dedir.
- "Gerçek paraya geç", "şunu al" gibi yönlendirici cümle kurmaz.

## Çıktı kalite ölçütleri
- Notteki her sayı o haftanın `veri/YYYY-Www.json` dosyasında birebir bulunur.
- `karsilastirma` içinde `belirgin_kotu: true` varsa bu uyarı notun en üstündedir.
- İşlem sayısı 30'dan azsa "örneklem küçük, karar için erken" cümlesi vardır.
- DOKUNDU ve ALTINA_GECTI ayrı raporlanır; kâğıt ve gerçek işlemler ayrı satırdadır.
- Kural dışı işlemler (süre aşımı, stop altında çıkış, tanımsız sebep) tek tek listelenir.
- Strateji sürümü başlıkta yazar.
