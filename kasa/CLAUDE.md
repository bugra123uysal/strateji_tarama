# Kasa Anayasası — Geri Çekilme Şirketi

> Bu dosya kasanın **şemasıdır**. Kasaya dokunan her ajan (`scribe`, `archivist`, `gc-gunluk`) önce bunu okur.
> Kaynak: [selmakcby/claude-obsidian-kit](https://github.com/selmakcby/claude-obsidian-kit) `vault-template/CLAUDE.md`
> (MIT) — bu şirkete daraltıldı: klasör adı `vault/` → `kasa/`, yalnız üç klasör, yalnız bu strateji.

## Amaç

Bu kasa Geri Çekilme Şirketi'nin kalıcı hafızasıdır ve **yalnızca "Güçlü Hissede Geri Çekilme" stratejisine
aittir.** Şu sorulara cevap verir:

- Strateji neden böyle? v1 neden böyle kuruldu, v2'ye neden (ne zaman) geçildi?
- Haftalar nasıl geçti? `gc-gunluk`'un haftalık özetleri.
- RSI Bollinger, geri çekilme, risk birimi (R) gibi kavramlar bu stratejide ne anlama geliyor?

## Neler GİRMEZ

- Teknik analiz kitabı, formasyon rehberi, genel eğitim notu.
- Başka stratejilerin notları (kırılım stratejisi ayrı bir şirkettedir; ona hiçbir şekilde dokunulmaz).
- Hisse tavsiyesi, fiyat tahmini, "al" listesi. Günlük adaylar panodadır (`takimlar/gc-tarama/cikti/`), kasada değil.

## Klasörler (yalnız bunlar)

```
kasa/
├── CLAUDE.md      ← bu anayasa
├── index.md       ← katalog — her yazımda güncellenir
├── log.md         ← yazım günlüğü (tek satır / olay)
├── _schema/       ← template.md + conventions.md (kitin kuralları)
├── decisions/     ← strateji sürüm kararları: YYYY-MM-DD-<konu>.md
├── sessions/      ← haftalık gc-gunluk özetleri: YYYY-Www.md
└── concepts/      ← stratejinin kavramları: rsi-bollinger.md, risk-birimi-r.md …
```

`architecture/`, `design/`, `entities/` bu kasada **yoktur**; kitin yönlendirme tablosu oraya işaret etse de
yazılmaz. En fazla 2 seviye; ilişkiler klasörle değil `[[bağlantı]]` ile kurulur.

## Not biçimi

Her notta frontmatter ([[_schema/template|template]]):

```yaml
---
type: decision | session | concept
date: YYYY-MM-DD
tags: []
links: []
status: draft | accepted | deprecated
source: user | gc-gunluk | scribe | kurulum
---
```

Gövde: `# Başlık` → `## Context` → `## Content` (tek fikir) → `## Related` (`[[bağlantı]]` + neden ilgili).

## Kurallar

- Dosya adları kebab-case ASCII. `decision` → `YYYY-MM-DD-` önekli; `session` → `YYYY-Www`.
- **Kaynaksız sayı yok** (ANAYASA §2): nottaki her sayı bir dosyaya (geri test raporu, günlük JSON'u) bağlanır.
- **Strateji kuralı kasada değişmez** (ANAYASA §7): karar notu bir sürüm kararını *kaydeder*;
  kuralın kendisi `sirket/STRATEJI-vN.md`'dedir. Öneriler `defter.md`'ye gider.
- Çelişki varsa Obsidian'ın "conflict" callout'u ile iki taraf da gösterilir; sessizce üzerine yazılmaz.
- Her yazımda `index.md` güncellenir ve `log.md`'ye tek satır: `## [YYYY-MM-DD] ingest | …`

## Sağlık denetimi

`python3 bin/kasa_lint.py kasa --exclude CLAUDE.md --exclude log.md` — yetim not, kırık bağlantı, eksik frontmatter (kitin `vault-lint.py`'si).
