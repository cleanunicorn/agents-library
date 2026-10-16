#!/usr/bin/env bash
# Exercise review-target computation in isolated temporary Git repositories.
# Usage: bash scripts/test-diff-target.sh

set -euo pipefail

SCRIPT="$(cd "$(dirname "$0")/../skills/review-pr/scripts" && pwd)/diff-target.sh"
pass=0
fail=0
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_OBJECT_DIRECTORY
unset GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_CONFIG GIT_CONFIG_COUNT GIT_CONFIG_PARAMETERS
unset GIT_EXTERNAL_DIFF GIT_DIFF_OPTS
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_ATTR_NOSYSTEM=1
export GIT_AUTHOR_NAME=Test GIT_COMMITTER_NAME=Test
export GIT_AUTHOR_EMAIL=test@example.invalid GIT_COMMITTER_EMAIL=test@example.invalid
export GIT_AUTHOR_DATE='2000-01-01T00:00:00Z' GIT_COMMITTER_DATE='2000-01-01T00:00:00Z'
export LC_ALL=C GIT_TERMINAL_PROMPT=0

tmp=$(mktemp -d)
trap 'cd / && rm -rf "$tmp"' EXIT
mkdir "$tmp/template"

assert_equal() {
  if [[ "$1" == "$2" ]]; then
    pass=$((pass + 1))
  else
    echo "FAIL: $case_name: $3 (expected '$1', got '$2')"
    fail=$((fail + 1))
  fi
}

assert_contains() {
  if [[ "$1" == *"$2"* ]]; then
    pass=$((pass + 1))
  else
    echo "FAIL: $case_name: $3 (missing '$2')"
    fail=$((fail + 1))
  fi
}

fixture() {
  case_name=$1
  git init -q -b main --template="$tmp/template" "$tmp/$case_name"
  cd "$tmp/$case_name"
  git config commit.gpgsign false
  git config core.hooksPath "$tmp/template"
  git config color.ui false
  git config core.autocrlf false
  printf 'original\nkeep1\nkeep2\nkeep3\nkeep4\nkeep5\nkeep6\nkeep7\nkeep8\nlast\n' > sample.txt
  git add sample.txt
  git commit -qm baseline
  git checkout -qb feature
}

fingerprint() {
  git rev-parse HEAD
  git ls-files --stage
  git status --porcelain=v1
  while IFS= read -r -d '' path; do
    printf '%s ' "$path"
    if [[ -f "$path" ]]; then
      git hash-object -- "$path"
    else
      echo absent
    fi
  done < <(git ls-files --cached --others --exclude-standard -z)
}

run_target() {
  code=0
  bash "$SCRIPT" "$@" > "$tmp/actual" 2> "$tmp/stderr" || code=$?
  actual=$(cat "$tmp/actual")
  assert_equal 0 "$code" "${1:-default} exit"
  assert_equal '' "$(cat "$tmp/stderr")" "${1:-default} stderr"
}

check_target() {
  local names=$1 before expected_summary
  before=$(fingerprint)
  run_target files
  assert_equal "$names" "$actual" 'sorted unique file union'
  expected_summary='MAIN main'
  if [[ -n "$names" ]]; then
    expected_summary+=$'\n'"$names"
  fi
  run_target
  assert_equal "$expected_summary" "$actual" 'default summary'
  run_target summary
  assert_equal "$expected_summary" "$actual" 'explicit summary'
  run_target main
  assert_equal main "$actual" 'detected main'

  # Independent Git transitions define the stream, including distinct bases.
  git diff main...HEAD > "$tmp/expected"
  git diff --cached >> "$tmp/expected"
  git diff >> "$tmp/expected"
  run_target diff
  patch=$actual
  if cmp -s "$tmp/expected" "$tmp/actual"; then
    pass=$((pass + 1))
  else
    echo "FAIL: $case_name: committed/index/worktree patch stream"
    fail=$((fail + 1))
  fi
  assert_equal "$before" "$(fingerprint)" 'target computation preserves repository state'
}

fixture clean
check_target ''
assert_equal '' "$patch" 'clean patch'

fixture staged-modify
printf 'staged-only\n' > sample.txt
git add sample.txt
check_target sample.txt
assert_contains "$patch" '+staged-only' 'staged modification'

