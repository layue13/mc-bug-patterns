#!/usr/bin/env python3
"""Validate AI triage output against review/triage.schema.json and the scan results.

usage: validate_triage.py FINDINGS_JSONL TRIAGE_JSONL [--src CHECKOUTS_DIR]

Checks (no third-party deps):
  * every line is valid JSON matching the schema's required/enum/type rules
  * finding_id exists in FINDINGS_JSONL, and no finding is judged twice
  * confirmed  -> trigger_path present;  needs_human -> needs present
  * every evidence quote really occurs in the cited file (when the file can be found) -- this catches
    hallucinated evidence, the main failure mode of LLM review
Exit code 1 if anything is invalid. Prints which findings are still untriaged.
"""
import argparse, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "review/triage.schema.json").read_text())


def norm(s: str) -> str:
    return " ".join(s.split())


def validate_one(t, known, seen, src):
    errs = []
    for k in SCHEMA["required"]:
        if k not in t:
            errs.append(f"missing '{k}'")
    for k in t:
        if k not in SCHEMA["properties"]:
            errs.append(f"unknown field '{k}'")
    if errs:
        return errs
    if t["verdict"] not in SCHEMA["properties"]["verdict"]["enum"]:
        errs.append(f"bad verdict {t['verdict']!r}")
    if t["confidence"] not in SCHEMA["properties"]["confidence"]["enum"]:
        errs.append(f"bad confidence {t['confidence']!r}")
    fid = t["finding_id"]
    if fid not in known:
        errs.append(f"unknown finding_id {fid}")
    if fid in seen:
        errs.append(f"duplicate verdict for {fid}")
    if t["verdict"] == "confirmed" and not t.get("trigger_path"):
        errs.append("confirmed requires trigger_path")
    if t["verdict"] == "needs_human" and not t.get("needs"):
        errs.append("needs_human requires needs")
    if not isinstance(t["evidence"], list) or not t["evidence"]:
        errs.append("evidence must be a non-empty list")
        return errs
    for i, ev in enumerate(t["evidence"]):
        if not isinstance(ev, dict) or set(ev) != {"file", "line", "quote"} or not isinstance(ev["line"], int) or ev["line"] < 1 or not str(ev["quote"]).strip():
            errs.append(f"evidence[{i}] malformed")
            continue
        p = pathlib.Path(ev["file"])
        if not p.is_file() and src:
            p = src / p
        if p.is_file():
            if norm(ev["quote"]) not in norm(p.read_text(encoding="utf-8", errors="replace")):
                errs.append(f"evidence[{i}] quote not found in {ev['file']} (hallucinated?)")
        else:
            errs.append(f"evidence[{i}] file not found: {ev['file']}")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("findings")
    ap.add_argument("triage")
    ap.add_argument("--src", default=None)
    a = ap.parse_args()
    src = pathlib.Path(a.src).resolve() if a.src else None
    known = {json.loads(l)["id"] for l in open(a.findings) if l.strip()}
    seen, bad = set(), 0
    counts = {}
    for n, line in enumerate(open(a.triage), 1):
        if not line.strip():
            continue
        try:
            t = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"line {n}: invalid JSON ({e})"); bad += 1; continue
        errs = validate_one(t, known, seen, src)
        if errs:
            bad += 1
            print(f"line {n} ({t.get('finding_id', '?')}): " + "; ".join(errs))
        else:
            seen.add(t["finding_id"])
            counts[t["verdict"]] = counts.get(t["verdict"], 0) + 1
    todo = known - seen
    print(f"valid: {sum(counts.values())}  invalid: {bad}  untriaged: {len(todo)}  verdicts: {counts}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
