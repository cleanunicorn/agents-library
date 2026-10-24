#!/usr/bin/env python3
"""Watch one manager run's Herdr workers for permission prompts and questions.

The manager only saw a blocked worker when a turn happened to read live
state. This watcher polls every registered worker on a fixed cadence and
records each prompt it finds as an event in the run directory; the manager
learns of due events through `wait`, run as a host background command whose
exit wakes it. Herdr 0.9.5 (protocol 22) has no queued or idle-conditional
way to message the manager, and typing into its terminal can submit whatever
sits in its input buffer, so the watcher never writes terminal input: it
calls only `herdr agent get` and `herdr agent read`. It detects and
notifies; the manager claims, decides and answers.

No prompt text is stored or printed — only a hash of it — so a secret on the
screen never reaches the store, the log, or a notification.

Commands (all take --run-dir):
  run          poll every --interval seconds until stopped; one per run
  stop         ask this run's watcher to exit, and wait for it
  status       JSON: watcher identity and heartbeat, workers, event counts
  register     add a worker or helper to poll (--name --item --role)
  unregister   stop polling a worker (--name)
  sweep        poll once (diagnosis and tests)
  wait         block until an event is due or the watcher is stale
  claim        take an event before handling it; prints its token
  resolve      mark a claimed event answered (--token)
  await-user   mark a claimed event as waiting on the user (--token)

Exit codes: 0 done, 1 refused (not claimable, stale token), 2 wait timed
out, 3 store error.
"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCHEMA_VERSION = 1
STORE = "watcher.sqlite3"
INTERVAL = 5.0
CALL_TIMEOUT = 4.0
STALE_AFTER_INTERVALS = 3
CLAIM_EXPIRES = 30.0
BACKOFF_FIRST, BACKOFF_CAP = 5.0, 30.0
READ_LINES = 40
PROMPT_TAIL_LINES = 15
OUTPUT_CAP = 64 * 1024
LISTED_EVENTS = 50

ACTIVE = ("pending", "claimed", "awaiting_user")
IS_ACTIVE = f"state IN {ACTIVE}"
# Statuses that end a turn: the worker's result file is the manager's signal,
# so an unchanged idle or done status is never a reason to read the screen.
FINISHED = ("idle", "done")
# Prompt UIs of the hosts the manager drives (Claude Code, Codex, opencode,
# Kilo). A layout none of these match is found only once Herdr says `blocked`.
PROMPT_PATTERNS = [re.compile(p, re.IGNORECASE) for p in (
    r"\bdo you want to\b",
    r"\b(allow|approve) (once|always|for this session)\b",
    r"\balways allow\b",
    r"\bdon't ask again\b",
    r"\bpermission (required|needed)\b",
    r"[\[(]y/n[\])]",
)]
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")
# A spinner line (one that starts with a spinner glyph) redraws its elapsed time
# and token count while a prompt waits; that must not change the prompt's
# identity. Every other line is the prompt's own — a pid, a `timeout 10s`, a
# path — and is kept as is, so a changed command is a new event.
SPINNER_LINE = re.compile(r"^\s*[\u2800-\u28ff\u2720-\u274b\u23f5\u23fa·•●○◐◓◑◒]+(?=\s)")
DURATION = r"\d+(?:\.\d+)?\s?(?:ms|s|m|h)\b"
REDRAWN = re.compile(rf"\b{DURATION}(?:\s*{DURATION})*|\b\d+(?:\.\d+)?k?\s+tokens\b")


class StoreError(Exception):
    pass


def connect(run_dir):
    db = sqlite3.connect(Path(run_dir) / STORE, timeout=5, isolation_level=None)
    db.row_factory = sqlite3.Row
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise StoreError(f"SCHEMA {version} is newer than this watcher's {SCHEMA_VERSION}; not touching it")
    if version < SCHEMA_VERSION:
        db.executescript(f"""
            BEGIN IMMEDIATE;
            CREATE TABLE IF NOT EXISTS lease (
                id INTEGER PRIMARY KEY CHECK (id = 1), instance TEXT, pid INTEGER, started_at REAL,
                heartbeat_at REAL, interval REAL, stop_requested INTEGER DEFAULT 0, stopped_at REAL);
            CREATE TABLE IF NOT EXISTS workers (
                name TEXT PRIMARY KEY, item TEXT, role TEXT, generation TEXT, instance_key TEXT, dismissed_hash TEXT,
                last_status TEXT, status_streak INTEGER DEFAULT 0, failures INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY, worker TEXT, item TEXT, role TEXT, instance_key TEXT,
                prompt_hash TEXT, kind TEXT, state TEXT, detected_at REAL, updated_at REAL,
                claim_token TEXT, claimed_at REAL, notified_at REAL, notify_count INTEGER DEFAULT 0);
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_prompt ON events (worker, instance_key, prompt_hash)
                WHERE {IS_ACTIVE};
            PRAGMA user_version = {SCHEMA_VERSION};
            COMMIT;
        """)
    return db


class transaction:
    """BEGIN IMMEDIATE … COMMIT, so a read-then-write is one atomic step."""

    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self.db.execute("BEGIN IMMEDIATE")
        return self.db

    def __exit__(self, kind, *_):
        self.db.execute("ROLLBACK" if kind else "COMMIT")


# --- Observing workers -------------------------------------------------------

def herdr(binary, args, timeout):
    """Run one Herdr command; return its stdout, or None on failure or timeout."""
    try:
        done = subprocess.run([binary, *args], capture_output=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout[:OUTPUT_CAP].decode("utf-8", "replace")


def instance_key(agent):
    session = agent.get("agent_session")
    value = session.get("value") if isinstance(session, dict) else None
    return str(value or agent.get("terminal_id") or "")


def normalize(line):
    if SPINNER_LINE.match(line):
        line = REDRAWN.sub("#", SPINNER_LINE.sub("", line))
    return " ".join(line.split())


def prompt_identity(screen):
    """Hash the normalized screen; the text itself is discarded."""
    lines = [normalize(ANSI.sub("", line)) for line in screen.splitlines()]
    normalized = "\n".join(line for line in lines if line)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def shows_prompt(screen):
    tail = "\n".join(ANSI.sub("", screen).splitlines()[-PROMPT_TAIL_LINES:])
    return any(pattern.search(tail) for pattern in PROMPT_PATTERNS)


def observe(binary, worker, timeout):
    """One worker's status, and the prompt identity when its screen is worth reading."""
    raw = herdr(binary, ["agent", "get", worker["name"]], timeout)
    try:
        agent = json.loads(raw)["result"]["agent"]
    except (TypeError, ValueError, KeyError):
        agent = None
    if not isinstance(agent, dict):
        return {"name": worker["name"], "error": True}
    status = agent.get("agent_status", "unknown")
    streak = worker["status_streak"] + 1 if status == worker["last_status"] else 1
    seen = {"name": worker["name"], "error": False, "status": status, "streak": streak,
            "instance_key": instance_key(agent), "prompt_hash": None, "kind": None}
    unchanged = streak >= 2 and status not in FINISHED
    if status not in ("blocked", "unknown") and not unchanged:
        return seen
    screen = herdr(binary, ["agent", "read", worker["name"], "--source", "recent-unwrapped",
                            "--lines", str(READ_LINES)], timeout)
    if screen is None:
        return {"name": worker["name"], "error": True}
    if status == "blocked":
        seen.update(prompt_hash=prompt_identity(screen), kind="blocked")
    elif shows_prompt(screen):
        seen.update(prompt_hash=prompt_identity(screen), kind="suspected")
    return seen


