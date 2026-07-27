#!/usr/bin/env bash
# Deterministic Phase 2 install for install-agents.
#
# Usage: install-agents.sh <source-dir> [--force] [agent ...]
#
# Copies <source-dir>/<agent>.md (every *.md in <source-dir> when no agent
# names are given) into .claude/agents/ at the repo root (current directory
# outside git), and seeds an empty journal per agent at
# .claude/agents/journals/<agent>.md. Prints one line per agent:
#   INSTALLED <name>   new file written
#   IDENTICAL <name>   destination already matches the source
#   CONFLICT <name>    destination exists and differs; left untouched (no --force)
#   UPDATED <name>     destination overwritten (--force only)
#   JOURNAL <name>     journal newly seeded (existing journals never touched)
#
# Exits 1 with FATAL on stderr when the source dir is missing, empty, or a
# named agent has no file; exits 2 when any CONFLICT was printed so the
# caller knows to resolve it.

set -u

src="${1:-}"
[ -n "$src" ] || { echo "FATAL usage: install-agents.sh <source-dir> [--force] [agent ...]" >&2; exit 1; }
shift

force=0
agents=()
for arg in "$@"; do
  case "$arg" in
    --force) force=1 ;;
    *) agents+=("$arg") ;;
  esac
done

[ -d "$src" ] || { echo "FATAL source dir not found: $src" >&2; exit 1; }

root=$(git rev-parse --show-toplevel 2>/dev/null) || root=$PWD
dest="$root/.claude/agents"
mkdir -p "$dest/journals"

if [ ${#agents[@]} -eq 0 ]; then
  for f in "$src"/*.md; do
    [ -f "$f" ] || continue
    agents+=("$(basename "$f" .md)")
  done
fi
[ ${#agents[@]} -gt 0 ] || { echo "FATAL no agent files (*.md) in $src" >&2; exit 1; }

status=0
for name in "${agents[@]}"; do
  srcfile="$src/$name.md"
  [ -f "$srcfile" ] || { echo "FATAL no such agent: $srcfile" >&2; exit 1; }
  destfile="$dest/$name.md"
  if [ ! -f "$destfile" ]; then
    cp "$srcfile" "$destfile"
    echo "INSTALLED $name"
  elif cmp -s "$srcfile" "$destfile"; then
    echo "IDENTICAL $name"
  elif [ "$force" -eq 1 ]; then
    cp "$srcfile" "$destfile"
    echo "UPDATED $name"
  else
    echo "CONFLICT $name"
    status=2
  fi
  journal="$dest/journals/$name.md"
  if [ ! -f "$journal" ]; then
    printf '# %s journal — durable, codebase-specific learnings\n' "$name" > "$journal"
    echo "JOURNAL $name"
  fi
done
exit "$status"
