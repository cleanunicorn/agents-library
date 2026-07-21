#!/usr/bin/env bash
# Deterministic Phase 0 data gathering for triage-issues.
#
# Usage: list-issues.sh
#
# Prints delimited sections:
#   == repo ==     the repo slug (nameWithOwner) — needed to scope searches
#   == labels ==   the label vocabulary (up to 200)
#   == issues ==   the open-issue list as JSON (the work list)
#
# Failure semantics match the skill's error handling:
#   - gh missing/unauthenticated, or the issue list failing → FATAL, exit 1
#     (the issue list is the work list; the skill cannot run without it)
#   - repo view / label list failing → a "(... failed)" marker line, exit 0
#     (triage still works; the orchestrator decides whether to continue)

set -u

command -v gh >/dev/null 2>&1 || { echo "FATAL gh is not installed" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "FATAL gh is not authenticated" >&2; exit 1; }

echo "== repo =="
gh repo view --json nameWithOwner -q .nameWithOwner || echo "(repo view failed)"

echo "== labels =="
gh label list --limit 200 || echo "(label list failed)"

echo "== issues =="
gh issue list --state open --limit 200 \
  --json number,title,author,labels,assignees,createdAt,updatedAt \
  || { echo "FATAL gh issue list failed" >&2; exit 1; }
