from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .explain import summarize
from .extract import extract_text
from .parser import parse_report
from .rag import lookup

DISCLAIMER = ("MediScan AI is an informational tool, not a medical device. It does not diagnose or recommend "
              "treatment. Flags use only the reference ranges printed on your report. Always consult a "
              "qualified doctor about your results.")
MAX_BYTES = 10 * 1024 * 1024
STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="MediScan AI", version="1.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze(file: UploadFile = File(...), use_llm: bool = True):
    data = file.file.read(MAX_BYTES + 1)  # processed in memory only; nothing is written to disk
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 10 MB).")
    try:
        text, meta = extract_text(data, file.filename)
    except ValueError as e:
        raise HTTPException(415, str(e))
    except Exception:
        raise HTTPException(422, "Could not read this file. Try a clearer PDF or image.")

    results = []
    for lv in parse_report(text):
        d = asdict(lv)
        key, g = lookup(lv.name)
        d.update(key=key, title=g["title"] if g else lv.name, category=g["category"] if g else "Other",
                 meaning=g["meaning"] if g else None,
                 context=(g["high"] if lv.status == "HIGH" else g["low"] if lv.status == "LOW" else None) if g else None)
        results.append(d)

    flagged = sorted((r for r in results if r["status"] != "NORMAL"), key=lambda r: -r["deviation_pct"])
    summary, engine = summarize(flagged, len(results), use_llm)
    meta.update(engine=engine, total=len(results), flagged=len(flagged))
    return {"meta": meta, "results": results, "summary": summary, "disclaimer": DISCLAIMER}
