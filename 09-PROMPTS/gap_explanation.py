"""Prompt template for explaining a detected NAS/MHMS -> IFRS gap in plain language."""


def _field(gap: dict, *keys: str) -> str:
    """Return the first present, non-empty value among the given keys.

    gaps.json stores references/treatments at the standard level using
    "lex_uz_reference"/"ifrs_reference", while callers may pass a merged
    dict using the shorter "lex_uz_ref"/"ifrs_ref" names. Checking both
    keeps this template usable either way.
    """
    for key in keys:
        value = gap.get(key)
        if value:
            return value
    return "N/A"


_EN_TEMPLATE = """You are an IFRS conversion specialist helping a mid-level accountant (ACCA-level, not a CFO) understand a specific accounting gap identified between Uzbekistan's National Accounting Standards (NAS/MHMS) and IFRS.

GAP DETECTED: {title}
MHMS STANDARD: MHMS #{mhms_id}
RISK LEVEL: {risk}

CURRENT NAS/MHMS TREATMENT:
{nas_treatment}

REQUIRED IFRS TREATMENT:
{mhms_treatment}

RELEVANT EXTRACT FROM THE FINANCIAL STATEMENT:
\"\"\"
{statement_extract}
\"\"\"

Write a plain-language explanation for the accountant that covers:
1. WHAT the gap is - describe it in simple terms. Avoid jargon like "liabilities recognition"; say things like "you owe someone money".
2. WHY it is a gap - explain the difference between the NAS/MHMS treatment and the IFRS treatment.
3. THE IMPACT - describe how this affects the balance sheet, income statement, and/or cash flow statement.
4. Cite both references exactly:
   - Per Lex.uz {lex_uz_ref}, ...
   - IFRS {ifrs_ref} states ...

Keep your response concise: 300-400 words maximum. Write for an ACCA-level accountant, not a CFO - clear and practical, not academic.

Respond in English.

Your response MUST cite both the Lex.uz and IFRS references exactly. Do not paraphrase the citations."""


_UZ_TEMPLATE = """Siz O'zbekiston Milliy hisob standartlari (NAS/MHMS) va IFRS o'rtasida aniqlangan farqni (gap) o'rta darajadagi buxgalterga (ACCA darajasida, moliya direktori emas) tushuntirayotgan IFRS konversiya bo'yicha mutaxassissiz.

ANIQLANGAN FARQ: {title}
MHMS STANDARTI: MHMS #{mhms_id}
XAVF DARAJASI: {risk}

JORIY NAS/MHMS YONDASHUVI:
{nas_treatment}

TALAB QILINADIGAN IFRS YONDASHUVI:
{mhms_treatment}

MOLIYAVIY HISOBOTDAN TEGISHLI QISM:
\"\"\"
{statement_extract}
\"\"\"

Buxgalter uchun sodda tilda tushuntirish yozing, quyidagilarni qamrab oling:
1. FARQ NIMA - buni sodda so'zlar bilan tasvirlab bering. "Majburiyatlarni tan olish" kabi murakkab atamalardan qoching; "kimgadir pul qarzdorsiz" kabi sodda gaplardan foydalaning.
2. NEGA BU FARQ HISOBLANADI - NAS/MHMS yondashuvi bilan IFRS yondashuvi o'rtasidagi farqni tushuntiring.
3. TA'SIRI - bu balans, foyda-zarar hisoboti va/yoki pul mablag'lari harakati hisobotiga qanday ta'sir qilishini tasvirlab bering.
4. Ikkala manbani ham aniq keltiring:
   - Lex.uz {lex_uz_ref} ga ko'ra, ...
   - IFRS {ifrs_ref} da ko'rsatilishicha ...

Javobingiz qisqa bo'lsin: maksimum 300-400 so'z. ACCA darajasidagi buxgalter uchun yozing, moliya direktori uchun emas - aniq va amaliy bo'lsin, akademik emas.

O'zbek tilida javob bering.

Javobingizda albatta Lex.uz va IFRS manbalarini aniq keltirishingiz SHART. Iqtiboslarni boshqacha so'zlar bilan ifodalamang."""


def create_gap_explanation_prompt(gap: dict, statement_extract: str, language: str = "en") -> str:
    """
    Returns a Claude prompt that explains a detected gap in plain language.

    Args:
        gap: single gap from gaps.json (has gap_id, title, nas_treatment,
            mhms_treatment, lex_uz_ref, ifrs_ref, adjustment_hint, etc.)
        statement_extract: relevant text/lines from the financial statement
            showing the gap
        language: "en" (English) or "uz" (Uzbek)

    Returns:
        str: Claude prompt string
    """
    template = _UZ_TEMPLATE if language == "uz" else _EN_TEMPLATE

    return template.format(
        title=_field(gap, "title"),
        mhms_id=_field(gap, "mhms_id"),
        risk=_field(gap, "risk"),
        nas_treatment=_field(gap, "nas_treatment"),
        mhms_treatment=_field(gap, "mhms_treatment"),
        lex_uz_ref=_field(gap, "lex_uz_ref", "lex_uz_reference"),
        ifrs_ref=_field(gap, "ifrs_ref", "ifrs_reference"),
        statement_extract=statement_extract,
    )
