#!/usr/bin/env bash
# List where the current repository says how to test it, in the order the
# skill trusts those sources. Read-only; runs nothing it finds.
#
# Usage: test-commands.sh
#
# Prints, in priority order (an earlier source overrules a later one):
#   SOURCE <path>                 a prose source to read: AGENTS.md, CLAUDE.md,
#                                 CONTRIBUTING*, then CI configs it can't parse
#   CANDIDATE <source> <command>  a command lifted mechanically from a CI
#                                 workflow `run:` line or a build manifest
#   CAUTION <path>:<line> <text>  a docs line pairing tests with live, shared,
#                                 or production resources — check it before
#                                 running the suite it names
#   NONE                          nothing found anywhere
#
# Exit 0 always: an empty result is an answer, not an error.

set -u

scan() {
  for f in AGENTS.md CLAUDE.md .claude/CLAUDE.md CONTRIBUTING CONTRIBUTING.md \
    CONTRIBUTING.rst docs/CONTRIBUTING.md .github/CONTRIBUTING.md; do
    [ -f "$f" ] && echo "SOURCE $f"
  done

  for f in .gitlab-ci.yml .circleci/config.yml Jenkinsfile azure-pipelines.yml \
    .buildkite/pipeline.yml; do
    [ -f "$f" ] && echo "SOURCE $f"
  done

  for f in .github/workflows/*.yml .github/workflows/*.yaml; do
    [ -f "$f" ] || continue
    while IFS= read -r line; do
      cmd=${line#*run:}
      cmd=$(echo "$cmd" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
      case "$cmd" in
        ""|"|"|"|-"|">"|">-") echo "SOURCE $f (multi-line run block)" ;;
        *) echo "CANDIDATE $f $cmd" ;;
      esac
    done < <(grep -E '^[[:space:]-]*run:' "$f")
  done

  if [ -f package.json ] && command -v python3 >/dev/null 2>&1; then
    runner=npm
    [ -f pnpm-lock.yaml ] && runner=pnpm
    [ -f yarn.lock ] && runner=yarn
    [ -f bun.lockb ] && runner=bun
    python3 - "$runner" <<'PY'
import json, re, sys
scripts = json.load(open("package.json")).get("scripts", {})
for name in scripts:
    if re.match(r"^(test|lint|check|typecheck|ci)([:-].*)?$", name):
        print(f"CANDIDATE package.json {sys.argv[1]} run {name}")
PY
  fi

  for f in Makefile makefile GNUmakefile; do
    [ -f "$f" ] || continue
    grep -oE '^(test|check|lint|ci)[A-Za-z0-9_-]*:' "$f" | tr -d : | sort -u |
      while IFS= read -r t; do echo "CANDIDATE $f make $t"; done
  done

  for f in justfile Justfile; do
    [ -f "$f" ] || continue
    grep -oE '^(test|check|lint|ci)[A-Za-z0-9_-]*' "$f" | sort -u |
      while IFS= read -r t; do echo "CANDIDATE $f just $t"; done
  done

  if [ -f pytest.ini ] || grep -qs '\[tool.pytest' pyproject.toml \
    || grep -qs '\[tool:pytest\]' setup.cfg || [ -f tox.ini ]; then
    echo "CANDIDATE python-config pytest"
  fi
  [ -f Cargo.toml ] && echo "CANDIDATE Cargo.toml cargo test"
  [ -f go.mod ] && echo "CANDIDATE go.mod go test ./..."

  for f in AGENTS.md CLAUDE.md .claude/CLAUDE.md CONTRIBUTING.md; do
    [ -f "$f" ] || continue
    grep -niE '\b(tests?|suites?|e2e|integration).*(live|shared|production|prod\b|staging|real (api|account|service)|credential|authoriz)|(live|shared|production|staging|credential|authoriz).*\b(tests?|suites?|e2e|integration)' "$f" |
      while IFS= read -r hit; do echo "CAUTION $f:$hit"; done
  done
}

out=$(scan | awk '!seen[$0]++')
echo "${out:-NONE}"
