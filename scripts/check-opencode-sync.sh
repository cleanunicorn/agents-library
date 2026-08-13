#!/usr/bin/env bash
# Verify .opencode/ symlinks are in sync with agents/ and skills/.
# Run this before merging when agents/ or skills/ changes.
# Exits 0 if in sync, 1 if any drift (missing or stale symlinks).

set -u

cd "$(dirname "$0")/.." || { echo "FATAL: cannot locate repo root" >&2; exit 1; }

status=0

for f in agents/*.md; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .md)
  link=".opencode/agents/${name}.md"
  [ -L "$link" ] || { echo "MISSING: $link — agent '$name' has no .opencode/ symlink"; status=1; }
done

for d in skills/*/; do
  [ -f "${d}SKILL.md" ] || continue
  name=$(basename "$d")
  link=".opencode/skills/${name}"
  [ -L "$link" ] || { echo "MISSING: $link — skill '$name' has no .opencode/ symlink"; status=1; }
done

for link in .opencode/agents/*.md; do
  [ -L "$link" ] || continue
  name=$(basename "$link" .md)
  [ -f "agents/${name}.md" ] || { echo "STALE: $link — no source agent agents/${name}.md"; status=1; }
done

for link in .opencode/skills/*; do
  [ -L "$link" ] || continue
  name=$(basename "$link")
  [ -d "skills/${name}" ] || { echo "STALE: $link — no source skill skills/${name}/"; status=1; }
done

if [ "$status" -eq 0 ]; then
  count=$(find .opencode/agents .opencode/skills -type l 2>/dev/null | wc -l)
  echo "OK: .opencode/ in sync ($count symlinks)"
fi

exit "$status"
