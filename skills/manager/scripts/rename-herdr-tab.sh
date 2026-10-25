#!/usr/bin/env bash
# Label this session's Herdr tab "<prefix> <project>" at startup.
#
# Usage: rename-herdr-tab.sh <prefix>     e.g. manager, issues
#
# <project> is the git toplevel directory's name, else the working
# directory's. Outside Herdr (HERDR_ENV not 1, or no HERDR_TAB_ID) it does
# nothing. A missing herdr or a failed rename prints one warning and still
# exits 0: a tab label must never block a session from starting.
#
# Shared step: skills/manager/scripts/ holds the canonical copy and every
# other skill ships a byte-identical copy, because a skill installed alone
# carries only its own directory. scripts/test-rename-herdr-tab.sh checks
# they match; edit the manager copy, then copy it over the others.

set -u

prefix=${1:-}
if [ -z "$prefix" ]; then
  echo "usage: rename-herdr-tab.sh <prefix>" >&2
  exit 2
fi

[ "${HERDR_ENV:-}" = 1 ] && [ -n "${HERDR_TAB_ID:-}" ] || exit 0

toplevel=$(git rev-parse --show-toplevel 2>/dev/null) || toplevel=$PWD
label="$prefix $(basename "$toplevel")"

if ! command -v herdr >/dev/null 2>&1; then
  echo "WARN herdr not found; tab not renamed to '$label'" >&2
  exit 0
fi
herdr tab rename "$HERDR_TAB_ID" "$label" >/dev/null 2>&1 ||
  echo "WARN herdr tab rename failed; tab not renamed to '$label'" >&2
exit 0
