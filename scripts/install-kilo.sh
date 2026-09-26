#!/usr/bin/env bash
# Install the library's agents and skills into Kilo Code's discovery paths
# (~/.config/kilo/ globally, ./.kilo/ with --project).
# The shared implementation lives in install-host.sh.

set -u
exec "$(dirname "$0")/install-host.sh" kilo "$@"
