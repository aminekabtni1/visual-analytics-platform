import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

def test_cleaning_report_exists():
    import json, pathlib
    p = pathlib.Path("data/processed/cleaning_report.json")
    assert p.exists(), "cleaning_report.json missing — run data/load_data.py"
    data = json.loads(p.read_text())
    assert "counts" in data and "cleaning_decisions" in data
    assert data["counts"]["clean_rows"] > 0
    assert data["counts"]["n_transactions"] > 5000
