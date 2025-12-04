# AI-Driven Analyzer for IDR Eligibility

A production-ready application that ingests ERA (ANSI 835) files and ERA-as-PDFs, extracts CPT remark codes and CAS (Claim Adjustment) codes, matches them against a local code database, and reports which claims/lines are eligible for IDR.

## Features

- **Multi-format Support**: Accepts raw 835 text files (.txt, .835, .edi) and PDF ERA/EOB documents
- **Intelligent Extraction**: Uses PyPDF2 for direct text extraction with OCR fallback for scanned documents
- **AI Enhancement**: Optional OpenAI integration for disambiguation and validation (gracefully degrades if unavailable)
- **Comprehensive Parsing**: Extracts CLP, SVC, CAS, LQ segments with CPT, modifiers, adjustment codes, and remark codes
- **IDR Eligibility**: Validates claims against local database of eligible codes and computes IDR timelines
- **Modern GUI**: Streamlit-based interface for file upload, results viewing, and code management
- **Multi-format Reports**: Generate CSV, JSON, and human-readable audit reports (HTML/PDF)

## Setup Instructions

### Prerequisites

- Python 3.11+
- Tesseract OCR (for OCR fallback functionality)
  - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
  - macOS: `brew install tesseract`
  - Linux: `sudo apt-get install tesseract-ocr`

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd era-idr-analyzer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Download spaCy model:
```bash
python -m spacy download en_core_web_sm
```

5. Configure environment:
```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY if desired (optional)
```

6. Run the application:
```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`

## Usage

### Running the Application

1. **Start the app**: Run `streamlit run app.py`
2. **Upload Files**: Use the sidebar to upload one or more ERA files (.pdf, .edi, .835, .txt)
3. **Configure Options**: 
   - Toggle OpenAI enhancement (if API key is configured)
   - Enable redaction to mask PHI in reports
4. **Process**: Click "Run Analysis" to process files
5. **View Results**: Review the interactive results table with filters
6. **Download Reports**: Export results as CSV, JSON, or Audit Report (HTML/PDF)
7. **Manage Codes**: Navigate to "Code Management" to add/edit/delete CPT, CAS, and Remark codes

### Features

- **Multi-format Support**: Handles both raw ANSI 835 EDI files and PDF ERA/EOB documents
- **OCR Fallback**: Automatically uses OCR for scanned PDFs when direct text extraction fails
- **IDR Eligibility**: Matches CPT, CAS, and RARC codes against local database
- **Timeline Calculation**: Computes Open Negotiation and IDR Initiation windows based on payment dates
- **Comprehensive Reports**: Generate CSV, JSON, and human-readable audit reports
- **Code Management**: CRUD interface for managing eligible codes

## Project Structure

```
era-idr-analyzer/
  app.py                      # Streamlit entrypoint
  requirements.txt
  .env.example
  README.md
  LICENSE
  logs/.gitkeep
  data/
    seed/
      cpt_seed.csv
      cas_seed.csv
      remark_seed.csv
  samples/
    835_minimal.edi
    era_simple.pdf
    era_bad.pdf
  src/
    __init__.py
    config.py
    db.py
    models.py                 # Pydantic models
    ocr.py
    pdf_extract.py
    era_tokenizer.py          # Segment & element parsing
    era_parser.py             # CLP, SVC, CAS, LQ extraction
    normalize.py              # CPT/modifiers, amounts, dates
    ai_enhance.py             # Optional OpenAI helpers
    rules.py                  # Eligibility evaluation & timelines
    reporter/
      __init__.py
      csv_report.py
      json_report.py
      audit_report.py         # Markdown->HTML->PDF
    ui/
      __init__.py
      forms.py                # CRUD for codes
      views.py                # Results grids, filters, downloads
    utils/
      logging.py
      time.py
      redaction.py
  tests/
    test_tokenizer.py
    test_parser.py
    test_rules.py
    test_reports.py
```

## Testing

Run tests with:
```bash
pytest -q
```

With coverage:
```bash
pytest --cov=src --cov-report=html
```

## License

See LICENSE file for details.

