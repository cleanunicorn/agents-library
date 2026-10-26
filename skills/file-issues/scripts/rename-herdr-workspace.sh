#!/usr/bin/env bash
# Label this session's Herdr workspace "<label>" at startup.
#
# Usage: rename-herdr-workspace.sh <label>     e.g. manager, issues
#
# The workspace, not the tab, because Herdr lists workspaces in its sidebar,
# which is where the user navigates between sessions. The label carries no
# project name: the sidebar already shows each workspace's directory.
# Outside Herdr (HERDR_ENV not 1, or no HERDR_WORKSPACE_ID) it does nothing.
# A missing herdr or a failed rename prints one warning and still exits 0:
# a label must never block a session from starting.
#
# Shared step: skills/manager/scripts/ holds the canonical copy and every
# other skill ships a byte-identical copy, because a skill installed alone
# carries only its own directory. scripts/test-rename-herdr-workspace.sh
# checks they match; edit the manager copy, then copy it over the others.

set -u

label=${1:-}
if [ -z "$label" ]; then
  echo "usage: rename-herdr-workspace.sh <label>" >&2
  exit 2
fi

[ "${HERDR_ENV:-}" = 1 ] && [ -n "${HERDR_WORKSPACE_ID:-}" ] || exit 0

if ! command -v herdr >/dev/null 2>&1; then
  echo "WARN herdr not found; workspace not renamed to '$label'" >&2
  exit 0
fi
herdr workspace rename "$HERDR_WORKSPACE_ID" "$label" >/dev/null 2>&1 ||
  echo "WARN herdr workspace rename failed; workspace not renamed to '$label'" >&2
exit 0
