"""Tiny RAG layer: retrieve curated glossary context for each test (aliases + fuzzy match)."""
import difflib
import json
import re
from pathlib import Path

GLOSSARY = json.loads(Path(__file__).with_name("glossary.json").read_text(encoding="utf-8"))


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


_INDEX = {norm(a): k for k, e in GLOSSARY.items() for a in [k, e["title"], *e.get("aliases", [])]}


def lookup(name: str):
    n = norm(name)
    k = _INDEX.get(n)
    if not k:
        m = difflib.get_close_matches(n, _INDEX, n=1, cutoff=0.84)
        k = _INDEX[m[0]] if m else None
    return (k, GLOSSARY[k]) if k else (None, None)
