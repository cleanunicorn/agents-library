#!/usr/bin/env python3
"""Check this repository's Claude/Codex packaging contracts using only stdlib.

These are repository invariants, not a replacement for either host's complete
manifest/YAML schema validator. No installation or model invocation is needed.
"""

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_NAME = "agents-library"
# Context ceilings — see test_definition_size_budgets. Lower them as
# definitions shrink; never raise one to admit growth.
DESCRIPTION_WORD_CEILING = 60
DESCRIPTION_CHAR_CEILING = 420
AGENT_WORD_CEILING = 1800
# Per-skill root ceilings, keyed by name: each is the current size rounded up.
# domains/, lenses/, references/ are loaded on demand and not budgeted here.
SKILL_ROOT_WORD_CEILINGS = {
    "batch-merge-prs": 1400,
    "describe-codebase": 1000,
    "install-agents": 1400,
    "manager": 2700,
    "plan-feature": 1300,
    "review-design": 1800,
    "review-pr": 2200,
    "review-ux-psychology": 3000,
    "simplify-sweep": 1800,
    "triage-issues": 2800,
}
# The manager's agent-type catalogue — see test_manager_roster_is_chosen_per_item.
# Further types are allowed; these are the ones the pipeline starts.
MANAGER_AGENT_TYPES = ("planner", "coordinator", "reviewer", "final reviewer")
MANAGER_CARD_LABELS = ("Does", "Writes", "Skill", "Brief", "Sees", "Never sees",
                       "Returns", "Runs", "Floor")
# Phrases that prescribe the team instead of letting the manager pick it. One
# alternative per line. "two levels" and "both roles" are the topology, not
# the roster, and README's "counterpart to `review-pr`" is a sibling skill.
MANAGER_FIXED_ROSTER = re.compile("(?i)" + "|".join((
    # A count in front of a roster noun. "one" is left out on purpose: the
    # contract itself says "one obvious home → one planner".
    r"\b(two|2|both|a pair of)\s+(\w+\s+){0,2}(planners|reviewers|plans)\b",
    r"\b(\d+|three|four|five|six|seven|eight|nine|ten)\s+(\w+\s+){0,2}"
    r"(planners|reviewers|reviews|team agents)\b",
    r"\b(two|both) reviews\b",
    r"\b(two|three) `(plan-feature|review-pr)`",
    r"\btwo agents\b",
    r"\ba second (planner|reviewer)\b",
    # Exactly two of something: arity, pairs, and closed A | B labels.
    r"\b(the other|either|neither) (plan|planner|reviewer|review)s?\b",
    r"\bone of two\b",
    r"\bthird agent\b",
    r"\bpaired roles\b",
    r"\ba pair runs\b",
    r"\bsame-kind pair\b",
    r"\bof a pair\b",
    r"\bcounterpart's\b",
    r"\b(planner|reviewer) A, B\b",
    r"\b(planner|reviewer) A and B\b",
    r"\b(planner|reviewer):\s+A \| B",
    r"\bplan a and plan b\b",
    r"\bplan_a\b",
    r"\bplan_b\b",
    # Fragments of main's sentences that survive no rewording of them.
    r"\bboth get\b",
    r"\btwo after the\b",
)))


