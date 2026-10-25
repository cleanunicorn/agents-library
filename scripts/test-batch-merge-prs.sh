#!/usr/bin/env bash
# Exercise merge-prs.sh's conflict pause, --continue and --skip against real
# temporary Git repositories: a local bare remote serving refs/pull/<n>/head,
# a read-only gh stub, and a fixed clock for auto-named branches.
# Usage: bash scripts/test-batch-merge-prs.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/skills/batch-merge-prs/scripts/merge-prs.sh"
ATTRIBUTE="$ROOT/skills/batch-merge-prs/scripts/attribute-failure.sh"
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
mkdir "$tmp/template" "$tmp/bin" "$tmp/failhooks" "$tmp/gitwrap"
export GH_LOG="$tmp/gh.log"

# gh may only read PR titles; any other call is a GitHub write attempt.
cat > "$tmp/bin/gh" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$GH_LOG"
if [ "$1 $2" = "pr view" ]; then echo "Title $3"; exit 0; fi
exit 1
EOF
# A fixed clock makes `auto` deterministic, so a collision can be staged.
cat > "$tmp/bin/date" <<'EOF'
#!/usr/bin/env bash
echo 20000101-0000
EOF
# A merge that fails without conflicts: the pre-merge-commit hook refuses.
cat > "$tmp/failhooks/pre-merge-commit" <<'EOF'
#!/bin/sh
exit 1
EOF
# A git whose `merge --abort` fails, to prove a failed abort stops the queue.
cat > "$tmp/gitwrap/git" <<EOF
#!/usr/bin/env bash
if [ "\$1 \${2:-}" = "merge --abort" ]; then exit 1; fi
exec $(command -v git) "\$@"
EOF
# A git whose merge-tree reports a tree and no conflicted paths.
mkdir "$tmp/emptytree"
cat > "$tmp/emptytree/git" <<EOF
#!/usr/bin/env bash
if [ "\$1" = merge-tree ]; then echo 0000000000000000000000000000000000000000; exit 0; fi
exec $(command -v git) "\$@"
EOF
chmod +x "$tmp/bin/gh" "$tmp/bin/date" "$tmp/failhooks/pre-merge-commit" "$tmp/gitwrap/git" \
  "$tmp/emptytree/git"
export PATH="$tmp/bin:$PATH"

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

assert_not_contains() {
  if [[ "$1" != *"$2"* ]]; then
    pass=$((pass + 1))
  else
    echo "FAIL: $case_name: $3 (unexpected '$2')"
    fail=$((fail + 1))
  fi
}

configure() {
  git config commit.gpgsign false
  git config core.hooksPath "$tmp/template"
  git config color.ui false
  git config core.autocrlf false
}

# fixture <name>: a bare remote whose main holds README.md and notes.txt.
fixture() {
  case_name=$1
  dir="$tmp/$case_name"
  git init -q --bare -b main "$dir/origin.git"
  git init -q -b main --template="$tmp/template" "$dir/seed"
  cd "$dir/seed"
  configure
  printf 'line1\nline2\nline3\n' > README.md
  printf 'note\n' > notes.txt
  git add -A
  git commit -qm base
  git remote add origin "$dir/origin.git"
  git push -q origin main
  : > "$GH_LOG"
}

# pr <n> <path> <content> [<path> <content>]...: PR n branches off the
# current main and is published only as refs/pull/<n>/head.
pr() {
  local n=$1 back=$PWD
  shift
  cd "$dir/seed"
  git checkout -q -B "pr-$n" main
  while [ "$#" -gt 0 ]; do
    printf '%b' "$2" > "$1"
    shift 2
  done
  git add -A
  git commit -qm "pr $n"
  git push -qf origin "HEAD:refs/pull/$n/head"   # -f: a PR head may move
  git checkout -q main
  cd "$back"
}

