#!/usr/bin/env python3
"""Install the library into every agent host on this machine.

Run it from a clone: `./install.py`. It shows two checklists — the hosts it
found (Claude Code, Codex, opencode, Kilo Code) and the agents and skills —
with everything checked by default. What you uncheck is saved, so the next
run starts from your last choice. Run `./install.py --help` for the flags.

Claude Code and Codex install the whole plugin through their own CLIs; the
item checklist applies to opencode and Kilo, which load files from disk.
"""

import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parent
PLUGIN = "agents-library"
MARKETPLACE_SOURCE = "cleanunicorn/agents-library"
SELECTION_VERSION = 1
PROJECT_SELECTION = ".agents-library.json"

EXIT_USAGE, EXIT_CONFLICT, EXIT_FAILED = 1, 2, 3

HELP_EPILOG = """\
Without --yes, an interactive checklist runs (arrows or j/k move, space
toggles, a toggles all, enter confirms, q cancels). Unchecked hosts and items
are saved to $XDG_CONFIG_HOME/agents-library/selection.json (with --project:
./.agents-library.json) and become the defaults of the next run. Items added
to the library later start checked.

Status lines (one per host/item):
  LINKED <host>/<name>    symlink created
  COPIED <host>/<name>    file or directory copied
  INSTALLED <host>/<plugin>  plugin installed through the host's CLI
  OK <host>/<name>        already installed correctly
  UPDATED <host>/<name>   destination overwritten (--force)
  REMOVED <host>/<name>   unchecked item this library had installed
  KEPT <host>/<name>      unchecked item left alone: it differs from the library
  SKIPPED <host>/<name>   host cannot take this install (reason on stderr)
  CONFLICT <host>/<name>  destination exists and differs (needs --force)
  FAILED <host>/<name>    operation failed (reason on stderr)

Exits 1 on usage error, 2 if any CONFLICT was printed, 3 if any FAILED.
"""


class Fatal(Exception):
    """A usage or setup error: reported as `FATAL: ...` with exit 1."""


@dataclass(frozen=True)
class Host:
    label: str
    binary: str
    kind: str  # "plugin": the host's CLI installs the whole plugin; "files": we place files
    mirror: Optional[str] = None  # the in-repo discovery dir (and the --project dir) for file hosts


# Keep the mirrors in sync with check-host-sync.sh and test-check-host-sync.py.
HOSTS: Dict[str, Host] = {
    "claude": Host("Claude Code", "claude", "plugin"),
    "codex": Host("Codex", "codex", "plugin"),
    "opencode": Host("opencode", "opencode", "files", mirror=".opencode"),
    "kilo": Host("Kilo Code", "kilo", "files", mirror=".kilo"),
}


@dataclass(frozen=True)
class Item:
    kind: str  # "agent" or "skill"
    name: str
    source: Path

    @property
    def subdir(self) -> str:
        return self.kind + "s"

    @property
    def filename(self) -> str:
        return self.name + ".md" if self.kind == "agent" else self.name


def discover_items(repo: Path = REPO) -> List[Item]:
    agents = [Item("agent", p.stem, p) for p in sorted((repo / "agents").glob("*.md"))]
    skills = [Item("skill", p.parent.name, p.parent)
              for p in sorted((repo / "skills").glob("*/SKILL.md"))]
    if not agents or not skills:
        raise Fatal(f"agents/ or skills/ not found at {repo}; run the installer from a complete clone")
    return agents + skills


# --- saved selection ------------------------------------------------------


@dataclass
class Selection:
    """What the user chose last time. Items store only what was unchecked, so
    an item added to the library later is installed by default; hosts store
    every explicit choice, and an unrecorded host defaults to "found on PATH"."""

    hosts: Dict[str, bool]
    excluded: List[str]


def selection_path(project: Optional[Path]) -> Path:
    if project:
        return project / PROJECT_SELECTION
    config = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config) / "agents-library" / "selection.json"


def load_selection(path: Path) -> Selection:
    if not path.exists():
        return Selection({}, [])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise Fatal(f"cannot read saved selection {path}: {error}; fix or delete it")
    hosts, excluded = data.get("hosts", {}), data.get("excluded", [])
    valid = (isinstance(hosts, dict) and all(isinstance(v, bool) for v in hosts.values())
             and isinstance(excluded, list) and all(isinstance(n, str) for n in excluded))
    if not valid:
        raise Fatal(f"saved selection {path} is malformed; fix or delete it")
    return Selection({k: v for k, v in hosts.items() if k in HOSTS}, list(excluded))


def save_selection(path: Path, selection: Selection) -> None:
    payload = {"version": SELECTION_VERSION, "hosts": selection.hosts,
               "excluded": sorted(set(selection.excluded))}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# --- interactive checklist -----------------------------------------------


