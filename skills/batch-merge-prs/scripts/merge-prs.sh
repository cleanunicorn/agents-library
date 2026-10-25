#!/usr/bin/env bash
# Locally batch-merge GitHub PR heads onto a new target branch. Never pushes,
# never writes to GitHub. Pauses on a conflict so the caller can resolve it.
#
# Usage:
#   merge-prs.sh <remote> <main-branch> <target-branch>|auto <pr-number>...
#   merge-prs.sh --continue <remote> <target-branch> <pr> <record-file> [<pr-number>...]
#   merge-prs.sh --skip <remote> <target-branch> <pr> <reason> [<pr-number>...]
#
# Behavior:
#   - A target of `auto` generates the branch name batch/<YYYYMMDD-HHMM> from
#     the current date/time (the default when the user didn't name a branch).
#   - Refuses to start on a dirty working tree, during a merge, or when the
#     target branch already exists: conflicts are resolved on this branch, so
#     it must be one the run created, never main or a PR branch.
#   - Creates <target-branch> from an up-to-date <remote>/<main-branch>.
#   - Fetches each PR via the base-repo pull ref (pull/<n>/head — works for
#     fork PRs) without creating a local branch, merges it with --no-ff so
#     each PR stays a distinct, revertable merge commit.
#   - Skips a PR whose head the branch already contains (nothing to merge).
#   - On conflict: leaves the merge in progress, prints the conflicted paths
#     and the PRs still queued, and exits 3. The caller resolves and stages
#     the result, then runs --continue with a record naming every conflicted
#     path; or runs --skip with the reason it could not resolve with
#     confidence. Both pass the queued PRs back and the loop resumes.
#   - A merge that fails without conflicts is FATAL, never a silent skip.
#   - Prints ledger lines on stdout (git's own output goes to stderr):
#       TARGET <branch> created-from <remote>/<main>
#       MERGED <n> <merge-commit-sha>
#       RESOLVED <n> <merge-commit-sha> <record-file>   after its MERGED
#       SKIPPED <n> fetch-failed
#       SKIPPED <n> already-contained
#       SKIPPED <n> unresolved <reason>
#       CONFLICT <n> <pr-head-sha> <path>               one per path, then
#       PENDING [<n>...]                                the PRs still queued
#   - --continue needs Git 2.38+ (`git merge-tree --write-tree`).
#   - Exit 0 once the queue is done, 3 when paused on a conflict, 2 for bad
#     args, 1 (FATAL on stderr) for anything else; nothing is reset or cleaned.

set -u

usage() {
  cat >&2 <<EOF
usage: $0 <remote> <main-branch> <target-branch>|auto <pr-number>...
       $0 --continue <remote> <target-branch> <pr> <record-file> [<pr-number>...]
       $0 --skip <remote> <target-branch> <pr> <reason> [<pr-number>...]
EOF
  exit 2
}

fatal() {
  echo "FATAL $*" >&2
  exit 1
}

require_pr_numbers() {
  local n
  for n in "$@"; do
    case $n in ''|*[!0-9]*) usage ;; esac
  done
}

merge_in_progress() {
  git rev-parse -q --verify MERGE_HEAD >/dev/null
}

# Abort the pending merge and prove the pre-merge tree is back; a half-undone
# merge is the user's to inspect, so nothing is reset to force progress.
abort_merge() {
  if ! git merge --abort >&2 || merge_in_progress || [ -n "$(git status --porcelain)" ]; then
    fatal "could not abort the merge of PR #$1 — inspect it by hand; nothing was reset"
  fi
}

# The paths the pending merge conflicts on, re-derived from the two commits:
# after staging, the index no longer has them, and MERGE_MSG's comment block
# depends on core.commentChar. Exit 1 from merge-tree means "conflicts".
conflicted_paths() {
  local listing status=0
  listing=$(git merge-tree --write-tree --name-only --no-messages HEAD MERGE_HEAD) || status=$?
  [ "$status" -le 1 ] || fatal "git merge-tree could not list the conflicts (needs Git 2.38+)"
  printf '%s\n' "$listing" | tail -n +2 | sed '/^$/d'
}

# Refuse to touch a merge that is not this run's pause on PR <n>.
check_pending() {
  local target=$1 n=$2
  [ "$(git symbolic-ref -q --short HEAD)" = "$target" ] || fatal "not on $target"
  merge_in_progress || fatal "no merge in progress on $target"
  head -n 1 "$(git rev-parse --git-path MERGE_MSG)" | grep -Eq "^Merge PR #$n(:|$)" \
    || fatal "the pending merge is not PR #$n"
}

