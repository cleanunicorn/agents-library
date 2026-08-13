#!/usr/bin/env bash
# Install the library's agents and skills into opencode's discovery paths.
# Run `install-opencode.sh --help` for full usage.

set -u

show_help() {
  cat << 'HELP'
Usage: install-opencode.sh [options] [name ...]

Options:
  --global          Install to ~/.config/opencode/  (default)
  --project         Install to ./.opencode/ in the current directory
  --copy            Copy instead of symlinking
  --symlink         Symlink even for --project (default for --global)
  --force           Overwrite existing items that differ
  --agents-only     Install only agents
  --skills-only     Install only skills
  -h, --help        Show this help

name ...            Limit to specific agent and/or skill names (default: all)

Defaults: --global --symlink.  Symlinks all 8 agents and 8 skills into
~/.config/opencode/ using absolute symlinks, so `git pull` in this repo
updates every linked install.  Use --project for a self-contained copy in
a specific project, or --copy anywhere files should not depend on this clone.

Status lines (one per item):
  LINKED <name>     symlink created
  COPIED <name>     file or directory copied
  OK <name>         already installed correctly
  CONFLICT <name>   destination exists and differs (needs --force)
  UPDATED <name>    destination overwritten (--force)
  FAILED <name>     operation failed (e.g. permission denied)

Exits 1 on usage error, 2 if any CONFLICT was printed, 3 if any FAILED.
HELP
}

# --- helpers ------------------------------------------------------------

resolve() {
  local resolved
  resolved=$(readlink -f "$1" 2>/dev/null) && echo "$resolved" && return
  echo "$(cd "$(dirname "$1")" 2>/dev/null && pwd)/$(basename "$1")"
}

contains() {
  local needle="$1"; shift
  for item in "$@"; do
    [ "$item" = "$needle" ] && return 0
  done
  return 1
}

