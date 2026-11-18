"""Plain-language explanations. Local Ollama (free, private) with a safe rule-based fallback."""
import os
import re

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

SYSTEM = (
    "You are a patient-education assistant that explains lab report values in simple language. "
    "Rules: NEVER diagnose; never state or imply the reader has a disease; never recommend medicines, "
    "doses or treatments. Use phrases like 'can be associated with' and 'your doctor can tell you'. "
    "Use ONLY the data and background provided. Max 220 words. Plain text, no markdown symbols. "
    "Structure: 'Overview' (2-3 sentences), 'What stands out' (one short line per flagged value, start with a dash), "
    "'Questions to ask your doctor' (3 dash lines)."
)

# Output guard: reject anything that sounds like a diagnosis or prescription.
UNSAFE = re.compile(
    r"(?i)\byou (likely |probably )?(have|suffer from|are suffering from)\b|\bdiagnosed with\b|"
    r"\byou are (anaemic|anemic|diabetic)\b|\b(take|start taking|prescribe[d]?)\b.{0,20}\b(mg|tablet|pill|medication)\b")


def rule_based(flagged: list[dict]) -> str:
    if not flagged:
        return ("Overview\nAll detected values fall inside the reference ranges printed on your report. "
                "Normal ranges can differ between labs, so your doctor's reading is what counts.")
    lines = [f"Overview\n{len(flagged)} detected value(s) fall outside the range printed on your report.\n\nWhat stands out"]
    for r in flagged:
        way = "above" if r["status"] == "HIGH" else "below"
        extra = f" {r['context']}" if r.get("context") else ""
        lines.append(f"- {r['title']}: {r['value']:g} {r.get('unit') or ''} is {way} the range ({r['ref_text']}). "
                     f"{r.get('meaning') or ''}{extra}".replace("  ", " ").strip())
    lines.append("\nQuestions to ask your doctor\n- What could explain these results for me?\n"
                 "- Do any of them need a repeat test or follow-up?\n- Does my diet, medication or lifestyle matter here?")
    return "\n".join(lines)


def summarize(flagged: list[dict], total: int, use_llm: bool = True):
    if not use_llm or not flagged:
        return rule_based(flagged), "rule-based"
    ctx = "\n".join(
        f"- {r['title']}: {r['value']:g} {r.get('unit') or ''} ({r['status']}, printed range {r['ref_text']}). "
        f"Background: {r.get('meaning') or 'n/a'} {r.get('context') or ''}" for r in flagged)
    prompt = f"{total} values were read; {len(flagged)} are outside the printed range:\n{ctx}"
    try:
        resp = httpx.post(f"{OLLAMA_URL}/api/chat", timeout=120, json={
            "model": MODEL, "stream": False, "options": {"temperature": 0.2},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]})
        resp.raise_for_status()
        text = resp.json()["message"]["content"].strip()
        if text and not UNSAFE.search(text):
            return text, f"ollama:{MODEL}"
    except Exception:
        pass
    return rule_based(flagged), "rule-based (LLM unavailable)"
