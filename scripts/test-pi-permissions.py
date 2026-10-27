#!/usr/bin/env python3
"""Exercise the manager's pi permission extension against real tool calls.

pi asks for nothing on its own: skills/manager/scripts/pi-permissions.mjs is a
pi worker's only permission prompt. The cases below drive it under `node`, one
verdict per (role, tool, input): escalations ask, routine commands pass, a
reviewer writes only to the run directory, and a bad setting blocks everything.
Reports a skip without `node`.
"""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PI_SCRIPT = ROOT / "skills" / "manager" / "scripts" / "pi-permissions.mjs"

ESCALATING = ("git push --force origin feat/x", "git push origin feat/x -f", "git push origin +feat/x",
              "git push origin main", "git push origin HEAD:main", "gh pr merge 12 --squash",
              "gh pr ready 12", "git branch -D feat/x", "git worktree remove ../wt",
              "rm -rf /tmp/run/x", "rm -fr x", "git -C ../wt push --force origin feat/x",
              "git -C ../wt branch -D feat/x", "git -C ../wt worktree remove ../other",
              "git push --force-with-lease origin feat/x", "git push --all origin",
              "git push --mirror origin", "git branch -Da feat/x")
# Shapes only the pattern recipes ask for: a chained command, or a spelling the
ESCALATING_BY_PATTERN = ("cd /tmp && rm -fr x", "git --no-pager -C ../wt push origin main",
                         "git branch --delete --force feat/x", "git branch --force --delete feat/x",
                         "rm -r -f x", "rm -f -r x", "rm --recursive --force x", "rm -Rf x",
                         "rm --force -R x")
ROUTINE = ("git push origin feat/x", "git push -u origin feat/main-fix", "git status",
           "git -C ../wt log --grep push",
           "gh pr view 12", "git branch -d feat/x", "rm notes.txt")


PI_DRIVER = """
const [script, cases] = process.argv.slice(-2);
const { default: register, decide, settings } = await import(script);
const out = [];
for (const c of JSON.parse(cases)) {
  if (c.hook) {
    let handler;
    Object.assign(process.env, c.env);
    register({ on: (name, fn) => { if (name === "tool_call") handler = fn; } });
    const ctx = { hasUI: c.ui !== undefined, cwd: c.cwd, ui: { select: async () => c.ui } };
    const result = await handler({ toolName: c.tool, input: c.input }, ctx);
    out.push(result?.block ? "block" : "allow");
  } else {
    out.push(decide(settings(c.env), c.tool, c.input, c.cwd).split(":")[0]);
  }
}
console.log(JSON.stringify(out));
"""


class PiPermissionsTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node not on PATH: pi's extension is not exercised")
    def test_pi_extension_enforces_each_role(self):
        with tempfile.TemporaryDirectory() as scratch:
            base = Path(scratch).resolve()
            run_dir, worktree, sibling = base / "run", base / "wt", base / "other"
            for directory in (run_dir, worktree, sibling):
                directory.mkdir()
            (run_dir / "escape").symlink_to(worktree)
            env = {"PI_MANAGER_RUN_DIR": str(run_dir), "PI_MANAGER_MAIN": "main",
                   "PI_MANAGER_DENY": str(sibling), "PI_MANAGER_GATE": "bash scripts/check.sh"}
            coordinator = {**env, "PI_MANAGER_ROLE": "coordinator"}
            reviewer = {**env, "PI_MANAGER_ROLE": "reviewer"}
            bash = lambda command: {"command": command}
            path = lambda target: {"path": str(target)}
            cases = [(coordinator, "bash", bash(c), "ask") for c in ESCALATING + ESCALATING_BY_PATTERN]
            cases += [(reviewer, "bash", bash(c), "ask") for c in ESCALATING + ESCALATING_BY_PATTERN]
            cases += [(coordinator, "bash", bash(c), "allow") for c in ROUTINE]
            cases += [
                (coordinator, "write", path(worktree / "a.py"), "allow"),
                (coordinator, "edit", path(sibling / "a.py"), "block"),
                (reviewer, "read", path("/etc/hosts"), "allow"),
                (reviewer, "write", path(run_dir / "herdr-kinds" / "reviewer-a.md"), "allow"),
                (reviewer, "write", path(worktree / "a.py"), "block"),
                (reviewer, "write", path(run_dir / ".." / "wt" / "a.py"), "block"),
                (reviewer, "write", path(run_dir / "escape" / "a.py"), "block"),
                (reviewer, "edit", {"path": "../wt/a.py"}, "block"),
                (reviewer, "bash", bash("git diff main...HEAD | head -n 40"), "allow"),
                (reviewer, "bash", bash("bash scripts/check.sh"), "allow"),
                # The gate is matched whole: nothing may ride along after it.
                (reviewer, "bash", bash(" bash scripts/check.sh "), "allow"),
                (reviewer, "bash", bash("bash scripts/check.sh && git push origin feat/x"), "ask"),
                (reviewer, "bash", bash("bash scripts/check.sh; touch x"), "ask"),
                (reviewer, "bash", bash("git log > notes.md"), "ask"),
                (reviewer, "bash", bash("cat $(echo x)"), "ask"),
                (reviewer, "bash", bash("find . -delete"), "ask"),
                (reviewer, "bash", bash("python3 -c 'open(\"x\",\"w\")'"), "ask"),
                (reviewer, "bash", bash("git log && touch x"), "ask"),
                # A lone `&`, a numbered redirect and a write-capable option each
                # write or run something, so none is a read.
                (reviewer, "bash", bash("git log & touch x"), "ask"),
                (reviewer, "bash", bash("git status & bash /tmp/evil.sh"), "ask"),
                (reviewer, "bash", bash("git log 2>/tmp/x"), "ask"),
                (reviewer, "bash", bash("cat /etc/hosts 1>/tmp/outside.txt"), "ask"),
                (reviewer, "bash", bash("git show HEAD 2>1"), "ask"),
                (reviewer, "bash", bash("git log &>/tmp/x"), "ask"),
                (reviewer, "bash", bash("git diff --output=/tmp/outside.patch"), "ask"),
                (reviewer, "bash", bash("git diff --ext-diff main"), "ask"),
                (reviewer, "bash", bash("sed -n 'w /tmp/outside.txt' README.md"), "ask"),
                (reviewer, "bash", bash("sed -n e README.md"), "ask"),
                (reviewer, "bash", bash("sed -n -i s/x/y/ README.md"), "ask"),
                (reviewer, "bash", bash("sed -n '1p' -i README.md"), "ask"),
                (reviewer, "bash", bash("sed -n 1p --in-place README.md"), "ask"),
                (reviewer, "bash", bash("sed -n 1p -e 'w /tmp/x' README.md"), "ask"),
                (reviewer, "bash", bash("sed -n 1p -f /tmp/script.sed README.md"), "ask"),
                (reviewer, "bash", bash("sed -n 1p README.md -s"), "ask"),
                (reviewer, "bash", bash("find . -fprint /tmp/x"), "ask"),
                (reviewer, "bash", bash("find . -fprintf ../wt/x.md %p"), "ask"),
                (reviewer, "bash", bash("find . -fls /tmp/x"), "ask"),
                (reviewer, "bash", bash("rg --pre 'touch /tmp/pwn' pattern ."), "ask"),
                (reviewer, "bash", bash("git log --oneline 2>&1 | head -n 5"), "allow"),
                (reviewer, "bash", bash("sed -n '1,40p' README.md"), "allow"),
                (reviewer, "bash", bash("rg -n pattern skills | head -n 20"), "allow"),
                (reviewer, "bash", bash("find skills -name '*.md'"), "allow"),
                (reviewer, "mcp_tool", {}, "ask"),
                ({**env, "PI_MANAGER_ROLE": "admin"}, "read", path("/etc/hosts"), "block"),
                ({**reviewer, "PI_MANAGER_RUN_DIR": "relative/run"}, "read", path("/etc/hosts"), "block"),
                ({**reviewer, "PI_MANAGER_MAIN": ""}, "read", path("/etc/hosts"), "block"),
            ]
            payload = [{"env": e, "tool": t, "input": i, "cwd": str(run_dir)} for e, t, i, _ in cases]
            # The registered hook: an escalation with no UI, or a denied one, blocks.
            # Each hook case is the dialog's answer; an absent "ui" key means no UI at all.
            hooks = [({}, "block"), ({"ui": "Deny"}, "block"), ({"ui": "Allow once"}, "allow")]
            payload += [{"hook": True, "env": coordinator, "tool": "bash", "input": bash("rm -rf x"),
                         "cwd": str(run_dir), **ui} for ui, _ in hooks]
            result = subprocess.run(["node", "--input-type=module", "-e", PI_DRIVER, "--",
                                     PI_SCRIPT.as_uri(), json.dumps(payload)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr[-600:])
            verdicts = json.loads(result.stdout)
        expected = [want for *_, want in cases] + [want for _, want in hooks]
        for (case, got, want) in zip(payload, verdicts, expected):
            with self.subTest(role=case["env"].get("PI_MANAGER_ROLE"), tool=case["tool"], input=case["input"]):
                self.assertEqual(got, want)


if __name__ == "__main__":
    unittest.main()
