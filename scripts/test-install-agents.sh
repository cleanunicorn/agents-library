#!/usr/bin/env bash
# Regression tests for the skill-local installer, using disposable projects.
# Command failures are injected even as root; filesystem cases exercise real
# destination and redirection errors independently of the injected failures.
# Usage: bash scripts/test-install-agents.sh

set -u

SCRIPT="$(cd "$(dirname "$0")/../skills/install-agents/scripts" && pwd)/install-agents.sh"
pass=0
fail=0
skip=0
tmp=$(mktemp -d) || exit 1
trap 'chmod -R u+w "$tmp"; rm -rf "$tmp"' EXIT
mkdir -p "$tmp/source definitions" "$tmp/bin"
src="$tmp/source definitions"
printf 'source architect\n' > "$src/architect.md"
printf 'source deadwood\n' > "$src/deadwood.md"
real_cp=$(command -v cp)
real_mkdir=$(command -v mkdir)

# Only the child installer sees these wrappers. A silent failure ensures the
# installer's own diagnostic is tested, rather than an incidental cp message.
cat > "$tmp/bin/command-wrapper" <<'WRAPPER'
#!/usr/bin/env bash
command_name=${0##*/}
if [ "$INJECT" = "$command_name" ]; then
  printf '%s\n' "$command_name" >> "$MARKER"
  exit 73
fi
case "$command_name" in
  cp) exec "$REAL_CP" "$@" ;;
  mkdir) exec "$REAL_MKDIR" "$@" ;;
esac
exit 74
WRAPPER
chmod +x "$tmp/bin/command-wrapper"
ln -s command-wrapper "$tmp/bin/cp"
ln -s command-wrapper "$tmp/bin/mkdir"
cat > "$tmp/fail-printf.bash" <<'INJECTION'
printf() {
  builtin printf 'printf\n' >> "$MARKER"
  return 73
}
INJECTION

check() {
  local message=$1
  shift
  if "$@"; then
    pass=$((pass + 1))
  else
    echo "FAIL [$case_name]: $message"
    fail=$((fail + 1))
  fi
}
has() { grep -Fxq "$1" "$stdout"; }
lacks() { ! has "$1"; }
no_success() { ! grep -Eq '^(INSTALLED|UPDATED|IDENTICAL|JOURNAL) ' "$stdout"; }
new_case() {
  case_name=$1
  project="$tmp/$case_name/project"
  mkdir -p "$project/.claude/agents/journals"
  dest="$project/.claude/agents"
  stdout="$tmp/$case_name/stdout"
  stderr="$tmp/$case_name/stderr"
  marker="$tmp/$case_name/marker"
  injection=none
}
run() {
  local bash_env=/dev/null
  [ "$injection" = printf ] && bash_env="$tmp/fail-printf.bash"
  (
    cd "$project" || exit 99
    unset GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR GIT_INDEX_FILE
    export GIT_CEILING_DIRECTORIES="$tmp"
    export PATH="$tmp/bin:$PATH" INJECT="$injection" MARKER="$marker"
    export REAL_CP="$real_cp" REAL_MKDIR="$real_mkdir" BASH_ENV="$bash_env"
    bash "$SCRIPT" "$src" "$@"
  ) > "$stdout" 2> "$stderr"
  code=$?
}
failed_definition() {
  check 'failure exit' test "$code" -eq 3
  check 'FAILED ledger' has 'FAILED architect'
  check 'no definition success' lacks 'INSTALLED architect'
  check 'no update success' lacks 'UPDATED architect'
  check 'no journal success' lacks 'JOURNAL architect'
  check 'journal not seeded' test ! -e "$dest/journals/architect.md"
  check 'contextual error' grep -Fq "$dest/architect.md" "$stderr"
}

for force in no yes; do
  args=(architect)
  [ "$force" = yes ] && args=(--force architect)
  new_case "dangling-$force"
  ln -s "$project/missing-target" "$dest/architect.md"
  run "${args[@]}"
  failed_definition
  check 'link retained' test -L "$dest/architect.md"
  check 'target absent' test ! -e "$project/missing-target"

  new_case "directory-$force"
  mkdir "$dest/architect.md"
  run "${args[@]}"
  failed_definition
  check 'directory retained' test -d "$dest/architect.md"
  check 'no nested copy' test ! -e "$dest/architect.md/architect.md"
done

new_case mkdir-obstruction
rm -rf "$project/.claude"
printf 'obstruction\n' > "$project/.claude"
run architect
check 'mkdir obstruction exits 1' test "$code" -eq 1
check 'mkdir diagnostic' grep -Fq FATAL "$stderr"
check 'no success after mkdir failure' no_success

new_case injected-mkdir
injection=mkdir
run architect
check 'injected mkdir exits 1' test "$code" -eq 1
check 'mkdir was invoked' grep -Fxq mkdir "$marker"
check 'installer mkdir diagnostic' grep -Fq FATAL "$stderr"
check 'no success after injected mkdir failure' no_success

for force in no yes; do
  new_case "injected-copy-$force"
  args=(architect)
  if [ "$force" = yes ]; then
    printf 'customized\n' > "$dest/architect.md"
    cp "$dest/architect.md" "$project/expected"
    args=(--force architect)
  fi
  injection=cp
  run "${args[@]}"
  failed_definition
  check 'cp was invoked' grep -Fxq cp "$marker"
  if [ "$force" = yes ]; then
    check 'silent failed cp preserves fixture' cmp -s "$project/expected" "$dest/architect.md"
  else
    check 'failed cp did not install' test ! -e "$dest/architect.md"
  fi
done

