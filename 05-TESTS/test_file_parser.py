"""Unit tests for file_parser's amount parsing and line-item extraction."""

import os
import sys
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "03-BACKEND")
)

from utils.file_parser import _parse_amount, _extract_line_items  # noqa: E402


class TestParseAmount(unittest.TestCase):
    def test_comma_thousands(self):
        self.assertEqual(_parse_amount("50,000,000"), 50000000.0)

    def test_space_thousands(self):
        self.assertEqual(_parse_amount("50 000 000"), 50000000.0)

    def test_us_style_decimal(self):
        self.assertEqual(_parse_amount("1,234.56"), 1234.56)

    def test_european_style_decimal(self):
        self.assertEqual(_parse_amount("1.234.567,89"), 1234567.89)

    def test_parenthesized_negative(self):
        self.assertEqual(_parse_amount("(1,234)"), -1234.0)

    def test_leading_minus(self):
        self.assertEqual(_parse_amount("-500"), -500.0)

    def test_plain_integer(self):
        self.assertEqual(_parse_amount("12"), 12.0)

    def test_space_thousands_with_comma_decimal(self):
        self.assertEqual(_parse_amount("1 234,50"), 1234.50)

    def test_empty_string_returns_none(self):
        self.assertIsNone(_parse_amount(""))

    def test_non_numeric_returns_none(self):
        self.assertIsNone(_parse_amount("N/A"))


class TestExtractLineItems(unittest.TestCase):
    def test_mixed_realistic_formats(self):
        text = (
            "Balance Sheet\n"
            "Захиралар 30 000 000\n"
            "Ijara majburiyati        12,500,000.50\n"
            "Cash and equivalents (500,000)\n"
            "1000 Current Assets 50,000,000\n"
            "Note 5: something not a line item at all\n"
            "Page 5\n"
        )
        items = _extract_line_items(text, source="PDF")

        self.assertEqual(items["Захиралар"]["amount"], 30000000.0)
        self.assertIsNone(items["Захиралар"]["code"])

        self.assertEqual(items["Ijara majburiyati"]["amount"], 12500000.5)

        self.assertEqual(items["Cash and equivalents"]["amount"], -500000.0)

        self.assertEqual(items["Current Assets"]["amount"], 50000000.0)
        self.assertEqual(items["Current Assets"]["code"], "1000")

        # Narrative lines and bare page numbers must not become line items.
        self.assertNotIn("Note 5: something not a line item at all", items)
        self.assertFalse(any("Page" in k for k in items))

    def test_empty_text_returns_empty_dict(self):
        self.assertEqual(_extract_line_items("", source="PDF"), {})

    def test_source_is_tagged(self):
        items = _extract_line_items("Revenue 1,000,000\n", source="PDF")
        self.assertEqual(items["Revenue"]["source"], "PDF")


if __name__ == "__main__":
    unittest.main()
