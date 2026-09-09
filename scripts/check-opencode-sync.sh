#!/usr/bin/env bash
# Verify .opencode/ symlinks are in sync with agents/ and skills/.
# Run this before merging when agents/ or skills/ changes.
# Exits 0 if in sync, 1 if any drift (missing, wrong, or stale symlinks).

set -u

cd "$(dirname "$0")/.." || { echo "FATAL: cannot locate repo root" >&2; exit 1; }

status=0

check_link() {
  local source="$1" link="$2"
  if [ ! -L "$link" ]; then
    echo "MISSING: $link — expected a symlink to $source"
    status=1
  elif [ ! "$link" -ef "$source" ]; then
    echo "WRONG: $link — does not resolve to $source"
    status=1
  fi
}

for f in agents/*.md; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .md)
  check_link "$f" ".opencode/agents/${name}.md"
done

for d in skills/*/; do
  [ -f "${d}SKILL.md" ] || continue
  name=$(basename "$d")
  check_link "${d%/}" ".opencode/skills/${name}"
done

for link in .opencode/agents/*.md; do
  [ -L "$link" ] || continue
  name=$(basename "$link" .md)
  [ -f "agents/${name}.md" ] || { echo "STALE: $link — no source agent agents/${name}.md"; status=1; }
done

for link in .opencode/skills/*; do
  [ -L "$link" ] || continue
  name=$(basename "$link")
  [ -f "skills/${name}/SKILL.md" ] || { echo "STALE: $link — no source skill skills/${name}/SKILL.md"; status=1; }
done

if [ "$status" -eq 0 ]; then
  count=$(find .opencode/agents .opencode/skills -type l 2>/dev/null | wc -l)
  echo "OK: .opencode/ in sync ($count symlinks)"
fi

exit "$status"
