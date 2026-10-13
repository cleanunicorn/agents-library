#!/usr/bin/env bash
# Run the failing command at the batch base, then each merge in order.
# Stop at the first failure and restore the starting branch (or detached HEAD).
# Usage: attribute-failure.sh <log-dir> <base> <command> <pr>=<merge-sha>...
# <command> is one shell string; entries are MERGED ledger pairs in merge order.
# Ledger: BASELINE pass|fail; AT <pr> <sha> pass|fail;
# CULPRIT <pr>|pre-existing|none. A PR culprit may interact with earlier merges;
# none means every revision passed (flakiness or state outside the tree).
# Logs land in <log-dir>/attr-<step>.log.
# FATAL/nonzero on checkout failure or tracked changes before/after a run:
# tests must not leave tracked side effects behind.

set -u

if [ "$#" -lt 4 ]; then
  echo "usage: $0 <log-dir> <base> <command> <pr>=<merge-sha>..." >&2
  exit 2
fi

log_dir=$1
base=$2
cmd=$3
shift 3

start=$(git symbolic-ref -q --short HEAD || git rev-parse HEAD)
mkdir -p "$log_dir"

require_clean() {
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "FATAL tracked files changed ($1) — commit, stash, or fix the test's side effects" >&2
    git checkout -q "$start" 2>/dev/null
    exit 1
  fi
}

run_at() {
  local rev=$1 step=$2
  require_clean "before $step"
  # Build caches (.pyc, make, incremental compilers) trust a file whose
  # whole-second mtime and size are unchanged. Waiting a second guarantees
  # every file this checkout rewrites is newer than any version they saw.
  sleep 1
  git checkout -q --detach "$rev" || { echo "FATAL cannot check out $rev" >&2; git checkout -q "$start"; exit 1; }
  if bash -c "$cmd" >"$log_dir/attr-$step.log" 2>&1; then
    result=pass
  else
    result=fail
  fi
  require_clean "after $step"
}

run_at "$base" baseline
echo "BASELINE $result"
culprit=pre-existing
if [ "$result" = pass ]; then
  culprit=none
  for entry in "$@"; do
    pr=${entry%%=*}
    sha=${entry#*=}
    run_at "$sha" "pr-$pr"
    echo "AT $pr $sha $result"
    if [ "$result" = fail ]; then
      culprit=$pr
      break
    fi
  done
fi

git checkout -q "$start"
echo "CULPRIT $culprit"
