"""Shared loader that builds the flat, self-contained gap list used across the app."""

import json
import os

_UTILS_DIR = os.path.dirname(__file__)
_REPO_ROOT = os.path.join(_UTILS_DIR, '..', '..')


def load_all_gaps() -> list:
    """
    Loads the full 58-gap skeleton from gaps.json, copies each standard's
    shared fields (nas_treatment, mhms_treatment, lex_uz_reference,
    ifrs_reference) down onto its individual gaps so every gap is a flat,
    self-contained dict, then overlays the 8 fully-researched HIGH-risk
    gaps from gaps_findings.json on top of the matching stub entries.

    Without the overlay, gap detection and citations would silently be
    useless: gaps.json's per-gap detection_keywords are still the literal
    placeholder "TODO: keywords" (so nothing ever matches), and it has no
    mhms_treatment/lex_uz_ref/ifrs_ref at the individual-gap level at all
    (those only exist at the standard level, under different field names).
    The ~50 gaps without a gaps_findings.json entry keep their inert TODO
    keywords, so they stay present in the list but never actually trigger.
    """
    gaps_json_path = os.path.join(_REPO_ROOT, '02-KNOWLEDGE-BASE', 'gaps.json')
    with open(gaps_json_path, 'r', encoding='utf-8') as f:
        gaps_db = json.load(f)

    all_gaps = []
    for tier in ['tier1', 'tier2']:
        for standard in gaps_db['tiers'].get(tier, []):
            for gap in standard.get('key_gaps', []):
                merged = {
                    'mhms_id': standard.get('mhms_id'),
                    'nas_treatment': standard.get('nas_treatment'),
                    'mhms_treatment': standard.get('mhms_treatment'),
                    'lex_uz_ref': standard.get('lex_uz_reference'),
                    'ifrs_ref': standard.get('ifrs_reference'),
                    **gap,
                }
                all_gaps.append(merged)

    findings_path = os.path.join(_REPO_ROOT, 'gaps_findings.json')
    if os.path.exists(findings_path):
        with open(findings_path, 'r', encoding='utf-8') as f:
            findings_by_id = {g['gap_id']: g for g in json.load(f)}

        for gap in all_gaps:
            override = findings_by_id.get(gap.get('gap_id'))
            if override:
                gap.update(override)

    return all_gaps