# merge_queue <n>...: merge each PR in order, pausing (exit 3) on a conflict.
merge_queue() {
  local n head title conflicted path
  while [ "$#" -gt 0 ]; do
    n=$1
    shift
    if ! git fetch -q "$remote" "pull/$n/head"; then
      echo "SKIPPED $n fetch-failed"
      continue
    fi
    head=$(git rev-parse FETCH_HEAD)
    if git merge-base --is-ancestor "$head" HEAD; then
      echo "SKIPPED $n already-contained"
      continue
    fi
    title=$(gh pr view "$n" --json title -q .title 2>/dev/null || echo "")
    if git merge --no-ff "$head" -m "Merge PR #$n${title:+: $title}" >&2; then
      echo "MERGED $n $(git rev-parse HEAD)"
      continue
    fi
    conflicted=$(git diff --name-only --diff-filter=U)
    if [ -z "$conflicted" ]; then
      merge_in_progress && abort_merge "$n"
      fatal "merging PR #$n failed without conflicts — see git's message above"
    fi
    while IFS= read -r path; do
      echo "CONFLICT $n $head $path"
    done <<< "$conflicted"
    echo "PENDING${*:+ $*}"
    exit 3
  done
  exit 0
}

continue_merge() {
  [ "$#" -ge 4 ] || usage
  remote=$1
  local target=$2 n=$3 record=$4 path missing="" conflicted
  shift 4
  require_pr_numbers "$n" "$@"
  check_pending "$target" "$n"
  [ -z "$(git diff --name-only --diff-filter=U)" ] \
    || fatal "unresolved paths remain: $(git diff --name-only --diff-filter=U | paste -sd, -)"
  [ -z "$(git diff --name-only)" ] \
    || fatal "unstaged changes — stage only the reviewed resolution"
  [ -s "$record" ] || fatal "resolution record $record is missing or empty"
  conflicted=$(conflicted_paths) || exit 1
  # An empty list would make every record pass: the pause had conflicts.
  [ -n "$conflicted" ] || fatal "could not list PR #$n's conflicted paths"
  while IFS= read -r path; do
    grep -qF -- "$path" "$record" || missing="$missing${missing:+, }$path"
  done <<< "$conflicted"
  [ -z "$missing" ] || fatal "resolution record does not name: $missing"
  git fetch -q "$remote" "pull/$n/head" || fatal "git fetch $remote pull/$n/head failed"
  [ "$(git rev-parse FETCH_HEAD)" = "$(git rev-parse MERGE_HEAD)" ] \
    || fatal "PR #$n moved since the pause — --skip it and rerun it later"
  # strip drops the commented conflict list Git appended to MERGE_MSG.
  git commit -q --no-edit --cleanup=strip >&2 || fatal "commit failed; the merge is still in progress"
  local sha
  sha=$(git rev-parse HEAD)
  echo "MERGED $n $sha"
  echo "RESOLVED $n $sha $record"
  merge_queue "$@"
}

skip_merge() {
  [ "$#" -ge 4 ] || usage
  remote=$1
  local target=$2 n=$3 reason
  reason=$(printf '%s' "$4" | tr '\r\n' '  ')
  shift 4
  [ -n "$reason" ] || usage
  require_pr_numbers "$n" "$@"
  check_pending "$target" "$n"
  abort_merge "$n"
  echo "SKIPPED $n unresolved $reason"
  merge_queue "$@"
}

case ${1:-} in
  --continue) shift; continue_merge "$@" ;;
  --skip) shift; skip_merge "$@" ;;
esac

[ "$#" -ge 4 ] || usage
remote=$1
main=$2
target=$3
shift 3
require_pr_numbers "$@"

if [ "$target" = "auto" ]; then
  target="batch/$(date +%Y%m%d-%H%M)"
fi

if [ -n "$(git status --porcelain)" ]; then
  fatal "working tree not clean — commit or stash first"
fi
merge_in_progress && fatal "a merge is in progress — finish or abort it first"

git fetch "$remote" >&2 || fatal "git fetch $remote failed"

if git show-ref --verify --quiet "refs/heads/$target"; then
  fatal "branch $target already exists — choose an unused name; resume a paused run with --continue or --skip"
fi
git checkout -q -b "$target" "$remote/$main" >&2 || fatal "could not create $target from $remote/$main"
echo "TARGET $target created-from $remote/$main"

merge_queue "$@"
