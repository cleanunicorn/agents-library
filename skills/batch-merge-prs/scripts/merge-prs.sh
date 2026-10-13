#!/usr/bin/env bash
# Merge GitHub PR heads locally; never push or write to GitHub.
# Usage: merge-prs.sh <remote> <main-branch> <target-branch>|auto <pr-number>...
# auto names batch/<YYYYMMDD-HHMM>. Refuse a dirty tree; fetch the remote,
# then create the target from remote/main or check out an existing target as-is.
# Fetch pull/<n>/head (including forks); --no-ff keeps each merge revertable.
# Abort conflicts and continue; skip heads already contained in the target.
# Ledger: TARGET <branch> existing|created-from <remote/main>;
# MERGED <n> <sha>; SKIPPED <n> fetch-failed|already-contained|conflicts <files>.
# Conflicting files are comma-separated. Exit 0 after the loop; nonzero on
# setup failures (arguments, dirty tree, remote fetch, or target checkout).

set -u

if [ "$#" -lt 4 ]; then
  echo "usage: $0 <remote> <main-branch> <target-branch>|auto <pr-number>..." >&2
  exit 2
fi

remote=$1
main=$2
target=$3
shift 3

if [ "$target" = "auto" ]; then
  target="batch/$(date +%Y%m%d-%H%M)"
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "FATAL working tree not clean — commit or stash first" >&2
  exit 1
fi

git fetch "$remote" || { echo "FATAL git fetch $remote failed" >&2; exit 1; }

if git show-ref --verify --quiet "refs/heads/$target"; then
  git checkout "$target" || exit 1
  echo "TARGET $target existing"
else
  git checkout -b "$target" "$remote/$main" || exit 1
  echo "TARGET $target created-from $remote/$main"
fi

for n in "$@"; do
  tmp="__batch_pr_$n"
  if ! git fetch "$remote" "pull/$n/head:$tmp"; then
    echo "SKIPPED $n fetch-failed"
    continue
  fi
  if git merge-base --is-ancestor "$tmp" HEAD; then
    echo "SKIPPED $n already-contained"
    git branch -D "$tmp" >/dev/null 2>&1 || true
    continue
  fi
  title=$(gh pr view "$n" --json title -q .title 2>/dev/null || echo "")
  if git merge --no-ff "$tmp" -m "Merge PR #$n${title:+: $title}"; then
    echo "MERGED $n $(git rev-parse HEAD)"
  else
    files=$(git diff --name-only --diff-filter=U | paste -sd, -)
    git merge --abort
    echo "SKIPPED $n conflicts ${files:-unknown}"
  fi
  git branch -D "$tmp" >/dev/null 2>&1 || true
done
