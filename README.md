# Bokhua Manual of Vascular Surgery

**ქართულენოვანი აკადემიური ჯიბის სახელმძღვანელო სისხლძარღვთა ქირურგებისა და რეზიდენტებისთვის**

- **ფორმატი:** `100 × 180 მმ`
- **ტექსტური კორპუსი:** `550 გვერდი` (`i–x` [10 გვ.] + `1–540` [540 გვ.] / `~137,500 სიტყვა`)
- **საბოლოო კაბადონი (Additive ილუსტრაციებით):** `~620–650 გვერდი`
- **სტრუქტურა:** Front Matter + `11 კარი` + `75 თავი` (`150 საბაზისო პრომპტი`)

## სწრაფი ნავიგაცია
- [სარედაქციო კონსტიტუცია](.agent/rules/editorial-constitution.md) — უცვლელი ენობრივი, კლინიკური და კაბადონის კანონები
- [გენერალური სარჩევი (`toc-master.md`)](00_reference/toc-master.md) — 75-ვე თავის დეტალური სპეციფიკაცია
- [VascQBank გლოსარიუმი (`glossary-vascqbank.md`)](00_reference/glossary-vascqbank.md) — სრული ტერმინოლოგიური ბაზა და Addendum
- [პროგრესის დაფა (`PROGRESS.md`)](PROGRESS.md) — თავების წერის, აუდიტისა და პროფესორის დასტურის ტრეკერი
- [ილუსტრაციების რეესტრი (`FIGURES.md`)](FIGURES.md) — ქირურგიული სქემების კატალოგი

## სამუშაო პროცესი (Slash-ბრძანებები)
1. `/draft-chapter <N> part <1|2>` (ან `full` 4-გვერდიანი მე-7 და მე-14 თავებისთვის) — თავის აკადემიური გენერაცია
2. `/audit-chapter <N>` — დამოუკიდებელი კლინიკური, რიცხვითი და ტერმინოლოგიური რეცენზია (`audits/ch-NN-audit.md`)
3. `/prof-notes <N>` — პროფესორის პრაქტიკული კორექტივების ჩაშენება და ფინალური `Prof Sign-off`

## ავტომატური ვალიდაცია
```bash
python3 scripts/check_chapter.py --selftest
python3 scripts/check_chapter.py manuscript/01-perioperative/ch-01.md --part 1
python3 scripts/check_chapter.py manuscript/01-perioperative/ch-01.md --part full
```
