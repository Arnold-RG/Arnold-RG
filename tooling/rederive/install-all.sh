#!/usr/bin/env bash
# Run: bash install-all.sh [owner] [workspace]
set -euo pipefail
owner="${1:-Arnold-RG}"
workspace="${2:-$HOME/code/Arnold-RG}"
for cmd in git gh node npx python3; do
  command -v "$cmd" >/dev/null || { echo "Missing prerequisite: $cmd" >&2; exit 1; }
done
gh auth status >/dev/null || { echo "Run: gh auth login" >&2; exit 1; }
npx --yes skills add EricJujianZou/rederive --skill rederive --global --yes --agent codex --agent cursor --agent claude-code
mkdir -p "$workspace"
while IFS= read -r name; do
  [[ -z "$name" ]] && continue
  if [[ -d "$workspace/$name" ]]; then
    printf 'Keeping existing folder: %s\n' "$workspace/$name"
  else
    gh repo clone "$owner/$name" "$workspace/$name" || echo "WARNING: clone failed for $name" >&2
  fi
done < <(gh repo list "$owner" --limit 500 --json name,isArchived --jq '.[] | select(.isArchived == false) | .name')
printf 'Ready. Open a repo in a supported coding agent and run /rederive.\n'
