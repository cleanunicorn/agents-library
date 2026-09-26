#!/usr/bin/env bash
# Smoke test for scripts/install-host.sh, run through both host wrappers.
# Runs the installer against temp sandboxes and verifies status lines,
# exit codes, idempotency, --force, filtering, and input validation.
#
# Usage: bash scripts/test-install-host.sh
# Exits 0 if all assertions pass, non-zero otherwise.

set -u

SCRIPT="$(cd "$(dirname "$0")" && pwd)/install-host.sh"
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

run_host_tests() {
  local host="$1" dest=".${host}" out code count

  cd "$tmp"

  # --- project copy: fresh install ---------------------------------------
  rm -rf "$dest"
  out=$(bash "$SCRIPT" "$host" --project 2>&1); code=$?
  assert_contains "$out" "COPIED architect" "$host: project copy installs agents"
  assert_contains "$out" "COPIED review-pr" "$host: project copy installs skills"
  assert_exit 0 "$code" "$host: project copy exit 0"

  # --- re-run: OK ---------------------------------------------------------
  out=$(bash "$SCRIPT" "$host" --project 2>&1); code=$?
  assert_contains "$out" "OK architect" "$host: re-run reports OK"
  assert_exit 0 "$code" "$host: re-run exit 0"

  # --- conflict detection -------------------------------------------------
  echo "x" > "$dest/agents/architect.md"
  out=$(bash "$SCRIPT" "$host" --project architect 2>&1); code=$?
  assert_contains "$out" "CONFLICT architect" "$host: conflict detected"
  assert_exit 2 "$code" "$host: conflict exit 2"

  # --- force overwrite ----------------------------------------------------
  out=$(bash "$SCRIPT" "$host" --project --force architect 2>&1); code=$?
  assert_contains "$out" "UPDATED architect" "$host: force updates"
  assert_exit 0 "$code" "$host: force exit 0"

  # --- agents-only creates no skills/ dir --------------------------------
  rm -rf "$dest"
  bash "$SCRIPT" "$host" --project --agents-only >/dev/null 2>&1
  if [ -d "$dest/skills" ]; then bad "$host: agents-only created skills/"; else ok "$host: agents-only skips skills/"; fi

  # --- global symlink: fresh install -------------------------------------
  rm -rf "$tmp/home-$host"
  out=$(env HOME="$tmp/home-$host" bash "$SCRIPT" "$host" 2>&1); code=$?
  assert_contains "$out" "LINKED architect" "$host: global symlink creates links"
  assert_exit 0 "$code" "$host: global exit 0"

  # --- global re-run: OK --------------------------------------------------
  out=$(env HOME="$tmp/home-$host" bash "$SCRIPT" "$host" 2>&1); code=$?
  assert_contains "$out" "OK architect" "$host: global re-run OK"
  assert_exit 0 "$code" "$host: global re-run exit 0"

  # --- invalid name (path traversal) -------------------------------------
  out=$(bash "$SCRIPT" "$host" --project "../etc" 2>&1); code=$?
  assert_contains "$out" "FATAL" "$host: invalid name rejected"
  assert_exit 1 "$code" "$host: invalid name exit 1"

  # --- unknown name -------------------------------------------------------
  out=$(bash "$SCRIPT" "$host" --project nonexistent 2>&1); code=$?
  assert_contains "$out" "FATAL" "$host: unknown name rejected"
  assert_exit 1 "$code" "$host: unknown name exit 1"

  # --- selective install --------------------------------------------------
  rm -rf "$dest"
  out=$(bash "$SCRIPT" "$host" --project architect review-pr 2>&1); code=$?
  assert_contains "$out" "COPIED architect" "$host: selective installs agent"
  assert_contains "$out" "COPIED review-pr" "$host: selective installs skill"
  assert_exit 0 "$code" "$host: selective exit 0"
  count=$(ls "$dest"/agents/*.md 2>/dev/null | wc -l)
  if [ "$count" = "1" ]; then ok "$host: selective installs exactly 1 agent"
  else bad "$host: selective installed $count agents (expected 1)"; fi
}

# --- unknown host is rejected ---------------------------------------------
out=$(bash "$SCRIPT" unknown-host 2>&1); code=$?
assert_contains "$out" "unknown host" "unknown host rejected"
assert_exit 1 "$code" "unknown host exit 1"

out=$(bash "$SCRIPT" 2>&1); code=$?
assert_contains "$out" "missing host" "missing host rejected"
assert_exit 1 "$code" "missing host exit 1"

for host in opencode kilo; do
  run_host_tests "$host"
done

echo
echo "Results: $pass passed, $fail failed"
exit "$fail"
