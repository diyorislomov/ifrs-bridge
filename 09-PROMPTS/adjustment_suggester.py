"""Prompt template and Claude API call for lightweight adjustment guidance."""

import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def create_adjustment_suggestion_prompt(gap: dict, language: str = "en") -> str:
    """
    Returns Claude prompt that suggests lightweight adjustment guidance.
    NOT full journal entries — just direction and affected accounts.
    """
    lang_instruction = "Respond in Uzbek." if language == "uz" else "Respond in English."

    prompt = f"""
You are an expert Uzbek accountant advising on NAS→MHMS transition adjustments.

## GAP: {gap['title']} (Gap ID: {gap['gap_id']})

### Required Treatment:
{gap['mhms_treatment']}

### Adjustment Guidance:
Suggest ONLY:
1. General approach (one sentence)
2. Which balance sheet / P&L accounts are affected
3. Direction of impact (Assets ↑/↓, Liabilities ↑/↓, Profit ↑/↓)
4. When the impact kicks in (immediate vs. gradual)

DO NOT provide:
- Full journal entries
- Specific debit/credit amounts
- Complex accounting mechanics

Use plain language. Assume a practicing accountant is reading this.

{lang_instruction}
"""
    return prompt


def call_adjustment_suggestion(gap: dict, language: str = "en") -> str:
    """Calls Claude to suggest lightweight adjustment approach."""
    client = Anthropic()
    prompt = create_adjustment_suggestion_prompt(gap, language)

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text