def record(db, worker, seen, now):
    """Fold one observation into the store; returns the id of a new event, if any."""
    current = db.execute("SELECT generation, dismissed_hash FROM workers WHERE name = ?",
                         (worker["name"],)).fetchone()
    if current is None or current["generation"] != worker["generation"]:
        return None  # unregistered or re-registered while this observation was in flight
    if seen["error"]:
        db.execute("UPDATE workers SET failures = failures + 1 WHERE name = ?", (seen["name"],))
        return None
    db.execute("UPDATE workers SET last_status = ?, status_streak = ?, failures = 0, instance_key = ?"
               " WHERE name = ?", (seen["status"], seen["streak"], seen["instance_key"], seen["name"]))
    # A replacement worker under the same name never inherits its predecessor's prompts.
    db.execute(f"UPDATE events SET state = 'superseded', updated_at = ? WHERE worker = ? AND {IS_ACTIVE}"
               " AND instance_key != ?", (now, seen["name"], seen["instance_key"]))
    # A suspected screen the manager resolved stays dismissed until the screen
    # changes; a `blocked` status always raises, since Herdr itself says so.
    if seen["kind"] == "suspected" and seen["prompt_hash"] == current["dismissed_hash"]:
        return None
    db.execute("UPDATE workers SET dismissed_hash = NULL WHERE name = ?", (seen["name"],))
    if seen["prompt_hash"] is None:
        if seen["status"] not in ("blocked", "unknown"):
            db.execute(f"UPDATE events SET state = 'cleared', updated_at = ? WHERE worker = ? AND {IS_ACTIVE}",
                       (now, seen["name"]))
        return None
    # A different prompt from the same worker (a follow-up dialog) replaces the old one.
    db.execute(f"UPDATE events SET state = 'superseded', updated_at = ? WHERE worker = ? AND {IS_ACTIVE}"
               " AND prompt_hash != ?", (now, seen["name"], seen["prompt_hash"]))
    existing = db.execute(f"SELECT id FROM events WHERE worker = ? AND instance_key = ? AND prompt_hash = ?"
                          f" AND {IS_ACTIVE}", (seen["name"], seen["instance_key"], seen["prompt_hash"])).fetchone()
    if existing:
        db.execute("UPDATE events SET updated_at = ? WHERE id = ?", (now, existing["id"]))
        return None
    event = uuid.uuid4().hex[:12]
    db.execute("INSERT INTO events (id, worker, item, role, instance_key, prompt_hash, kind, state,"
               " detected_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
               (event, seen["name"], worker["item"], worker["role"], seen["instance_key"],
                seen["prompt_hash"], seen["kind"], now, now))
    return event