# main_change <path> <content>|--rm: advance the remote main.
main_change() {
  cd "$dir/seed"
  if [ "$2" = --rm ]; then git rm -q "$1"; else printf '%b' "$2" > "$1"; git add "$1"; fi
  git commit -qm "main: $1"
  git push -q origin main
}

clone_work() {
  git clone -q "$dir/origin.git" "$dir/work"
  cd "$dir/work"
  configure
}

pr_head() { git -C "$dir/seed" rev-parse "refs/heads/pr-$1"; }

run_merge() {
  code=0
  bash "$SCRIPT" "$@" > "$tmp/out" 2> "$tmp/err" || code=$?
  out=$(cat "$tmp/out")
  err=$(cat "$tmp/err")
}

# The SHA a ledger line names: `MERGED <n> <sha>`.
merged_sha() { sed -n "s/^MERGED $1 //p" "$tmp/out"; }

# Everything GitHub and the user's main could be written through.
protected_refs() {
  git -C "$dir/origin.git" for-each-ref
  git -C "$dir/work" rev-parse refs/heads/main
}

merge_state() {
  git rev-parse HEAD
  git rev-parse -q --verify MERGE_HEAD || echo no-merge
  git ls-files --stage
  git status --porcelain=v1
}

# --- Two PRs conflict with each other, twice in one queue ------------------

fixture pr-vs-pr
pr 1 README.md 'A1\nline2\nline3\n'
pr 2 README.md 'B1\nline2\nline3\n'
pr 3 notes.txt 'note C\n'
pr 4 notes.txt 'note D\n'
clone_work
before=$(protected_refs)

run_merge origin main batch-1 1 2 3 4
assert_equal 3 "$code" 'first conflict pauses with exit 3'
assert_contains "$out" 'TARGET batch-1 created-from origin/main' 'target line'
assert_contains "$out" "CONFLICT 2 $(pr_head 2) README.md" 'conflict line names PR, head and path'
assert_contains "$out" $'\nPENDING 3 4' 'remaining queue is returned'
assert_not_contains "$out" 'SKIPPED' 'a conflict is not skipped'
assert_equal "$(pr_head 2)" "$(git rev-parse -q --verify MERGE_HEAD || true)" 'merge left in progress'
m1=$(merged_sha 1)

printf 'A1 B1\nline2\nline3\n' > README.md
git add README.md
printf 'README.md: PR 1 set A1, PR 2 set B1 on the same line; kept both.\n' > "$tmp/rec-2.md"
run_merge --continue origin batch-1 2 "$tmp/rec-2.md" 3 4
assert_equal 3 "$code" 'second conflict pauses again'
m2=$(merged_sha 2)
assert_contains "$out" "RESOLVED 2 $m2 $tmp/rec-2.md" 'resolution recorded against its merge'
assert_contains "$out" "CONFLICT 4 $(pr_head 4) notes.txt" 'second conflict reported'
assert_equal 'PENDING' "$(grep '^PENDING' "$tmp/out")" 'nothing left after PR 4'
m3=$(merged_sha 3)
assert_equal 3 "$(git rev-list --parents -n 1 "$m2" | wc -w | tr -d ' ')" 'resolved merge has two parents'
assert_equal "$(pr_head 2)" "$(git rev-parse "$m2^2")" 'second parent is the PR head'
assert_equal $'A1 B1\nline2\nline3' "$(git show "$m2:README.md")" 'both intents kept'
assert_equal 'Merge PR #2: Title 2' "$(git log -1 --format=%B "$m2" | sed '/^$/d')" 'merge message has no conflict comments'

