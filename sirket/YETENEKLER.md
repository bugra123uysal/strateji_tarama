# YETENEKLER — Geri Çekilme Şirketi

> Bu şirketin takımlarının kullandığı yeteneklerin kataloğu.
> Bir yetenek, o işin nasıl yapılacağını adım adım, şablonuyla ve kontrol listesiyle anlatan tek dosyadır:
> `skills/<ad>/SKILL.md`. Ajan koşu adımında **yalnızca ilgili yeteneği** okur.

## Neden bu dosyalar var — üç gerekçe

1. **Token sorununu çözmek.** Bir işin nasıl yapılacağını her koşuda baştan anlatmak pahalıdır ve her
   seferinde biraz farklı çıkar. Yetenek dosyası bir kez yazılır, ajan koşuda sadece ilgili adımda okur.
2. **Ajanın hatırlaması.** Ajanın hafızası yok; oturum kapanınca her şey gider. `defter.md` dünü,
   `skills/` ise **nasıl yapıldığını** hatırlar. Yazmadığın şey olmamıştır.
3. **Ajanın gelişmesi.** Her yetenek dosyasının sonunda `## Öğrenilenler` bölümü var. Ajan koşuda aldığı
   veriyle **kendini geliştirir**: dersi `defter.md`'ye yazar, aynı ders üç koşuda tekrar ederse yeteneğin
   `## Öğrenilenler` bölümüne öneri bırakır. Kararı patron verir.

## Katalog

| Takım | Yetenek | Ne işe yarar | Kaynak | Lisans |
|---|---|---|---|---|
| `gc-tarama` | [`kaynak-dogrulama`](../skills/kaynak-dogrulama/SKILL.md) | Her iddiayı birincil kaynağa açıp ✅/🟡/⛔ ile sınıflar. | kendi üretimimiz | — |
| `gc-gunluk` | [`gunluk-yorumu`](../skills/gunluk-yorumu/SKILL.md) | İşlem istatistiğini sayı uydurmadan, örneklem büyüklüğüne saygıyla yorumlar. | kendi üretimimiz | — |
## Nasıl çalışır (teknik)

- Kaynak: `takimlar/<takim>/takim.md` frontmatter'ındaki `skills: [ad1, ad2]` alanı.
- `bin/agents_uret.py` bu alanı **şirket alanı** sayar (agent frontmatter'ına sızmaz) ve önsöze
  `Yeteneklerin: ...` satırını ekler.
- `bin/kos.py` `istem()` aynı satırı koşu istemine koyar — `python bin/kos.py <takim> --kuru` ile görülür.
- Bağın bütünlüğünü `tests/test_skills.py` denetler.
