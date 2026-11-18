"""Deterministic lab-value parser. No LLM: numbers and ranges come straight from the text."""
import re
from dataclasses import dataclass

NUM = r"\d+(?:\.\d+)?"
DASH = r"(?:-|–|—|to)"

RANGE_RE = re.compile(
    rf"(?:(?P<lo>{NUM})\s*{DASH}\s*(?P<hi>{NUM})"
    rf"|(?P<lt>[<≤])=?\s*(?P<ltv>{NUM})"
    rf"|(?P<gt>[>≥])=?\s*(?P<gtv>{NUM})"
    rf"|(?:up\s*to|upto|upper\s*limit)\s*(?P<upv>{NUM}))"
    r"(?:\s+[A-Za-zµμ%][\w/%^µμ.]*)?\s*$", re.I)

ROW_RE = re.compile(
    rf"^(?P<name>[A-Za-z][A-Za-z0-9 ()/%,.'\-]*?)\s*:?\s+(?:[HL]\s+)?(?P<value>{NUM})"
    r"(?:\s+(?P<unit>\S+?))?(?:\s+(?:H|L|HIGH|LOW|High|Low|\*+))?\s*$")

NOISE = re.compile(r"(?i)\b(page|date|age|phone|mobile|collected|reported|registered|barcode|"
                   r"sample|patient|doctor|uhid|sex|years?|lab\s*no)\b")
FLAGS = {"H", "L", "HIGH", "LOW", "High", "Low"}


@dataclass
class LabValue:
    name: str
    value: float
    unit: str | None
    ref_low: float | None
    ref_high: float | None
    ref_text: str
    status: str            # LOW | HIGH | NORMAL
    deviation_pct: float   # distance outside the printed range, in %
    source_line: str


def _clean(line: str) -> str:
    line = re.sub(r"(?<=\d),(?=\d{3}\b)", "", line)                      # 12,500 -> 12500
    line = re.sub(rf"\(\s*({NUM}\s*{DASH}\s*{NUM})\s*\)", r"\1", line)    # (70-100) -> 70-100
    line = re.sub(r"(?<=\s)(\d+(?:\.\d+)?)(?=[A-Za-z%µμ])", r"\1 ", line)  # 11.2g/dL -> 11.2 g/dL
    return re.sub(r"\s+", " ", line).strip()


def classify(v, lo, hi, lo_strict=False, hi_strict=False):
    if lo is not None and (v < lo or (lo_strict and v == lo)):
        return "LOW"
    if hi is not None and (v > hi or (hi_strict and v == hi)):
        return "HIGH"
    return "NORMAL"


def parse_line(raw: str) -> LabValue | None:
    line = _clean(raw)
    m = RANGE_RE.search(line)
    if not m:
        return None
    lo = hi = None
    lo_s = hi_s = False
    if m["lo"] is not None:
        lo, hi = float(m["lo"]), float(m["hi"])
        if lo > hi:
            return None
    elif m["ltv"] is not None:
        hi, hi_s = float(m["ltv"]), True
    elif m["gtv"] is not None:
        lo, lo_s = float(m["gtv"]), True
    else:
        hi = float(m["upv"])
    head = line[: m.start()].strip()
    head = re.sub(r"(?i)[\s:\-]*(ref(erence)?\.?(\s*range)?|normal|range)\s*[:\-]?\s*$", "", head)
    r = ROW_RE.match(head)
    if not r:
        return None
    name = re.sub(r"\s+", " ", r["name"]).strip(" :-.,")
    if len(name) < 2 or len(name) > 60 or NOISE.search(name):
        return None
    unit = r["unit"]
    if unit in FLAGS:
        unit = None
    v = float(r["value"])
    status = classify(v, lo, hi, lo_s, hi_s)
    dev = 0.0
    if status == "LOW" and lo:
        dev = (lo - v) / lo * 100
    elif status == "HIGH" and hi:
        dev = (v - hi) / hi * 100
    return LabValue(name, v, unit, lo, hi, m.group(0).strip(), status, round(dev, 1), raw.strip())


def parse_report(text: str) -> list[LabValue]:
    seen, out = set(), []
    for line in text.splitlines():
        lv = parse_line(line)
        if lv and (lv.name.lower(), lv.value) not in seen:
            seen.add((lv.name.lower(), lv.value))
            out.append(lv)
    return out