@dataclass
class Row:
    key: str
    label: str
    checked: bool
    note: str = ""


class Checklist:
    """The checklist's state and key handling, kept apart from curses so it
    can be tested without a terminal."""

    def __init__(self, title: str, rows: List[Row]):
        self.title, self.rows, self.cursor = title, rows, 0

    def press(self, key: str) -> Optional[str]:
        """Apply one key; return "done" or "cancel" when the checklist ends."""
        if key in ("up", "k"):
            self.cursor = (self.cursor - 1) % len(self.rows)
        elif key in ("down", "j"):
            self.cursor = (self.cursor + 1) % len(self.rows)
        elif key == " ":
            row = self.rows[self.cursor]
            row.checked = not row.checked
        elif key == "a":
            target = not all(row.checked for row in self.rows)
            for row in self.rows:
                row.checked = target
        elif key == "enter":
            return "done"
        elif key in ("q", "esc"):
            return "cancel"
        return None

    def checked(self) -> List[str]:
        return [row.key for row in self.rows if row.checked]


def run_checklist(checklist: Checklist) -> List[str]:
    import curses

    names = {curses.KEY_UP: "up", curses.KEY_DOWN: "down", 10: "enter", 13: "enter",
             curses.KEY_ENTER: "enter", 27: "esc"}

    def loop(screen) -> Optional[str]:
        curses.curs_set(0)
        while True:
            draw(screen, checklist)
            code = screen.getch()
            key = names.get(code, chr(code) if 0 <= code < 256 else "")
            outcome = checklist.press(key)
            if outcome:
                return outcome

    if curses.wrapper(loop) == "cancel":
        raise Fatal("cancelled; nothing was installed or saved")
    return checklist.checked()


def draw(screen, checklist: Checklist) -> None:
    import curses

    screen.erase()
    height, width = screen.getmaxyx()
    lines = [checklist.title, "space toggle · a all · enter confirm · q cancel", ""]
    for row in checklist.rows:
        lines.append(f"[{'x' if row.checked else ' '}] {row.label}  {row.note}".rstrip())
    # Scroll so the cursor row stays visible on short terminals.
    offset = max(0, checklist.cursor + 3 - (height - 1))
    for y, line in enumerate(lines[:3] + lines[3 + offset:]):
        if y >= height:
            break
        selected = y >= 3 and y - 3 + offset == checklist.cursor
        screen.addnstr(y, 0, line, width - 1, curses.A_REVERSE if selected else 0)
    screen.refresh()


def host_rows(selection: Selection, project: Optional[Path]) -> List[Row]:
    rows = []
    for key, host in HOSTS.items():
        found = shutil.which(host.binary) is not None
        note = "found" if found else "not found on PATH"
        if host.kind == "plugin":
            note += " · whole plugin via its CLI"
        if project and key == "codex":
            note += " · no project scope, skipped"
        rows.append(Row(key, host.label, selection.hosts.get(key, found), note))
    return rows


def item_rows(items: List[Item], excluded: List[str]) -> List[Row]:
    return [Row(item.name, f"{item.kind:5}  {item.name}", item.name not in excluded) for item in items]


# --- resolving the selection from flags, saved state, and the checklist ----


def split_names(value: Optional[str]) -> List[str]:
    return [name.strip() for name in (value or "").split(",") if name.strip()]


def resolve(args, items: List[Item], saved: Selection, project: Optional[Path]) -> Selection:
    names = {item.name for item in items}
    for name in split_names(args.only) + split_names(args.skip):
        if name not in names:
            raise Fatal(f"unknown agent or skill: {name}")
    hosts = split_names(args.hosts)
    for name in hosts:
        if name not in HOSTS:
            raise Fatal(f"unknown host: {name}; expected one of {', '.join(HOSTS)}")

    chosen = Selection(dict(saved.hosts), list(saved.excluded))
    if args.all:
        chosen.excluded = []
    if args.only:
        chosen.excluded = sorted(names - set(split_names(args.only)))
    chosen.excluded = sorted(set(chosen.excluded) | set(split_names(args.skip)))
    if hosts:
        chosen.hosts = {key: key in hosts for key in HOSTS}

    if args.yes:
        return chosen
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise Fatal("not a terminal; pass --yes to install the saved selection without the checklist")

    rows = host_rows(chosen, project)
    picked_hosts = run_checklist(Checklist("Install into which hosts?", rows))
    chosen.hosts = {row.key: row.key in picked_hosts for row in rows}
    if any(HOSTS[key].kind == "files" for key in picked_hosts):
        title = "Install which agents and skills? (opencode and Kilo; plugin hosts get all)"
        picked_items = run_checklist(Checklist(title, item_rows(items, chosen.excluded)))
        chosen.excluded = sorted(names - set(picked_items))
    return chosen


