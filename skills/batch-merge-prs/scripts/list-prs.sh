#!/usr/bin/env bash
# Discover open PRs when the user names none.
# Usage: list-prs.sh
# Output: == main == then the main branch; == prs == then the open-PR JSON.
# FATAL/nonzero if gh is missing/unauthenticated, main is undetectable, or the
# PR list cannot be fetched: these are required inputs.

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