def sweep(db, binary, now, timeout):
    """Poll every registered worker at once, so one hung command cannot stall the rest."""
    workers = [dict(row) for row in db.execute("SELECT * FROM workers ORDER BY name")]
    if not workers:
        return {"workers": 0, "new": [], "failures": 0}
    with ThreadPoolExecutor(max_workers=len(workers)) as pool:
        seen = list(pool.map(lambda worker: observe(binary, worker, timeout), workers))
    new = []
    with transaction(db):
        for worker, observation in zip(workers, seen):
            event = record(db, worker, observation, now)
            if event:
                new.append({"id": event, "worker": worker["name"], "item": worker["item"],
                            "role": worker["role"], "kind": observation["kind"]})
    return {"workers": len(workers), "new": new, "failures": sum(1 for s in seen if s["error"])}


# --- Watcher lifecycle -------------------------------------------------------

def lease(db):
    row = db.execute("SELECT * FROM lease WHERE id = 1").fetchone()
    return dict(row) if row else None


def is_alive(held, now):
    if not held or held["stopped_at"] is not None:
        return False
    return now - held["heartbeat_at"] < STALE_AFTER_INTERVALS * held["interval"]


def acquire(db, interval, now):
    """Take the run's lease unless a live watcher holds it; returns our instance id or None."""
    with transaction(db):
        held = lease(db)
        if is_alive(held, now) and not held["stop_requested"]:
            return None
        instance = uuid.uuid4().hex[:8]
        db.execute("INSERT OR REPLACE INTO lease (id, instance, pid, started_at, heartbeat_at, interval,"
                   " stop_requested, stopped_at) VALUES (1, ?, ?, ?, ?, ?, 0, NULL)",
                   (instance, os.getpid(), now, now, interval))
        return instance


def heartbeat(db, instance, now):
    """Renew our lease; returns 'stop', 'superseded', or None to keep going."""
    with transaction(db):
        held = lease(db)
        if not held or held["instance"] != instance:
            return "superseded"
        if held["stop_requested"]:
            db.execute("UPDATE lease SET stopped_at = ? WHERE id = 1", (now,))
            return "stop"
        db.execute("UPDATE lease SET heartbeat_at = ? WHERE id = 1", (now,))
        return None