def active_hosts(selection: Selection) -> List[str]:
    """Hosts to install into: explicit choices win; otherwise a host is on
    when its CLI is on PATH."""
    return [key for key, host in HOSTS.items()
            if selection.hosts.get(key, shutil.which(host.binary) is not None)]


# --- installing -------------------------------------------------------------


class Ledger:
    def __init__(self, dry_run: bool):
        self.dry_run, self.status = dry_run, 0

    def report(self, status: str, target: str, reason: str = "") -> None:
        print(f"{status} {target}", flush=True)
        if reason:
            print(f"install: {target}: {reason}", file=sys.stderr, flush=True)
        code = {"CONFLICT": EXIT_CONFLICT, "FAILED": EXIT_FAILED}.get(status, 0)
        self.status = max(self.status, code)


def same_link(dest: Path, source: Path) -> bool:
    return dest.is_symlink() and dest.resolve() == source.resolve()


def same_copy(dest: Path, source: Path) -> bool:
    if dest.is_symlink() or not dest.exists():
        return False
    if source.is_file():
        return dest.is_file() and filecmp.cmp(source, dest, shallow=False)
    return dest.is_dir() and not differs(filecmp.dircmp(source, dest))


def differs(comparison: filecmp.dircmp) -> bool:
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return True
    _, mismatch, errors = filecmp.cmpfiles(comparison.left, comparison.right,
                                           comparison.common_files, shallow=False)
    if mismatch or errors:
        return True
    return any(differs(sub) for sub in comparison.subdirs.values())


def remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def place(source: Path, dest: Path, method: str) -> None:
    """Write source to dest via a temp path, so a failed copy never leaves a
    half-written destination behind."""
    temp = dest.with_name(f".{dest.name}.tmp.{os.getpid()}")
    try:
        if method == "symlink":
            temp.symlink_to(source)
        elif source.is_dir():
            shutil.copytree(source, temp, symlinks=True)
        else:
            shutil.copy2(source, temp)
        if dest.exists() or dest.is_symlink():
            remove(dest)
        temp.rename(dest)
    finally:
        if temp.exists() or temp.is_symlink():
            remove(temp)


def install_files(host_key: str, root: Path, items: List[Item], excluded: List[str],
                  method: str, force: bool, ledger: Ledger) -> None:
    for directory in (root, root / "agents", root / "skills"):
        if directory.is_symlink():
            ledger.report("FAILED", f"{host_key}/{directory.name}",
                          f"{directory} is a symlink; refusing to write through it")
            return

    for item in items:
        target = f"{host_key}/{item.name}"
        dest = root / item.subdir / item.filename
        present = dest.exists() or dest.is_symlink()
        ours = same_link(dest, item.source) if method == "symlink" else same_copy(dest, item.source)

        if item.name in excluded:
            if not present:
                continue
            if not (same_link(dest, item.source) or same_copy(dest, item.source)):
                ledger.report("KEPT", target, f"{dest} differs from the library; left in place")
                continue
            if not ledger.dry_run:
                remove(dest)
            ledger.report("REMOVED", target)
            continue

        if ours:
            ledger.report("OK", target)
            continue
        if present and not force:
            ledger.report("CONFLICT", target, f"{dest} exists and differs; rerun with --force to replace it")
            continue
        status = "UPDATED" if present else ("LINKED" if method == "symlink" else "COPIED")
        if ledger.dry_run:
            ledger.report(status, target)
            continue
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            place(item.source, dest, method)
        except OSError as error:
            ledger.report("FAILED", target, str(error))
            continue
        ledger.report(status, target)


def run(command: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True)


def claude_installed(cwd: Path, scope: str) -> bool:
    listing = run(["claude", "plugin", "list", "--json"], cwd)
    try:
        entries = json.loads(listing.stdout) if listing.returncode == 0 else []
    except ValueError:
        return False
    for entry in entries:
        if entry.get("id") != f"{PLUGIN}@{PLUGIN}" or entry.get("scope") != scope:
            continue
        if scope == "user" or Path(entry.get("projectPath", "")) == cwd:
            return True
    return False


def codex_installed(cwd: Path) -> bool:
    listing = run(["codex", "plugin", "list", "-m", PLUGIN, "--json"], cwd)
    try:
        installed = json.loads(listing.stdout).get("installed", []) if listing.returncode == 0 else []
    except (ValueError, AttributeError):
        return False
    return any(entry.get("pluginId") == f"{PLUGIN}@{PLUGIN}" for entry in installed)


