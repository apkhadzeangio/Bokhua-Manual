#!/usr/bin/env python3
"""
Bokhua Manual of Vascular Surgery (100x180 mm | 550 გვ. | 75 თავი)
ავტომატური სარედაქციო, ტერმინოლოგიური და კაბადონის ვალიდატორი.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

WORDS_PER_PAGE = 250
FULL_TOLERANCE = 0.15          # ±15% full რეჟიმში
PART1_MIN_RATIO = 0.40         # 40%–58% part 1 რეჟიმში
PART1_MAX_RATIO = 0.58
PART2_ONLY_MIN_RATIO = 0.40    # თუ part 2 ცალკე ფაილადაა (### 1.-ის გარეშე)
PART2_ONLY_MAX_RATIO = 0.62
MAX_TABLE_COLS = 4
MAX_CELL_WORDS_WARN = 16       # >16 სიტყვა უჯრაში -> [WARNING]

PASSPORT_PAGES_RE = re.compile(r"\(\s*(\d+)\s*გვ\.")
FIGURE_HEADER_RE = re.compile(
    r"^\s*>\s*\*\*\[სურ\.\s*([0-9]+\.[0-9]+)\s*\|\s*([0-9]+(?:\.[0-9]+)?)\s*გვ\."
)
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|[\s:\-\|]+\|\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
GUIDELINE_TAG_RE = re.compile(r"\[(ESVS|SVS|ACC/AHA|ESC|GVG|KDIGO|WIfI)[^\]]*\]")
PURE_MARKDOWN_TOKEN_RE = re.compile(r"^[>#*\-–—•✓⚠⚡⛔🔴|\[\]()0-9.:,;!?/]+$")

CLOSING_MARKERS = (
    "ბოხუას კლინიკური მარგალიტები",
    "გადარჩენის კლინიკური წესები",
)

# (compiled_regex, forbidden_label, replacement_hint)
FORBIDDEN_PATTERNS: Sequence[Tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"პატჩ", re.IGNORECASE), "პატჩ*", "ნაფლეთი / ნაფლეთით პლასტიკა"),
    (
        re.compile(r"ფლაპ", re.IGNORECASE),
        "ფლაპ*",
        "ნაფლეთი (მაგ., თერძის კუნთის / დიდი ბადექონის ნაფლეთი)",
    ),
    (re.compile(r"\bშიზ", re.IGNORECASE), "შიზ*", "სისხლძარღვოვანი ინტროდიუსერი"),
    (re.compile(r"კლამპ", re.IGNORECASE), "კლამპ*", "სისხლძარღვოვანი დამჭერი / გადაკეტვა"),
    (re.compile(r"ტურნიკეტ", re.IGNORECASE), "ტურნიკეტ*", "ლახტი (ესმარხის ლახტი)"),
    (re.compile(r"რუპტურ", re.IGNORECASE), "რუპტურ*", "გასკდომა"),
    (
        re.compile(r"ანევრიზმ(?:ული|ის)\s+პარკ", re.IGNORECASE),
        "ანევრიზმული/ანევრიზმის პარკი",
        "ანევრიზმული ტომარა",
    ),
    (re.compile(r"ლენდინგ", re.IGNORECASE), "ლენდინგ*", "ფიქსაციის ზონა"),
    (re.compile(r"სილინგ", re.IGNORECASE), "სილინგ*", "ჰერმეტიზაციის ზონა"),
    (
        re.compile(r"ჰოსტილურ", re.IGNORECASE),
        "ჰოსტილურ*",
        "ენდოვასკულური მკურნალობისთვის არახელსაყრელი ყელი",
    ),
    (re.compile(r"კოჭ-მხრის", re.IGNORECASE), "კოჭ-მხრის", "გოჯ-მხრის ინდექსი (ABI)"),
    (
        re.compile(r"დამასრულებელი\s+ანგიოგრაფ", re.IGNORECASE),
        "დამასრულებელი ანგიოგრაფია",
        "საკონტროლო ანგიოგრაფია",
    ),
    (
        re.compile(r"(?<!უნი)(?<!უნი-)(?<!ნეოაორტო-)\bილიაკურ", re.IGNORECASE),
        "ილიაკურ*",
        "თეძოს (საერთო/გარეთა/შიგნითა) არტერია/ვენა",
    ),
    (
        re.compile(r"პერონეალურ", re.IGNORECASE),
        "პერონეალურ*",
        "მცირე წვივის (არტერია/ნერვი)",
    ),
    (
        re.compile(r"დაღმავალი\s+აორტ", re.IGNORECASE),
        "დაღმავალი აორტა",
        "გულმკერდის დასწვრივი აორტა",
    ),
    (
        re.compile(
            r"(?:თრომბო|რაბდომიო|ჰემოდია)ლიზის(?:ი|ის|მა|ით|ს|ად|ზე|ში)\b",
            re.IGNORECASE,
        ),
        "-ლიზისი (ჭარბი სუფიქსი)",
        "უსუფიქსო ფორმა: თრომბოლიზი / რაბდომიოლიზი / ჰემოდიალიზი",
    ),
    (
        re.compile(r"სტენტ[-\s]+გრაფტ", re.IGNORECASE),
        "სტენტ-გრაფტი",
        "სტენტგრაფტი (ერთსიტყვიანად)",
    ),
    (
        re.compile(r"დუპლექს[-\s]+სკანირებ", re.IGNORECASE),
        "დუპლექს-სკანირება",
        "დუპლექსსკანირება (ერთსიტყვიანად)",
    ),
    (
        re.compile(r"რისკ[-\s]+ფაქტორ", re.IGNORECASE),
        "რისკ-ფაქტორი",
        "რისკფაქტორი (ერთსიტყვიანად)",
    ),
    (
        re.compile(r"მინი[-\s]+ფლებექტომ", re.IGNORECASE),
        "მინი-ფლებექტომია",
        "მინიფლებექტომია (ერთსიტყვიანად)",
    ),
    (
        re.compile(r"სიმპათექტომ", re.IGNORECASE),
        "სიმპათექტომია",
        "სიმპატექტომია ('ტ'-თი)",
    ),
    (re.compile(r"IVC[-\s]+ფილტრ", re.IGNORECASE), "IVC ფილტრი", "კავა-ფილტრი"),
    (
        re.compile(r"\b(?:მაა|კმი)\b"),
        "მაა / კმი",
        "გამოიყენე ლათინური აბრევიატურა (AAA, ALI)",
    ),
]


@dataclass
class ValidationReport:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)
    word_count: int = 0
    pages: Optional[int] = None
    guideline_count: int = 0
    figure_count: int = 0
    figure_pages: float = 0.0

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def count_words_and_figures(lines: Sequence[str]) -> Tuple[int, int, float]:
    """
    ითვლის ძირითადი ტექსტის სიტყვებს (ფენსირებული კოდის, ცხრილის გამყოფი ხაზებისა და
    Additive ილუსტრაციის ბლოკების '> **[სურ. ...]**' გამოკლებით) და ცალკე აღრიცხავს სურათებს.
    """
    total = 0
    fig_count = 0
    fig_pages = 0.0
    in_fence = False
    in_figure_block = False

    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            in_figure_block = False
            continue
        if in_fence:
            continue

        stripped = line.strip()
        fig_match = FIGURE_HEADER_RE.match(stripped)
        if fig_match:
            in_figure_block = True
            fig_count += 1
            fig_pages += float(fig_match.group(2))
            continue

        if in_figure_block:
            if stripped.startswith(">"):
                continue
            in_figure_block = False

        if not stripped or stripped.startswith("<!--"):
            continue
        if TABLE_SEPARATOR_RE.match(stripped):
            continue
        cleaned = stripped.replace("|", " ")
        for tok in cleaned.split():
            if PURE_MARKDOWN_TOKEN_RE.match(tok):
                continue
            total += 1
    return total, fig_count, fig_pages


def split_markdown_table_cells(line: str) -> List[str]:
    """ყოფს Markdown-ცხრილის სტრიქონს უჯრებად (გაქცეული \\|-ის გათვალისწინებით)."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith(r"\|"):
        s = s[:-1]
    cells = re.split(r"(?<!\\)\|", s)
    return [c.strip() for c in cells]


