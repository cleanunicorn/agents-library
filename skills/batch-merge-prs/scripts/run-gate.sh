#!/usr/bin/env bash
# Run one gate in Herdr or shell with identical live output, log, and status.
# Usage: run-gate.sh <label> <log-file> <command>
# Run the single command string with bash -c in the current directory.
# End with GATE <label> exit=<status> log=<log-file> for pane watchers,
# and exit with the command's status.

set -u

if [ "$#" -ne 3 ]; then
  echo "usage: $0 <label> <log-file> <command>" >&2
  exit 2
fi

label=$1
log=$2
cmd=$3

mkdir -p "$(dirname "$log")"
echo "\$ $cmd" | tee "$log"
bash -c "$cmd" 2>&1 | tee -a "$log"
status=${PIPESTATUS[0]}
echo "GATE $label exit=$status log=$log"
exit "$status"
