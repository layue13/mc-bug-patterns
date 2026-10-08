"""python3 tests/test_validate_triage.py -- validator accepts good verdicts, rejects hallucinated evidence."""
import json, pathlib, subprocess, sys, tempfile

root = pathlib.Path(__file__).parent.parent
d = pathlib.Path(tempfile.mkdtemp())
(d / "A.java").write_text("class A {\n  int f(boolean simulate) {\n    return 1;\n  }\n}\n")
(d / "findings.jsonl").write_text(json.dumps({"id": "f1"}) + "\n" + json.dumps({"id": "f2"}) + "\n")

def run(rows):
    (d / "t.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    p = subprocess.run([sys.executable, str(root / "scripts/validate_triage.py"), str(d / "findings.jsonl"), str(d / "t.jsonl")], capture_output=True, text=True)
    return p.returncode, p.stdout

good = {"finding_id": "f1", "verdict": "confirmed", "confidence": "high", "reasoning": "r", "trigger_path": "hopper",
        "evidence": [{"file": str(d / "A.java"), "line": 2, "quote": "int f(boolean simulate)"}]}
bad_quote = {**good, "finding_id": "f2", "evidence": [{"file": str(d / "A.java"), "line": 3, "quote": "this text is not in the file"}]}
checks = [
    ("accepts a grounded verdict", run([good])[0] == 0),
    ("rejects a hallucinated quote", run([good, bad_quote])[0] == 1),
    ("rejects confirmed without trigger_path", run([{k: v for k, v in good.items() if k != "trigger_path"}])[0] == 1),
    ("rejects duplicate verdicts", run([good, good])[0] == 1),
    ("rejects unknown finding_id", run([{**good, "finding_id": "zzz"}])[0] == 1),
]
for n, c in checks:
    print(("ok   " if c else "FAIL ") + n)
sys.exit(0 if all(c for _, c in checks) else 1)
