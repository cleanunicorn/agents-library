#!/usr/bin/env bash
# Fast local checks. No model invocations, credentials, or network needed.
# Usage: bash scripts/check.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo "Checking shell syntax..."
for script in scripts/*.sh skills/*/scripts/*.sh; do
  bash -n "$script"
done

echo "Checking for unused Python imports..."
python3 scripts/check-unused-imports.py

echo "Checking plugin JSON syntax..."
for manifest in .claude-plugin/*.json .codex-plugin/*.json .agents/plugins/*.json; do
  python3 -m json.tool "$manifest" >/dev/null
done

echo "Checking Claude/Codex plugin layout..."
python3 scripts/test-plugin-layout.py

echo "Checking every fix sweeps the whole repository..."
python3 scripts/test-fix-everywhere.py

echo "Checking batch-merge-prs answers routine worker approvals and relays the rare ones..."
python3 scripts/test-batch-merge-approval.py

echo "Checking the README table of contents and in-page links..."
python3 scripts/test-readme-toc.py

echo "Checking no fenced block holds two slash commands..."
python3 scripts/test-paste-blocks.py

echo "Checking the manager answers routine approvals and relays the rare ones..."
python3 scripts/test-manager-approval.py

echo "Checking the manager stays a console for every later message..."
python3 scripts/test-manager-console.py

echo "Checking every Herdr prompt is confirmed delivered before it is waited on..."
python3 scripts/test-herdr-prompt-delivery.py

echo "Checking the manager's worker watcher against a stub Herdr..."
python3 scripts/test-manager-watcher.py

bash scripts/check-host-sync.sh
python3 scripts/test-check-host-sync.py
python3 scripts/test-install.py
bash scripts/test-install-agents.sh
./scripts/test-diff-target.sh
bash scripts/test-rename-herdr-tab.sh

echo "Checking the eval runner parses transcripts offline..."
python3 scripts/test-run-evals.py
python3 run_evals.py --dry-run

echo "All local checks passed."
