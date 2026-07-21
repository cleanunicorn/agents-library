#!/usr/bin/env bash
# Deterministic review-target computation for review-pr.
#
# Usage: diff-target.sh [main|files|diff]
#   main    print the detected main branch name
#   files   print the changed-file list: committed vs main, uncommitted, and
#           untracked (the union is the review target)
#   diff    print the combined diff (committed vs main, then uncommitted;
#           untracked files appear in `files` but not here — read them directly)
#   (none)  print "MAIN <name>" followed by the changed-file list
#
# Exits non-zero with FATAL on stderr if no main branch can be detected.

set -u

detect_main() {
  local ref
  if ref=$(git symbolic-ref -q refs/remotes/origin/HEAD 2>/dev/null); then
    echo "${ref##*/}"
    return 0
  fi
  local b
  for b in main master; do
    if git show-ref --verify --quiet "refs/heads/$b"; then
      echo "$b"
      return 0
    fi
  done
  echo "FATAL cannot detect the main branch" >&2
  return 1
}

main=$(detect_main) || exit 1

changed_files() {
  {
    git diff --name-only "$main...HEAD" 2>/dev/null
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
    git diff "$main...HEAD" 2>/dev/null
    git diff
    ;;
  summary)
    echo "MAIN $main"
    changed_files
    ;;
  *)
    echo "usage: $0 [main|files|diff]" >&2
    exit 2
    ;;
esac
