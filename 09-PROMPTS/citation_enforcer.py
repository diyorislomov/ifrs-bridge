"""Meta-prompt that re-prompts Claude to add missing Lex.uz/IFRS citations."""

import os
import sys

# citation_validator.py lives under 03-BACKEND/utils, a sibling directory
# whose name ("03-BACKEND") isn't a valid dotted-import identifier, so it
# is added to sys.path directly rather than imported as a package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "03-BACKEND"))

from utils.citation_validator import validate_citations  # noqa: E402


def _field(gap: dict, *keys: str) -> str:
    """Return the first present, non-empty value among the given keys."""
    for key in keys:
        value = gap.get(key)
        if value:
            return value
    return "N/A"


def create_citation_enforcer_prompt(gap_explanation_response: str, gap: dict) -> str:
    """
    Meta-prompt: validates and re-prompts Claude if citations are missing.

    Args:
        gap_explanation_response: Claude's prior response (may lack citations)
        gap: gap dict with lex_uz_ref and ifrs_ref

    Returns:
        str: Claude prompt to enforce citations, or "" if citations already
            satisfy citation_validator.py's rules.
    """
    lex_uz_ref = _field(gap, "lex_uz_ref", "lex_uz_reference")
    ifrs_ref = _field(gap, "ifrs_ref", "ifrs_reference")

    result = validate_citations(gap_explanation_response, lex_uz_ref, ifrs_ref)

    if result["is_valid"]:
        return ""

    missing_list = ", ".join(result["missing"]) if result["missing"] else "citations"

    return f"""Your explanation above is good, but it is missing required citations. Before finalizing, revise it to explicitly cite BOTH of the following sources, worded exactly as shown:

- Lex.uz reference: "{lex_uz_ref}"
- IFRS reference: "{ifrs_ref}"

Missing from your response: {missing_list}

Rewrite your explanation, keeping all of the original content and structure, but add the exact citations verbatim (for example: "Per Lex.uz {lex_uz_ref}, ..." and "IFRS {ifrs_ref} states ..."). Do not paraphrase, abbreviate, or omit either citation."""
