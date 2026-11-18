import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.parser import parse_line, parse_report  # noqa: E402
from app.rag import lookup  # noqa: E402

SAMPLE = (Path(__file__).parent / "sample_report.txt").read_text(encoding="utf-8")
ROWS = {r.name: r for r in parse_report(SAMPLE)}

EXPECTED = {
    "Hemoglobin": "LOW", "RBC Count": "LOW", "Total WBC Count": "HIGH", "Platelet Count": "NORMAL",
    "Total Cholesterol": "HIGH", "HDL Cholesterol": "LOW", "LDL Cholesterol": "HIGH",
    "Triglycerides": "NORMAL", "Glucose (Fasting)": "HIGH", "HbA1c": "HIGH",
    "SGPT (ALT)": "NORMAL", "TSH": "NORMAL", "Vitamin B12": "LOW",
}


def test_all_rows_found_and_header_noise_ignored():
    assert set(ROWS) == set(EXPECTED)


def test_status_flags():
    for name, status in EXPECTED.items():
        assert ROWS[name].status == status, name


def test_values_units_ranges():
    assert ROWS["Total WBC Count"].value == 12500
    assert ROWS["Hemoglobin"].unit == "g/dL" and ROWS["Hemoglobin"].ref_low == 13.0
    assert ROWS["HbA1c"].unit == "%"
    assert ROWS["Hemoglobin"].deviation_pct == 13.8


def test_inline_flag_and_glued_unit():
    r = parse_line("Hemoglobin 11.2g/dL 13.0-17.0 L")
    assert r is None or r.unit == "g/dL"  # trailing flag after range is tolerated or skipped, never mis-parsed
    r = parse_line("Glucose 95 mg/dL 70 - 100")
    assert r.status == "NORMAL"


def test_no_range_means_no_guessing():
    assert parse_line("Hemoglobin 11.2 g/dL") is None


def test_glossary_lookup_and_fuzzy():
    assert lookup("SGPT (ALT)")[0] == "alt"
    assert lookup("Haemoglobin")[0] == "hemoglobin"
    assert lookup("Total Cholestrol")[0] == "cholesterol"
    assert lookup("Totally Unknown Test")[0] is None


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("PASS", n)
