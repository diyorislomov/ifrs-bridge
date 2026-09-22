"""Prompt template and Claude API call for explaining a detected NAS/MHMS gap."""

import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def create_gap_explanation_prompt(gap: dict, statement_extract: str, language: str = "en") -> str:
    """
    Returns Claude prompt that explains a detected gap in plain language.

    Args:
        gap: gap dict from gaps.json (has gap_id, title, mhms_treatment, lex_uz_ref, ifrs_ref, etc.)
        statement_extract: relevant text from financial statement showing the gap
        language: "en" (English) or "uz" (Uzbek)

    Returns:
        str: Claude prompt string
    """
    lang_instruction = "Respond in Uzbek." if language == "uz" else "Respond in English."

    prompt = f"""
You are an expert Uzbek accountant explaining NAS→MHMS gaps to professionals.

## GAP DETECTED: {gap['title']} (Gap ID: {gap['gap_id']})

### Current Treatment (NAS):
[This is what the company currently does under old standards]

### Required Treatment (MHMS/IFRS):
{gap['mhms_treatment']}

### Statement Extract (the evidence):
{statement_extract}

### Your Task:
1. Explain WHY this is a gap (what changed, why it matters)
2. Explain WHAT the impact is (which financial statement line items change)
3. Cite BOTH:
   - {gap['lex_uz_ref']} (the exact Uzbek standard)
   - {gap['ifrs_ref']} (the IFRS equivalent)

Use plain language — no jargon. Assume the reader is an accountant, not an auditor.

{lang_instruction}

CRITICAL: Your response MUST include BOTH citations exactly as written above. Do not paraphrase or merge them.
"""
    return prompt


def call_gap_explanation(gap: dict, statement_extract: str, language: str = "en") -> str:
    """
    Calls Claude API to explain a gap.

    Returns:
        str: Claude's explanation with mandatory citations
    """
    client = Anthropic()
    prompt = create_gap_explanation_prompt(gap, statement_extract, language)

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text