printf 'note C D\n' > notes.txt
git add notes.txt
printf 'notes.txt: kept C from PR 3 and D from PR 4.\n' > "$tmp/rec-4.md"
run_merge --continue origin batch-1 4 "$tmp/rec-4.md"
assert_equal 0 "$code" 'queue finishes'
m4=$(merged_sha 4)
assert_contains "$out" "RESOLVED 4 $m4" 'second resolution recorded'
assert_equal '' "$(git status --porcelain)" 'tree clean after the queue'
assert_equal $'Merge PR #1: Title 1\nMerge PR #2: Title 2\nMerge PR #3: Title 3\nMerge PR #4: Title 4' \
  "$(git log --reverse --first-parent --format=%s origin/main..HEAD)" 'merge order preserved'
assert_equal "$before" "$(protected_refs)" 'remote refs and main unchanged'
assert_equal '' "$(grep -v '^pr view ' "$GH_LOG" || true)" 'gh only read PR titles'

code=0
bash "$ATTRIBUTE" "$tmp/attr" origin/main '! grep -q B1 README.md' \
  1="$m1" 2="$m2" 3="$m3" 4="$m4" > "$tmp/out" 2> "$tmp/err" || code=$?
assert_contains "$(cat "$tmp/out")" 'CULPRIT 2' 'attribution names the resolved PR'
assert_equal batch-1 "$(git symbolic-ref --short HEAD)" 'attribution returns to the batch branch'

# --- A PR conflicts with main: content, modify/delete, a path with a space --

fixture pr-vs-main
main_change 'a b.txt' 'old\n'
pr 1 README.md 'P1\nline2\nline3\n' 'a b.txt' 'pr\n'
main_change README.md 'M1\nline2\nline3\n'
main_change 'a b.txt' --rm
clone_work
# A non-default comment prefix changes MERGE_MSG's conflict block; the
# record check must not depend on it.
git config core.commentChar ';'
before=$(protected_refs)

run_merge origin main auto 1
assert_equal 3 "$code" 'conflict with main pauses'
assert_contains "$out" 'TARGET batch/20000101-0000 created-from origin/main' 'auto names the branch'
assert_contains "$out" "CONFLICT 1 $(pr_head 1) README.md" 'content conflict listed'
assert_contains "$out" "CONFLICT 1 $(pr_head 1) a b.txt" 'modify/delete path with a space listed whole'

printf 'M1 P1\nline2\nline3\n' > README.md
git add README.md 'a b.txt'
printf 'README.md: main set M1, PR set P1; kept both.\n' > "$tmp/rec-1.md"
state=$(merge_state)
run_merge --continue origin batch/20000101-0000 1 "$tmp/rec-1.md"
assert_equal 1 "$code" 'record must name every conflicted path'
assert_contains "$err" 'a b.txt' 'missing path named'
assert_equal "$state" "$(merge_state)" 'rejected continue changes nothing'

printf 'a b.txt: PR edited a file main deleted; kept the PR edit.\n' >> "$tmp/rec-1.md"
run_merge --continue origin batch/20000101-0000 1 "$tmp/rec-1.md"
assert_equal 0 "$code" 'complete record continues'
m1=$(merged_sha 1)
assert_equal 'pr' "$(git show "$m1:a b.txt")" 'modify/delete resolved as recorded'
assert_equal 'Merge PR #1: Title 1' "$(git log -1 --format=%B "$m1" | sed '/^$/d')" \
  'conflict comments stripped under any comment prefix'
assert_equal "$before" "$(protected_refs)" 'remote refs and main unchanged'

# --- Guards on --continue, then an explicit --skip -------------------------

fixture skip
pr 1 README.md 'A1\nline2\nline3\n'
pr 2 README.md 'B1\nline2\nline3\n'
pr 3 notes.txt 'note C\n'
clone_work
before=$(protected_refs)
run_merge origin main batch-1 1 2 3
assert_equal 3 "$code" 'paused on PR 2'
printf 'README.md: kept both.\n' > "$tmp/rec-2.md"
state=$(merge_state)

run_merge --continue origin batch-1 2 "$tmp/rec-2.md" 3
assert_equal 1 "$code" 'unresolved paths refuse continue'
assert_contains "$err" 'unresolved' 'unresolved diagnostic'
assert_equal "$state" "$(merge_state)" 'unresolved continue changes nothing'