valid_name() {
  case "$1" in
    -*|*/*|*\\*|.|..) return 1 ;;
    *) return 0 ;;
  esac
}

# --- locate the source repo (parent of this script's directory) ----------

src_root=$(cd "$(dirname "$0")/.." && pwd)
agents_src="$src_root/agents"
skills_src="$src_root/skills"

[ -d "$agents_src" ] || { echo "FATAL: agents/ not found at $src_root" >&2; exit 1; }
[ -d "$skills_src" ] || { echo "FATAL: skills/ not found at $src_root" >&2; exit 1; }

# --- parse arguments ----------------------------------------------------

scope="global"
force=0
category="both"
method=""
names=()

while [ $# -gt 0 ]; do
  case "$1" in
    --global)       scope="global";    shift ;;
    --project)      scope="project";   shift ;;
    --copy)         method="copy";     shift ;;
    --symlink)      method="symlink";  shift ;;
    --force)        force=1;           shift ;;
    --agents-only)  category="agents"; shift ;;
    --skills-only)  category="skills"; shift ;;
    -h|--help)      show_help; exit 0 ;;
    --)  shift; while [ $# -gt 0 ]; do names+=("$1"); shift; done ;;
    -*)  echo "FATAL: unknown option: $1" >&2; exit 1 ;;
    *)   names+=("$1"); shift ;;
  esac
done

# --- resolve destination ------------------------------------------------

case "$scope" in
  global)  dest_root="${HOME}/.config/opencode" ;;
  project) dest_root="${PWD}/.opencode" ;;
esac
dest_agents="$dest_root/agents"
dest_skills="$dest_root/skills"

# reject if a parent path is a symlink (defense-in-depth against write-through)
for d in "$dest_root" "$dest_agents" "$dest_skills"; do
  [ -e "$d" ] && [ -L "$d" ] && { echo "FATAL: $d is a symlink — refusing to write through it" >&2; exit 1; }
done

# --- resolve method (default: symlink for global, copy for project) -----

if [ -z "$method" ]; then
  case "$scope" in
    global)  method="symlink" ;;
    project) method="copy" ;;
  esac
fi

# --- collect every available agent and skill ----------------------------

all_agents=()
for f in "$agents_src"/*.md; do
  [ -f "$f" ] && all_agents+=("$(basename "$f" .md)")
done

all_skills=()
for d in "$skills_src"/*/; do
  [ -f "${d}SKILL.md" ] && all_skills+=("$(basename "$d")")
done

# --- filter to selection ------------------------------------------------

sel_agents=()
sel_skills=()

if [ ${#names[@]} -gt 0 ]; then
  for name in "${names[@]}"; do
    valid_name "$name" || { echo "FATAL: invalid name: $name" >&2; exit 1; }
    if contains "$name" "${all_agents[@]}"; then
      sel_agents+=("$name"); continue
    fi
    if contains "$name" "${all_skills[@]}"; then
      sel_skills+=("$name"); continue
    fi
    echo "FATAL: unknown agent or skill: $name" >&2; exit 1
  done
else
  if [ ${#all_agents[@]} -gt 0 ]; then sel_agents=("${all_agents[@]}"); fi
  if [ ${#all_skills[@]} -gt 0 ]; then sel_skills=("${all_skills[@]}"); fi
fi

[ "$category" = "skills" ] && sel_agents=()
[ "$category" = "agents" ] && sel_skills=()

total=$(( ${#sel_agents[@]} + ${#sel_skills[@]} ))
[ "$total" -gt 0 ] || { echo "FATAL: nothing selected" >&2; exit 1; }

[ ${#sel_agents[@]} -gt 0 ] && mkdir -p "$dest_agents"
[ ${#sel_skills[@]} -gt 0 ] && mkdir -p "$dest_skills"

# --- install helpers ----------------------------------------------------

status=0

bump_status() { [ "$1" -gt "$status" ] && status=$1; }

do_symlink() {
  src="$1" dest="$2" name="$3"

  if [ -L "$dest" ] && [ "$(resolve "$dest")" = "$(resolve "$src")" ]; then
    echo "OK $name"; return
  fi

  if [ ! -e "$dest" ] && [ ! -L "$dest" ]; then
    if ln -s "$src" "$dest"; then echo "LINKED $name"
    else echo "FAILED $name"; bump_status 3; fi
    return
  fi

  if [ "$force" -ne 1 ]; then
    echo "CONFLICT $name"; bump_status 2; return

  fi

  tmp="${dest}.tmp.$$"
  if ln -s "$src" "$tmp" && rm -rf "$dest" && mv "$tmp" "$dest"; then
    echo "UPDATED $name"
  else
    rm -rf "$tmp"; echo "FAILED $name"; bump_status 3
  fi
}
do_copy() {
  src="$1" dest="$2" name="$3"

  if { [ -e "$dest" ] || [ -L "$dest" ]; } && diff -rq "$src" "$dest" >/dev/null 2>&1; then
    echo "OK $name"; return
  fi

  if [ ! -e "$dest" ] && [ ! -L "$dest" ]; then
    if cp -r "$src" "$dest"; then echo "COPIED $name"
    else echo "FAILED $name"; bump_status 3; fi
    return
  fi

  if [ "$force" -ne 1 ]; then
    echo "CONFLICT $name"; bump_status 2; return

  fi

  tmp="${dest}.tmp.$$"
  if cp -r "$src" "$tmp" && rm -rf "$dest" && mv "$tmp" "$dest"; then
    echo "UPDATED $name"
  else
    rm -rf "$tmp"; echo "FAILED $name"; bump_status 3
  fi
}
install_item() {
  if [ "$method" = "symlink" ]; then do_symlink "$@"
  else                               do_copy    "$@"; fi
}

# --- install agents -----------------------------------------------------

if [ ${#sel_agents[@]} -gt 0 ]; then
  for name in "${sel_agents[@]}"; do
    src="$agents_src/$name.md"
    dest="$dest_agents/$name.md"
    [ -f "$src" ] || { echo "FATAL: no such agent: $src" >&2; exit 1; }
    install_item "$src" "$dest" "$name"
  done
fi

# --- install skills -----------------------------------------------------

if [ ${#sel_skills[@]} -gt 0 ]; then
  for name in "${sel_skills[@]}"; do
    src="$skills_src/$name"
    dest="$dest_skills/$name"
    [ -d "$src" ] || { echo "FATAL: no such skill: $src" >&2; exit 1; }
    install_item "$src" "$dest" "$name"
  done
fi

exit "$status"
