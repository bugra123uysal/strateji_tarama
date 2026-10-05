# Defter — gc-gunluk

> Ajan yazar, insan okur. Her koşudan en fazla bir ders. Yeni ders üste.

## Dersler

- 2026-10-05 (2026-W41): `islemler.csv` ikinci haftadır boş (0 işlem); not şablonu bu durumda hep aynı
  boş tabloyu üretiyor. Boş hafta için kısa bir şablon yeterli; geri test dosyası haftadan haftaya
  değişiyor (2026-09-27 → 2026-09-29, v1 → v3), notta hangi dosya/sürümün referans alındığı yazılmalı.
- 2026-09-28 (2026-W40): `islemler.csv` yalnızca başlık satırıyla boş geldiğinde `veri/YYYY-Www.json`
  içindeki tüm kırılımlar (`tum`, `DOKUNDU`, `ALTINA_GECTI`, `gercek`, `kagit`) `islem: 0, orneklem_kucuk: true`
  oluyor ve `karsilastirma.*.fark_r` `null` dönüyor (`karsilastir()` gerçek işlem 0 iken `beklenti_net_r`
  bulamıyor). Bu durumda notta boş tablo bırakmak yerine "kapanmış işlem yok, geri testle kıyas yapılamadı"
  cümlesini açıkça yazmak gerekiyor — aksi halde patron notu "veri eksik/hata" ile "henüz işlem yok" arasında
  ayıramaz.

## Kural önerileri (insana)