printf 'A1 B1\nline2\nline3\n' > README.md
git add README.md
printf 'extra\n' >> README.md
run_merge --continue origin batch-1 2 "$tmp/rec-2.md" 3
assert_equal 1 "$code" 'unstaged changes refuse continue'
assert_contains "$err" 'unstaged' 'unstaged diagnostic'
printf 'A1 B1\nline2\nline3\n' > README.md
state=$(merge_state)

run_merge --continue origin batch-1 2 "$tmp/missing.md" 3
assert_equal 1 "$code" 'missing record refuses continue'
printf 'notes only\n' > "$tmp/rec-wrong.md"
run_merge --continue origin batch-1 2 "$tmp/rec-wrong.md" 3
assert_equal 1 "$code" 'record without the path refuses continue'
run_merge --continue origin batch-2 2 "$tmp/rec-2.md" 3
assert_equal 1 "$code" 'wrong target refuses continue'
run_merge --continue origin batch-1 3 "$tmp/rec-2.md"
assert_equal 1 "$code" 'wrong PR refuses continue'
assert_contains "$err" 'not PR #3' 'wrong PR diagnostic'
assert_equal "$state" "$(merge_state)" 'rejected continues change nothing'

pr 2 README.md 'B2\nline2\nline3\n'
before=$(protected_refs)
run_merge --continue origin batch-1 2 "$tmp/rec-2.md" 3
assert_equal 1 "$code" 'a PR that moved since the pause refuses continue'
assert_contains "$err" 'moved' 'moved diagnostic'
assert_equal "$state" "$(merge_state)" 'moved continue changes nothing'

run_merge --skip origin batch-1 2 '' 3
assert_equal 2 "$code" 'skip needs a reason'
run_merge --skip origin batch-1 2 'PR 1 and PR 2 retitle line 1 differently' 3
assert_equal 0 "$code" 'skip finishes the queue'
assert_contains "$out" 'SKIPPED 2 unresolved PR 1 and PR 2 retitle line 1 differently' 'skip reason in ledger'
assert_contains "$out" 'MERGED 3 ' 'later PR still merges'
assert_equal $'A1\nline2\nline3' "$(cat README.md)" 'skipped PR left no trace'
assert_equal '' "$(git status --porcelain)" 'tree clean after skip'

run_merge --continue origin batch-1 2 "$tmp/rec-2.md"
assert_equal 1 "$code" 'continue without a pending merge refuses'
assert_contains "$err" 'no merge in progress' 'no pending merge diagnostic'
assert_equal "$before" "$(protected_refs)" 'remote refs and main unchanged'
assert_equal '' "$(grep -v '^pr view ' "$GH_LOG" || true)" 'gh only read PR titles'

# --- Start refuses anything but a fresh branch from a clean tree -----------

fixture start
pr 1 notes.txt 'note C\n'
clone_work
git branch batch-1
git branch batch/20000101-0000
state=$(merge_state)
for target in batch-1 main auto; do
  run_merge origin main "$target" 1
  assert_equal 1 "$code" "existing target $target refused"
  assert_contains "$err" 'already exists' "existing target $target diagnostic"
done
assert_equal main "$(git symbolic-ref --short HEAD)" 'still on main'
assert_equal "$state" "$(merge_state)" 'refused starts change nothing'
run_merge origin main batch-2 '1;true'
assert_equal 2 "$code" 'non-numeric PR refused'
printf 'x\n' > stray.txt
run_merge origin main batch-2 1
assert_equal 1 "$code" 'dirty tree refused'
assert_contains "$err" 'not clean' 'dirty diagnostic'
rm stray.txt

# --- A merge that fails without conflicts is FATAL, not skipped ------------