def run(db, args):
    instance = acquire(db, args.interval, time.time())
    if instance is None:
        print(f"ALREADY_RUNNING {lease(db)['instance']}")
        return 0
    print(f"START {instance} pid={os.getpid()} interval={args.interval}", flush=True)
    while True:
        started = time.monotonic()
        verdict = heartbeat(db, instance, time.time())
        if verdict == "stop":
            print(f"STOPPED {instance}", flush=True)
            return 0
        if verdict == "superseded":
            print(f"SUPERSEDED {instance}", flush=True)
            return 0
        result = sweep(db, args.herdr, time.time(), args.timeout)
        for event in result["new"]:
            print(event_line(event), flush=True)
        time.sleep(max(0.0, args.interval - (time.monotonic() - started)))


def stop(db, _args):
    with transaction(db):
        held = lease(db)
        if not is_alive(held, time.time()):
            print("NOT_RUNNING")
            return 0
        db.execute("UPDATE lease SET stop_requested = 1 WHERE id = 1")
    deadline = time.monotonic() + STALE_AFTER_INTERVALS * held["interval"] + CALL_TIMEOUT
    while time.monotonic() < deadline:
        if lease(db)["stopped_at"] is not None:
            print(f"STOPPED {held['instance']}")
            return 0
        time.sleep(0.1)
    print(f"STOP_REQUESTED {held['instance']} (no exit seen yet)")
    return 0


# --- Manager side ------------------------------------------------------------

def backoff(notified):
    return min(BACKOFF_FIRST * 2 ** (notified - 1), BACKOFF_CAP)


def take_due(db, now):
    """Events the manager should hear about now; marks them notified."""
    with transaction(db):
        db.execute("UPDATE events SET state = 'pending', claim_token = NULL, notified_at = NULL,"
                   " notify_count = 0 WHERE state = 'claimed' AND claimed_at <= ?", (now - CLAIM_EXPIRES,))
        due = [dict(row) for row in db.execute("SELECT * FROM events WHERE state = 'pending' ORDER BY detected_at")
               if row["notified_at"] is None or now >= row["notified_at"] + backoff(row["notify_count"])]
        for event in due:
            db.execute("UPDATE events SET notified_at = ?, notify_count = notify_count + 1 WHERE id = ?",
                       (now, event["id"]))
    return due


def event_line(event):
    """One event as the manager reads it: ids and identities, never prompt text."""
    return (f"EVENT {event['id']} worker={event['worker']} item={event['item']} role={event['role']}"
            f" kind={event['kind']}")


def wait(db, args):
    """Exit when an event is due or the watcher has died — the manager's wake-up."""
    deadline = None if args.wait_timeout is None else time.monotonic() + args.wait_timeout
    while True:
        now = clock(args)
        lines = [event_line(event) for event in take_due(db, now)]
        if not is_alive(lease(db), now) and args.now is None:
            lines.append("WATCHER stale")
        if lines:
            print("\n".join(lines))
            return 0
        if args.now is not None or (deadline is not None and time.monotonic() >= deadline):
            print("TIMEOUT")
            return 2
        time.sleep(1)


def claim(db, args):
    now = clock(args)
    token = uuid.uuid4().hex[:12]
    with transaction(db):
        changed = db.execute("UPDATE events SET state = 'claimed', claim_token = ?, claimed_at = ? WHERE id = ?"
                             " AND (state IN ('pending', 'awaiting_user') OR (state = 'claimed' AND claimed_at <= ?))",
                             (token, now, args.event, now - CLAIM_EXPIRES)).rowcount
        event = db.execute("SELECT * FROM events WHERE id = ?", (args.event,)).fetchone()
    if not changed:
        print(f"NOT_CLAIMABLE {args.event} state={event['state'] if event else 'unknown'}")
        return 1
    print(f"CLAIMED {args.event} token={token} worker={event['worker']} item={event['item']} role={event['role']}")
    return 0


