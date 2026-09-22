"""Validates that a Claude gap explanation contains both required citations."""

import os
import sys

# citation_validator.py lives under 03-BACKEND/utils, a sibling directory
# whose name ("03-BACKEND") isn't a valid dotted-import identifier, so it
# is added to sys.path directly rather than imported as a package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "03-BACKEND"))

from utils.citation_validator import validate_citations  # noqa: E402


def enforce_citations(claude_response: str, gap: dict) -> dict:
    """
    Validates that Claude's response contains BOTH required citations.
    If missing, re-prompts Claude to add them.

    Args:
        claude_response: Claude's initial explanation
        gap: gap dict with lex_uz_ref and ifrs_ref

    Returns:
        dict: {"is_valid": bool, "response": str, "missing": list}
    """
    result = validate_citations(
        claude_response,
        gap['lex_uz_ref'],
        gap['ifrs_ref']
    )

    if result['is_valid']:
        return {"is_valid": True, "response": claude_response, "missing": []}

    # If citations missing, return what's missing (don't re-prompt in MVP)
    return {
        "is_valid": False,
        "response": claude_response,
        "missing": result['missing']
    }
