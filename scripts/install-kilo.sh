#!/usr/bin/env bash
# Install the library's agents and skills into Kilo Code's discovery paths
# (~/.config/kilo/ globally, ./.kilo/ with --project).
# The shared implementation lives in install-host.sh.

set -u
# --as names the wrapper so install-host.sh's usage output reads install-kilo.sh.
exec "$(dirname "$0")/install-host.sh" kilo --as "$(basename "$0")" "$@"
