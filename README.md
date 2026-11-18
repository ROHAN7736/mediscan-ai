# MediScan AI: Medical Report Intelligence
![MediScan AI demo](screenshots/demo.png)
![MediScan AI demo](screenshots/demo1.png)
![MediScan AI demo](screenshots/demo2.png)
Upload a lab report (PDF / scan / image) and get structured values, out-of-range flags and a plain-language summary.
**Informational only. Not a diagnostic system.**

## Why it's built this way
| Design decision | Reason |
|---|---|
| **Deterministic parser** extracts values and ranges (regex), the LLM never sees raw numbers to "guess" | Accuracy and auditability in a medical context |
| **Source line shown for every value** | User can verify extraction against the original report |
| **Flags use only the range printed on the report** | Labs differ; no invented thresholds |
| **RAG over a curated glossary** (alias + fuzzy retrieval) | Explanations are grounded, not hallucinated |
| **Local LLM via Ollama** | Free, and medical data never leaves the machine |
| **Output safety guard** | Replies that sound like a diagnosis or prescription are rejected and replaced with rule-based text |
| **In-memory processing, no storage** | Privacy by design |
| **OCR fallback per page** | Handles scanned reports and photos |

## Run
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# OCR engine: Ubuntu `sudo apt install tesseract-ocr` | macOS `brew install tesseract` | Windows: UB-Mannheim installer
ollama pull llama3.1:8b          # optional but recommended (set OLLAMA_MODEL to change)
uvicorn app.main:app --reload    # open http://localhost:8000
```
No Ollama? The app still works with built-in glossary explanations. Docker: `docker build -t mediscan . && docker run -p 8000:8000 mediscan`.

## API
`POST /api/analyze?use_llm=true` (multipart `file`) returns `{meta, results[], summary, disclaimer}`. Docs at `/docs`.

## Test
`pytest -q` covers parsing of ranges (`a-b`, `<x`, `>x`, `up to x`), thousands separators, glued units, and glossary matching.

## Known limitations
- Only lines that contain a numeric reference range are parsed (qualitative results like "Negative" are skipped).
- OCR quality depends on scan quality; always verify against the source line shown.
- Glossary covers ~35 common tests. Extend `app/glossary.json` to add more.

## Roadmap
Add a labelled accuracy benchmark, multi-language reports, trend comparison across reports, embedding-based retrieval.
