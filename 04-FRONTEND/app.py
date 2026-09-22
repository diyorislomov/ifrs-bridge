import json
import os
import sys
import tempfile
from datetime import datetime

import streamlit as st

# Add backend to path (04-FRONTEND/app.py -> repo root -> 03-BACKEND)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '03-BACKEND'))

from utils.file_parser import extract_statement
from utils.gap_detector import detect_gaps
from utils.claude_api import call_gap_explanation
from utils.citation_validator import validate_citations

REPO_ROOT = os.path.join(os.path.dirname(__file__), '..')


def _load_gaps() -> list:
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
    gaps_json_path = os.path.join(REPO_ROOT, '02-KNOWLEDGE-BASE', 'gaps.json')
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

    findings_path = os.path.join(REPO_ROOT, 'gaps_findings.json')
    if os.path.exists(findings_path):
        with open(findings_path, 'r', encoding='utf-8') as f:
            findings_by_id = {g['gap_id']: g for g in json.load(f)}

        for gap in all_gaps:
            override = findings_by_id.get(gap.get('gap_id'))
            if override:
                gap.update(override)

    return all_gaps


def _save_uploaded_file(uploaded_file) -> str:
    """Writes an uploaded file to a cross-platform temp path and returns it."""
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return tmp.name


ALL_GAPS = _load_gaps()

st.set_page_config(page_title="IFRS Bridge Simulator", layout="wide", initial_sidebar_state="expanded")
st.title("🌉 IFRS Bridge Simulator")
st.write("Automated NAS→IFRS gap detection for Uzbek accountants | AI-powered, Claude API, real citations")

# Initialize session state
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None
if 'detected_gaps' not in st.session_state:
    st.session_state.detected_gaps = None
if 'explanations' not in st.session_state:
    st.session_state.explanations = {}

# Sidebar navigation
st.sidebar.title("📑 Navigation")
page = st.sidebar.radio("Go to:", [
    "1️⃣ Upload",
    "2️⃣ Extract",
    "3️⃣ Detect Gaps",
    "4️⃣ Explain",
    "5️⃣ Export Report"
])

# ============ PAGE 1: UPLOAD ============
if page == "1️⃣ Upload":
    st.header("Step 1: Upload Your NAS Financial Statement")
    st.write("Upload a PDF or Excel file containing your financial statement (Balance Sheet, P&L, Notes)")

    uploaded_file = st.file_uploader("Choose file", type=['pdf', 'xlsx', 'xls'])

    if uploaded_file:
        st.success(f"✅ File uploaded: {uploaded_file.name}")

        if st.button("Extract Data"):
            with st.spinner("Extracting financial data..."):
                temp_path = _save_uploaded_file(uploaded_file)
                try:
                    st.session_state.extracted_data = extract_statement(temp_path)
                finally:
                    os.remove(temp_path)
                st.success("✅ Data extracted! Go to Step 2.")

# ============ PAGE 2: EXTRACT ============
elif page == "2️⃣ Extract":
    st.header("Step 2: Review Extracted Data")

    if st.session_state.extracted_data is None:
        st.warning("⚠️ No data extracted yet. Go to Step 1 to upload a file.")
    else:
        data = st.session_state.extracted_data

        if 'error' in data:
            st.error(f"Error: {data['error']}")
        else:
            st.subheader("Company Information")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Company:** {data.get('company_name', 'Unknown')}")
            with col2:
                st.write(f"**Period End:** {data.get('period_end', 'Unknown')}")

            st.subheader("Line Items Extracted")
            if data['line_items']:
                st.write(f"Found {len(data['line_items'])} line items:")
                for account, details in list(data['line_items'].items())[:20]:  # Show first 20
                    st.write(f"- **{account}:** {details.get('amount', 0):,.0f} UZS")
            else:
                st.warning("No line items found. Check your file format.")

# ============ PAGE 3: DETECT GAPS ============
elif page == "3️⃣ Detect Gaps":
    st.header("Step 3: Detect IFRS Gaps")

    if st.session_state.extracted_data is None:
        st.warning("⚠️ No data extracted yet. Go to Step 1 first.")
    else:
        if st.button("🔍 Scan for Gaps"):
            with st.spinner("Scanning for NAS→IFRS gaps..."):
                st.session_state.detected_gaps = detect_gaps(
                    st.session_state.extracted_data.get('line_items', {}),
                    st.session_state.extracted_data.get('notes', {}),
                    ALL_GAPS
                )
                st.success(f"✅ Found {len(st.session_state.detected_gaps)} gaps!")

        if st.session_state.detected_gaps:
            st.subheader(f"Gaps Detected ({len(st.session_state.detected_gaps)})")

            # Filter by severity
            severity_filter = st.selectbox("Filter by severity:", ["All", "HIGH", "MEDIUM", "LOW"])

            filtered = st.session_state.detected_gaps
            if severity_filter != "All":
                filtered = [g for g in filtered if g.get('severity') == severity_filter]

            for gap in filtered:
                with st.expander(f"**{gap['gap_id']}** - {gap['title']} ({gap['severity']})"):
                    st.write(f"**Keywords Found:** {', '.join(gap.get('keywords_found', []))}")
                    st.write(f"**Confidence:** {gap.get('confidence', 0)*100:.0f}%")
                    st.write(f"**Evidence:** {gap['evidence']}")

