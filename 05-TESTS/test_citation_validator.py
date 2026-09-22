"""Unit tests for citation_validator."""

import os
import sys
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "03-BACKEND")
)

from utils.citation_validator import validate_citations  # noqa: E402


class TestValidateCitations(unittest.TestCase):
    def setUp(self):
        self.lex_uz_ref = "MHMS #22"
        self.ifrs_ref = "IAS 16"

    def test_both_citations_present(self):
        output = (
            "Per Lex.uz MHMS #22, PP&E is recorded at historical cost. "
            "Under IFRS IAS 16, componentization is required."
        )
        result = validate_citations(output, self.lex_uz_ref, self.ifrs_ref)
        self.assertTrue(result["is_valid"])
        self.assertTrue(result["has_lex_uz"])
        self.assertTrue(result["has_ifrs"])
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["errors"], [])

    def test_case_insensitive_match(self):
        output = "See lex.UZ mhms #22 versus ifrs ias 16 requirements."
        result = validate_citations(output, self.lex_uz_ref, self.ifrs_ref)
        self.assertTrue(result["is_valid"])

    def test_missing_lex_uz_marker(self):
        output = "Under IFRS IAS 16, componentization is required per MHMS #22."
        result = validate_citations(output, self.lex_uz_ref, self.ifrs_ref)
        self.assertFalse(result["is_valid"])
        self.assertFalse(result["has_lex_uz"])
        self.assertTrue(result["has_ifrs"])
        self.assertIn("Lex.uz", result["missing"])

    def test_missing_ifrs_marker(self):
        output = "Per Lex.uz MHMS #22, PP&E is recorded at historical cost."
        result = validate_citations(output, self.lex_uz_ref, self.ifrs_ref)
        self.assertFalse(result["is_valid"])
        self.assertTrue(result["has_lex_uz"])
        self.assertFalse(result["has_ifrs"])
        self.assertIn("IFRS/IAS", result["missing"])

    def test_missing_specific_lex_uz_ref(self):
        output = "Per Lex.uz general guidance and IFRS IAS 16 requirements."
        result = validate_citations(output, self.lex_uz_ref, self.ifrs_ref)
        self.assertFalse(result["is_valid"])
        self.assertFalse(result["has_lex_uz"])
        self.assertIn(self.lex_uz_ref, result["missing"])

    def test_missing_specific_ifrs_ref(self):
        output = "Per Lex.uz MHMS #22 and general IFRS standards."
        result = validate_citations(output, self.lex_uz_ref, self.ifrs_ref)
        self.assertFalse(result["is_valid"])
        self.assertFalse(result["has_ifrs"])
        self.assertIn(self.ifrs_ref, result["missing"])

    def test_ias_marker_accepted_for_ifrs(self):
        output = "Per Lex.uz MHMS #22, and under IAS 16 componentization is required."
        result = validate_citations(output, self.lex_uz_ref, self.ifrs_ref)
        self.assertTrue(result["has_ifrs"])
        self.assertTrue(result["is_valid"])

    def test_empty_output_produces_error(self):
        result = validate_citations("", self.lex_uz_ref, self.ifrs_ref)
        self.assertFalse(result["is_valid"])
        self.assertIn("claude_output is empty", result["errors"])

    def test_whitespace_only_output_produces_error(self):
        result = validate_citations("   \n  ", self.lex_uz_ref, self.ifrs_ref)
        self.assertFalse(result["is_valid"])
        self.assertIn("claude_output is empty", result["errors"])

    def test_output_field_echoes_input(self):
        output = "Per Lex.uz MHMS #22 and IFRS IAS 16."
        result = validate_citations(output, self.lex_uz_ref, self.ifrs_ref)
        self.assertEqual(result["output"], output)

    def test_no_false_positive_on_partial_word(self):
        output = "This discusses IFRSish concepts without proper Lex.uz MHMS #22 citation."
        result = validate_citations(output, self.lex_uz_ref, self.ifrs_ref)
        self.assertFalse(result["has_ifrs"])


if __name__ == "__main__":
    unittest.main()
