import re

import pdfplumber
from openpyxl import load_workbook


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
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() or ""

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

            # Extract balance sheet items (simplified: look for account codes + amounts)
            # Format: "1000  Current Assets  50,000,000"
            bs_pattern = r'(\d{4})\s+([A-Za-z\s\w]+?)\s+([\d,]+)'
            for match in re.finditer(bs_pattern, full_text):
                account_code = match.group(1)
                account_name = match.group(2).strip()
                amount_str = match.group(3).replace(',', '')
                try:
                    amount = float(amount_str)
                    data['line_items'][account_name] = {
                        'code': account_code,
                        'amount': amount,
                        'source': 'PDF'
                    }
                except ValueError:
                    pass

            # Extract notes (section after "Notes to Financial Statements").
            # find() returns 0 for a match at the very start of the text, and 0 is
            # falsy, so `a.find(x) or a.find(y)` would wrongly fall through to the
            # second search in that case. Check each marker explicitly instead.
            notes_start = full_text.find("Notes to Financial Statements")
            if notes_start == -1:
                notes_start = full_text.find("Тушунтиришлар")
            if notes_start >= 0:
                notes_text = full_text[notes_start:notes_start + 5000]  # First 5000 chars of notes
                data['notes']['raw'] = notes_text

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

            for row in ws.iter_rows(min_row=1, max_row=100, values_only=True):
                if len(row) >= 2 and row[0] and row[1]:  # Account name, amount
                    try:
                        account_name = str(row[0]).strip()
                        amount = float(str(row[1]).replace(',', '')) if row[1] else 0
                        data['line_items'][account_name] = {
                            'sheet': sheet_name,
                            'amount': amount,
                            'source': 'Excel'
                        }
                    except ValueError:
                        pass

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
