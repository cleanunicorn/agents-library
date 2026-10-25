#!/usr/bin/env bash
# Exercise the shared Herdr tab-rename step against a stub `herdr`, offline.
# Usage: bash scripts/test-rename-herdr-tab.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CANONICAL="$ROOT/skills/manager/scripts/rename-herdr-tab.sh"
COPIES=("$ROOT/skills/file-issues/scripts/rename-herdr-tab.sh")
pass=0
fail=0
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 LC_ALL=C

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
mkdir "$tmp/bin" "$tmp/nobin"
cat > "$tmp/bin/herdr" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$STUB_LOG"
echo "herdr: noisy output"
exit "${STUB_EXIT:-0}"
EOF
chmod +x "$tmp/bin/herdr"
# git without herdr, for the herdr-missing case.
ln -s "$(command -v git)" "$tmp/nobin/git"
for tool in bash basename dirname; do ln -s "$(command -v "$tool")" "$tmp/nobin/$tool"; done

# run <script> <dir> <prefix> [env...] — sets code, out, err, calls.
run() {
  local script=$1 dir=$2 prefix=$3
  shift 3
  rm -f "$tmp/log"
  code=0
  (cd "$dir" && env STUB_LOG="$tmp/log" "$@" bash "$script" "$prefix") \
    > "$tmp/out" 2> "$tmp/err" || code=$?
  out=$(cat "$tmp/out")
  err=$(cat "$tmp/err")
  calls=$(cat "$tmp/log" 2>/dev/null || true)
}

in_herdr=(PATH="$tmp/bin:$PATH" HERDR_ENV=1 HERDR_TAB_ID="w1:t2")

git init -q "$tmp/my project"
mkdir -p "$tmp/my project/src/deep" "$tmp/plain dir"

case_name=git-toplevel
run "$CANONICAL" "$tmp/my project" manager "${in_herdr[@]}"
assert_equal 0 "$code" 'exit'
assert_equal $'tab\nrename\nw1:t2\nmanager my project' "$calls" 'herdr argv'
assert_equal '' "$out$err" 'silent on success'

case_name=nested-dir
run "$CANONICAL" "$tmp/my project/src/deep" manager "${in_herdr[@]}"
assert_equal $'tab\nrename\nw1:t2\nmanager my project' "$calls" 'toplevel, not cwd'

case_name=no-git-fallback
run "$CANONICAL" "$tmp/plain dir" manager "${in_herdr[@]}"
assert_equal $'tab\nrename\nw1:t2\nmanager plain dir' "$calls" 'cwd basename'

case_name=issues-prefix
run "$CANONICAL" "$tmp/my project" issues "${in_herdr[@]}"
assert_equal $'tab\nrename\nw1:t2\nissues my project' "$calls" 'issues label'

for env_case in "outside:HERDR_ENV=" "env-not-1:HERDR_ENV=0" "no-tab-id:HERDR_TAB_ID="; do
  case_name=${env_case%%:*}
  run "$CANONICAL" "$tmp/my project" manager "${in_herdr[@]}" "${env_case#*:}"
  assert_equal 0 "$code" 'exit'
  assert_equal '' "$calls" 'herdr not called'
  assert_equal '' "$out$err" 'silent'
done

case_name=herdr-missing
run "$CANONICAL" "$tmp/my project" manager PATH="$tmp/nobin" HERDR_ENV=1 HERDR_TAB_ID=w1:t2
assert_equal 0 "$code" 'never blocks'
assert_equal 1 "$(printf '%s\n' "$err" | grep -c .)" 'one warning line'
assert_equal '' "$out" 'stdout silent'

case_name=rename-fails
run "$CANONICAL" "$tmp/my project" manager "${in_herdr[@]}" STUB_EXIT=3
assert_equal 0 "$code" 'never blocks'
assert_equal 1 "$(printf '%s\n' "$err" | grep -c .)" 'one warning line'
assert_equal '' "$out" 'herdr output suppressed'

case_name=usage
run "$CANONICAL" "$tmp/my project" "" "${in_herdr[@]}"
assert_equal 2 "$code" 'missing prefix exit'
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
  run "$tmp/installed-$skill/scripts/rename-herdr-tab.sh" "$tmp/plain dir" issues "${in_herdr[@]}"
  assert_equal $'tab\nrename\nw1:t2\nissues plain dir' "$calls" 'standalone copy runs'
done

# A plugin install puts the skill in its own git checkout (the plugin cache).
# Called by path from the project, the label must name the project.
case_name=plugin-cache
git init -q "$tmp/plugin-cache"
cp -R "$ROOT/skills/manager" "$tmp/plugin-cache/manager"
run "$tmp/plugin-cache/manager/scripts/rename-herdr-tab.sh" "$tmp/my project/src" manager "${in_herdr[@]}"
assert_equal $'tab\nrename\nw1:t2\nmanager my project' "$calls" 'project, not the skill checkout'

# The callers' wording is the other half of the contract: run from the
# project by the skill's path. "Run it from this skill's directory" labeled
# every installed session after the skill (`manager manager`).
for caller in "manager:skills/manager/SKILL.md" "manager:skills/manager/references/herdr.md" \
              "issues:skills/file-issues/SKILL.md"; do
  case_name="caller:${caller#*:}"
  text=$(tr -s ' \n' '  ' < "$ROOT/${caller#*:}")
  code=0; grep -qF "bash <skill>/scripts/rename-herdr-tab.sh ${caller%%:*}" <<< "$text" || code=$?
  assert_equal 0 "$code" 'calls the helper by the skill path'
  code=0; grep -qiE "rename-herdr-tab\.sh [a-z]+\`? from this skill's directory" <<< "$text" || code=$?
  assert_equal 1 "$code" 'never runs it from the skill directory'
done

printf '\nResults: %s passed, %s failed\n' "$pass" "$fail"
[[ "$fail" -eq 0 ]]
