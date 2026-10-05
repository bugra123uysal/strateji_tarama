# Geri Çekilme Şirketi — Kasa

Şirketin kalıcı hafızası; yalnız "Güçlü Hissede Geri Çekilme" stratejisine aittir. Kurallar: `kasa/CLAUDE.md`.

## Kararlar
- [[decisions/2026-09-29-strateji-v3]] — sinyal günü trend koşulu (EMA50>EMA200, fiyat>EMA200); v3 geri testi
- [[decisions/2026-09-28-strateji-v2]] — evren "…üzerine_deneme" takipçisine taşındı, 1Y performans > %30; v2 geri testi (yerini v3 aldı)
- [[decisions/2026-09-28-strateji-v1]] — v1 neden böyle kuruldu, ilk geri test, kurulum kararları (yerini v2 aldı)

## Kavramlar
- [[concepts/rsi-bollinger]] — giriş sinyalinin tanımı ve hesap tuzakları
- [[concepts/geri-cekilme]] — güçlü hisse, rejim, hikâye değişimi, sahte geri çekilme
- [[concepts/risk-birimi-r]] — R, adet, beklenti, komisyonun R payı

## Haftalar
`sessions/` altında `YYYY-Www.md` — gc-gunluk her pazartesi yazar.
- [[sessions/2026-W41]] — kapanmış işlem yok (v3), örneklem küçük; geri testle kıyas yapılamadı
- [[sessions/2026-W40]] — kapanmış işlem yok, örneklem küçük; geri testle kıyas yapılamadı

---
Şema: [[_schema/template|template]] · [[_schema/conventions|conventions]] · denetim: `python3 bin/kasa_lint.py kasa --exclude CLAUDE.md --exclude log.md`
