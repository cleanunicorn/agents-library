#!/usr/bin/env bash
# Select exactly one version per merged PR; retries reuse its release commit.
# Usage: release-version.sh <major|minor|patch> <merge-sha>
# Runs only in the release workflow's disposable checkout, never a user tree.
set -euo pipefail

fatal() {
  echo "FATAL $*" >&2
  exit 1
}

[ "$#" -eq 2 ] || fatal "expected bump and merge SHA"
bump=$1
merge_sha=$2
case "$bump" in major|minor|patch) ;; *) fatal "invalid bump: $bump" ;; esac
[[ "$merge_sha" =~ ^[0-9a-f]{40}$ ]] || fatal "invalid merge SHA"
[ -z "$(git status --porcelain)" ] || fatal "release checkout is dirty"

# A competing release may advance main between fetch and push. Retry from
# the fetched tip in this disposable checkout, never force-push either ref.
for attempt in 1 2 3; do
  git fetch origin refs/heads/main:refs/remotes/origin/main --tags >&2
  git merge-base --is-ancestor "$merge_sha" origin/main || fatal "merge SHA is not on main"
  release_commit=$(git log origin/main --format=%H --grep="^Release-Merge: $merge_sha\$" -n 1)
  if [ -n "$release_commit" ]; then
    version=$(git show "$release_commit:.codex-plugin/plugin.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')
    [ "$(git rev-parse "refs/tags/v$version^{commit}")" = "$release_commit" ] \
      || fatal "release tag v$version does not match its recorded commit"
    printf 'version=%s\n' "$version" >> "$GITHUB_OUTPUT"
    exit 0
  fi
  git merge --ff-only origin/main >&2
  version=$(python3 - "$bump" <<'PY'
import json
import sys
from pathlib import Path

path = Path('.codex-plugin/plugin.json')
manifest = json.loads(path.read_text())
major, minor, patch = map(int, manifest['version'].split('.'))
bump = sys.argv[1]
if bump == 'major':
    major, minor, patch = major + 1, 0, 0
elif bump == 'minor':
    minor, patch = minor + 1, 0
else:
    patch += 1
manifest['version'] = f'{major}.{minor}.{patch}'
path.write_text(json.dumps(manifest, indent=2) + '\n')
print(manifest['version'])
PY
  )
  git add .codex-plugin/plugin.json
  git commit -m "release: v$version" -m "Release-Merge: $merge_sha" >&2
  git tag -a "v$version" -m "release: v$version"
  if git push --atomic origin HEAD:refs/heads/main "refs/tags/v$version" >&2; then
    printf 'version=%s\n' "$version" >> "$GITHUB_OUTPUT"
    exit 0
  fi
  # Only discard the tag and checkout this attempt created. If the remote
  # accepted the push but its response was lost, the next fetch recovers it.
  git tag -d "v$version" >&2
  git checkout --detach refs/remotes/origin/main >&2
done
fatal "could not publish a release after $attempt attempts; rerun the workflow"
