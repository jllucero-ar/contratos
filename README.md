# Legal Contract Analyzer

Automated contract analysis pipeline using AI. Extracts text from PDF contracts, sends it to an AI model, and generates a structured JSON analysis and a formatted PDF report.

Built as part of a legal engineering portfolio.

---

## What it does

1. **Extracts text** from any PDF contract (digital or scanned)
2. **Analyzes** the contract using an AI model (Claude, Gemini, or OpenAI)
3. **Outputs** a structured JSON file and a formatted PDF report

The analysis covers:
- Parties and identification (name, tax ID)
- Object and purpose
- Term and renewal conditions
- Price and adjustment mechanisms
- Key clauses: early termination, late payment penalties, liability limits, jurisdiction, notifications
- Detected risks
- Executive summary

---

## Stack

- **Python 3.10+**
- **pdfplumber** — text extraction from digital PDFs
- **pytesseract + pdf2image** — OCR fallback for scanned PDFs
- **Anthropic / OpenAI / Google Gemini** — AI analysis (configurable via `.env`)
- **reportlab** — PDF report generation

---

## Project structure

```
CONTRATOS/
├── core/
│   ├── extractor.py       # PDF text extraction (pdfplumber + OCR fallback)
│   ├── ia_client.py       # Unified AI client (Claude / OpenAI / Gemini)
│   └── pdf_report.py      # PDF report generator
├── contratos/
│   └── analizador.py      # Contract-specific prompt and JSON schema
├── data/
│   └── test/              # Sample contracts for testing
├── main.py                # Entry point
└── .env                   # API keys and provider config (not committed)
```

---

## Installation

```bash
pip install -r requirements.txt
```

For OCR support, Tesseract must be installed on the system:
- Windows: [tesseract-ocr installer](https://github.com/tesseract-ocr/tesseract)
- Linux: `sudo apt install tesseract-ocr tesseract-ocr-spa`
- Mac: `brew install tesseract`

---

## Configuration

Copy `.env.example` to `.env` and set your preferred AI provider and API key:

```
IA_PROVEEDOR=anthropic
ANTHROPIC_API_KEY=your-key-here
```

Supported providers: `anthropic`, `openai`, `gemini`

---

## Usage

**Single contract:**
```bash
python main.py data/test/contrato.pdf
```

**Multiple contracts:**
```bash
python main.py data/test/contrato1.pdf data/test/contrato2.pdf
```

Output files are saved automatically to `data/json/` and `data/pdf/`.

---

## Why this project

Contract review is one of the most time-consuming tasks in legal practice. This tool demonstrates how AI can be integrated into a legal workflow to extract structured information from unstructured documents — reducing review time and enabling downstream automation.

The modular architecture (`core/`) is designed to be reused across different document types: contracts, court rulings, regulatory filings, and more.

---

## Author

**José Luis Lucero**  
Lawyer (UBA) | Legal Engineer  
Buenos Aires, Argentina  
[LinkedIn](https://www.linkedin.com/in/jose-luis-l-b452a873)

---

*This tool was built for portfolio and demonstration purposes. AI-generated analysis does not replace professional legal advice.*
