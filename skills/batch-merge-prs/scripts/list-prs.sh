#!/usr/bin/env bash
# Deterministic Phase 0 data gathering for batch-merge-prs.
#
# Usage: list-prs.sh
#
# Prints delimited sections:
#   == main ==     the detected main branch name
#   == prs ==      the open-PR list as JSON (the work list)
#
# Exit non-zero with FATAL on stderr when gh is missing/unauthenticated or the
# PR list cannot be fetched — the skill cannot run without either.

set -u

command -v gh >/dev/null 2>&1 || { echo "FATAL gh is not installed" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "FATAL gh is not authenticated" >&2; exit 1; }

echo "== main =="
if ref=$(git symbolic-ref -q refs/remotes/origin/HEAD 2>/dev/null); then
  echo "${ref##*/}"
elif git show-ref --verify --quiet refs/heads/main; then
  echo "main"
elif git show-ref --verify --quiet refs/heads/master; then
  echo "master"
else
  echo "FATAL cannot detect the main branch" >&2
  exit 1
fi

echo "== prs =="
gh pr list --state open \
  --json number,title,author,headRefName,baseRefName,isDraft,mergeable,labels,additions,deletions,changedFiles \
  || { echo "FATAL gh pr list failed" >&2; exit 1; }
