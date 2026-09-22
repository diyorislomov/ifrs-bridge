import re

from pdfminer.high_level import extract_text as _pdfminer_extract_text
from openpyxl import load_workbook

# A trailing amount at the end of a line: optional leading minus/parenthesis,
# digits grouped by comma/space/dot separators, optional decimal part,
# optional closing parenthesis (accounting notation for negatives).
_AMOUNT_RE = re.compile(r'\(?-?\d[\d,.\s\xa0]{0,20}\d\)?\s*$')
# An optional numeric account code at the start of a line (e.g. "1000",
# "10.1"), separated from the account name by whitespace.
_LEADING_CODE_RE = re.compile(r'^\s*(\d{1,6}(?:[.\-]\d+)?)\s+')


def _parse_amount(raw: str):
    """
    Parses a numeric string into a float, tolerating the amount formats seen
    across real financial statements: comma or space thousands separators
    (including non-breaking spaces), a comma OR dot decimal separator
    (auto-detected), and parentheses or a leading minus for negatives.
    Returns None if the string isn't a parseable number.
    """
    s = raw.strip()
    if not s:
        return None

    negative = False
    if s.startswith('(') and s.endswith(')'):
        negative = True
        s = s[1:-1].strip()
    if s.startswith('-'):
        negative = True
        s = s[1:].strip()

    s = s.replace(' ', '').replace('\xa0', '')
    if not s:
        return None

    if ',' in s and '.' in s:
        # Whichever separator appears last is the decimal point.
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            s = s.replace(',', '.')  # single comma, 1-2 trailing digits -> decimal
        else:
            s = s.replace(',', '')  # otherwise a thousands separator
    elif '.' in s:
        parts = s.split('.')
        if len(parts) > 2 or len(parts[-1]) == 3:
            s = s.replace('.', '')  # multiple dots, or 3 trailing digits -> thousands separator

    try:
        value = float(s)
    except ValueError:
        return None
    return -value if negative else value


def _extract_line_items(text: str, source: str) -> dict:
    """
    Scans text line by line for "<optional code> <name> <amount>" rows,
    without requiring a rigid account-code prefix or a specific number
    format -- real statement text extracted from a PDF rarely preserves
    strict column alignment, decimals/space-thousands are common, and many
    line items have no visible code at all.
    """
    line_items = {}
    for raw_line in text.split('\n'):
        line = raw_line.strip()
        if not line:
            continue

        amount_match = _AMOUNT_RE.search(line)
        if not amount_match:
            continue

        amount_str = amount_match.group().strip()
        if sum(c.isdigit() for c in amount_str) < 2:
            continue  # skip isolated single digits (e.g. footnote markers)

        name_part = line[:amount_match.start()].strip()
        if not name_part:
            continue

        code = None
        code_match = _LEADING_CODE_RE.match(name_part)
        if code_match:
            code = code_match.group(1)
            name_part = name_part[code_match.end():].strip()
        if not name_part:
            continue

        amount = _parse_amount(amount_str)
        if amount is None:
            continue

        line_items[name_part] = {
            'code': code,
            'amount': amount,
            'source': source,
        }

    return line_items


def extract_from_pdf(pdf_path: str) -> dict:
    """
    Extracts financial statement data from PDF.

    Returns:
        dict: {
            "company_name": str,
            "period_end": str,
            "line_items": {...},  # Balance sheet + P&L lines
            "notes": {...}        # Notes to financial statements
        }
    """
    data = {"line_items": {}, "notes": {}}

    try:
        full_text = _pdfminer_extract_text(pdf_path) or ""

        # Simple extraction: look for balance sheet and P&L sections
        # (In production, use ML-based table detection; for MVP, regex is fine)

        # Extract company name (usually on first page)
        company_match = re.search(r'(?:компания|ТОВ|МЧЖ|JSC|LLC)\s+(["\']?[\w\s\-]+["\']?)', full_text[:500])
        if company_match:
            data['company_name'] = company_match.group(1).strip()

        # Extract reporting period (look for date pattern YYYY-MM-DD or Uzbek date)
        period_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', full_text)
        if period_match:
            data['period_end'] = f"{period_match.group(1)}-{period_match.group(2)}-{period_match.group(3)}"

        data['line_items'] = _extract_line_items(full_text, source='PDF')

        # Notes section, if a header for one is present (used for a shorter,
        # more targeted excerpt when available).
        # find() returns 0 for a match at the very start of the text, and 0 is
        # falsy, so `a.find(x) or a.find(y)` would wrongly fall through to the
        # second search in that case. Check each marker explicitly instead.
        notes_start = full_text.find("Notes to Financial Statements")
        if notes_start == -1:
            notes_start = full_text.find("Тушунтиришлар")
        if notes_start >= 0:
            data['notes']['raw'] = full_text[notes_start:notes_start + 5000]
        else:
            # No recognizable "notes" header -- most real statements won't
            # use this exact phrase. Fall back to a chunk of the full
            # document text so gap-keyword matching still has real content
            # to search, instead of nothing at all.
            data['notes']['raw'] = full_text[:5000]

    except Exception as e:
        data['error'] = str(e)

    return data


def extract_from_excel(excel_path: str) -> dict:
    """
    Extracts financial statement data from Excel (XLSX).

    Returns: same dict structure as PDF
    """
    data = {"line_items": {}, "notes": {}}

    wb = None
    try:
        wb = load_workbook(excel_path, read_only=True)

        # Assume first sheet is balance sheet, second is P&L
        for sheet_idx, sheet_name in enumerate(wb.sheetnames[:2]):
            ws = wb[sheet_name]

            for row in ws.iter_rows(min_row=1, max_row=200, values_only=True):
                if len(row) < 2 or not row[0]:
                    continue

                account_name = str(row[0]).strip()
                if not account_name:
                    continue

                # The amount isn't always in column B (e.g. current/prior
                # period columns) -- take the last cell in the row that
                # parses as a number.
                amount = None
                for cell in reversed(row[1:]):
                    if cell is None:
                        continue
                    amount = cell if isinstance(cell, (int, float)) else _parse_amount(str(cell))
                    if amount is not None:
                        break

                if amount is not None:
                    data['line_items'][account_name] = {
                        'sheet': sheet_name,
                        'amount': float(amount),
                        'source': 'Excel'
                    }

    except Exception as e:
        data['error'] = str(e)
    finally:
        # read_only workbooks keep the underlying file handle open until
        # closed; on Windows this locks the file and blocks deletion.
        if wb is not None:
            wb.close()

    return data


def extract_statement(file_path: str) -> dict:
    """
    Main entry point: detects file type and extracts data.
    """
    lower_path = file_path.lower()
    if lower_path.endswith('.pdf'):
        return extract_from_pdf(file_path)
    elif lower_path.endswith(('.xlsx', '.xls')):
        return extract_from_excel(file_path)
    else:
        return {'error': 'Unsupported file type'}
