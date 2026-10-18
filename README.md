# Legal Contract Analyzer

Automated contract analysis pipeline using AI. Extracts text from PDF contracts, sends it to an AI model, and generates a structured JSON analysis and a formatted PDF report.

Built as part of a legal engineering portfolio.

---

## What it does

1. **Extracts text** from any PDF contract (digital or scanned)
2. **Analyzes** the contract using an AI model (Claude, Gemini, or OpenAI)
3. **Outputs** a structured JSON file and a formatted PDF report

The analysis covers:
- Parties and identification (`parte_a` / `parte_b`: name, tax ID, role — works for any contract type; A and B follow the order in which the parties appear in the contract header, the role field says who is who)
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
│   ├── ia_client.py       # Unified AI client (Claude / OpenAI / Gemini), truncation + token usage
│   ├── anonimizador.py    # Reversible masking of DNI / CUIT / CUIL / email / phone
│   ├── controles.py       # Deterministic checks (CCyCN citation verification)
│   ├── audit_log.py       # JSONL audit log (no contract text, no personal data)
│   └── pdf_report.py      # PDF report generator
├── contratos/
│   ├── analizador.py      # Pipeline, prompt and PROMPT_VERSION
│   └── esquema.py         # Pydantic output schema
├── evaluacion/            # Golden set, comparator and evaluation runner
├── tests/                 # pytest suite (all AI calls are mocked)
├── data/                  # git-ignored: test/, json/, pdf/, logs/
├── main.py                # Entry point
└── .env                   # API keys and provider config (not committed)
```

---

## Installation

```bash
pip install -r requirements.txt
```

For OCR support (scanned PDFs), two system dependencies are required in addition to the Python packages. Both must be available on your `PATH`:

**Tesseract** (OCR engine, with the Spanish language pack `spa`):
- Windows: [tesseract-ocr installer](https://github.com/UB-Mannheim/tesseract/wiki) (select Spanish during setup)
- Linux: `sudo apt install tesseract-ocr tesseract-ocr-spa`
- Mac: `brew install tesseract tesseract-lang`

**Poppler** (used by `pdf2image` to convert PDF pages to images):
- Windows: download the [Poppler binaries](https://github.com/oschwartz10612/poppler-windows/releases), extract them and add the `Library\bin` folder to your `PATH`
- Linux: `sudo apt install poppler-utils`
- Mac: `brew install poppler`

---

## Configuration

Copy `.env.example` to `.env` and set your preferred AI provider and API key:

```
IA_PROVEEDOR=anthropic
ANTHROPIC_API_KEY=your-key-here
```

Supported providers: `anthropic`, `openai`, `gemini`

`IA_MAX_TOKENS` (default `8000`) sets the output token limit. If a response is cut off by that limit the run fails with a specific "truncated" error instead of returning broken JSON.

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

## Governance controls

The model is probabilistic; these controls around it are deterministic and auditable. Each one is small on purpose and states what it does **not** guarantee.

| Control | What it does | Why it exists |
|---|---|---|
| **Schema validation** (`contratos/esquema.py`) | The model output is validated against a Pydantic schema (all keys required, unknown keys rejected, `null` allowed for missing data). On failure it retries **once**, sending the model the validation errors (paths and messages only, never the offending values). A second failure returns a clear error. | A "valid-looking" answer can silently miss fields or invent new ones. Downstream code (PDF, automation) needs a contract it can trust. |
| **Truncation detection** (`core/ia_client.py`) | Reads `stop_reason` (Anthropic), `finish_reason` (OpenAI) and the Gemini finish reason. A response cut by the token limit is reported as its own error and is not retried. | A truncated JSON is the most common cause of confusing "invalid JSON" failures; naming it makes it fixable (`IA_MAX_TOKENS`). |
| **Citation check** (`core/controles.py`) | Extracts every CCyCN article citation from the output and flags those outside **1–2671** or with an unrecognizable format (`art. XX`, `art. 1198 bis`). Citations to other statutes (e.g. Ley 24.240) are counted but not validated. Result goes in the `controles` block. | The prompt requires legal grounding, and models fabricate article numbers. A range check catches the impossible ones cheaply. It **informs, it does not block**. |
| **Literal check** (`core/controles.py`) | Checks that the values meant to be copied from the contract (party names, tax IDs, start/end dates, term, initial price, payment date) actually appear in the source text. Numbers are compared ignoring formatting (`$250.000` = `250000`), names ignoring case and accents. Anything not found is listed in `controles.literalidad`. | Catches invented or altered values (a wrong amount, a made-up company). Free-text fields (object, clauses, risks) are paraphrases and are not checked. |
| **Anonymization** (`core/anonimizador.py`) | Before calling the provider, DNI, CUIT, CUIL, emails and phones are replaced by markers (`[DNI_1]`, `[CUIT_1]`, ...). The marker→value map exists only in memory for that run and the real values are restored in the final JSON. The result reports how many distinct values of each type were masked and whether any marker was left unrestored. | Data minimization: the provider does not need identifiers to analyze clauses. |
| **Audit log** (`core/audit_log.py`) | One JSONL line per run in `data/logs/analisis_YYYYMMDD.jsonl`: timestamp, provider, model, `PROMPT_VERSION`, SHA-256 of the PDF, token counts, attempts, result of each control, success or error code. Failed runs are logged too. | Reproducibility and traceability: you can tell which prompt version, model and input produced a given result, and compare behavior across versions. |

`PROMPT_VERSION` (in `contratos/analizador.py`) must be bumped whenever the system prompt, the schema or the prompt builder changes.

### What these controls do NOT do

- **Citation check verifies existence and format only.** An article number inside 1–2671 passes even if that article says nothing relevant to the claim. Content accuracy still needs a human (or a separate evaluation step).
- **Anonymization covers five identifier types only.** Names, addresses, amounts and any other contract text are still sent to the provider. Detection is regex-based and deliberately conservative (phones need a label, `+54` or an area code starting with `0`; DNI needs a label), so unusual formats can slip through.
- **The audit log never stores contract text or personal data**, only the PDF hash, counters and error *codes* (never free-form error messages, which may echo contract fragments). `data/` is git-ignored.
- **Literal check finds what is absent, not what is misread.** A real amount attached to the wrong concept passes. It can also raise false alarms when the contract spells a number out ("diez días") or the model derives it (e.g. a term computed from dates). Numbers with a single digit are skipped. It reports; it does not block.
- Schema validation checks structure, not truth.

### Example output (fictitious data)

```json
{
  "partes": {
    "parte_a": {"nombre": "Inversiones del Sur S.A.", "identificacion": "CUIT 30-71234567-8", "rol": "locador"},
    "parte_b": {"nombre": "María Ejemplo", "identificacion": "DNI 12.345.678", "rol": "locatario"}
  },
  "objeto": "Locación de un local comercial.",
  "plazo": {
    "inicio": "1 de abril de 2025",
    "vencimiento": "31 de marzo de 2028",
    "duracion": "36 meses",
    "observaciones": null
  },
  "canon": {
    "monto_inicial": "$250.000 mensuales",
    "ajuste": "Trimestral por IPC",
    "vencimiento_pago": "Primeros 5 días hábiles"
  },
  "clausulas": {
    "rescision": "Preaviso de 60 días.",
    "mora": "Mora automática.",
    "limitacion_responsabilidad": null,
    "jurisdiccion": "Tribunales ordinarios de CABA.",
    "notificaciones": "Carta documento. Contacto: maria@ejemplo.example"
  },
  "riesgos": [
    "La mora automática sin interpelación contradice la regla general (art. 886 CCyCN).",
    "Cláusula de actualización cuestionable (art. 9999 CCyCN)."
  ],
  "observaciones_generales": "Locación comercial estándar con ajuste por IPC (art. 1187 CCyCN).",
  "controles": {
    "citas_ccycn": {
      "encontradas": ["886", "9999", "1187"],
      "invalidas": [{"cita": "9999", "motivo": "fuera_de_rango"}],
      "otras_normas_no_verificadas": 0,
      "paso": false
    },
    "literalidad": {
      "verificados": 7,
      "no_verificables": 2,
      "no_encontrados": [],
      "paso": true
    },
    "paso": false
  },
  "anonimizacion": {
    "por_tipo": {"EMAIL": 1, "CUIT": 1, "DNI": 1},
    "total": 3,
    "marcadores_sin_restaurar": 0
  }
}
```

And the matching audit log line:

```json
{"timestamp": "2026-10-17T17:22:11+00:00", "proveedor": "anthropic", "modelo": "claude-opus-4-5", "prompt_version": "2.0", "pdf_sha256": "46fbda2b...a280b28", "tokens": {"entrada": 1850, "salida": 420}, "intentos": 1, "controles": {"esquema_valido": true, "respuesta_completa": true, "citas_ccycn": {"paso": false, "encontradas": 3, "invalidas": 1}, "literalidad": {"paso": true, "verificados": 7, "no_encontrados": 0}, "anonimizacion": {"por_tipo": {"EMAIL": 1, "CUIT": 1, "DNI": 1}, "total": 3, "marcadores_sin_restaurar": 0}}, "exito": true, "error_codigo": null}
```

### Tests

```bash
pip install -r requirements-dev.txt
pytest
```

No test calls a real API: the provider SDKs and the analyzer's AI call are mocked, and all sample data is fictitious.

---

## Evaluation

`evaluacion/` measures whether the analysis is *correct*, not just well-formed.

- **Golden set** (`evaluacion/golden/`): 5 fictitious contracts (PDF + source text + hand-annotated expectations), each with a deliberate trap: fields the contract does not state (must stay `null`), amounts and terms written in words, two dates or two identical amounts with different meaning, and an incomplete framework contract. `parte_a`/`parte_b` follow the order of appearance in the contract header.
- **Expectations** per field: `nulo`, `permite_nulo`, `contiene`, `no_contiene`, `alguno`. Matching ignores case and accents and tolerates number formatting (`$400.000` = `400000`).
- **Runner:** `python evaluacion/evaluar.py [--casos lc01,sv02]` runs the analyzer on the set (this **calls the real provider API and consumes tokens**) and writes `evaluacion/reportes/eval_<timestamp>_<provider>-<model>_p<PROMPT_VERSION>.{json,md}`.
- **Compare runs:** `python evaluacion/evaluar.py --comparar evaluacion/reportes/*.json` prints a table across providers, models and prompt versions (no API calls).

Metrics: field accuracy, null-respect rate (how often the model refuses to invent what the contract does not say), invalid CCyCN citation rate, values not found in the source text, retries, errors and tokens.

Limits: five contracts are a smoke test, not a benchmark; `contiene` checks key facts, not full-sentence quality; results vary between runs of the same model.

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
