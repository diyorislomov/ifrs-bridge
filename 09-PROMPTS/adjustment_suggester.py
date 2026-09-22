"""Prompt template for lightweight (non-journal-entry) adjustment guidance."""


def _field(gap: dict, *keys: str) -> str:
    """Return the first present, non-empty value among the given keys.

    See gap_explanation.py for why both naming conventions are checked.
    """
    for key in keys:
        value = gap.get(key)
        if value:
            return value
    return "N/A"


_EN_TEMPLATE = """You are an IFRS conversion specialist providing LIGHTWEIGHT adjustment guidance to an ACCA-level accountant. Do NOT provide full journal entries or detailed workings - only the general approach.

GAP: {title}
MHMS STANDARD: MHMS #{mhms_id}

CURRENT NAS/MHMS TREATMENT:
{nas_treatment}

REQUIRED IFRS TREATMENT:
{mhms_treatment}

ADJUSTMENT HINT:
{adjustment_hint}

RELEVANT EXTRACT FROM THE FINANCIAL STATEMENT:
\"\"\"
{statement_extract}
\"\"\"

Write lightweight adjustment guidance that covers:
1. The GENERAL approach to fix the gap - describe the concept, not the mechanics. For example: "You'll need to recognize a Right-of-Use asset on the balance sheet" - NOT "Dr. ROU Asset 4,200M Cr. Lease Liability 4,200M".
2. The ACCOUNTS likely affected - name the balance sheet and/or P&L line items involved.
3. The DIRECTION of impact - state clearly whether each affected item increases or decreases (e.g., assets up, liabilities up, profit down).
4. Cite both references exactly:
   - Per Lex.uz {lex_uz_ref}, ...
   - IFRS {ifrs_ref} states ...
5. End your response with exactly this line: "For detailed journal entries and full impact analysis, see IFRS Bridge Pro (v1.5+)."

Do not provide specific monetary amounts, debit/credit entries, or full workings.

Respond in English.

Your response MUST cite both the Lex.uz and IFRS references exactly. Do not paraphrase the citations."""


_UZ_TEMPLATE = """Siz ACCA darajasidagi buxgalterga YENGIL (to'liq bo'lmagan) tuzatish bo'yicha yo'l-yo'riq beruvchi IFRS konversiya bo'yicha mutaxassissiz. To'liq buxgalteriya provodkalari yoki batafsil hisob-kitoblarni BERMANG - faqat umumiy yondashuvni tushuntiring.

FARQ: {title}
MHMS STANDARTI: MHMS #{mhms_id}

JORIY NAS/MHMS YONDASHUVI:
{nas_treatment}

TALAB QILINADIGAN IFRS YONDASHUVI:
{mhms_treatment}

TUZATISH BO'YICHA MASLAHAT:
{adjustment_hint}

MOLIYAVIY HISOBOTDAN TEGISHLI QISM:
\"\"\"
{statement_extract}
\"\"\"

Quyidagilarni qamrab olgan yengil tuzatish bo'yicha yo'l-yo'riq yozing:
1. Farqni bartaraf etishning UMUMIY yondashuvi - tushunchani tasvirlab bering, mexanizmni emas. Masalan: "Balansda Foydalanish huquqi aktivini tan olishingiz kerak bo'ladi" - "Dt Foydalanish huquqi aktivi 4,200 mln Kt Ijara majburiyati 4,200 mln" EMAS.
2. Ta'sir qiladigan HISOBLAR - balans va/yoki foyda-zarar hisobotidagi tegishli moddalarni nomlang.
3. Ta'sir YO'NALISHI - har bir moddaning oshishi yoki kamayishini aniq ko'rsating (masalan, aktivlar oshadi, majburiyatlar oshadi, foyda kamayadi).
4. Ikkala manbani ham aniq keltiring:
   - Lex.uz {lex_uz_ref} ga ko'ra, ...
   - IFRS {ifrs_ref} da ko'rsatilishicha ...
5. Javobingizni aynan quyidagi jumla bilan yakunlang: "Batafsil provodkalar va to'liq ta'sir tahlili uchun IFRS Bridge Pro (v1.5+) dan foydalaning."

Aniq pul miqdorlari, debet/kredit yozuvlari yoki to'liq hisob-kitoblarni bermang.

O'zbek tilida javob bering.

Javobingizda albatta Lex.uz va IFRS manbalarini aniq keltirishingiz SHART. Iqtiboslarni boshqacha so'zlar bilan ifodalamang."""


def create_adjustment_suggestion_prompt(gap: dict, statement_extract: str, language: str = "en") -> str:
    """
    Returns a Claude prompt that suggests lightweight adjustment guidance
    (NOT full workings).

    Args:
        gap: gap from gaps.json (has adjustment_hint, nas_treatment,
            mhms_treatment)
        statement_extract: relevant financial statement text
        language: "en" or "uz"

    Returns:
        str: Claude prompt string
    """
    template = _UZ_TEMPLATE if language == "uz" else _EN_TEMPLATE

    return template.format(
        title=_field(gap, "title"),
        mhms_id=_field(gap, "mhms_id"),
        nas_treatment=_field(gap, "nas_treatment"),
        mhms_treatment=_field(gap, "mhms_treatment"),
        adjustment_hint=_field(gap, "adjustment_hint"),
        lex_uz_ref=_field(gap, "lex_uz_ref", "lex_uz_reference"),
        ifrs_ref=_field(gap, "ifrs_ref", "ifrs_reference"),
        statement_extract=statement_extract,
    )