# ============ PAGE 4: EXPLAIN ============
elif page == "4️⃣ Explain":
    st.header("Step 4: Get AI Explanations with Citations")

    if st.session_state.detected_gaps is None:
        st.warning("⚠️ No gaps detected yet. Go to Step 3 first.")
    else:
        st.write("Click on a gap below to get Claude's explanation with mandatory Lex.uz + IFRS citations")

        language = st.selectbox("Response language:", ["English", "Uzbek"])
        lang_code = "uz" if language == "Uzbek" else "en"

        for gap in st.session_state.detected_gaps[:8]:  # Show first 8 (HIGH-risk)
            with st.expander(f"**{gap['gap_id']}** - {gap['title']}"):

                # Show MHMS treatment
                st.write("**Required MHMS Treatment:**")
                st.write(gap.get('mhms_treatment', 'N/A'))

                stored = st.session_state.explanations.get(gap['gap_id'])

                # Get Claude explanation
                if st.button(f"Explain {gap['gap_id']}", key=f"btn_{gap['gap_id']}"):
                    with st.spinner("Calling Claude API..."):
                        try:
                            # Find full gap from DB for citation refs
                            full_gap = next((g for g in ALL_GAPS if g.get('gap_id') == gap['gap_id']), gap)

                            explanation = call_gap_explanation(
                                full_gap,
                                f"Statement showed: {gap['evidence']}",
                                language=lang_code
                            )

                            # Validate citations
                            lex_uz_ref = full_gap.get('lex_uz_ref', 'Lex.uz MHMS')
                            ifrs_ref = full_gap.get('ifrs_ref', 'IFRS')

                            citation_result = validate_citations(explanation, lex_uz_ref, ifrs_ref)

                            # Store explanation (including citation status, so it can be
                            # redisplayed on a later rerun without re-calling Claude)
                            stored = {
                                'text': explanation,
                                'citations_valid': citation_result['is_valid'],
                                'missing_citations': citation_result['missing'],
                                'timestamp': datetime.now().isoformat()
                            }
                            st.session_state.explanations[gap['gap_id']] = stored

                        except Exception as e:
                            st.error(f"Error calling Claude: {str(e)}")

                # Display the stored explanation, if any -- this stays outside the
                # button's if-block so it persists across reruns (e.g. after clicking
                # a different gap's button), instead of vanishing until re-clicked.
                if stored:
                    st.write("**Claude's Explanation:**")
                    st.write(stored['text'])

                    if stored['citations_valid']:
                        st.success("✅ Citations validated")
                    else:
                        st.warning(f"⚠️ Missing citations: {stored['missing_citations']}")

# ============ PAGE 5: EXPORT ============
elif page == "5️⃣ Export Report":
    st.header("Step 5: Download Report")

    if not st.session_state.detected_gaps or not st.session_state.explanations:
        st.warning("⚠️ No analysis done yet. Complete Steps 3-4 first.")
    else:
        report_format = st.selectbox("Format:", ["PDF", "JSON", "Text"])

        if st.button("📥 Generate Report"):
            with st.spinner("Generating report..."):

                # Create report data
                report = {
                    "generated_at": datetime.now().isoformat(),
                    "total_gaps": len(st.session_state.detected_gaps),
                    "gaps_explained": len(st.session_state.explanations),
                    "explanations": st.session_state.explanations
                }

                if report_format == "JSON":
                    report_json = json.dumps(report, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="Download JSON",
                        data=report_json,
                        file_name=f"ifrs_bridge_report_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
                    st.success("✅ Report ready for download!")

                elif report_format == "Text":
                    report_text = f"""IFRS BRIDGE REPORT
Generated: {report['generated_at']}

Total Gaps Found: {report['total_gaps']}
Gaps Explained: {report['gaps_explained']}

EXPLANATIONS:
{json.dumps(report['explanations'], ensure_ascii=False, indent=2)}
"""
                    st.download_button(
                        label="Download Text",
                        data=report_text,
                        file_name=f"ifrs_bridge_report_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain"
                    )
                    st.success("✅ Report ready for download!")

                elif report_format == "PDF":
                    st.info("PDF export coming in v1.1 (use Text or JSON for now)")

# Footer
st.sidebar.markdown("---")
st.sidebar.write("**IFRS Bridge v1.0 MVP**")
st.sidebar.write("Phase 2.3 | Claude API | 8 HIGH-risk gaps | Real citations")
