# AI-Driven Analyzer for IDR Eligibility

A production-ready application that ingests ERA (ANSI 835) files and ERA-as-PDFs, extracts CPT remark codes and CAS (Claim Adjustment) codes, matches them against a local code database, and reports which claims/lines are eligible for IDR.

## Screenshots

| | |
|---|---|
| ![Processing Results](screenshots/Processing%20Results.png) | ![Code Management](screenshots/Code%20Management.png) |
| **Processing Results** — Interactive results table showing parsed claims/lines with IDR eligibility status and filters. | **Code Management** — Add, edit, and delete CPT, CAS, and remark codes in the local eligibility database. |
| ![AI Model Selection](screenshots/AI%20Model%20Selection.png) | ![Report Generation](screenshots/Report%20Generation.png) |
| **AI Model Selection** — Settings page for choosing an AI provider (OpenAI, Claude/Anthropic, or Ollama) and configuring API keys. | **Report Generation** — Export options for CSV, JSON, and human-readable audit reports (HTML/PDF). |

## Features

- **Multi-format Support**: Accepts raw 835 text files (.txt, .835, .edi) and PDF ERA/EOB documents
- **Intelligent Extraction**: Uses PyPDF2 for direct text extraction with OCR fallback for scanned documents
- **AI Enhancement**: Optional AI integration (OpenAI, Claude/Anthropic, or Ollama) for disambiguation and validation (gracefully degrades if unavailable)
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

