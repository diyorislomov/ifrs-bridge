"""Unit tests for file_parser's amount parsing and line-item extraction."""

import os
import sys
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "03-BACKEND")
)

from utils.file_parser import (  # noqa: E402
    _parse_amount,
    _extract_line_items,
    _extract_line_items_cell_per_line,
    _extract_line_items_ocr,
    _split_ocr_amount_region,
    _find_company_name,
    _find_sections,
)


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

    def test_two_column_current_and_prior_period(self):
        text = (
            "Захиралар / Inventory 30,000,000 25,000,000\n"
            "Cash (500,000) (400,000)\n"
            "1000 Current Assets 50,000,000 45,000,000\n"
        )
        items = _extract_line_items(text, source="PDF")

        # Bilingual "uz / en" label keeps only the segment after the slash.
        self.assertEqual(items["Inventory"]["amount"], 30000000.0)
        self.assertEqual(items["Inventory"]["prior_amount"], 25000000.0)

        self.assertEqual(items["Cash"]["amount"], -500000.0)
        self.assertEqual(items["Cash"]["prior_amount"], -400000.0)

        self.assertEqual(items["Current Assets"]["code"], "1000")
        self.assertEqual(items["Current Assets"]["prior_amount"], 45000000.0)

    def test_space_grouped_number_not_mis_split_as_two_columns(self):
        # "30 000 000" is ONE number using spaces as thousands separators,
        # not two separate columns -- regression test for a real bug found
        # while adding two-column support (it briefly split this into
        # cur="000" prev="000" with "Захиралар 30" swallowed as the label).
        items = _extract_line_items("Захиралар 30 000 000\n", source="PDF")
        self.assertEqual(items["Захиралар"]["amount"], 30000000.0)
        self.assertNotIn("prior_amount", items["Захиралар"])

    def test_date_header_line_ignored(self):
        items = _extract_line_items("Statement as of June 30, 2026\n", source="PDF")
        self.assertEqual(items, {})


class TestFindCompanyName(unittest.TestCase):
    def test_quoted_name_with_latin_suffix(self):
        text = '"Example Trading" LLC\nFinancial Statements'
        self.assertEqual(_find_company_name(text), "Example Trading LLC")

    def test_quoted_name_with_guillemets_and_cyrillic_suffix(self):
        text = "«Namuna Savdo» MChJ\nMoliyaviy hisobot"
        self.assertEqual(_find_company_name(text), "Namuna Savdo MChJ")

    def test_unquoted_name_falls_back_to_trailing_words(self):
        text = "ABC AJ konsolidatsiyalashgan hisobot"
        self.assertEqual(_find_company_name(text), "ABC AJ")

    def test_no_suffix_returns_none(self):
        self.assertIsNone(_find_company_name("No legal suffix here at all"))


class TestFindSections(unittest.TestCase):
    def test_splits_into_recognized_sections(self):
        text = (
            "БАЛАНС ҲИСОБОТИ\n"
            "Захиралар 30,000,000\n"
            "\n"
            "ДАРОМАД ВА ХАРАЖАТЛАР ТЎҒРИСИДАГИ ҲИСОБОТ\n"
            "Revenue 100,000,000\n"
            "\n"
            "ТУШУНТИРИШЛАР\n"
            "Note 1: something.\n"
        )
        sections = _find_sections(text)
        self.assertEqual(set(sections.keys()), {"balance_sheet", "p_and_l", "notes"})
        self.assertIn("Захиралар", sections["balance_sheet"])
        self.assertNotIn("Revenue", sections["balance_sheet"])  # bounded, not full text
        self.assertIn("Revenue", sections["p_and_l"])
        self.assertIn("Note 1", sections["notes"])

    def test_no_recognized_headers_returns_empty(self):
        self.assertEqual(_find_sections("Just some random text with numbers 123"), {})

    def test_last_section_runs_to_end_of_text(self):
        text = "ТУШУНТИРИШЛАР\nline one\nline two\n"
        sections = _find_sections(text)
        self.assertEqual(sections["notes"], text)


