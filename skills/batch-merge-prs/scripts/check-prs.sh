#!/usr/bin/env bash
# Resolve the user's PR list and classify each PR against <remote>/<main>.
# Read-only: fetches, never checks out, merges, or writes to GitHub.
#
# Usage: check-prs.sh <remote> <pr-number|pr-url>...
#
# Prints, in order:
#   MAIN <branch>                      the detected main branch of <remote>
#   REPO <owner/name>                  the repository gh resolves here
# then one line per listed PR, in the order given:
#   IN_MAIN <n> merged-on-github <merge-sha>   GitHub merged it into main
#   IN_MAIN <n> head-reachable <head-sha>      its head commit is in main
#   IN_MAIN <n> patch-equivalent <head-sha>    every commit is already in main
#                                              as an equivalent patch (squash
#                                              or rebase merge)
#   TODO <n> <head-sha> <state>                merge it (state OPEN|DRAFT|CLOSED)
#   SKIPPED <n> fetch-failed                   pull/<n>/head could not be fetched
#   SKIPPED <arg> other-repo <owner/name>      a URL for a different repository
#   SKIPPED <arg> bad-ref                      neither a number nor a PR URL
#
# A PR number listed twice is reported once. Exit non-zero with FATAL on
# stderr when gh is missing/unauthenticated, the remote cannot be fetched, or
# no main branch can be detected.

set -u

if [ "$#" -lt 2 ]; then
  echo "usage: $0 <remote> <pr-number|pr-url>..." >&2
  exit 2
fi

remote=$1
shift

command -v gh >/dev/null 2>&1 || { echo "FATAL gh is not installed" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "FATAL gh is not authenticated" >&2; exit 1; }
git fetch -q "$remote" || { echo "FATAL git fetch $remote failed" >&2; exit 1; }

detect_main() {
  local ref b
  if ref=$(git symbolic-ref -q "refs/remotes/$remote/HEAD" 2>/dev/null); then
    echo "${ref##*/}"
    return 0
  fi
  for b in main master; do
    if git show-ref --verify --quiet "refs/remotes/$remote/$b"; then
      echo "$b"
      return 0
    fi
  done
  echo "FATAL cannot detect the main branch of $remote" >&2
  return 1
}

main=$(detect_main) || exit 1
base="$remote/$main"
repo=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
echo "MAIN $main"
echo "REPO ${repo:-unknown}"

seen=" "
for arg in "$@"; do
  case "$arg" in
    *[!0-9]*|"")
      if [[ "$arg" =~ github\.com/([^/]+/[^/]+)/pull/([0-9]+) ]]; then
        slug=${BASH_REMATCH[1]}
        n=${BASH_REMATCH[2]}
        if [ -n "$repo" ] && [ "$slug" != "$repo" ]; then
          echo "SKIPPED $arg other-repo $slug"
          continue
        fi
      else
        echo "SKIPPED $arg bad-ref"
        continue
      fi
      ;;
    *) n=$arg ;;
  esac

  case "$seen" in *" $n "*) continue ;; esac
  seen="$seen$n "

  state=$(gh pr view "$n" --json state -q .state 2>/dev/null || echo "")
  merge_sha=$(gh pr view "$n" --json mergeCommit -q '.mergeCommit.oid // ""' 2>/dev/null || echo "")
  if [ "$state" = "MERGED" ] && [ -n "$merge_sha" ] \
    && git merge-base --is-ancestor "$merge_sha" "$base" 2>/dev/null; then
    echo "IN_MAIN $n merged-on-github $merge_sha"
    continue
  fi

  if ! git fetch -q "$remote" "pull/$n/head" 2>/dev/null; then
    echo "SKIPPED $n fetch-failed"
    continue
  fi
  head=$(git rev-parse FETCH_HEAD)

  if git merge-base --is-ancestor "$head" "$base"; then
    echo "IN_MAIN $n head-reachable $head"
    continue
  fi
  # `git cherry` marks a commit `-` when an equivalent patch is already in
  # <base>; no `+` line means nothing in the PR is new.
  if ! git cherry "$base" "$head" | grep -q '^+'; then
    echo "IN_MAIN $n patch-equivalent $head"
    continue
  fi

  draft=$(gh pr view "$n" --json isDraft -q .isDraft 2>/dev/null || echo "")
  [ "$draft" = "true" ] && state="DRAFT"
  echo "TODO $n $head ${state:-UNKNOWN}"
done
