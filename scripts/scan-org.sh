#!/usr/bin/env bash
# Scan every non-archived repo of a GitHub org (or a local directory of checkouts) with the
# mcmod-derived Semgrep rules, then aggregate by paradigm.
#
#   scripts/scan-org.sh ORG [OUT_DIR]          # needs: gh (authenticated), git, semgrep, python3
#   scripts/scan-org.sh --dir CHECKOUTS [OUT]  # scan already-cloned repos: CHECKOUTS/<repo>/...
#
# Env: JOBS (default 4), INCLUDE_FORKS=1 to include forks, REPO_FILTER=regex on repo names.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
rules=("$here/semgrep/rules/mc-java.yml" "$here/semgrep/rules/mc-build.yml")
jobs="${JOBS:-4}"

if [[ "${1:-}" == "--dir" ]]; then
  src="$(cd "${2:?checkouts dir}" && pwd)"; out="${3:-scan-out}"; mode=dir
else
  org="${1:?usage: scan-org.sh ORG [OUT_DIR] | --dir CHECKOUTS [OUT_DIR]}"; out="${2:-scan-out}"; mode=org
  src="$out/clones"
fi
mkdir -p "$out" "$out/json"
out="$(cd "$out" && pwd)"

if [[ $mode == org ]]; then
  mkdir -p "$src"
  jq_filter='.[] | select(.isArchived|not) | '"$([[ -n "${INCLUDE_FORKS:-}" ]] && echo true || echo '(.isFork|not)')"' | .name'
  gh repo list "$org" --limit 1000 --json name,isArchived,isFork --jq "$jq_filter" > "$out/repos.txt"
  [[ -n "${REPO_FILTER:-}" ]] && grep -E "$REPO_FILTER" "$out/repos.txt" > "$out/repos.f" && mv "$out/repos.f" "$out/repos.txt"
  echo "cloning $(wc -l < "$out/repos.txt") repos (depth 1)..."
  xargs -P "$jobs" -I{} sh -c '[ -d "$1/{}" ] || gh repo clone "$2/{}" "$1/{}" -- --depth 1 --quiet 2>/dev/null || echo "clone failed: {}" >&2' _ "$src" "$org" < "$out/repos.txt"
fi

scan_one() {
  repo_dir="$1"; out="$2"; shift 2
  name="$(basename "$repo_dir")"
  args=(); for r in "$@"; do args+=(--config "$r"); done
  semgrep scan "${args[@]}" --json --quiet --metrics off --no-git-ignore \
    --include '*.java' --include '*.gradle' --include '*.gradle.kts' --include 'pom.xml' --include '*.properties' --include '*.toml' \
    --exclude 'build' --exclude '.gradle' --exclude 'run' \
    "$repo_dir" > "$out/json/$name.json" 2> "$out/json/$name.err" || true
}
export -f scan_one
find "$src" -mindepth 1 -maxdepth 1 -type d | xargs -P "$jobs" -I{} bash -c 'scan_one "$@"' _ {} "$out" "${rules[@]}"

python3 "$here/scripts/aggregate.py" "$out/json" --src "$src"
cp "$out/json/findings.csv" "$out/json/findings.jsonl" "$out/json/SUMMARY.md" "$out/"
echo "next: AI triage reads $out/findings.jsonl -- see review/README.md"