fixture staged-add
printf 'staged-new\n' > added.txt
git add added.txt
check_target added.txt
assert_contains "$patch" 'new file mode' 'staged addition header'
assert_contains "$patch" '+staged-new' 'staged addition content'

fixture staged-delete
git rm -q sample.txt
check_target sample.txt
assert_contains "$patch" 'deleted file mode' 'staged deletion header'
assert_contains "$patch" '-original' 'staged deletion content'

fixture partial-disjoint
sed 's/original/staged-first/' sample.txt > edited
mv edited sample.txt
git add sample.txt
sed 's/last/unstaged-last/' sample.txt > edited
mv edited sample.txt
check_target sample.txt
assert_contains "$patch" '+staged-first' 'staged partial hunk'
assert_contains "$patch" '+unstaged-last' 'unstaged partial hunk'
assert_equal 2 "$(printf '%s\n' "$patch" | grep -c '^diff --git ' || true)" 'two partial transitions'

fixture partial-same-line
printf 'staged-middle\n' > sample.txt
git add sample.txt
printf 'unstaged-final\n' > sample.txt
check_target sample.txt
assert_contains "$patch" '+staged-middle' 'index content survives replacement'
assert_contains "$patch" '-staged-middle' 'unstaged patch uses index base'
assert_contains "$patch" '+unstaged-final' 'worktree content survives replacement'

fixture partial-cancel
printf 'staged-cancelled\n' > sample.txt
git add sample.txt
git show HEAD:sample.txt > sample.txt
check_target sample.txt
assert_contains "$patch" '+staged-cancelled' 'cancelled index edit retained'
assert_contains "$patch" '-staged-cancelled' 'cancelling worktree edit retained'
assert_contains "$patch" '+original' 'restored worktree content'
assert_equal 2 "$(printf '%s\n' "$patch" | grep -c '^diff --git ' || true)" 'two cancelling transitions'

fixture partial-add
printf 'added-index\n' > added.txt
git add added.txt
printf 'added-worktree\n' > added.txt
check_target added.txt
assert_contains "$patch" '+added-index' 'new file index content'
assert_contains "$patch" '+added-worktree' 'new file worktree content'

fixture committed
printf 'committed-only\n' > sample.txt
git add sample.txt
git commit -qm change
check_target sample.txt
assert_contains "$patch" '+committed-only' 'committed change retained'

fixture unstaged
printf 'unstaged-only\n' > sample.txt
check_target sample.txt
assert_contains "$patch" '+unstaged-only' 'unstaged change retained'

fixture untracked
printf 'untracked-content\n' > untracked.txt
check_target untracked.txt
assert_equal '' "$patch" 'untracked has no patch'

fixture combined
printf 'committed-stage\n' > sample.txt
git add sample.txt
git commit -qm change
printf 'index-stage\n' > sample.txt
printf 'new-index\n' > z-added.txt
git add sample.txt z-added.txt
printf 'worktree-stage\n' > sample.txt
printf 'untracked\n' > a-untracked.txt
check_target $'a-untracked.txt\nsample.txt\nz-added.txt'
assert_contains "$patch" '+committed-stage' 'committed transition retained'
assert_contains "$patch" '+index-stage' 'index transition retained'
assert_contains "$patch" '+worktree-stage' 'worktree transition retained'

case_name=usage
code=0
bash "$SCRIPT" invalid > "$tmp/actual" 2> "$tmp/stderr" || code=$?
assert_equal 2 "$code" 'invalid mode exit'
assert_equal '' "$(cat "$tmp/actual")" 'invalid mode stdout'
assert_contains "$(cat "$tmp/stderr")" 'usage:' 'invalid mode diagnostic'

fixture no-main
git branch -D main >/dev/null
code=0
bash "$SCRIPT" files > "$tmp/actual" 2> "$tmp/stderr" || code=$?
assert_equal 1 "$code" 'no main exit'
assert_equal '' "$(cat "$tmp/actual")" 'no main stdout'
assert_contains "$(cat "$tmp/stderr")" 'FATAL cannot detect the main branch' 'no main diagnostic'

printf '\nResults: %s passed, %s failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]]
