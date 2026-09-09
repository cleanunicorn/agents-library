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


if __name__ == "__main__":
    unittest.main()
