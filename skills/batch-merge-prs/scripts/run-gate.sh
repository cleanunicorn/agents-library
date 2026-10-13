#!/usr/bin/env bash
# Run one test command, show its output live, keep a log, and end with a
# machine-readable status line. Used for every gate command, whether it runs
# in a Herdr pane or a plain shell, so both paths report the same way.
#
# Usage: run-gate.sh <label> <log-file> <command>
#
# <command> is one string, run with `bash -c` from the current directory.
# Output goes to the terminal and to <log-file>. The last line printed is:
#   GATE <label> exit=<status> log=<log-file>
# A watcher (`herdr pane wait-output --regex 'GATE <label> exit='`) keys on it.
#
# Exits with the command's own status.

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
