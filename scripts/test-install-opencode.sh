#!/usr/bin/env bash
# Smoke test for scripts/install-opencode.sh.
# Runs the installer against temp sandboxes and verifies status lines,
# exit codes, idempotency, --force, filtering, and input validation.
#
# Usage: bash scripts/test-install-opencode.sh
# Exits 0 if all assertions pass, non-zero otherwise.

set -u

SCRIPT="$(cd "$(dirname "$0")" && pwd)/install-opencode.sh"
pass=0
fail=0

ok()   { pass=$((pass + 1)); }
bad()  { echo "FAIL: $1"; fail=$((fail + 1)); }

assert_contains() {
  echo "$1" | grep -q "$2" && ok || bad "$3 (expected '$2')"
}

assert_exit() {
  [ "$1" = "$2" ] && ok || bad "$3 (expected exit $1, got $2)"
}

tmp=$(mktemp -d)
trap 'cd / && rm -rf "$tmp"' EXIT

# --- project copy: fresh install ---------------------------------------
cd "$tmp"
out=$(bash "$SCRIPT" --project 2>&1); code=$?
assert_contains "$out" "COPIED architect" "project copy installs agents"
assert_contains "$out" "COPIED review-pr" "project copy installs skills"
assert_exit 0 "$code" "project copy exit 0"

# --- re-run: OK ---------------------------------------------------------
out=$(bash "$SCRIPT" --project 2>&1); code=$?
assert_contains "$out" "OK architect" "re-run reports OK"
assert_exit 0 "$code" "re-run exit 0"

# --- conflict detection -------------------------------------------------
echo "x" > .opencode/agents/architect.md
out=$(bash "$SCRIPT" --project architect 2>&1); code=$?
assert_contains "$out" "CONFLICT architect" "conflict detected"
assert_exit 2 "$code" "conflict exit 2"

# --- force overwrite ----------------------------------------------------
out=$(bash "$SCRIPT" --project --force architect 2>&1); code=$?
assert_contains "$out" "UPDATED architect" "force updates"
assert_exit 0 "$code" "force exit 0"

# --- agents-only creates no skills/ dir --------------------------------
rm -rf .opencode
bash "$SCRIPT" --project --agents-only >/dev/null 2>&1
[ -d .opencode/skills ] && bad "agents-only created skills/" || ok "agents-only skips skills/"

# --- global symlink: fresh install -------------------------------------
out=$(env HOME="$tmp/home1" bash "$SCRIPT" 2>&1); code=$?
assert_contains "$out" "LINKED architect" "global symlink creates links"
assert_exit 0 "$code" "global exit 0"

# --- global re-run: OK --------------------------------------------------
out=$(env HOME="$tmp/home1" bash "$SCRIPT" 2>&1); code=$?
assert_contains "$out" "OK architect" "global re-run OK"
assert_exit 0 "$code" "global re-run exit 0"

# --- invalid name (path traversal) -------------------------------------
out=$(bash "$SCRIPT" --project "../etc" 2>&1); code=$?
assert_contains "$out" "FATAL" "invalid name rejected"
assert_exit 1 "$code" "invalid name exit 1"

# --- unknown name -------------------------------------------------------
out=$(bash "$SCRIPT" --project nonexistent 2>&1); code=$?
assert_contains "$out" "FATAL" "unknown name rejected"
assert_exit 1 "$code" "unknown name exit 1"

# --- selective install --------------------------------------------------
rm -rf .opencode
out=$(bash "$SCRIPT" --project architect review-pr 2>&1); code=$?
assert_contains "$out" "COPIED architect" "selective installs agent"
assert_contains "$out" "COPIED review-pr" "selective installs skill"
assert_exit 0 "$code" "selective exit 0"
count=$(ls .opencode/agents/*.md 2>/dev/null | wc -l)
[ "$count" = "1" ] && ok "selective installs exactly 1 agent" || bad "selective installed $count agents (expected 1)"

echo
echo "Results: $pass passed, $fail failed"
exit "$fail"