fixture hook
pr 1 notes.txt 'note C\n'
clone_work
git config core.hooksPath "$tmp/failhooks"
run_merge origin main batch-1 1
assert_equal 1 "$code" 'non-conflict merge failure is fatal'
assert_contains "$err" 'FATAL' 'fatal diagnostic'
assert_not_contains "$out" 'SKIPPED' 'not reported as a skip'
assert_equal '' "$(git status --porcelain)" 'tree restored'
assert_equal no-merge "$(git rev-parse -q --verify MERGE_HEAD || echo no-merge)" 'no merge left in progress'

# --- A failed abort stops the queue and keeps the merge --------------------

fixture abort
pr 1 README.md 'A1\nline2\nline3\n'
pr 2 README.md 'B1\nline2\nline3\n'
pr 3 notes.txt 'note C\n'
clone_work
run_merge origin main batch-1 1 2 3
state=$(merge_state)
code=0
PATH="$tmp/gitwrap:$PATH" bash "$SCRIPT" --skip origin batch-1 2 'contradictory' 3 \
  > "$tmp/out" 2> "$tmp/err" || code=$?
assert_equal 1 "$code" 'failed abort is fatal'
assert_contains "$(cat "$tmp/err")" 'could not abort' 'abort diagnostic'
assert_not_contains "$(cat "$tmp/out")" 'MERGED 3' 'queue stopped'
assert_equal "$state" "$(merge_state)" 'merge state kept for the user'

# --- The prose that drives the script agrees with it ------------------------

case_name=contract
skill_dir="$ROOT/skills/batch-merge-prs"
skill=$(cat "$skill_dir/SKILL.md")
assert_contains "$skill" 'references/conflicts.md' 'Phase 1 links the conflict procedure'
assert_contains "$skill" 'references/test-gate.md' 'resolved merges still reach the test gate'
assert_contains "$skill" 'read-only reviewer using **review-pr**' 'and the read-only review'
procedure=$(cat "$skill_dir/references/conflicts.md")
for op in --continue --skip; do
  assert_contains "$procedure" "merge-prs.sh $op" "procedure shows $op"
done
# The rule this replaced, in the places that described it.
old_rule=$(grep -rniE 'never resolve|SKIPPED <n> conflicts|conflicting PR is aborted|uses it as-is' \
  "$skill_dir" "$ROOT/README.md" "$ROOT/AGENTS.md" "$ROOT/docs" || true)
assert_equal '' "$old_rule" 'the abort-only conflict rule is gone everywhere'
schema=$(grep -B1 'from merge-prs\.sh,' "$ROOT/AGENTS.md" | tr '\n' ' ')
for line in $(sed -n 's/^#       \([A-Z]*\) .*/\1/p' "$SCRIPT" | sort -u); do
  assert_contains "$schema" "$line" "AGENTS.md schema names $line"
done

# --- An empty conflict list fails closed -----------------------------------

fixture empty-list
pr 1 README.md 'A1\nline2\nline3\n'
pr 2 README.md 'B1\nline2\nline3\n'
clone_work
run_merge origin main batch-1 1 2
printf 'A1 B1\nline2\nline3\n' > README.md
git add README.md
printf 'notes only\n' > "$tmp/rec-empty.md"
state=$(merge_state)
code=0
PATH="$tmp/emptytree:$PATH" bash "$SCRIPT" --continue origin batch-1 2 "$tmp/rec-empty.md" \
  > "$tmp/out" 2> "$tmp/err" || code=$?
assert_equal 1 "$code" 'no listed conflicts refuses continue'
assert_contains "$(cat "$tmp/err")" 'could not list' 'empty list diagnostic'
assert_equal "$state" "$(merge_state)" 'empty-list continue changes nothing'

case_name=usage
run_merge
assert_equal 2 "$code" 'no arguments'
assert_contains "$err" 'usage:' 'usage diagnostic'

printf '\nResults: %s passed, %s failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]]
