---
type: concept
date: 2026-09-28
tags: [gosterge, sinyal, rsi]
links: [[decisions/2026-09-28-strateji-v1]]
status: accepted
source: kurulum
---

# RSI Bollinger

## Context
v1'in giriş sinyali fiyatın değil, RSI'ın kendi Bollinger bandına göre tanımlanır. Bu not tanımı ve
hesaplamadaki tuzakları tutar; hesap `bin/gc_hesap.py`'dedir.

## Content
- `rsi` = RSI(kapanış, 14), Wilder yumuşatması — TradingView `ta.rsi` ile aynı: ilk ortalama ilk 14 değişimin
  basit ortalaması, sonra `(önceki × 13 + yeni) / 14`.
- `orta` = SMA(rsi, 14); `alt/üst` = orta ∓ 2 × stdev(rsi, 14).
- **Tuzak 1 — stdev:** TradingView `ta.stdev` popülasyon standart sapmasıdır (ddof=0). pandas'ın varsayılanı
  örneklem (ddof=1) — kullanılırsa bant genişler ve sinyal kayar.
- **Tuzak 2 — fiyat serisi:** TradingView grafiği bölünmeye göre düzeltilmiş, temettüye göre düzeltilmemiş fiyat
  kullanır; yfinance'te `auto_adjust=False` + `Close` bununla örtüşür.
- **Tuzak 3 — yarım bar:** gün içinde RSI sürekli değişir; sinyal yalnız kapanmış günlük barla hesaplanır.
- `mesafe` = rsi − alt. Dün `mesafe` ≤ 2 (bölgede) ve dün dip, bugün yukarı dönüş → sinyal.
- Tip: son 5 barda `mesafe` < 0 olduysa ALTINA_GECTI, olmadıysa DOKUNDU. İki tip ayrı ölçülür.

## Related
- [[decisions/2026-09-28-strateji-v1]] — bu tanımın strateji içindeki yeri
- [[concepts/geri-cekilme]] — sinyalin hangi evrende arandığı