class PluginLayoutTests(unittest.TestCase):
    def manifest(self, path):
        manifest = json.loads((ROOT / path).read_text(encoding="utf-8"))
        self.assertIsInstance(manifest, dict, path)
        return manifest

    def nonempty_string(self, value):
        self.assertIsInstance(value, str)
        self.assertTrue(value.strip(), "expected a nonempty string")

    def local_directory(self, value, expected):
        self.nonempty_string(value)
        self.assertTrue(value.startswith("./"), value)
        path = (ROOT / value).resolve()
        self.assertEqual(path, ROOT / expected)
        self.assertTrue(path.is_dir(), str(path))

    def marketplace_entry(self, path):
        marketplace = self.manifest(path)
        self.assertEqual(marketplace["name"], PLUGIN_NAME)
        self.assertIsInstance(marketplace["plugins"], list)
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], PLUGIN_NAME)
        return entry

    def test_shared_plugin_identity(self):
        for platform in ("claude", "codex"):
            with self.subTest(platform=platform):
                manifest = self.manifest(f".{platform}-plugin/plugin.json")
                self.assertEqual(manifest["name"], PLUGIN_NAME)
                self.nonempty_string(manifest["description"])
                self.nonempty_string(manifest["author"]["name"])

    def test_claude_marketplace(self):
        marketplace = self.manifest(".claude-plugin/marketplace.json")
        self.nonempty_string(marketplace["owner"]["name"])
        entry = self.marketplace_entry(".claude-plugin/marketplace.json")
        self.assertEqual(entry["source"]["source"], "github")
        self.assertEqual(entry["source"]["repo"], "cleanunicorn/agents-library")

    def test_claude_component_discovery(self):
        manifest = self.manifest(".claude-plugin/plugin.json")
        for component in ("agents", "skills"):
            with self.subTest(component=component):
                paths = manifest.get(component, f"./{component}/")
                if isinstance(paths, str):
                    paths = [paths]
                self.assertIsInstance(paths, list)
                self.assertTrue(paths, f"{component} must remain discoverable")
                for path in paths:
                    self.local_directory(path, component)

    def test_release_version_ownership(self):
        # Release automation splits the Codex version into three integers;
        # Claude intentionally follows commit SHAs instead of a second version.
        claude = self.manifest(".claude-plugin/plugin.json")
        self.assertNotIn("version", claude)
        codex = self.manifest(".codex-plugin/plugin.json")
        self.nonempty_string(codex["version"])
        self.assertRegex(codex["version"], r"\A(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")

    def test_codex_skill_discovery(self):
        codex = self.manifest(".codex-plugin/plugin.json")
        self.local_directory(codex["skills"], "skills")

    def test_codex_interface(self):
        interface = self.manifest(".codex-plugin/plugin.json")["interface"]
        for field in ("displayName", "shortDescription", "longDescription",
                      "developerName", "category"):
            with self.subTest(field=field):
                self.nonempty_string(interface[field])
        self.assertIsInstance(interface["capabilities"], list)
        for capability in interface["capabilities"]:
            self.nonempty_string(capability)
        prompts = interface["defaultPrompt"]
        self.assertIsInstance(prompts, list)
        self.assertTrue(1 <= len(prompts) <= 3)
        for prompt in prompts:
            self.nonempty_string(prompt)
            self.assertLessEqual(len(prompt), 128)

    def test_codex_marketplace(self):
        marketplace = self.manifest(".agents/plugins/marketplace.json")
        self.nonempty_string(marketplace["interface"]["displayName"])
        entry = self.marketplace_entry(".agents/plugins/marketplace.json")
        self.assertEqual(entry["source"]["source"], "local")
        self.local_directory(entry["source"]["path"], "")
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
        self.assertEqual(entry["category"],
                         self.manifest(".codex-plugin/plugin.json")["interface"]["category"])

    def test_shared_definition_frontmatter(self):
        agents = sorted((ROOT / "agents").glob("*.md"))
        skill_dirs = sorted(path for path in (ROOT / "skills").iterdir() if path.is_dir())
        self.assertTrue(agents, "Claude/opencode agents are missing")
        self.assertTrue(skill_dirs, "shared skills are missing")
        definitions = [(path, path.stem, True) for path in agents]
        definitions += [(path / "SKILL.md", path.name, False) for path in skill_dirs]
        for path, name, is_agent in definitions:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertTrue(path.is_file(), "missing definition")
                self.assertTrue(path.resolve().is_relative_to(ROOT), "definition leaves plugin root")
                text = path.read_text(encoding="utf-8")
                header = re.match(r"\A---\n(.*?)\n---(?:\n|\Z)", text, re.S)
                self.assertIsNotNone(header, "missing frontmatter delimiters")
                header = header.group(1)
                # Every definition uses unquoted keys and a block description.
                # Enforce that format instead of partially decoding YAML scalars.
                inside_description = False
                for line in header.splitlines():
                    if not line.strip() or line.lstrip().startswith("#"):
                        continue
                    if line.startswith("  "):
                        self.assertTrue(inside_description,
                                        "only descriptions use block values in this repository")
                        continue
                    field = re.fullmatch(r"([a-z][a-z0-9_-]*):(?:[ \t].*)?", line)
                    self.assertIsNotNone(field,
                                         "expected a field or a two-space-indented description line")
                    inside_description = field.group(1) == "description"
                required = ("name", "description", "mode") if is_agent else ("name", "description")
                for field in required:
                    declarations = re.findall(rf"(?m)^{field}:", header)
                    self.assertEqual(len(declarations), 1, f"expected exactly one {field}")
                self.assertRegex(header, rf"(?m)^name: {re.escape(name)}$")
                self.assertRegex(header, r"(?m)^description: [>|][-+]?\n  \S",
                                 "use a nonempty indented block description (description: >-)")
                if is_agent:
                    self.assertRegex(header, r"(?m)^mode: subagent$")

    def test_definition_size_budgets(self):
        """Descriptions and definition bodies stay within a context ceiling.

        Every description is loaded into the model's context on every task so
        it can route to the right definition; hosts truncate long ones when
        many are installed. A definition's root file is loaded whole when it
        runs. Words (and characters, so one long token cannot hide) are the
        measure, not lines: a single 1,000-character line costs as much as
        twenty short ones.
        """
        agents = sorted((ROOT / "agents").glob("*.md"))
        skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
        self.assertEqual({path.parent.name for path in skills}, set(SKILL_ROOT_WORD_CEILINGS),
                         "a skill was added or removed — give it a root ceiling")
        for path in agents + skills:
            with self.subTest(path=str(path.relative_to(ROOT))):
                text = path.read_text(encoding="utf-8")
                header = re.match(r"\A---\n(.*?)\n---", text, re.S).group(1) + "\n"
                # The block runs to the next top-level field, blank lines included.
                block = re.search(r"(?ms)^description: [>|][-+]?\n((?:(?:  [^\n]*)?\n)+?)(?=^\S|\Z)", header)
                self.assertIsNotNone(block, "missing block description")
                description = " ".join(block.group(1).split())
                words = len(description.split())
                self.assertLessEqual(words, DESCRIPTION_WORD_CEILING, f"description is {words} words")
                self.assertLessEqual(len(description), DESCRIPTION_CHAR_CEILING,
                                     f"description is {len(description)} characters")
                body_words = len(text.split())
                ceiling = (AGENT_WORD_CEILING if path.parent.name == "agents"
                           else SKILL_ROOT_WORD_CEILINGS[path.parent.name])
                self.assertLessEqual(body_words, ceiling, f"root file is {body_words} words")

    def test_manager_role_marker_agrees(self):
        """The manager skill's two roles are told apart by one literal line.

        SKILL.md's opening paragraph is the only router: the exact first line
        makes a manager, a launch header without it fails closed, anyone else
        is the super manager. The super manager sends that line and the launch
        brief opens with it. A second router in a reference, or a sender that
        puts anything else on the line, is how a started manager ends up
        starting managers of its own.
        """
        marker = "role: manager"
        skill = ROOT / "skills/manager"
        texts = {name: (skill / name).read_text(encoding="utf-8")
                 for name in ("SKILL.md", "references/super-manager.md",
                              "references/manager-brief.md")}
        router = " ".join(texts["SKILL.md"].split())
        self.assertRegex(router, rf"A prompt whose first line is exactly `{marker}` makes you a \*\*manager\*\*",
                         "SKILL.md no longer routes on the exact first line")
        self.assertRegex(router, r"without that first line is a malformed launch: start nobody",
                         "SKILL.md no longer fails closed on a malformed launch")
        self.assertRegex(router, r"Anyone else is the \*\*super manager\*\*",
                         "SKILL.md no longer has a default role")
        for name in ("references/super-manager.md", "references/manager-brief.md"):
            self.assertNotRegex(" ".join(texts[name].split()),
                                r"(?i)go back to `SKILL\.md`|makes you (a|the) \*\*",
                                f"{name} decides a role; SKILL.md is the only router")
        # Every fenced block that carries the marker is a launch form: the
        # marker is its first line, alone.
        launch_forms = 0
        for name, text in texts.items():
            for block in re.findall(r"(?ms)^[ \t]*```\n(.*?)^[ \t]*```", text):
                if marker in block:
                    launch_forms += 1
                    self.assertEqual(block.splitlines()[0].strip(), marker,
                                     f"{name}: a launch form does not open with the bare marker")
        self.assertGreaterEqual(launch_forms, 2, "expected the brief header and the compact launch form")
        # Nothing shares the marker's line when it is quoted inline as something to send.
        for name, text in texts.items():
            with self.subTest(file=name):
                self.assertIn(marker, text, f"{name} no longer names `{marker}`")
                self.assertEqual(re.findall(rf"`{marker} [^`]*`", text), [],
                                 f"{name} sends the marker with a suffix")

    def test_manager_hosting_falls_back_when_a_create_fails(self):
        """A failed Herdr create falls to native subagents, at both levels.

        `hosting-agents.md` is the only file both roles read for hosting, so it
        owns this rule. "Prefer Herdr, else native subagents" answers a host
        that has no Herdr; it does not answer a `workspace create` or
        `tab create` that failed, and without this rule that run is blocked.
        """
        hosting = " ".join((ROOT / "skills/manager/references/hosting-agents.md")
                           .read_text(encoding="utf-8").split())
        self.assertRegex(hosting, r"`herdr workspace create` or `herdr tab create` fails"
                                  r".{0,200}?native subagents",
                         "a failed create no longer falls back to native subagents")
        self.assertRegex(hosting, r"`herdr tab create` fails"
                                  r".{0,250}?keep the recorded manager workspace id",
                         "a failed team tab must not lose its parent workspace id")

    def test_manager_agent_type_cards(self):
        """The manager's catalogue defines every type it can start, the same way.

        `references/agent-types.md` carries one card per type with the same
        labels on every card, exactly one type that writes, a brief that
        exists, and floors that still say who may own each responsibility.
        """
        skill = ROOT / "skills/manager"
        catalogue = skill / "references/agent-types.md"
        self.assertTrue(catalogue.is_file(), "the agent-type catalogue is missing")
        catalogue_lines = catalogue.read_text(encoding="utf-8").splitlines()
        rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
                for line in catalogue_lines if line.lstrip().startswith("|")]
        header = next((row for row in rows if row and row[0] == "Label"), None)
        self.assertIsNotNone(header, "agent-types.md has no `| Label | <type> | …` card table")
        types = header[1:]
        for name in MANAGER_AGENT_TYPES:
            self.assertIn(name, types, f"{name}: a type the pipeline starts has no card")
        cards = {}
        for row in rows:
            if row[0] in MANAGER_CARD_LABELS:
                # zip would silently drop a cell that a stray pipe split off.
                self.assertEqual(len(row), len(types) + 1, f"`{row[0]}` row has {len(row) - 1} cells")
                self.assertNotIn(row[0], cards, f"`{row[0]}` appears on the cards twice")
                cards[row[0]] = dict(zip(types, row[1:]))
        for label in MANAGER_CARD_LABELS:
            with self.subTest(label=label):
                self.assertIn(label, cards, f"no `{label}` row on the cards")
                for name in types:
                    self.assertTrue(cards[label].get(name), f"{name}: `{label}` is empty")
        # A blanket prohibition contradicts the card's own `Sees` cell: what an
        # agent may see was produced earlier in the run too.
        for name in types:
            self.assertNotRegex(cards["Never sees"][name], r"(?i)\b(anything|everything|nothing)\b",
                                f"{name}: `Never sees` must list artifacts, not forbid the whole run")
        # The floors are who may own a responsibility. These are their
        # load-bearing words, not the sentences around them.
        floors = {"planner": r"coordinator did not write",
                  "reviewer": r"neither planned nor implemented",
                  "final reviewer": r"did not write"}
        for name, owner in floors.items():
            self.assertRegex(cards["Floor"][name], owner, f"{name}: the floor lost its eligible owner")
        catalogue_text = " ".join(" ".join(catalogue_lines).split())
        for clause, why in ((r"never writes the plan it would then merge", "a failed sole planner"),
                            (r"`reuse:<label>`", "a Phase 4 reviewer reused for the final pass"),
                            (r"nothing left to check", "a final review with no new commits"),
                            (r"no delegation at all", "a host that cannot delegate")):
            self.assertRegex(catalogue_text, clause, f"the Floors section no longer covers {why}")
        writers = [name for name in types if re.match(r"\W*yes\b", cards["Writes"][name], re.I)]
        self.assertEqual(writers, ["coordinator"], "exactly one type writes to the worktree")
        for name in types:
            brief = re.search(r"`([\w-]+\.md)`", cards["Brief"][name])
            self.assertIsNotNone(brief, f"{name}: `Brief` names no file")
            self.assertTrue((skill / "references" / brief.group(1)).is_file(),
                            f"{name}: brief {brief.group(1)} does not exist")

    def test_manager_roster_is_chosen_per_item(self):
        """The manager sizes its team to the work item; no count is prescribed.

        SKILL.md points at the catalogue and keeps the rules that never
        depended on a count. A phrase that fixes the old roster — "two
        planners", "a third agent", `plan_a` — is how the prescribed team comes
        back, one copy-edit at a time. To say how many agents a run had, name
        the roster ("the roster's planners", "every plan"), not a number.
        """
        skill = ROOT / "skills/manager"
        root_text = " ".join((skill / "SKILL.md").read_text(encoding="utf-8").split())
        self.assertIn("references/agent-types.md", root_text, "SKILL.md does not point at the catalogue")
        for rule in ("Single writer.", "Independence.", "Re-run the gate yourself.", "Honest ledger."):
            self.assertIn(f"**{rule}**", root_text, f"SKILL.md lost the rule `{rule}`")
        self.assertRegex(root_text, r"\*\*Pick the roster\.\*\*.{0,600}?\broster record\b.{0,600}?\breason\b",
                         "Phase 0 no longer records the roster and its reason")
        self.assertRegex(root_text, r"- Team: roster\b", "the team block no longer reports the roster")
        # Phase 7 may hand the final pass to a Phase 4 reviewer, so a rule that
        # holds in every phase cannot say every final reviewer is new to the run.
        self.assertIn("`reuse:<label>`", root_text, "Phase 7 lost the reuse route")
        self.assertNotRegex(root_text, r"(?<!fresh )final reviewer has done nothing else",
                            "rule 2 forbids the reuse route Phase 7 allows")
        # SKILL.md still lets a manager run every pass itself on a host with no
        # delegation, where the independence floors cannot be met; the rule that
        # makes falling below a floor `blocked` has to name that exception.
        if re.search(r"unless the host has no delegation", root_text):
            self.assertRegex(root_text, r"\*\*A member that fails\.\*\*.{0,400}?below a floor"
                                        r".{0,200}?no delegation",
                             "rule 10 blocks the no-delegation fallback SKILL.md still offers")

        guides = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "docs/evals.md",
                  skill / "SKILL.md", *sorted((skill / "references").glob("*.md"))]
        for path in guides:
            with self.subTest(path=str(path.relative_to(ROOT))):
                text = path.read_text(encoding="utf-8")
                if path.name == "README.md":
                    # README also describes the sibling skills ("Ten specialized
                    # reviewers" is review-pr); only its manager section is a copy.
                    section = re.search(r"(?ms)^## The Manager Skill\n.*?(?=^## |\Z)", text)
                    self.assertIsNotNone(section, "README.md lost its manager section")
                    text = section.group(0)
                if path.name == "evals.md":
                    # Its table rows describe fixtures ("two planted plans"),
                    # not the team; the prose below them describes the pipeline.
                    text = "\n".join(line for line in text.splitlines()
                                     if not line.lstrip().startswith("|"))
                found = MANAGER_FIXED_ROSTER.search(" ".join(text.split()))
                self.assertIsNone(found, f"a fixed roster is back — found {found and found.group(0)!r}")


if __name__ == "__main__":
    unittest.main()
