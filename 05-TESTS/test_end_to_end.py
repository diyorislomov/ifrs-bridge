"""
End-to-end test: Extract a financial statement -> Detect gaps -> Get Claude
explanation -> Validate citations.

By default this runs against a small synthetic sample statement generated
in-place (no real Uzbek company data is available locally), so it exercises
the full pipeline end-to-end without any manual setup. To test against a
real filing instead, set TEST_FILE to its path before running, e.g.:

    TEST_FILE="/path/to/galla_altep_q1_2026.pdf" python 05-TESTS/test_end_to_end.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '03-BACKEND'))

from utils.file_parser import extract_statement  # noqa: E402
from utils.gap_detector import detect_gaps  # noqa: E402
from utils.claude_api import call_gap_explanation  # noqa: E402
from utils.citation_validator import validate_citations  # noqa: E402
from utils.gaps_loader import load_all_gaps  # noqa: E402


def _make_sample_statement() -> str:
    """
    Builds a small synthetic XLSX statement containing terms that match
    real detection keywords from gaps_findings.json (leases, inventory),
    so the pipeline has something genuine to find when no real filing is
    available locally.
    """
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Balance Sheet"
    ws.append(["Ijara majburiyati", 12_000_000])
    ws.append(["Захиралар", 30_000_000])
    ws.append(["Cash and equivalents", 5_000_000])

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    wb.save(tmp.name)
    return tmp.name


# All 58 gaps, with the 8 researched ones carrying real mhms_treatment,
# lex_uz_ref, and ifrs_ref (see gaps_loader.py for why gaps.json alone is
# not enough).
all_gaps = load_all_gaps()

generated_sample = False
test_file = os.environ.get("TEST_FILE")
if not test_file:
    test_file = _make_sample_statement()
    generated_sample = True

print("=" * 60)
print("IFRS BRIDGE MVP — END-TO-END TEST")
print("=" * 60)
if generated_sample:
    print(f"(no TEST_FILE set — using generated sample statement at {test_file})")

# Step 1: Extract
print("\n[1/5] Extracting financial data...")
extracted = extract_statement(test_file)
if extracted.get('error'):
    print(f"✗ Extraction reported an error: {extracted['error']}")
else:
    print(f"✓ Company: {extracted.get('company_name', 'Unknown')}")
    print(f"✓ Period: {extracted.get('period_end', 'Unknown')}")
    print(f"✓ Line items found: {len(extracted.get('line_items', {}))}")

if generated_sample:
    os.remove(test_file)

# Step 2: Detect gaps
print("\n[2/5] Detecting gaps...")
detected = detect_gaps(
    extracted.get('line_items', {}),
    extracted.get('notes', {}),
    all_gaps
)
print(f"✓ Gaps found: {len(detected)}")
for gap in detected[:5]:
    print(f"  - {gap['gap_id']}: {gap['title']} ({gap['severity']})")

# Step 3: Get explanation for first HIGH-risk gap
if detected:
    high_gaps = [g for g in detected if g['severity'] == 'HIGH']
    if high_gaps:
        detected_gap = high_gaps[0]

        # detect_gaps() output doesn't carry lex_uz_ref/ifrs_ref (only
        # gap_id, title, severity, evidence, etc.) -- look up the full,
        # citation-bearing gap from all_gaps before calling Claude, the
        # same way 04-FRONTEND/app.py's Explain page does.
        gap = next((g for g in all_gaps if g.get('gap_id') == detected_gap['gap_id']), detected_gap)

        print(f"\n[3/5] Getting explanation for {gap['gap_id']}...")
        try:
            explanation = call_gap_explanation(gap, detected_gap['evidence'], language='en')
            print(f"✓ Claude response received ({len(explanation)} chars)")

            # Step 4: Validate citations
            print("\n[4/5] Validating citations...")
            validation = validate_citations(
                explanation,
                gap.get('lex_uz_ref', ''),
                gap.get('ifrs_ref', '')
            )
            print(f"✓ Citations valid: {validation['is_valid']}")
            if not validation['is_valid']:
                print(f"  Missing: {validation['missing']}")

            # Step 5: Show results
            print("\n[5/5] Results:")
            print("=" * 60)
            print(f"GAP: {gap['title']}")
            print(f"EVIDENCE: {detected_gap['evidence']}")
            print(f"CLAUDE EXPLANATION:\n{explanation[:500]}...")
            print("=" * 60)

        except Exception as e:
            print(f"✗ Claude API failed: {e}")
            print("  Make sure ANTHROPIC_API_KEY is set in .env")
    else:
        print("No HIGH-risk gaps to test")
else:
    print("No gaps detected (which is OK for MVP test)")

print("\n✅ END-TO-END TEST COMPLETE")
