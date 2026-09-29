---
name: gunluk-yorumu
description: gunluk_hesap.py'nin ürettiği işlem istatistiğini (R cinsinden beklenti, kazanma oranı, kural dışı işlemler, geri test kıyası) sayı uydurmadan, örneklem büyüklüğüne saygı göstererek haftalık günlük notuna çevirir. gc-gunluk takımı kullanır.
kaynak: Geri Çekilme Şirketi'nin kendi üretimi — dış kaynak yok
lisans: —
uyarlayan: Geri Çekilme Şirketi (2026-09-28)
takimlar: [gc-gunluk]
---

# Günlük yorumu

## Ne zaman
Haftalık `gc-gunluk` koşusunda, `takimlar/gc-gunluk/veri/YYYY-Www.json` okunduktan sonra.

## Temel kural
Sayıyı betik hesaplar. Sen JSON'daki değeri **aynen** yazarsın; yeniden hesaplamaz, yuvarlamaz,
ortalamayı kafadan almazsın. JSON'da olmayan bir sayı notta yer alamaz.

## Okuma sırası
1. `karsilastirma.*.belirgin_kotu` true olan var mı? Varsa notun **ilk cümlesi** budur:
   "Gerçek/kâğıt sonuç geri testten belirgin şekilde kötü (<tip>: fark <fark_r> R)."
2. `ozet.tum.orneklem_kucuk` true ise ikinci cümle: "Örneklem küçük (<islem> işlem < 30), karar için erken."
3. Sinyal tipine göre tablo: DOKUNDU / ALTINA_GECTI / tümü — işlem, kazanma %, beklenti R, net beklenti R,
   en büyük kayıp R, toplam net USD. Kâğıt ve gerçek ayrı satır.
4. `kural_disi` listesi: her işlem için sembol, tarih ve ihlal. Yorum: disiplin sorunu mu (stop aşağı
   çekildi, süre aşıldı) yoksa kayıt sorunu mu (tip/sürüm boş)?
5. Geri test kıyası: `geri_test.ozet` ile yan yana; farkı yorumlarken hayatta kalma yanlılığını hatırlat.

## Yorum ilkeleri
- 30 işlemden azsa "şu tip daha iyi" deme; yalnız "şimdilik şöyle görünüyor, örneklem küçük" de.
- Kazanma oranını tek başına övme ya da yerme; beklenti (R) belirleyicidir.
- Kural değişikliği önerisi notta **yazılmaz**; yalnız `takimlar/gc-gunluk/defter.md` → "Kural önerileri (insana)"
  bölümüne tek satır olarak gider (ANAYASA §7).
- Yönlendirici dil yok: "artık gerçek paraya geç", "şunu al" gibi cümleler kurulmaz; karar insanındır.

## Şablon
```markdown
# İşlem günlüğü — YYYY-Www — strateji v3
> (varsa) belirgin kötü uyarısı
> (varsa) örneklem küçük uyarısı

## Sonuçlar (sinyal tipine göre)
| Tip | İşlem | Kazanma % | Beklenti R | Net R | En büyük kayıp R | Net USD |

## Kural dışı işlemler
## Geri test ile kıyas
## Bu hafta ne öğrendik (tek paragraf, sayı yalnız JSON'dan)
```

## Öğrenilenler
Bu skill koşuda aldığı veriyle **kendini geliştirir**: her koşudan sonra ne işe yaradığını ve nerede
yanıldığını `takimlar/<takim>/defter.md`'ye tek ders olarak yaz. Aynı ders üç koşuda tekrar ediyorsa
koşu kaydına "yetenek önerisi: `gunluk-yorumu` → ## Öğrenilenler'e şu satır eklensin" yaz; kararı patron verir,
skill'i kendi başına değiştirme.

- (henüz ders yok)
