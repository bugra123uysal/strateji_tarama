---
type: concept
date: 2026-09-28
tags: [strateji, evren, rejim]
links: [[decisions/2026-09-28-strateji-v1]], [[concepts/rsi-bollinger]]
status: accepted
source: kurulum
---

# Geri çekilme

## Context
Stratejinin adı "Güçlü Hissede Geri Çekilme". Bu not "güçlü hisse" ile "geri çekilme"nin bu şirkette neye
karşılık geldiğini ve nerede işe yaramadığını tutar.

## Content
- **Güçlü hisse = takipçi evreni.** Trendde (fiyat günlük EMA100/200 ve haftalık EMA21/50 üstünde), 1 yılda
  güçlü, analist notu Al/Güçlü al, yeterince oynak (ADR > %3,5). Filtreler `sirket/STRATEJI-v1.md`'de.
- **Geri çekilme = kısa süreli aşırı satım.** RSI kendi alt bandına iner ve döner ([[concepts/rsi-bollinger]]);
  fikir, trend sürerken fiyatın ortalamaya dönmesini yakalamaktır.
- **Piyasa rejimi:** SPY SMA200 altındaysa (KIRMIZI) hiçbir aday "uygun" olmaz — geniş düşüşte geri çekilme
  çoğu zaman devam eden düşüştür.
- **Geri çekilme değil, hikâye değişimi:** bilanço hayal kırıklığı, rehberlik düşürme, dava, muhasebe sorunu,
  hisse satışı/sulandırma. gc-tarama bunları "KIRMIZI BAYRAK" diye not eder; kural sonucu değişmez, karar insanındır.
- **Sahte geri çekilme:** satın alma anlaşmasındaki hisse (fiyat anlaşma bedeline sabitlenir, ATR çok düşük).
  İlk koşuda LNTH, ITGR, DV böyle çıktı → düşük oynaklık uyarısı eklendi.

## Related
- [[concepts/rsi-bollinger]] — geri çekilmenin ölçüsü
- [[decisions/2026-09-28-strateji-v1]] — evren ve rejim kurallarının kararı
