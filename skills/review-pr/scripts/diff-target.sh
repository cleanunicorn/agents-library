#!/usr/bin/env bash
# Deterministic review-target computation for review-pr.
#
# Usage: diff-target.sh [main|files|diff]
#   main    print the detected main branch name
#   files   print the sorted unique union: committed vs main, staged, unstaged,
#           and untracked files (the union is the review target)
#   diff    print patches in order: main→HEAD, HEAD→index, index→worktree;
#           partially staged files may have two uncommitted patches, even when
#           they cancel out. Untracked files appear in `files` but not here —
#           read them directly.
#   (none)  print "MAIN <name>" followed by the changed-file list
#
# Exits non-zero with FATAL on stderr if no main branch can be detected.

set -euo pipefail

detect_main() {
  local ref
  if ref=$(git symbolic-ref -q refs/remotes/origin/HEAD 2>/dev/null); then
    if ! git rev-parse --verify "$ref^{commit}" >/dev/null 2>&1; then
      echo "FATAL default branch ref $ref is unavailable" >&2
      return 1
    fi
    echo "$ref"
    return 0
  fi
  local b
  for b in main master; do
    if git show-ref --verify --quiet "refs/heads/$b"; then
      echo "refs/heads/$b"
      return 0
    fi
  done
  echo "FATAL cannot detect the main branch" >&2
  return 1
}

case "${1:-summary}" in
  main|files|diff|summary) ;;
  *)
    echo "usage: $0 [main|files|diff]" >&2
    exit 2
    ;;
esac

main_ref=$(detect_main) || exit 1
main=${main_ref#refs/remotes/origin/}
main=${main#refs/heads/}

changed_files() {
  {
    git diff --name-only "$main_ref...HEAD"
    git diff --cached --name-only
    git diff --name-only
    git ls-files -o --exclude-standard
  } | sort -u
}

case "${1:-summary}" in
  main)
    echo "$main"
    ;;
  files)
    changed_files
    ;;
  diff)
    git diff "$main_ref...HEAD"
    git diff --cached
    git diff
    ;;
  summary)
    echo "MAIN $main"
    changed_files
    ;;
esac
