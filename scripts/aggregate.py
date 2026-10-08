#!/usr/bin/env python3
"""Merge per-repo semgrep JSON outputs into one CSV + a Markdown summary grouped by paradigm.

usage: aggregate.py OUT_DIR   (reads OUT_DIR/*.json produced by scan-org.sh, writes findings.csv and SUMMARY.md)
"""
import csv, json, sys, collections, pathlib

CATS = json.loads((pathlib.Path(__file__).parent.parent / "data/mcmod-bug-catalog.json").read_text())["_categories"]
out = pathlib.Path(sys.argv[1])
rows = []
for f in sorted(out.glob("*.json")):
    repo = f.stem
    try:
        data = json.loads(f.read_text())
    except json.JSONDecodeError:
        print(f"skip unreadable {f}", file=sys.stderr)
        continue
    for r in data.get("results", []):
        meta = r["extra"].get("metadata", {})
        rows.append({
            "repo": repo,
            "rule": r["check_id"].split(".")[-1],
            "pattern": meta.get("pattern", "?"),
            "confidence": meta.get("confidence", "?"),
            "severity": r["extra"]["severity"],
            "file": r["path"],
            "line": r["start"]["line"],
            "cases": " ".join(map(str, meta.get("cases", []))),
        })

with open(out / "findings.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["repo", "rule", "pattern", "confidence", "severity", "file", "line", "cases"])
    w.writeheader()
    w.writerows(rows)

by_pat = collections.Counter(r["pattern"] for r in rows)
by_rule = collections.Counter((r["pattern"], r["rule"], r["confidence"]) for r in rows)
by_repo = collections.Counter(r["repo"] for r in rows)
with open(out / "SUMMARY.md", "w") as fh:
    fh.write(f"# Scan summary\n\n{len(rows)} findings in {len(by_repo)} repos.\n\n## By paradigm\n\n| paradigm | meaning | findings |\n|---|---|---|\n")
    for p, n in sorted(by_pat.items()):
        fh.write(f"| {p} | {CATS.get(p, '')} | {n} |\n")
    fh.write("\n## By rule\n\n| paradigm | rule | confidence | findings |\n|---|---|---|---|\n")
    for (p, rule, conf), n in sorted(by_rule.items(), key=lambda kv: (kv[0][0], -kv[1])):
        fh.write(f"| {p} | {rule} | {conf} | {n} |\n")
    fh.write("\n## Top repos\n\n| repo | findings |\n|---|---|\n")
    for repo, n in by_repo.most_common(20):
        fh.write(f"| {repo} | {n} |\n")
print(f"{len(rows)} findings -> {out}/findings.csv, {out}/SUMMARY.md")