def settle(db, args):
    state = "resolved" if args.command == "resolve" else "awaiting_user"
    with transaction(db):
        event = db.execute("SELECT * FROM events WHERE id = ?", (args.event,)).fetchone()
        if event is None:
            print(f"UNKNOWN {args.event}")
            return 1
        if event["state"] in ("cleared", "superseded", "resolved"):
            print(f"ALREADY {event['state']} {args.event}")
            return 0
        if event["claim_token"] != args.token:
            print(f"STALE_TOKEN {args.event} state={event['state']}")
            return 1
        db.execute("UPDATE events SET state = ?, updated_at = ? WHERE id = ?", (state, clock(args), args.event))
        if state == "resolved" and event["kind"] == "suspected":
            db.execute("UPDATE workers SET dismissed_hash = ? WHERE name = ?", (event["prompt_hash"], event["worker"]))
    print(f"{state.upper()} {args.event}")
    return 0


def status(db, args):
    now = clock(args)
    held = lease(db)
    counts = {state: 0 for state in ACTIVE}
    for row in db.execute("SELECT state, COUNT(*) AS n FROM events GROUP BY state"):
        counts[row["state"]] = row["n"]
    events = [dict(row) for row in db.execute(
        "SELECT id, worker, item, role, kind, state, detected_at, updated_at FROM events ORDER BY"
        f" {IS_ACTIVE} DESC, detected_at DESC LIMIT {LISTED_EVENTS}")]
    print(json.dumps({
        "watcher": {
            "instance": held["instance"] if held else None,
            "pid": held["pid"] if held else None,
            "started_at": held["started_at"] if held else None,
            "heartbeat_age": round(now - held["heartbeat_at"], 1) if held else None,
            "alive": is_alive(held, now),
        },
        "counts": counts,
        "workers": [dict(row) for row in db.execute(
            "SELECT name, item, role, last_status, failures FROM workers ORDER BY name")],
        "events": events,
    }))
    return 0


def register(db, args):
    with transaction(db):
        db.execute("INSERT OR REPLACE INTO workers (name, item, role, generation) VALUES (?, ?, ?, ?)",
                   (args.name, args.item, args.role, uuid.uuid4().hex[:12]))
    print(f"REGISTERED {args.name} item={args.item} role={args.role}")
    return 0


def unregister(db, args):
    with transaction(db):
        db.execute("DELETE FROM workers WHERE name = ?", (args.name,))
        db.execute(f"UPDATE events SET state = 'cleared', updated_at = ? WHERE worker = ? AND {IS_ACTIVE}",
                   (clock(args), args.name))
    print(f"UNREGISTERED {args.name}")
    return 0


def sweep_once(db, args):
    result = sweep(db, args.herdr, clock(args), args.timeout)
    print(f"SWEEP workers={result['workers']} new={len(result['new'])} failures={result['failures']}")
    return 0


def clock(args):
    return args.now if args.now is not None else time.time()


def parse(argv):
    parser = argparse.ArgumentParser(description="Watch a manager run's Herdr workers for prompts.")
    commands = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--run-dir", required=True, help="the manager's run directory")
    common.add_argument("--herdr", default="herdr", help="Herdr binary (tests pass a stub)")
    common.add_argument("--now", type=float, help="fixed clock, epoch seconds (tests)")
    for name, handler in [("run", run), ("stop", stop), ("status", status), ("register", register),
                          ("unregister", unregister), ("sweep", sweep_once), ("wait", wait),
                          ("claim", claim), ("resolve", settle), ("await-user", settle)]:
        command = commands.add_parser(name, parents=[common])
        command.set_defaults(handler=handler)
        if name in ("run", "sweep"):
            command.add_argument("--timeout", type=float, default=CALL_TIMEOUT, help="per Herdr call, seconds")
        if name == "run":
            command.add_argument("--interval", type=float, default=INTERVAL)
        if name == "wait":
            command.add_argument("--timeout", dest="wait_timeout", type=float, help="give up after seconds")
        if name in ("register", "unregister"):
            command.add_argument("--name", required=True)
        if name == "register":
            command.add_argument("--item", required=True)
            command.add_argument("--role", required=True)
        if name in ("claim", "resolve", "await-user"):
            command.add_argument("--event", required=True)
        if name in ("resolve", "await-user"):
            command.add_argument("--token", required=True)
    return parser.parse_args(argv)


def main(argv):
    args = parse(argv)
    try:
        db = connect(args.run_dir)
    except (StoreError, sqlite3.Error) as error:
        print(f"STORE_ERROR {Path(args.run_dir) / STORE}: {error}")
        return 3
    return args.handler(db, args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
