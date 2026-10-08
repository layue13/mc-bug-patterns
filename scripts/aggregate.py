#!/usr/bin/env python3
"""Merge per-repo semgrep JSON outputs into CSV / Markdown / JSONL for human and AI triage.

usage: aggregate.py JSON_DIR [--src CHECKOUTS_DIR]

Reads JSON_DIR/*.json (one per repo, produced by scan-org.sh) and writes next to them:
  findings.csv    flat table
  SUMMARY.md      counts by paradigm / rule / repo
  findings.jsonl  one object per finding with the enclosing method's source and the matching
                  bug.mcmod.cn cases -- this is the input for AI review (see review/README.md)

Finding paths are resolved as-is first, then relative to --src, so both scan modes work.
"""
import argparse, csv, collections, hashlib, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = json.loads((ROOT / "data/mcmod-bug-catalog.json").read_text())
CATS = CATALOG["_categories"]
CASES = {e["id"]: e for e in CATALOG["entries"]}

MAX_METHOD_LINES = 120
FALLBACK_RADIUS = 30
SIG = re.compile(r"^\s*(?:@\w+(?:\([^)]*\))?\s*)*(?:(?:public|protected|private|static|final|abstract|synchronized|default)\s+)*[\w<>\[\],.? ]+\s+\w+\s*\([^;]*$|^\s*(?:public|protected|private)\s+\w+\s*\([^;]*$")
NOT_SIG = re.compile(r"^\s*(if|for|while|switch|catch|else|return|new|throw)\b")


def read_lines(path: pathlib.Path):
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None


def brace_delta(line: str) -> int:
    line = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)   # drop string literals
    line = re.sub(r"//.*$", "", line)
    return line.count("{") - line.count("}")


def enclosing_block(lines, lineno):
    """Heuristic: nearest preceding method signature, brace-matched forward. Returns (start, end) 1-based."""
    i = lineno - 1
    fallback = (max(1, lineno - FALLBACK_RADIUS), min(len(lines), lineno + FALLBACK_RADIUS))
    start = None
    for j in range(i, max(-1, i - 400), -1):
        if SIG.match(lines[j]) and not NOT_SIG.match(lines[j]):
            # signature may wrap lines; the opening brace must appear within a few lines
            if any("{" in lines[k] for k in range(j, min(len(lines), j + 7))):
                start = j
                break
    if start is None:
        return fallback
    depth, seen, end = 0, False, None
    for k in range(start, min(len(lines), start + 600)):
        d = brace_delta(lines[k])
        if d:
            seen = True
        depth += d
        if seen and depth <= 0:
            end = k
            break
    if end is None or end < i:   # unclosed, or the signature found belongs to an earlier, already-closed method
        return fallback
    if end - start + 1 > MAX_METHOD_LINES:
        end = start + MAX_METHOD_LINES - 1
    return start + 1, end + 1


def snippet(path_str: str, lineno: int, src):
    p = pathlib.Path(path_str)
    lines = read_lines(p) if p.is_file() else (read_lines(src / p) if src else None)
    if lines is None:
        return None
    if p.suffix == ".java":
        a, b = enclosing_block(lines, lineno)
    else:
        a, b = max(1, lineno - 5), min(len(lines), lineno + 5)
    body = "\n".join(f"{n:>5}{'>' if n == lineno else ' '}| {lines[n - 1]}" for n in range(a, b + 1))
    return {"start": a, "end": b, "text": body}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_dir")
    ap.add_argument("--src", default=None)
    args = ap.parse_args()
    out = pathlib.Path(args.json_dir)
    src = pathlib.Path(args.src).resolve() if args.src else None

    rows = []
    for f in sorted(out.glob("*.json")):
        repo = f.stem
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError:
            print(f"skip unreadable {f}")
            continue
        for r in data.get("results", []):
            meta = r["extra"].get("metadata", {})
            rule = r["check_id"].split(".")[-1]
            fid = hashlib.sha1(f"{repo}|{rule}|{r['path']}|{r['start']['line']}".encode()).hexdigest()[:10]
            cases = [CASES[c] for c in meta.get("cases", []) if c in CASES]
            rows.append({
                "id": fid, "repo": repo, "rule": rule,
                "pattern": meta.get("pattern", "?"), "confidence": meta.get("confidence", "?"),
                "severity": r["extra"]["severity"], "message": " ".join(r["extra"]["message"].split()),
                "file": r["path"], "line": r["start"]["line"],
                "cases": [{k: c[k] for k in ("id", "name", "level", "url", "summary")} for c in cases],
                "code": snippet(r["path"], r["start"]["line"], src),
            })

    with open(out / "findings.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "repo", "rule", "pattern", "confidence", "severity", "file", "line", "cases"])
        for r in rows:
            w.writerow([r["id"], r["repo"], r["rule"], r["pattern"], r["confidence"], r["severity"], r["file"], r["line"],
                        " ".join(str(c["id"]) for c in r["cases"])])

    with open(out / "findings.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

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
    no_code = sum(1 for r in rows if r["code"] is None)
    print(f"{len(rows)} findings ({no_code} without source context) -> {out}/findings.csv, findings.jsonl, SUMMARY.md")


if __name__ == "__main__":
    main()
