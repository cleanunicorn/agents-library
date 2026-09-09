#!/usr/bin/env bash
# Fast local checks. No model invocations, credentials, or network needed.
# Usage: bash scripts/check.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo "Checking shell syntax..."
for script in scripts/*.sh skills/*/scripts/*.sh; do
  bash -n "$script"
done

echo "Checking plugin JSON syntax..."
for manifest in .claude-plugin/*.json .codex-plugin/*.json .agents/plugins/*.json; do
  python3 -m json.tool "$manifest" >/dev/null
done

echo "Checking Claude/Codex plugin layout..."
python3 scripts/test-plugin-layout.py

bash scripts/check-opencode-sync.sh
python3 scripts/test-check-opencode-sync.py
bash scripts/test-install-opencode.sh
python3 run_evals.py --dry-run

echo "All local checks passed."