def extract_pages(text: str, explicit_pages: Optional[int]) -> Optional[int]:
    if explicit_pages is not None:
        return explicit_pages
    for line in text.splitlines()[:25]:
        m = PASSPORT_PAGES_RE.search(line)
        if m:
            return int(m.group(1))
    return None


def validate_chapter_text(
    text: str,
    part: str = "full",
    explicit_pages: Optional[int] = None,
) -> ValidationReport:
    report = ValidationReport()
    lines = text.splitlines()

    # 1. პასპორტისა და გვერდების კვოტის შემოწმება
    pages = extract_pages(text, explicit_pages)
    report.pages = pages
    words, fig_count, fig_pages = count_words_and_figures(lines)
    report.word_count = words
    report.figure_count = fig_count
    report.figure_pages = fig_pages

    if fig_count > 0:
        report.info.append(
            f"[INFO] Additive ილუსტრაციები: {fig_count} სქემა (+{fig_pages:.2f} გვ. "
            "ტექსტური კვოტის ზემოდან)."
        )

    if pages is None or pages <= 0:
        report.errors.append(
            "[ERROR] პასპორტის ბლოკში ვერ მოიძებნა გვერდების კვოტა "
            "(მაგ., '(6 გვ. / ~1,500 სიტყვა)') და არც --pages არის მითითებული."
        )
    else:
        full_budget = pages * WORDS_PER_PAGE
        has_sec1 = any(re.match(r"^\s*###\s*1\.", ln) for ln in lines)
        has_sec4 = any(re.match(r"^\s*###\s*4\.", ln) for ln in lines)

        if part == "1":
            min_w = int(round(full_budget * PART1_MIN_RATIO))
            max_w = int(round(full_budget * PART1_MAX_RATIO))
            report.info.append(
                f"[INFO] გვერდების კვოტა: {pages} გვ. (სრული ბიუჯეტი ~{full_budget} სიტყვა) | "
                f"Part 1/2 სამიზნე: {min_w}–{max_w} სიტყვა | ფაქტობრივი: {words} სიტყვა."
            )
            if words < min_w or words > max_w:
                # მცირე გადაცდომა (±5%) -> WARNING, უფრო დიდი -> ERROR
                soft_min = int(round(full_budget * (PART1_MIN_RATIO - 0.05)))
                soft_max = int(round(full_budget * (PART1_MAX_RATIO + 0.05)))
                msg = (
                    f"Part 1/2 სიტყვების რაოდენობა ({words}) სცდება სრული ბიუჯეტის "
                    f"40%–58% დიაპაზონს ({min_w}–{max_w} სიტყვა)."
                )
                if words < soft_min or words > soft_max:
                    report.errors.append(f"[ERROR] {msg}")
                else:
                    report.warnings.append(f"[WARNING] {msg}")
            if has_sec4:
                report.errors.append(
                    "[ERROR] Part 1/2 რეჟიმში აღმოჩნდა '### 4.' ქვეთავი — "
                    "Part 1/2 მკაცრად უნდა გაჩერდეს §3-ის ბოლოს!"
                )
        elif part == "2" and not has_sec1:
            min_w = int(round(full_budget * PART2_ONLY_MIN_RATIO))
            max_w = int(round(full_budget * PART2_ONLY_MAX_RATIO))
            report.info.append(
                f"[INFO] გვერდების კვოტა: {pages} გვ. | ცალკე Part 2/2 სამიზნე: "
                f"{min_w}–{max_w} სიტყვა | ფაქტობრივი: {words} სიტყვა."
            )
            if words < min_w or words > max_w:
                report.warnings.append(
                    f"[WARNING] ცალკე Part 2/2 სიტყვების რაოდენობა ({words}) სცდება "
                    f"სამიზნე დიაპაზონს ({min_w}–{max_w} სიტყვა)."
                )
        else:
            min_w = int(round(full_budget * (1.0 - FULL_TOLERANCE)))
            max_w = int(round(full_budget * (1.0 + FULL_TOLERANCE)))
            ideal_min = int(round(full_budget * 0.88))
            ideal_max = int(round(full_budget * 1.12))
            report.info.append(
                f"[INFO] გვერდების კვოტა: {pages} გვ. (~{full_budget} სიტყვა, ±15%: "
                f"{min_w}–{max_w}) | ფაქტობრივი: {words} სიტყვა."
            )
            if words < min_w or words > max_w:
                report.errors.append(
                    f"[ERROR] სიტყვების რაოდენობა ({words}) სცდება ±15% ტოლერანტობას "
                    f"({min_w}–{max_w} სიტყვა {pages} გვერდისთვის)."
                )
            elif words < ideal_min or words > ideal_max:
                report.warnings.append(
                    f"[WARNING] სიტყვების რაოდენობა ({words}) სცდება იდეალურ ±12% ზღვარს "
                    f"({ideal_min}–{ideal_max}), თუმცა ჯდება ±15% ლიმიტში."
                )

    # 2 & 3. ცხრილების (100x180 მმ) და აკრძალული ჟარგონის ხაზობრივი სკანირება
    in_fence = False
    for idx, line in enumerate(lines, start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        stripped = line.strip()
        if stripped.startswith("<!--"):
            continue

        # Markdown ცხრილის შემოწმება
        is_table_row = (
            stripped.startswith("|")
            and stripped.endswith("|")
            and stripped.count("|") >= 2
        )
        if is_table_row:
            cells = split_markdown_table_cells(stripped)
            col_count = len(cells)
            if col_count > MAX_TABLE_COLS:
                report.errors.append(
                    f"[ERROR] ხაზი {idx}: ცხრილს აქვს {col_count} სვეტი "
                    f"(მაქსიმუმ დასაშვებია {MAX_TABLE_COLS} სვეტი 100 მმ სიგანისთვის)."
                )
            if not TABLE_SEPARATOR_RE.match(stripped):
                for cell in cells:
                    cell_words = len(cell.split())
                    if cell_words > MAX_CELL_WORDS_WARN:
                        report.warnings.append(
                            f"[WARNING] ხაზი {idx}: გადატვირთული უჯრა "
                            f"({cell_words} სიტყვა, სასურველია <=15)."
                        )

        # აკრძალული ჟარგონისა და კალკების სკანირება
        for pattern, label, replacement in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(line):
                found = match.group(0)
                report.errors.append(
                    f"[ERROR] ხაზი {idx}: აკრძალული ტერმინი '{found}' ({label}) -> "
                    f"ჩაანაცვლე: {replacement}."
                )

    # 4. მტკიცებულებითი კოდებისა და დასკვნითი ბლოკის შემოწმება
    non_fenced_lines: List[str] = []
    in_fence = False
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            non_fenced_lines.append(line)
    clean_body = "\n".join(non_fenced_lines)

    guideline_matches = GUIDELINE_TAG_RE.findall(clean_body)
    report.guideline_count = len(guideline_matches)
    if report.guideline_count == 0:
        report.errors.append(
            "[ERROR] ტექსტში არ იძებნება გაიდლაინის მტკიცებულებითი კოდები "
            "(მაგ., [ESVS 2024: I-A], [SVS 2023: 1-B])."
        )
    else:
        report.info.append(
            f"[INFO] ნაპოვნია გაიდლაინის {report.guideline_count} მტკიცებულებითი კოდი."
        )

    if part in ("full", "2"):
        has_closing = any(marker in clean_body for marker in CLOSING_MARKERS)
        if not has_closing:
            report.errors.append(
                "[ERROR] ტექსტში არ იძებნება დასკვნითი საფირმო ბლოკი "
                "('ბოხუას კლინიკური მარგალიტები' ან 'გადარჩენის კლინიკური წესები')."
            )

    return report


def run_selftest() -> int:
    print("მიმდინარეობს check_chapter.py თვითტესტირება (--selftest)...")

    filler_sentence = (
        "ბარძაყის საერთო არტერიის ოპერაციული მიდგომა სრულდება გრძივი განაკვეთით "
        "სისხლძარღვის გამოყოფითა და მობილიზაციით ნერვული ღეროების სრული დაცვით. "
    )  # 15 სიტყვა

    valid_sample = (
        "> **კარი VI | თავი 41 | გვ. 270–271 (1 გვ. / ~250 სიტყვა)**\n"
        "> ## მუცლის აორტის ანევრიზმის ენდოვასკულური მკურნალობა\n"
        "> *Endovascular Aneurysm Repair (EVAR)*\n"
        "> **საყრდენი გაიდლაინები:** ESVS 2024 | **კლინიკური კვინტესენცია:** "
        "ჰერმეტიზაციის ზონის ზუსტი გაზომვა განსაზღვრავს სტენტგრაფტის გამძლეობას.\n\n"
        "### 1. დეფინიცია და კლასიფიკაცია\n"
        "კათეტერული თრომბოლიზის შემდეგ ან აორტო-უნიილიაკური სტენტგრაფტის იმპლანტაციისას "
        "ფასდება თეძოს საერთო არტერია, ნეოაორტოილიაკური რეკონსტრუქცია და ილიოკავალური სეგმენტი "
        "[ESVS 2024: I-A]. დუპლექსსკანირება, გოჯ-მხრის ინდექსი (ABI), ხარის პერიკარდიუმის "
        "ნაფლეთით პლასტიკა, წელის სიმპატექტომია, კავა-ფილტრი და საკონტროლო ანგიოგრაფია "
        "ამცირებს რისკფაქტორებს [SVS 2023: 1-B].\n\n"
        "| პარამეტრი | ღია ქირურგია | ენდოვასკულური |\n"
        "| :--- | :--- | :--- |\n"
        "| ფიქსაციის ზონა | მოკლე ყელი | >=15 მმ ყელი |\n"
        "| ჰეპარინიზაცია | ACT 200–250 წმ | ACT >=250–300 წმ |\n\n"
        "> **[სურ. 41.1 | 0.5 გვ. | assets/figures/06-thoracic-abdominal-aorta-iliac/fig-41-01.svg]**\n"
        "> **სათაური:** პროქსიმალური ჰერმეტიზაციის ზონის გეომეტრია.\n"
        "> **ლეგენდა:** (1) თირკმლის არტერიები; (2) აორტის ყელი; (3) ანევრიზმული ტომარა.\n\n"
        + (filler_sentence * 8)
        + "\n\n> **ბოხუას კლინიკური მარგალიტები (Pearls & Pitfalls)**\n"
        "> - ✓ **Pearl:** სისხლძარღვოვანი ინტროდიუსერი შეიყვანეთ ექოსკოპიური კონტროლით.\n"
        "> - ⚠ **Pitfall:** არ გადაკეტოთ კალციფიცირებული სეგმენტი უხეში სისხლძარღვოვანი დამჭერით.\n"
    )

    rep_valid = validate_chapter_text(valid_sample, part="full")
    if not rep_valid.ok or rep_valid.warnings or rep_valid.figure_count != 1:
        print("SELFTEST FAILED სწორ ნიმუშზე:")
        for msg in rep_valid.errors + rep_valid.warnings:
            print("  ", msg)
        return 1

    # შევამოწმოთ დარღვევებიანი ნიმუში
    invalid_sample = (
        "> **კარი VI | თავი 41 | გვ. 270–275 (6 გვ. / ~1,500 სიტყვა)**\n"
        "პაციენტს ჩაუტარდა პატჩი და თრომბოლიზისი ილიაკური არტერიის ოკლუზიის გამო.\n"
        "დაყენდა სტენტ-გრაფტი, IVC ფილტრი, გაიზომა კოჭ-მხრის ინდექსი მაა-ს დროს.\n\n"
        "| სვ1 | სვ2 | სვ3 | სვ4 | სვ5 |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 1 | 2 | 3 | 4 | 5 |\n"
    )
    rep_invalid = validate_chapter_text(invalid_sample, part="full")
    joined_errors = "\n".join(rep_invalid.errors)

    expected_Substring_Checks = [
        "5 სვეტი",
        "პატჩ",
        "ილიაკურ",
        "-ლიზისი",
        "სტენტ-გრაფტი",
        "IVC ფილტრი",
        "კოჭ-მხრის",
        "მაა / კმი",
        "გაიდლაინის მტკიცებულებითი კოდები",
        "დასკვნითი საფირმო ბლოკი",
    ]
    missing_detections = [s for s in expected_Substring_Checks if s not in joined_errors]
    if missing_detections:
        print(f"SELFTEST FAILED — ვერ დაიჭირა დარღვევები: {missing_detections}")
        print("ნაპოვნი შეცდომები:\n", joined_errors)
        return 1

    print(
        f"  ✓ სწორი ნიმუში (ნათესაობითი 'თრომბოლიზის შემდეგ', 'აორტო-უნიილიაკური', "
        f"3-სვეტიანი ცხრილი, {rep_valid.word_count} სიტყვა): 0 შეცდომა, 0 გაფრთხილება."
    )
    print(
        f"  ✓ დარღვევებიანი ნიმუში (5-სვეტიანი ცხრილი, 'პატჩი', 'ილიაკური არტერია', "
        f"'თრომბოლიზისი' და სხვ.): წარმატებით დაიბლოკა ({len(rep_invalid.errors)} ERROR)."
    )
    print("SELFTEST PASSED")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bokhua Manual of Vascular Surgery — თავის ავტომატური ვალიდატორი."
    )
    parser.add_argument(
        "filepath",
        nargs="?",
        help="შესამოწმებელი Markdown ფაილის მისამართი (მაგ., manuscript/01-perioperative/ch-01.md)",
    )
    parser.add_argument(
        "--part",
        choices=("1", "2", "full"),
        default="full",
        help="ვალიდაციის რეჟიმი: '1' (Part 1/2), '2' (Part 2/2) ან 'full' (default: full)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="გვერდების კვოტის ხელით მითითება (თუ პასპორტიდან არ იკითხება)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="ჩაშენებული თვითტესტის გაშვება მეხსიერებაში",
    )

    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()

    if not args.filepath:
        parser.error("მიუთითეთ ფაილის მისამართი (filepath) ან გაუშვით --selftest.")

    path = pathlib.Path(args.filepath)
    if not path.is_file():
        print(f"[ERROR] ფაილი ვერ მოიძებნა: {path}", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")
    report = validate_chapter_text(text, part=args.part, explicit_pages=args.pages)

    print(f"=== Bokhua Manual Validator: {path} (mode: {args.part}) ===")
    for msg in report.info:
        print(msg)
    for msg in report.warnings:
        print(msg)
    for msg in report.errors:
        print(msg)

    if report.ok:
        print(
            f"✅ VALIDATION PASSED: 0 შეცდომა, {len(report.warnings)} გაფრთხილება."
        )
        return 0
    else:
        print(
            f"❌ VALIDATION FAILED: {len(report.errors)} შეცდომა, "
            f"{len(report.warnings)} გაფრთხილება."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
