#!/usr/bin/env bash
# Exercise the shared Herdr workspace-rename step against a stub `herdr`, offline.
# Usage: bash scripts/test-rename-herdr-workspace.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CANONICAL="$ROOT/skills/manager/scripts/rename-herdr-workspace.sh"
COPIES=("$ROOT/skills/file-issues/scripts/rename-herdr-workspace.sh")
pass=0
fail=0
export LC_ALL=C

tmp=$(mktemp -d)
trap 'cd / && rm -rf "$tmp"' EXIT

assert_equal() {
  if [[ "$1" == "$2" ]]; then
    pass=$((pass + 1))
  else
    echo "FAIL: $case_name: $3 (expected '$1', got '$2')"
    fail=$((fail + 1))
  fi
}

# A stub `herdr` that logs its argv one argument per line, and exits with
# $STUB_EXIT so a failing rename can be simulated.
mkdir "$tmp/bin" "$tmp/nobin" "$tmp/my project"
cat > "$tmp/bin/herdr" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$STUB_LOG"
echo "herdr: noisy output"
exit "${STUB_EXIT:-0}"
STUB
chmod +x "$tmp/bin/herdr"
# bash without herdr, for the herdr-missing case.
ln -s "$(command -v bash)" "$tmp/nobin/bash"

# run <script> <label> [env...] — sets code, out, err, calls.
run() {
  local script=$1 label=$2
  shift 2
  rm -f "$tmp/log"
  code=0
  (cd "$tmp/my project" && env STUB_LOG="$tmp/log" "$@" bash "$script" "$label") \
    > "$tmp/out" 2> "$tmp/err" || code=$?
  out=$(cat "$tmp/out")
  err=$(cat "$tmp/err")
  calls=$(cat "$tmp/log" 2>/dev/null || true)
}

in_herdr=(PATH="$tmp/bin:$PATH" HERDR_ENV=1 HERDR_WORKSPACE_ID="w1" HERDR_TAB_ID="w1:t2")

# The label is the bare skill name: the sidebar already shows the project.
case_name=manager
run "$CANONICAL" manager "${in_herdr[@]}"
assert_equal 0 "$code" 'exit'
assert_equal $'workspace\nrename\nw1\nmanager' "$calls" 'herdr argv'
assert_equal '' "$out$err" 'silent on success'

case_name=issues
run "$CANONICAL" issues "${in_herdr[@]}"
assert_equal $'workspace\nrename\nw1\nissues' "$calls" 'issues label'

for env_case in "outside:HERDR_ENV=" "env-not-1:HERDR_ENV=0" "no-workspace-id:HERDR_WORKSPACE_ID="; do
  case_name=${env_case%%:*}
  run "$CANONICAL" manager "${in_herdr[@]}" "${env_case#*:}"
  assert_equal 0 "$code" 'exit'
  assert_equal '' "$calls" 'herdr not called'
  assert_equal '' "$out$err" 'silent'
done

case_name=herdr-missing
run "$CANONICAL" manager PATH="$tmp/nobin" HERDR_ENV=1 HERDR_WORKSPACE_ID=w1
assert_equal 0 "$code" 'never blocks'
assert_equal 1 "$(printf '%s\n' "$err" | grep -c .)" 'one warning line'
assert_equal '' "$out" 'stdout silent'

case_name=rename-fails
run "$CANONICAL" manager "${in_herdr[@]}" STUB_EXIT=3
assert_equal 0 "$code" 'never blocks'
assert_equal 1 "$(printf '%s\n' "$err" | grep -c .)" 'one warning line'
assert_equal '' "$out" 'herdr output suppressed'

case_name=usage
run "$CANONICAL" "" "${in_herdr[@]}"
assert_equal 2 "$code" 'missing label exit'
assert_equal '' "$calls" 'herdr not called'

# Each skill installs alone, so every copy must match and run from its own
# directory with no repository around it.
for copy in "${COPIES[@]}"; do
  case_name="copy:${copy#"$ROOT/"}"
  code=0
  cmp -s "$CANONICAL" "$copy" || code=$?
  assert_equal 0 "$code" 'byte-identical to the manager copy'
  skill=$(basename "$(dirname "$(dirname "$copy")")")
  cp -R "$(dirname "$(dirname "$copy")")" "$tmp/installed-$skill"
  run "$tmp/installed-$skill/scripts/rename-herdr-workspace.sh" issues "${in_herdr[@]}"
  assert_equal $'workspace\nrename\nw1\nissues' "$calls" 'standalone copy runs'
done

# The callers' wording is the other half of the contract: each skill calls
# the helper by its path with its own label, and none still renames a tab.
for caller in "manager:skills/manager/SKILL.md" "manager:skills/manager/references/herdr.md" \
              "issues:skills/file-issues/SKILL.md"; do
  case_name="caller:${caller#*:}"
  text=$(tr -s ' \n' '  ' < "$ROOT/${caller#*:}")
  code=0; grep -qF "bash <skill>/scripts/rename-herdr-workspace.sh ${caller%%:*}" <<< "$text" || code=$?
  assert_equal 0 "$code" 'calls the helper by the skill path'
  code=0; grep -qE "rename-herdr-tab|HERDR_TAB_ID" <<< "$text" || code=$?
  assert_equal 1 "$code" 'no tab rename left'
done

printf '\nResults: %s passed, %s failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]]
