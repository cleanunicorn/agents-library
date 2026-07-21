#!/usr/bin/env bash
# Locally batch-merge GitHub PR heads onto a target branch. Never pushes,
# never writes to GitHub.
#
# Usage: merge-prs.sh <remote> <main-branch> <target-branch> <pr-number>...
#
# Behavior:
#   - Refuses to run on a dirty working tree.
#   - Creates <target-branch> from an up-to-date <remote>/<main-branch> if it
#     doesn't exist; otherwise checks it out as-is.
#   - Fetches each PR via the base-repo pull ref (pull/<n>/head — works for
#     fork PRs), merges it with --no-ff so each PR stays a distinct,
#     revertable merge commit.
#   - On conflict: aborts that one merge and continues with the rest. Never
#     leaves a half-resolved merge.
#   - Prints one ledger line per PR on stdout:
#       MERGED <n>
#       SKIPPED <n> fetch-failed | SKIPPED <n> conflicts
#   - Exit 0 once the loop ran; non-zero only for setup failures (dirty tree,
#     bad args, fetch/checkout of the target failed).

set -u

if [ "$#" -lt 4 ]; then
  echo "usage: $0 <remote> <main-branch> <target-branch> <pr-number>..." >&2
  exit 2
fi

remote=$1
main=$2
target=$3
shift 3

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
  title=$(gh pr view "$n" --json title -q .title 2>/dev/null || echo "")
  if git merge --no-ff "$tmp" -m "Merge PR #$n${title:+: $title}"; then
    echo "MERGED $n"
  else
    git merge --abort
    echo "SKIPPED $n conflicts"
  fi
  git branch -D "$tmp" >/dev/null 2>&1 || true
done
