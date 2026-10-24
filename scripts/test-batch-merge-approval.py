#!/usr/bin/env python3
"""Check that batch-merge-prs answers routine worker approvals and relays only the rare ones.

batch-merge-prs runs its reviewer and investigators in Herdr tabs. Relaying
every permission prompt stalls them until the user answers; approving
everything lets a worker merge, push, or touch secrets because a dialog
offered "Allow". These checks hold both halves of the rule in
references/herdr.md § Approvals, and keep that file standalone: the skill is
installed without the manager, so it must not lean on the manager's policy.

The patterns match load-bearing words, not prose ornament, so a copy-edit
that keeps the rule keeps these green.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "batch-merge-prs"

# The relay-everything rule this policy replaced, in any of its phrasings.
OLD_RELAY_RULE = re.compile(r"(?i)never approve|relay any question or approval")

# Any path into the manager skill: its files are not installed alongside this one.
MANAGER_REFERENCE = re.compile(r"skills/manager|\.\./manager|manager/references|console\.md")

# Each escalation case in herdr.md § Approvals, by the words that make it
# that case. All of a case's words must sit in one numbered item, in any order.
# Words match as substrings, so none may hide inside another ("push" in "force-push").
ESCALATIONS = {
    "merges and remote writes": ("merging", "a push", "force-push", "pr write", "main branch"),
    "destruction outside the run": ("rm -rf", "branch", "worktree", "this run did not create"),
    "secrets and global settings": ("secrets", "credentials", "global"),
    "the ask-first list": ("ask-first list",),
    "an unclassifiable prompt": ("cannot classify",),
}


def section(text, heading):
    """Return one `## heading` section, up to the next one."""
    found = re.search(rf"(?ms)^## {heading}\n.*?(?=^## |\Z)", text)
    if not found:
        raise AssertionError(f"no '## {heading}' section")
    return found.group(0)


def relay_list(policy):
    """Return the numbered escalation list under § Approvals' relay bullet."""
    found = re.search(r"(?ms)^- \*\*Relay to the user only\*\*.*?(?=^\S|\Z)", policy)
    if not found:
        raise AssertionError("§ Approvals has no '**Relay to the user only**' bullet")
    return found.group(0)


class BatchMergeApprovalTests(unittest.TestCase):
    def read(self, relative):
        return (SKILL / relative).read_text(encoding="utf-8")

    def expect(self, label, text, pattern, why):
        # Prose wraps anywhere; match the words, not the line breaks.
        if not re.search(pattern, " ".join(text.split())):
            self.fail(f"{label}: {why} — nothing matched {pattern!r}")

    def test_old_relay_everything_rule_is_gone(self):
        for path in sorted(SKILL.rglob("*.md")):
            with self.subTest(path=str(path.relative_to(ROOT))):
                found = OLD_RELAY_RULE.search(" ".join(path.read_text(encoding="utf-8").split()))
                self.assertIsNone(found, f"{path.name} still forbids answering approvals")

    def test_policy_is_standalone(self):
        for path in sorted(SKILL.rglob("*.md")):
            with self.subTest(path=str(path.relative_to(ROOT))):
                found = MANAGER_REFERENCE.search(path.read_text(encoding="utf-8"))
                self.assertIsNone(found, f"{path.name} depends on the manager skill's files")

    def test_routine_prompts_are_answered_persistently_within_the_run(self):
        policy = section(self.read("references/herdr.md"), "Approvals")
        label = "herdr.md § Approvals"
        self.expect(label, policy, r"(?i)answer every routine",
                    "routine prompts are no longer answered by default")
        self.expect(label, policy, r"(?i)broadest persistent option",
                    "answers are not persistent, so the same prompt returns")
        self.expect(label, policy, r"(?i)never the user's global host settings",
                    "a persistent answer could rewrite global host settings")
        self.expect(label, policy, r"(?i)outside the run's own scope",
                    "a persistent answer could write settings into the user's checkout")
        self.expect(label, policy, r"(?i)session or once",
                    "no fallback when only an out-of-scope option persists")
        self.expect(label, policy, r"agent send-keys",
                    "a blocked menu cannot be answered with agent prompt")

    def test_every_answer_is_logged_and_redacted(self):
        policy = section(self.read("references/herdr.md"), "Approvals")
        label = "herdr.md § Approvals"
        self.expect(label, policy, r"<run-dir>/approvals\.md",
                    "auto-answers are not logged for the user to audit")
        self.expect(label, policy, r"(?i)time.{0,20}worker.{0,20}asked.{0,20}option",
                    "the approvals log no longer says what each row records")
        self.expect(label, policy, r"(?i)own one-line summary.{0,80}never the prompt's text pasted in",
                    "a prompt's text, secrets and all, could be pasted into the log")
        self.expect(label, policy, r"(?i)redact any secret.{0,120}log.{0,40}user",
                    "a secret shown in a prompt could reach the log or the user")
        report = self.read("SKILL.md")
        self.expect("SKILL.md", report, r"approvals\.md",
                    "the Phase 4 report does not point the user at the approvals log")

    def test_every_escalation_case_is_relayed(self):
        policy = section(self.read("references/herdr.md"), "Approvals")
        # The user must see "Allow always" was on offer, and get the scope they chose.
        self.expect("herdr.md § Approvals", policy,
                    r"(?i)verbatim with the host's options.{0,80}exactly the option the user names",
                    "an escalated prompt loses its menu, or the user's answer is widened")
        items = [" ".join(item.split()).lower()
                 for item in re.split(r"(?m)^  \d+\. ", relay_list(policy))[1:]]
        for case, words in ESCALATIONS.items():
            with self.subTest(case=case):
                self.assertTrue(any(all(word in item for word in words) for item in items),
                                f"herdr.md § Approvals: escalation case missing: {case}")

    def test_a_dialog_never_widens_the_skill_or_a_role(self):
        policy = section(self.read("references/herdr.md"), "Approvals")
        label = "herdr.md § Approvals"
        self.expect(label, policy, r"(?i)never authori[sz]es",
                    "an Allow in a host dialog could authorize a forbidden action")
        self.expect(label, policy, r"(?i)host permission is not role permission",
                    "an approved prompt could widen a read-only role")
        self.expect(label, policy, r"(?i)unattended.{0,120}reject",
                    "unattended runs have no reversible default for an escalation")
        # The escalation list is only safe because the skill itself never writes GitHub.
        self.expect("SKILL.md", self.read("SKILL.md"),
                    r"(?i)no github writes:\*\* never push, merge, close, or comment",
                    "the skill-level ban on GitHub writes is gone")

    def test_readme_names_every_escalation_case(self):
        # The README says "only", so a case it leaves out reads as auto-answered.
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        found = re.search(r"(?s)### The Batch PR Merge Skill\n.*?(?=\n### )", readme)
        self.assertIsNotNone(found, "README has no batch-merge-prs section")
        label = "README batch-merge-prs"
        text = found.group(0)
        self.expect(label, text, r"(?i)answers its herdr workers' routine permission prompts itself",
                    "README no longer says the skill answers routine approvals")
        relayed = re.search(r"(?i)relays to you only(.*?)\.", " ".join(text.split()))
        self.assertIsNotNone(relayed, f"{label}: no 'relays to you only' list")
        for words in (("merges", "pushes", "github writes"), ("main-branch",),
                      ("destruction outside the run",), ("secrets", "global settings"),
                      ("ask-first list",), ("cannot classify",)):
            with self.subTest(words=words):
                self.assertTrue(all(word in relayed.group(1).lower() for word in words),
                                f"{label}: relay list omits {words}")


if __name__ == "__main__":
    unittest.main()