5. Configure environment (optional — keys can also be set in the app's **Settings** page):
```bash
cp .env.example .env
# Edit .env and set API keys if desired (optional)
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
3. **Configure AI Provider**: Navigate to "Settings" to choose your AI provider and enter API keys
4. **Configure Options**: 
   - Toggle AI enhancement (if a provider is configured)
   - Enable redaction to mask PHI in reports
5. **Process**: Click "Run Analysis" to process files
6. **View Results**: Review the interactive results table with filters
7. **Download Reports**: Export results as CSV, JSON, or Audit Report (HTML/PDF)
8. **Manage Codes**: Navigate to "Code Management" to add/edit/delete CPT, CAS, and Remark codes

### Features

- **Multi-format Support**: Handles both raw ANSI 835 EDI files and PDF ERA/EOB documents
- **OCR Fallback**: Automatically uses OCR for scanned PDFs when direct text extraction fails
- **Glossary Exclusion**: Automatically detects and strips glossary/definition sections from ERA PDFs so that code descriptions are not double-counted as claim data
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
    ai_enhance.py             # AI helpers (OpenAI, Anthropic, Ollama)
    rules.py                  # Eligibility evaluation & timelines
    reporter/
      __init__.py
      csv_report.py
      json_report.py
      audit_report.py         # Markdown->HTML->PDF
    ui/
      __init__.py
      forms.py                # CRUD for codes
      settings.py             # AI provider & API key settings
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

## AI Providers

The application supports three AI providers for optional enhancement of ERA parsing and validation. Configure your preferred provider in the **Settings** page within the app, or via environment variables in `.env`.

### OpenAI

- **API Key**: Required. Obtain from your OpenAI account dashboard.
- **Default Model**: `gpt-4o-mini`
- **Environment Variables**: `OPENAI_API_KEY`, `AI_MODEL`
- **Available Models**:
  | Model | Description |
  |-------|-------------|
  | `gpt-4o` | Most capable OpenAI model — best accuracy, higher cost |
  | `gpt-4o-mini` | Compact and fast — good balance of cost and quality |
  | `gpt-4.1` | Latest GPT-4.1 — strong coding and instruction following |
  | `gpt-4.1-mini` | Smaller GPT-4.1 — fast and affordable |
  | `gpt-4.1-nano` | Smallest GPT-4.1 — lowest cost, fastest responses |
  | `o3-mini` | Reasoning model — best for complex analytical tasks |

### Claude (Anthropic)

- **API Key**: Required. Obtain from the Anthropic console.
- **Default Model**: `claude-sonnet-4-6`
- **Environment Variables**: `ANTHROPIC_API_KEY`, `AI_MODEL`
- **Available Models**:
  | Model | Description |
  |-------|-------------|
  | `claude-sonnet-4-6` | Latest Sonnet — best balance of speed and intelligence |
  | `claude-opus-4-8` | Most capable Claude — highest accuracy, slower |
  | `claude-haiku-4-5-20251001` | Fastest Claude — lowest cost, good for simple tasks |

### Ollama (Local) — Recommended for HIPAA Compliance

- **API Key**: Not required. Ollama runs entirely on the local machine.
- **Default Model**: `llama3.2:latest`
- **Default URL**: `http://localhost:11434`
- **Environment Variables**: `OLLAMA_BASE_URL`
- **Available Models** (must be pulled locally via `ollama pull <model>`):
  | Model | Size | Description |
  |-------|------|-------------|
  | `llama3.2:latest` | 2.0 GB | Meta Llama 3.2 — general-purpose |
  | `phi3:mini` | 2.2 GB | Microsoft Phi-3 Mini — strong reasoning |
  | `qwen2.5:3b` | 1.9 GB | Qwen 2.5 3B — fast and compact |
  | `deepseek-coder:6.7b` | 3.8 GB | DeepSeek Coder 6.7B — code and structured data |

**Why Ollama is the recommended provider for HIPAA-covered environments:**

Ollama runs all AI inference locally on the workstation. No data — redacted or otherwise — ever leaves the machine. This eliminates the need for a Business Associate Agreement (BAA), removes any risk of third-party data retention, and ensures full compliance with the HIPAA Security Rule's transmission security requirements by avoiding transmission entirely. The PHI redaction layer still runs as defense in depth, but it is not a required safeguard when using Ollama since no network boundary is crossed.

### Switching Providers

Set `AI_PROVIDER` in `.env` to `openai`, `anthropic`, or `ollama`, or use the **Settings** page in the app. The active provider can be changed at any time without restarting the application.

## Testing

Run tests with:
```bash
pytest -q
```

With coverage:
```bash
pytest --cov=src --cov-report=html
```

## HIPAA Compliance & PHI Handling

This application processes ERA (ANSI 835) files that contain Protected Health Information (PHI) including patient names, member IDs, claim numbers, and dates of service.

### Deployment Model

This application is designed to run locally on a secured, authenticated laptop within the client's office. Operating system-level authentication serves as the access control mechanism. PHI data is processed and stored locally and does not traverse a network under normal operation.

### AI Provider Comparison for HIPAA

| Concern | OpenAI / Anthropic | Ollama (Local) |
|---------|-------------------|----------------|
| PHI leaves the machine | Yes — data sent over the internet | **No** — all inference runs locally |
| BAA required | Yes | **No** — no third party involved |
| PHI redaction | Critical safeguard | Runs as defense in depth, not strictly required |
| API key exposure risk | Keys could be leaked | No API keys used |
| Data retention by provider | Provider may log prompts | **No external retention** |

**Ollama is the recommended AI provider for HIPAA-covered environments.** With Ollama, the entire data pipeline — parsing, AI enhancement, eligibility evaluation, and reporting — runs on the local workstation. No PHI crosses a network boundary at any point.

### PHI Redaction Before AI Calls

When AI enhancement is enabled, **all PHI is automatically redacted before any data reaches the AI provider**, regardless of which provider is selected. The redaction layer (`src/utils/redaction.py`) strips the following from ERA segments:

- **Patient names** (NM1 segments) — replaced with initials only
- **Patient/member IDs** — masked, keeping only the last 4 characters
- **Claim control numbers** (CLP segments) — masked
- **Subscriber/reference IDs** (REF segments) — masked
- **Free-text descriptions** — names and long identifiers are redacted via pattern matching

This ensures that only billing codes (CPT, CAS, RARC), amounts, and structural segment data are used for AI analysis. For cloud providers (OpenAI, Anthropic), this is a critical HIPAA safeguard. For Ollama, it provides defense in depth since data never leaves the machine regardless.

### Data at Rest

- **SQLite database** (`era_idr.db`) stores only billing code reference data (CPT, CAS, RARC codes and descriptions). Patient data is held transiently in Streamlit session state during processing.
- **Log files** (`logs/app.log`) are configured with `diagnose=False` to prevent PHI from leaking into stack traces.
- **Exported reports** (CSV, JSON, HTML, PDF) can optionally be redacted using the "Redact Identifiers in Audit Output" checkbox in the sidebar.

### Recommendations for Operators

1. **Use Ollama for HIPAA compliance**: Select Ollama as the AI provider in Settings. This keeps all data local and eliminates the need for a BAA or third-party risk assessment.
2. **Verify sample files**: Ensure the ERA files in `samples/` do not contain real patient data before pushing to any remote repository.
3. **Enable redaction for exports**: When exporting reports that will leave the secured workstation, enable the "Redact Identifiers" option.
4. **Cloud provider BAA**: If using OpenAI or Anthropic instead of Ollama, confirm that your provider agreement includes a Business Associate Agreement (BAA). Even with redaction in place, a BAA provides an additional legal safeguard.
5. **Disk encryption**: Ensure the workstation has full-disk encryption enabled (e.g., BitLocker on Windows).

## License

See LICENSE file for details.

