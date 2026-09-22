"""Validates that Claude-generated gap explanations cite both Lex.uz and IFRS sources."""

import re


def validate_citations(claude_output: str, expected_lex_uz_ref: str, expected_ifrs_ref: str) -> dict:
    """
    Validates that Claude output contains BOTH required citations.

    Returns: {
        "is_valid": bool,
        "has_lex_uz": bool,
        "has_ifrs": bool,
        "missing": list[str],
        "errors": list[str],
        "output": str
    }
    """
    errors: list[str] = []
    missing: list[str] = []

    if not claude_output or not claude_output.strip():
        errors.append("claude_output is empty")

    text = claude_output.lower()

    has_lex_uz_marker = "lex.uz" in text
    has_lex_uz_ref = bool(expected_lex_uz_ref) and expected_lex_uz_ref.lower() in text
    has_lex_uz = has_lex_uz_marker and has_lex_uz_ref

    has_ifrs_marker = bool(re.search(r"\b(ifrs|ias)\b", text))
    has_ifrs_ref = bool(expected_ifrs_ref) and expected_ifrs_ref.lower() in text
    has_ifrs = has_ifrs_marker and has_ifrs_ref

    if not has_lex_uz_marker:
        missing.append("Lex.uz")
    if not has_lex_uz_ref:
        missing.append(expected_lex_uz_ref or "expected_lex_uz_ref")
    if not has_ifrs_marker:
        missing.append("IFRS/IAS")
    if not has_ifrs_ref:
        missing.append(expected_ifrs_ref or "expected_ifrs_ref")

    is_valid = has_lex_uz and has_ifrs and not errors

    return {
        "is_valid": is_valid,
        "has_lex_uz": has_lex_uz,
        "has_ifrs": has_ifrs,
        "missing": missing,
        "errors": errors,
        "output": claude_output,
    }
