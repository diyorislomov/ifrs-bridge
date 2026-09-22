"""Bridges the Claude prompt/API modules in 09-PROMPTS/ for backend and frontend consumers."""

import os
import sys

# gap_explanation.py and adjustment_suggester.py live in 09-PROMPTS/, a sibling
# directory whose name isn't a valid dotted-import identifier (starts with a
# digit), so it is added to sys.path directly rather than imported as a package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '09-PROMPTS'))

from gap_explanation import call_gap_explanation, create_gap_explanation_prompt  # noqa: E402
from adjustment_suggester import call_adjustment_suggestion, create_adjustment_suggestion_prompt  # noqa: E402

__all__ = [
    "call_gap_explanation",
    "create_gap_explanation_prompt",
    "call_adjustment_suggestion",
    "create_adjustment_suggestion_prompt",
]
