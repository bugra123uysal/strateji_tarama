---
type: concept
date: 2026-09-28
tags: [risk, olcu, pozisyon]
links: [[decisions/2026-09-28-strateji-v1]]
status: accepted
source: kurulum
---

# Risk birimi (R)

## Context
Sonuçları dolar ya da yüzde yerine R ile ölçmek, farklı fiyattaki ve oynaklıktaki işlemleri aynı cetvelle
karşılaştırır. Bu not R'nin tanımını ve komisyonla ilişkisini tutar.

## Content
- **R = giriş − stop.** Stop = giriş − 1,5 × ATR(14); stop yalnız yukarı taşınır.
- **Adet = aşağı yuvarla(portföy × %1 ÷ R).** Her işlem portföyün %1'ini riske atar; portföy `bin/ayar.py`'de.
- **Sonuç R cinsinden:** (çıkış − giriş) ÷ (giriş − ilk stop). +1R = riske atılan kadar kazanç; −1R = tam stop.
- **Beklenti:** işlem başı ortalama R. Kazanma oranı tek başına anlamsızdır; beklenti belirleyicidir.
- **Komisyonun R payı:** gidiş-dönüş komisyon ÷ işlem başı risk. Sabit dolar komisyonda küçük portföy cezalandırılır —
  kurulumda 2.500 USD'lik portföyde bu pay yüksekti, 50.000 USD'ye çıkınca önemsizleşti
  ([[decisions/2026-09-28-strateji-v1]]).
- **Adet 0:** R, işlem başı risk tutarından büyükse (pahalı ve oynak hisse) tek hisse bile tavanı aşar → aday elenir.
- `islemler.csv`'de `ilk_stop` kolonu bu yüzden zorunludur: onsuz R hesaplanamaz.

## Related
- [[decisions/2026-09-28-strateji-v1]] — portföy ve komisyon kararları
- [[concepts/geri-cekilme]] — stop'un neden ATR ile çizildiği (oynaklığa göre)
