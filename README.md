# IFRS Bridge Simulator

Automated NAS→IFRS gap detection tool for Uzbek accountants.

**Status:** Phase 2 Implementation | **Target Launch:** August 31, 2026

## What It Does
Upload a NAS financial statement (PDF/Excel) → Detect IFRS gaps → Export plain-language report.

## Tech Stack
- Python + Claude API (claude-3-5-sonnet-20241022)
- Streamlit
- pdfplumber, openpyxl
- Supabase

## Quick Start
1. \git clone https://github.com/diyorislomov/ifrs-bridge.git\
2. \pip install -r requirements.txt\
3. \streamlit run 04-FRONTEND/app.py\

## License
MIT