class TestParseAmountRejectsCodeReferences(unittest.TestCase):
    # Regression tests: a label ending in a parenthetical account-code
    # reference (e.g. "(0100, 0300)") was being misparsed as a negative
    # amount by the single-line extractor, because its own integer part
    # incorrectly allowed a leading zero.
    def test_rejects_parenthesized_code_list(self):
        self.assertIsNone(_parse_amount("(0100, 0300)"))

    def test_rejects_bare_leading_zero_code(self):
        self.assertIsNone(_parse_amount("0100"))

    def test_accepts_lone_zero_as_valid_amount(self):
        self.assertEqual(_parse_amount("0"), 0.0)

    def test_accepts_decimal_starting_with_zero(self):
        self.assertEqual(_parse_amount("0.5"), 0.5)
        self.assertEqual(_parse_amount("0,5"), 0.5)


class TestExtractLineItemsCellPerLine(unittest.TestCase):
    # Real Uzbek NAS statements exported from the tax portal render each
    # table cell (bilingual label lines, row code, each amount) as its own
    # separate text line, rather than a whole row on one line -- this is
    # the exact structure that was silently producing zero line items.
    def test_bilingual_label_code_and_two_amounts(self):
        text = (
            "бошлангич (кайта тиклаш) киймат (0100, 0300)\n"
            "первоначальная (восстановительная) стоимость (0100, 0300)\n"
            "010\n"
            "19 312 416 279\n"
            "28 089 943 259\n"
        )
        items = _extract_line_items_cell_per_line(text, source="PDF")
        key = "первоначальная (восстановительная) стоимость (0100, 0300)"
        self.assertIn(key, items)
        self.assertEqual(items[key]["code"], "010")
        self.assertEqual(items[key]["amount"], 19312416279.0)
        self.assertEqual(items[key]["prior_amount"], 28089943259.0)

    def test_zero_balance_captured_as_prior_amount(self):
        text = "эскириш (0500)\nизнос (0500)\n021\n21 591 934\n0\n"
        items = _extract_line_items_cell_per_line(text, source="PDF")
        self.assertEqual(items["износ (0500)"]["prior_amount"], 0.0)

    def test_section_headers_produce_no_line_items(self):
        text = "АКТИВ\nI. Узок муддатли активлар\nI. Долгосрочные активы\nАсосий воситалари:\nОсновные средства:\n"
        self.assertEqual(_extract_line_items_cell_per_line(text, source="PDF"), {})

    def test_single_amount_row_has_no_prior_amount(self):
        text = "label uz\nlabel ru\n040\n1 000 000\n"
        items = _extract_line_items_cell_per_line(text, source="PDF")
        self.assertEqual(items["label ru"]["amount"], 1000000.0)
        self.assertNotIn("prior_amount", items["label ru"])

    def test_extract_from_pdf_merges_both_strategies_cleanly(self):
        # Full end-to-end check against a real-document-derived transcript:
        # must produce exactly the correct rows, with no garbage entries
        # from the single-line extractor misfiring on label-only lines.
        import unittest.mock as mock
        from utils.file_parser import extract_from_pdf

        full_text = (
            "бошлангич (кайта тиклаш) киймат (0100, 0300)\n"
            "первоначальная (восстановительная) стоимость (0100, 0300)\n"
            "010\n"
            "19 312 416 279\n"
            "28 089 943 259\n"
            "эскириш (0200)\n"
            "износ (0200)\n"
            "011\n"
            "11 094 637 081\n"
            "14 731 076 314\n"
        )
        with mock.patch("utils.file_parser._pdfminer_extract_text", return_value=full_text):
            result = extract_from_pdf("fake.pdf")

        self.assertIsNone(result.get("error"))
        self.assertEqual(len(result["line_items"]), 2)
        self.assertEqual(result["line_items"]["износ (0200)"]["amount"], 11094637081.0)

    def test_scanned_pdf_falls_back_to_ocr(self):
        # A scanned/image-only PDF: pdfminer finds no text layer at all,
        # returning just one form-feed character per page. extract_from_pdf
        # must detect that and fall back to OCR rather than reporting zero
        # line items.
        import unittest.mock as mock
        from utils.file_parser import extract_from_pdf

        ocr_text = "износ (0500) 021 21 591 934 0\n"
        with mock.patch("utils.file_parser._pdfminer_extract_text", return_value="\x0c\x0c"), \
             mock.patch("utils.file_parser._ocr_extract_text", return_value=ocr_text):
            result = extract_from_pdf("fake.pdf")

        self.assertIsNone(result.get("error"))
        self.assertTrue(result["ocr_used"])
        self.assertEqual(result["line_items"]["износ (0500)"]["amount"], 21591934.0)
        self.assertEqual(result["line_items"]["износ (0500)"]["prior_amount"], 0.0)

    def test_ocr_unavailable_leaves_empty_text_without_crashing(self):
        import unittest.mock as mock
        from utils.file_parser import extract_from_pdf

        with mock.patch("utils.file_parser._pdfminer_extract_text", return_value="\x0c"), \
             mock.patch("utils.file_parser._ocr_extract_text", side_effect=Exception("tesseract not found")):
            result = extract_from_pdf("fake.pdf")

        self.assertIsNone(result.get("error"))
        self.assertFalse(result["ocr_used"])
        self.assertEqual(result["line_items"], {})


