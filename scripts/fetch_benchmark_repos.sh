#!/usr/bin/env bash
# Clone the repositories used by benchmark/cases.json with enough history to read each fix commit's parent.
#   scripts/fetch_benchmark_repos.sh DEST_DIR
# Prints the --repo arguments to pass to run_benchmark.py. Env: DEPTH (default 4000), ONLY="name1 name2".
set -euo pipefail
dest="${1:?usage: fetch_benchmark_repos.sh DEST_DIR}"; depth="${DEPTH:-4000}"
declare -A URL=(
  [mekanism]=https://github.com/mekanism/mekanism
  [ae2]=https://github.com/AppliedEnergistics/applied-energistics-2
  [create]=https://github.com/Creators-of-Create/create
  [botania]=https://github.com/VazkiiMods/botania
  [refinedstorage]=https://github.com/refinedmods/refinedstorage
)
mkdir -p "$dest"
args=()
for name in ${ONLY:-mekanism ae2 create botania refinedstorage}; do
  d="$dest/$name"
  if [[ ! -d "$d/.git" ]]; then GIT_LFS_SKIP_SMUDGE=1 git clone --quiet --depth 1 "${URL[$name]}" "$d"; fi
  br="$(git -C "$d" branch --show-current)"
  git -C "$d" fetch --quiet --depth="$depth" origin "$br"
  echo "$name: $(git -C "$d" rev-list --count HEAD) commits on $br" >&2
  args+=(--repo "$name=$d")
done
echo "python3 scripts/run_benchmark.py ${args[*]}"