for shape in directory bad-parent printf; do
  new_case "journal-$shape"
  case "$shape" in
    directory) mkdir "$dest/journals/architect.md" ;;
    bad-parent)
      printf 'obstruction\n' > "$project/obstruction"
      ln -s "$project/obstruction/journal.md" "$dest/journals/architect.md"
      ;;
    printf) injection=printf ;;
  esac
  run architect
  check 'journal failure exit' test "$code" -eq 3
  check 'definition success retained' has 'INSTALLED architect'
  check 'definition bytes' cmp -s "$src/architect.md" "$dest/architect.md"
  check 'journal FAILED' has 'FAILED architect'
  check 'no false JOURNAL' lacks 'JOURNAL architect'
  check 'journal error context' grep -Fq "$dest/journals/architect.md" "$stderr"
  if [ "$shape" = printf ]; then
    check 'printf was invoked' grep -Fxq printf "$marker"
  fi
done

new_case lifecycle
run architect
check 'fresh exit' test "$code" -eq 0
check 'fresh INSTALLED' has 'INSTALLED architect'
check 'fresh JOURNAL' has 'JOURNAL architect'
check 'fresh definition bytes' cmp -s "$src/architect.md" "$dest/architect.md"
printf '# architect journal — durable, codebase-specific learnings\n' > "$project/expected-journal"
check 'seed journal bytes' cmp -s "$project/expected-journal" "$dest/journals/architect.md"
run architect
check 'rerun exit' test "$code" -eq 0
check 'rerun IDENTICAL' has 'IDENTICAL architect'
check 'no journal reseed' lacks 'JOURNAL architect'
printf 'customized definition\n' > "$dest/architect.md"
cp "$dest/architect.md" "$project/expected"
printf 'learned journal\n' > "$dest/journals/architect.md"
cp "$dest/journals/architect.md" "$project/expected-journal"
run architect
check 'custom conflict exit' test "$code" -eq 2
check 'custom CONFLICT' has 'CONFLICT architect'
check 'custom bytes retained' cmp -s "$project/expected" "$dest/architect.md"
run --force architect
check 'forced exit' test "$code" -eq 0
check 'forced UPDATED' has 'UPDATED architect'
check 'forced definition bytes' cmp -s "$src/architect.md" "$dest/architect.md"
check 'journal content preserved' cmp -s "$project/expected-journal" "$dest/journals/architect.md"

new_case live-links
cp "$src/architect.md" "$project/definition-target"
printf 'journal target\n' > "$project/journal-target"
cp "$project/journal-target" "$project/expected-journal"
ln -s "$project/definition-target" "$dest/architect.md"
ln -s "$project/journal-target" "$dest/journals/architect.md"
run architect
check 'linked identical exit' test "$code" -eq 0
check 'linked IDENTICAL' has 'IDENTICAL architect'
printf 'custom target\n' > "$project/definition-target"
cp "$project/definition-target" "$project/expected"
run architect
check 'linked conflict exit' test "$code" -eq 2
check 'linked CONFLICT' has 'CONFLICT architect'
check 'linked custom preserved' cmp -s "$project/expected" "$project/definition-target"
run --force architect
check 'linked force exit' test "$code" -eq 0
check 'linked UPDATED' has 'UPDATED architect'
check 'definition symlink retained' test -L "$dest/architect.md"
check 'linked target updated' cmp -s "$src/architect.md" "$project/definition-target"
check 'journal symlink retained' test -L "$dest/journals/architect.md"
check 'journal target preserved' cmp -s "$project/expected-journal" "$project/journal-target"

new_case dangling-journal-success
ln -s "$project/journal-target" "$dest/journals/architect.md"
run architect
check 'dangling journal successful exit' test "$code" -eq 0
check 'dangling journal successful ledger' has 'JOURNAL architect'
check 'journal link retained' test -L "$dest/journals/architect.md"
check 'journal target seeded' test -f "$project/journal-target"

for parent in agents journals; do
  new_case "parent-link-$parent"
  linked="$dest"
  [ "$parent" = journals ] && linked="$dest/journals"
  mv "$linked" "$project/parent-target"
  ln -s "$project/parent-target" "$linked"
  run architect
  check 'parent link exit' test "$code" -eq 0
  check 'parent link preserved' test -L "$linked"
  check 'parent link INSTALLED' has 'INSTALLED architect'
  check 'parent link JOURNAL' has 'JOURNAL architect'
  check 'parent definition bytes' cmp -s "$src/architect.md" "$dest/architect.md"
done

for order in conflict-first failure-first; do
  new_case "$order"
  printf 'custom definition\n' > "$dest/architect.md"
  mkdir "$dest/deadwood.md"
  args=(architect deadwood)
  [ "$order" = failure-first ] && args=(deadwood architect)
  run "${args[@]}"
  check 'failure outranks conflict' test "$code" -eq 3
  check 'conflict reported' has 'CONFLICT architect'
  check 'failure reported' has 'FAILED deadwood'
  check 'conflict still seeds journal' has 'JOURNAL architect'
done

new_case continue
mkdir "$dest/architect.md"
run architect deadwood
check 'continuation failure exit' test "$code" -eq 3
check 'first FAILED' has 'FAILED architect'
check 'later INSTALLED' has 'INSTALLED deadwood'
check 'later JOURNAL' has 'JOURNAL deadwood'
check 'later bytes' cmp -s "$src/deadwood.md" "$dest/deadwood.md"

new_case permission-copy
chmod 555 "$dest"
if ( : > "$dest/permission-probe" ) 2>/dev/null; then
  rm -f "$dest/permission-probe"
  echo 'SKIP: supplemental permission fixture (writes allowed despite chmod 555); injected copy failures still run'
  skip=$((skip + 1))
else
  run architect
  failed_definition
fi
chmod u+w "$dest"

echo "install-agents results: $pass passed, $fail failed, $skip skipped"
[ "$fail" -eq 0 ]