class TestSplitOcrAmountRegion(unittest.TestCase):
    def test_explicit_delimiter_splits_current_and_prior(self):
        cur, prior = _split_ocr_amount_region("| 19 312 416 279 | _ 28 089 943 259")
        self.assertEqual(cur, "19 312 416 279")
        self.assertEqual(prior, "28 089 943 259")

    def test_short_trailing_group_treated_as_separate_zero_balance(self):
        cur, prior = _split_ocr_amount_region("27 274 021 0")
        self.assertEqual(cur, "27 274 021")
        self.assertEqual(prior, "0")

    def test_no_delimiter_single_plausible_amount_kept(self):
        cur, prior = _split_ocr_amount_region("34 110 619 922")
        self.assertEqual(cur, "34 110 619 922")
        self.assertIsNone(prior)

    def test_ambiguous_run_together_amounts_rejected_not_guessed(self):
        # Two real amounts ("7 551 481" twice) OCR'd with no visible column
        # gap between them -- regression test for a bug where this got
        # silently concatenated into a fabricated ~75-trillion-unit amount
        # instead of being recognized as unparseable.
        cur, prior = _split_ocr_amount_region("7 551 481 7 551 481")
        self.assertIsNone(cur)
        self.assertIsNone(prior)

    def test_empty_region_returns_none(self):
        self.assertEqual(_split_ocr_amount_region(""), (None, None))


class TestExtractLineItemsOcr(unittest.TestCase):
    # Real Tesseract OCR output for a scanned (image-only, no text layer)
    # Uzbek NAS balance sheet -- unlike a text-layer PDF, OCR reconstructs
    # each table row as ONE line (label, row code, and amount(s) together),
    # with the column gridline sometimes misread as a stray "|" character
    # and sometimes lost entirely.
    def test_real_ocr_row_with_delimiter(self):
        text = (
            "первоначальная (восстановительная) стоимость (0100, 0300) "
            "010 | 19 312 416 279 | _ 28 089 943 259\n"
        )
        items = _extract_line_items_ocr(text, source="OCR")
        key = "первоначальная (восстановительная) стоимость (0100, 0300)"
        self.assertEqual(items[key]["code"], "010")
        self.assertEqual(items[key]["amount"], 19312416279.0)
        self.assertEqual(items[key]["prior_amount"], 28089943259.0)

    def test_row_code_not_confused_with_account_code_reference_in_label(self):
        # The label itself contains "(0100, 0300)" -- digits preceded by a
        # comma+space, not by label text -- which must NOT be mistaken for
        # the row code.
        text = "остаточная стоимость (стр 010-011) 012 | 8217 779 198 | _ 13 358 866 945\n"
        items = _extract_line_items_ocr(text, source="OCR")
        key = "остаточная стоимость (стр 010-011)"
        self.assertEqual(items[key]["code"], "012")
        self.assertEqual(items[key]["amount"], 8217779198.0)

    def test_no_delimiter_ambiguous_amounts_produce_no_entry(self):
        text = "Инвестиции в дочернии и хозяйственные общества (0620) 050 7 551 481 7 551 481\n"
        items = _extract_line_items_ocr(text, source="OCR")
        self.assertNotIn(
            "Инвестиции в дочернии и хозяйственные общества (0620)", items
        )

    def test_label_only_line_produces_no_entry(self):
        text = "бошлангич (кайта тиклаш) киймат (0100, 0300)\n"
        self.assertEqual(_extract_line_items_ocr(text, source="OCR"), {})

    def test_source_is_tagged(self):
        text = "износ (0500) 021 21 591 934 0\n"
        items = _extract_line_items_ocr(text, source="OCR")
        self.assertEqual(items["износ (0500)"]["source"], "OCR")


if __name__ == "__main__":
    unittest.main()
