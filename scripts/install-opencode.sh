#!/usr/bin/env bash
# Install the library's agents and skills into opencode's discovery paths
# (~/.config/opencode/ globally, ./.opencode/ with --project).
# The shared implementation lives in install-host.sh.

set -u
exec "$(dirname "$0")/install-host.sh" opencode "$@"
