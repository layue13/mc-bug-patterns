#!/usr/bin/env python3
"""Run the Semgrep rules against real fix commits and report which rules react to the fix.

usage: run_benchmark.py --repo local=PATH [--repo local=PATH ...] [--cases benchmark/cases.json]
                        [--rules semgrep/rules] [--out benchmark/out] [--limit N]

For each case it materialises the changed .java files at <commit>^ (before) and <commit> (after),
runs semgrep on both, and compares hit counts per (rule, file):

  fixed-signal  hits(before) > hits(after)   the rule flagged what the commit changed
  persistent    hits(before) == hits(after) > 0   the rule fires but is unaffected by the fix (noise or unrelated)
  introduced    hits(after) > hits(before)   rule fires only after the fix (noise)
  silent        no hits in either version     the bug class is not covered by any rule

Only fix-signal is evidence the rule is aimed at a real bug. Nothing here proves precision on whole
repositories; it measures how the rules behave on the files that real bug fixes touched.
"""
import argparse, collections, json, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def git_show(repo, rev, path):
    p = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True)
    return p.stdout if p.returncode == 0 else None


def semgrep(rules, target):
    cmd = ["semgrep", "scan", "--json", "--quiet", "--metrics", "off", "--no-git-ignore", "--config", str(rules / "mc-java.yml"), str(target)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(p.stdout)["results"]
    except (json.JSONDecodeError, KeyError):
        print("semgrep failed:", p.stderr[-300:], file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", action="append", default=[], help="local_name=path_to_clone")
    ap.add_argument("--cases", default=str(ROOT / "benchmark/cases.json"))
    ap.add_argument("--rules", default=str(ROOT / "semgrep/rules"))
    ap.add_argument("--out", default=str(ROOT / "benchmark/out"))
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    repos = dict(r.split("=", 1) for r in a.repo)
    rules = pathlib.Path(a.rules)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = json.load(open(a.cases))["cases"]
    if a.limit:
        cases = cases[: a.limit]

    results, skipped, mat = [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for c in cases:
            repo = repos.get(c["local"])
            if not repo:
                skipped.append((c["id"], "no --repo for " + c["local"]))
                continue
            n = {"before": 0, "after": 0}
            for side, rev in (("before", c["commit"] + "^"), ("after", c["commit"])):
                for f in c["files"]:
                    data = git_show(repo, rev, f)
                    if data is None:
                        continue
                    dst = tmp / c["id"] / side / f
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(data)
                    n[side] += 1
            if n["before"] == 0:
                skipped.append((c["id"], "parent revision/files unavailable (shallow history?)"))
                continue
            mat.append((c, n))
        findings = semgrep(rules, tmp)           # one semgrep run for every case
        if findings is None:
            sys.exit("semgrep failed")
        cnt_by_case = collections.defaultdict(collections.Counter)
        for r in findings:
            rel = pathlib.Path(r["path"]).relative_to(tmp)
            case_id, side, f = rel.parts[0], rel.parts[1], str(pathlib.Path(*rel.parts[2:]))
            cnt_by_case[case_id][(r["check_id"].split(".")[-1], f, side)] += 1
        for c, n in mat:
            cnt = cnt_by_case[c["id"]]
            per_rule = {}
            for rule, f in {(k[0], k[1]) for k in cnt}:
                b, af = cnt[(rule, f, "before")], cnt[(rule, f, "after")]
                kind = "fixed-signal" if b > af else "persistent" if b == af else "introduced"
                per_rule.setdefault(rule, []).append({"file": f, "before": b, "after": af, "kind": kind})
            results.append({**{k: c.get(k) for k in ("id", "repo", "commit", "date", "message", "auto_label", "files", "expect", "source", "split")},
                            "files_before": n["before"], "files_after": n["after"], "rules": per_rule})

    # ---- aggregate
    by_rule = collections.defaultdict(collections.Counter)
    for r in results:
        for rule, items in r["rules"].items():
            kinds = {i["kind"] for i in items}
            for k in ("fixed-signal", "persistent", "introduced"):
                if k in kinds:
                    by_rule[rule][k] += 1
    covered = [r for r in results if any(i["kind"] == "fixed-signal" for items in r["rules"].values() for i in items)]
    silent = [r for r in results if not r["rules"]]
    def has_signal(r):
        return any(i["kind"] == "fixed-signal" for items in r["rules"].values() for i in items)

    by_split = collections.defaultdict(lambda: collections.Counter())
    for r in results:
        sp = r.get("split") or "tuning"
        by_split[sp]["cases"] += 1
        by_split[sp]["fixed-signal"] += has_signal(r)
        by_split[sp]["silent"] += not r["rules"]
        by_split[sp]["persistent-only"] += (not has_signal(r)) and bool(r["rules"])
    by_label = collections.defaultdict(lambda: [0, 0])
    for r in results:
        by_label[r["auto_label"]][0] += 1
        by_label[r["auto_label"]][1] += any(i["kind"] == "fixed-signal" for items in r["rules"].values() for i in items)

    (out / "results.json").write_text(json.dumps({"results": results, "skipped": skipped}, ensure_ascii=False, indent=1))
    with open(out / "REPORT.md", "w") as fh:
        n = len(results)
        fh.write(f"# Benchmark report\n\n{n} cases evaluated, {len(skipped)} skipped.\n\n")
        fh.write(f"- cases where some rule shows a **fixed-signal**: {len(covered)} ({len(covered) * 100 // max(n, 1)}%)\n")
        fh.write(f"- cases where **no rule fires at all** (silent): {len(silent)} ({len(silent) * 100 // max(n, 1)}%)\n\n")
        fh.write("## By split\n\n`tuning` repos were used to adjust the rules (numbers are optimistic); `holdout` repos were not.\n\n| split | cases | fixed-signal | persistent only | silent |\n|---|---:|---:|---:|---:|\n")
        for sp, k in sorted(by_split.items()):
            fh.write(f"| {sp} | {k['cases']} | {k['fixed-signal']} | {k['persistent-only']} | {k['silent']} |\n")
        fh.write("\n")
        fh.write("## By message-keyword label (unverified)\n\n| label | cases | with fixed-signal |\n|---|---:|---:|\n")
        for k, (t, h) in sorted(by_label.items()):
            fh.write(f"| {k} | {t} | {h} |\n")
        fh.write("\n## By rule (cases in which the rule fired in a changed file)\n\n| rule | fixed-signal | persistent | introduced |\n|---|---:|---:|---:|\n")
        for rule, k in sorted(by_rule.items(), key=lambda kv: -sum(kv[1].values())):
            fh.write(f"| {rule} | {k['fixed-signal']} | {k['persistent']} | {k['introduced']} |\n")
        fh.write("\n## Cases with a fixed-signal\n\n")
        for r in covered:
            fs = [(rule, i["file"].split("/")[-1], i["before"], i["after"]) for rule, items in r["rules"].items() for i in items if i["kind"] == "fixed-signal"]
            fh.write(f"- `{r['id']}` {r['date']} — {r['message']}\n")
            for rule, f, b, af in fs:
                fh.write(f"    - {rule} in {f}: {b} → {af}\n")
        if skipped:
            fh.write("\n## Skipped\n\n" + "\n".join(f"- {i}: {why}" for i, why in skipped) + "\n")
    print(f"{n} cases, fixed-signal in {len(covered)}, silent {len(silent)}, skipped {len(skipped)} -> {out}/REPORT.md")


if __name__ == "__main__":
    main()