def install_plugin(host_key: str, project: Optional[Path], ledger: Ledger) -> None:
    target = f"{host_key}/{PLUGIN}"
    cwd = project or Path.cwd()
    if shutil.which(HOSTS[host_key].binary) is None:
        ledger.report("FAILED", target, f"`{HOSTS[host_key].binary}` is not on PATH")
        return

    if host_key == "claude":
        scope = "project" if project else "user"
        if claude_installed(cwd, scope):
            ledger.report("OK", target)
            return
        commands = [["claude", "plugin", "install", PLUGIN, "--marketplace", MARKETPLACE_SOURCE,
                     "--scope", scope]]
    else:
        if project:
            ledger.report("SKIPPED", target, "Codex has no project scope; run without --project to install it")
            return
        if codex_installed(cwd):
            ledger.report("OK", target)
            return
        commands = [["codex", "plugin", "marketplace", "add", MARKETPLACE_SOURCE],
                    ["codex", "plugin", "add", f"{PLUGIN}@{PLUGIN}"]]

    if ledger.dry_run:
        ledger.report("INSTALLED", target)
        return
    for command in commands:
        result = run(command, cwd)
        # An already-registered Codex marketplace fails `marketplace add`; the
        # `plugin add` that follows is what decides the outcome.
        if result.returncode != 0 and command is commands[-1]:
            output = (result.stderr or result.stdout).strip()
            ledger.report("FAILED", target, f"`{' '.join(command)}` exited {result.returncode}: {output}")
            return
    ledger.report("INSTALLED", target)


# --- entry point ------------------------------------------------------------


def parse_args(argv: List[str]):
    parser = argparse.ArgumentParser(
        prog="install.py", description="Install the library's agents and skills into your agent hosts.",
        epilog=HELP_EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-y", "--yes", action="store_true",
                        help="skip the checklist; install the saved selection (default: everything)")
    parser.add_argument("--hosts", metavar="LIST", help=f"comma-separated hosts to install into: {','.join(HOSTS)}")
    parser.add_argument("--only", metavar="LIST", help="comma-separated agents/skills to keep; uncheck the rest")
    parser.add_argument("--skip", metavar="LIST", help="comma-separated agents/skills to uncheck")
    parser.add_argument("--all", action="store_true", help="re-check every agent and skill")
    parser.add_argument("--project", action="store_true",
                        help="install into the current directory's project instead of globally")
    method = parser.add_mutually_exclusive_group()
    method.add_argument("--copy", dest="method", action="store_const", const="copy",
                        help="copy files (default with --project)")
    method.add_argument("--symlink", dest="method", action="store_const", const="symlink",
                        help="symlink files into this clone (default globally; `git pull` updates them)")
    parser.add_argument("--force", action="store_true", help="overwrite existing items that differ")
    parser.add_argument("--dry-run", action="store_true", help="print what would happen; change and save nothing")
    parser.add_argument("--list", action="store_true", help="print hosts, items, and the saved selection, then exit")
    return parser.parse_args(argv)


def print_listing(items: List[Item], saved: Selection, path: Path) -> None:
    print(f"selection: {path}{'' if path.exists() else ' (none saved; everything is on)'}")
    active = active_hosts(saved)
    for key, host in HOSTS.items():
        found = "found" if shutil.which(host.binary) else "not found"
        print(f"host  {key:9} {'on ' if key in active else 'off'}  {host.kind:6} {found}")
    for item in items:
        print(f"{item.kind:5} {item.name:20} {'off' if item.name in saved.excluded else 'on'}")


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    project = Path.cwd() if args.project else None
    path = selection_path(project)
    items = discover_items()
    saved = load_selection(path)
    if args.list:
        print_listing(items, saved, path)
        return 0

    chosen = resolve(args, items, saved, project)
    hosts = active_hosts(chosen)
    if not hosts:
        raise Fatal("no host selected and none found on PATH; pass --hosts to choose one")
    if not args.dry_run:
        save_selection(path, chosen)
        print(f"install: selection saved to {path}", file=sys.stderr)
    if chosen.excluded and any(HOSTS[key].kind == "plugin" for key in hosts):
        print("install: Claude Code and Codex install the whole plugin; unchecked items "
              "apply to opencode and Kilo only", file=sys.stderr)

    method = args.method or ("copy" if project else "symlink")
    ledger = Ledger(args.dry_run)
    for key in hosts:
        host = HOSTS[key]
        if host.kind == "plugin":
            install_plugin(key, project, ledger)
            continue
        root = project / host.mirror if project else Path.home() / ".config" / key
        install_files(key, root, items, chosen.excluded, method, args.force, ledger)
    return ledger.status


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Fatal as error:
        print(f"FATAL: {error}", file=sys.stderr)
        sys.exit(EXIT_USAGE)
    except KeyboardInterrupt:
        sys.exit(130)
