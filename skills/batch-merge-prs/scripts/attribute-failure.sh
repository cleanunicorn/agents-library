#!/usr/bin/env bash
# Find which merged PR first makes a failing test command fail. Re-runs the
# command at <base> and then at each batch merge commit in order, and stops
# at the first failure. Returns to the starting branch when done.
#
# Usage: attribute-failure.sh <log-dir> <base> <command> <pr>=<merge-sha>...
#
#   <base>      the commit the batch was cut from, e.g. origin/main
#   <command>   the failing gate command, one string
#   <pr>=<sha>  each MERGED ledger entry, in merge order
#
# Prints:
#   BASELINE pass|fail                 the command at <base>
#   AT <pr> <sha> pass|fail            the command at each merge commit
#   CULPRIT <pr>                       first merge where it fails; when earlier
#                                      PRs are present this may be an
#                                      interaction, not <pr> alone
#   CULPRIT pre-existing               it already fails at <base>
#   CULPRIT none                       it passes at every merge (flaky, or
#                                      depends on state outside the tree)
# Logs land in <log-dir>/attr-<step>.log.
#
# Exit non-zero with FATAL when the tree is dirty before or after a run
# (tests must not leave tracked changes behind) or a checkout fails.

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

culprit() {
  git checkout -q "$start"
  echo "CULPRIT $1"
  exit 0
}

run_at "$base" baseline
echo "BASELINE $result"
[ "$result" = fail ] && culprit pre-existing

for entry in "$@"; do
  pr=${entry%%=*}
  sha=${entry#*=}
  run_at "$sha" "pr-$pr"
  echo "AT $pr $sha $result"
  [ "$result" = fail ] && culprit "$pr"
done

culprit none
