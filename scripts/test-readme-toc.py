#!/usr/bin/env python3
"""Check README.md's table of contents and every in-page link in the guides.

The table of contents is the list between the toc markers. It must name every
`##` section, in document order, with the heading's own text as its label, so
an added, renamed, or moved section fails here instead of leaving a dead or
missing link behind.

Anchors follow GitHub's slug rule for the headings these guides use: lowercase,
drop punctuation other than hyphens and underscores, turn each space into a
hyphen, and suffix repeats with -1, -2 in document order. This models the
renderer; it is not one.
"""

import re
import unittest
from pathlib import Path
from typing import NamedTuple


ROOT = Path(__file__).resolve().parent.parent
LINKED_GUIDES = ("README.md", "AGENTS.md", "templates/AGENTS.md")
TOC_START = "<!-- toc:start -->"
TOC_END = "<!-- toc:end -->"
TOC_LABEL = "**Contents**"

HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
TOC_ENTRY = re.compile(r"^- \[([^\]]+)\]\(#([^)\s]+)\)$")
IN_PAGE_LINK = re.compile(r"\]\(#([^)\s]+)\)")


class Heading(NamedTuple):
    line: int
    level: int
    title: str
    anchor: str


def slug(title):
    text = title.replace("`", "").strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def prose_lines(text):
    """Yield (line number, line) outside fenced code, where `#` is a comment."""
    fence = None
    for number, line in enumerate(text.splitlines(), start=1):
        if fence is None:
            opener = FENCE.match(line)
            if opener:
                fence = opener.group(1)
                continue
            yield number, line
            continue
        closer = line.strip()
        if closer and set(closer) == {fence[0]} and len(closer) >= len(fence):
            fence = None


def headings(text):
    found, used = [], set()
    for number, line in prose_lines(text):
        match = HEADING.match(line)
        if not match:
            continue
        title = match.group(2)
        base = anchor = slug(title)
        suffix = 0
        while anchor in used:
            suffix += 1
            anchor = f"{base}-{suffix}"
        used.add(anchor)
        found.append(Heading(number, len(match.group(1)), title, anchor))
    return found


def link_problems(text):
    anchors = {heading.anchor for heading in headings(text)}
    return [f"line {number}: link #{anchor} matches no heading"
            for number, line in prose_lines(text)
            for anchor in IN_PAGE_LINK.findall(line)
            if anchor not in anchors]


def toc_problems(text):
    lines = list(prose_lines(text))
    starts = [number for number, line in lines if line.strip() == TOC_START]
    ends = [number for number, line in lines if line.strip() == TOC_END]
    if len(starts) != 1 or len(ends) != 1 or starts[0] > ends[0]:
        return [f"expected one {TOC_START} … {TOC_END} block, found "
                f"{len(starts)} start and {len(ends)} end markers"]
    start, end = starts[0], ends[0]

    all_headings = headings(text)
    sections = [heading for heading in all_headings if heading.level == 2]
    problems = []
    if not any(heading.level == 1 and heading.line < start for heading in all_headings):
        problems.append("the table of contents must come after the document title")
    if sections and sections[0].line < end:
        problems.append(f"the table of contents must come before the first section "
                        f"(## {sections[0].title}, line {sections[0].line})")

    body = [(number, line) for number, line in lines
            if start < number < end and line.strip()]
    if not body or body[0][1].strip() != TOC_LABEL:
        problems.append(f"the table of contents must open with {TOC_LABEL}")
    else:
        body = body[1:]

    by_anchor = {heading.anchor: heading for heading in all_headings}
    listed = []
    for number, line in body:
        entry = TOC_ENTRY.match(line.strip())
        if not entry:
            problems.append(f"line {number}: not a `- [Title](#anchor)` entry: {line.strip()}")
            continue
        label, anchor = entry.groups()
        target = by_anchor.get(anchor)
        if target is None:
            problems.append(f"line {number}: link #{anchor} matches no heading")
        elif target.level != 2:
            problems.append(f"line {number}: link #{anchor} is not a `##` section")
        elif anchor in listed:
            problems.append(f"line {number}: #{anchor} is listed twice")
        else:
            listed.append(anchor)
            if label != target.title:
                problems.append(f"line {number}: label {label!r} should match "
                                f"its heading {target.title!r}")

    for section in sections:
        if section.anchor not in listed:
            problems.append(f"## {section.title} (line {section.line}) has no "
                            f"table of contents entry #{section.anchor}")

    in_document_order = [section.anchor for section in sections if section.anchor in listed]
    if listed != in_document_order:
        problems.append(f"table of contents is out of document order: "
                        f"expected {in_document_order}, found {listed}")
    return problems


FIXTURE = """# Title

Intro.

<!-- toc:start -->
**Contents**

- [Install (Codex plugin)](#install-codex-plugin)
- [Updating](#updating)
<!-- toc:end -->

## Install (Codex plugin)

```sh
# Global: a shell comment, not a heading
## not a section either
```

See [Updating](#updating).

## Updating

### Troubleshooting
"""

INSTALL_ENTRY = "- [Install (Codex plugin)](#install-codex-plugin)\n"
UPDATING_ENTRY = "- [Updating](#updating)\n"


class LiveGuideTests(unittest.TestCase):
    def test_readme_toc_lists_every_section(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(toc_problems(text), [])

    def test_in_page_links_resolve(self):
        for guide in LINKED_GUIDES:
            with self.subTest(guide=guide):
                text = (ROOT / guide).read_text(encoding="utf-8")
                self.assertEqual(link_problems(text), [])


class SlugTests(unittest.TestCase):
    def test_github_slug_rule(self):
        cases = {
            "Install (Codex plugin)": "install-codex-plugin",
            "5. Run the checks locally": "5-run-the-checks-locally",
            "End-to-end tests (Playwright)": "end-to-end-tests-playwright",
            "The `manager` skill": "the-manager-skill",
        }
        for title, anchor in cases.items():
            with self.subTest(title=title):
                self.assertEqual(slug(title), anchor)

    def test_repeats_are_suffixed_across_levels(self):
        text = "# Setup\n## Setup\n### Setup\n## Other ##\n"
        self.assertEqual([heading.anchor for heading in headings(text)],
                         ["setup", "setup-1", "setup-2", "other"])

    def test_fenced_hash_lines_are_not_headings(self):
        self.assertEqual([heading.title for heading in headings(FIXTURE)],
                         ["Title", "Install (Codex plugin)", "Updating", "Troubleshooting"])


class TocDriftTests(unittest.TestCase):
    def assertProblem(self, text, fragment):
        problems = toc_problems(text)
        self.assertTrue(any(fragment in problem for problem in problems),
                        f"no problem mentions {fragment!r}: {problems}")

    def test_fixture_is_clean(self):
        self.assertEqual(toc_problems(FIXTURE), [])
        self.assertEqual(link_problems(FIXTURE), [])

    def test_link_with_no_heading_fails(self):
        self.assertProblem(FIXTURE.replace("](#updating)\n<!--", "](#updatng)\n<!--"),
                           "#updatng matches no heading")

    def test_section_with_no_entry_fails(self):
        self.assertProblem(FIXTURE + "\n## Releasing\n", "## Releasing")

    def test_section_added_with_its_entry_passes(self):
        text = FIXTURE.replace(UPDATING_ENTRY, UPDATING_ENTRY + "- [Releasing](#releasing)\n")
        self.assertEqual(toc_problems(text + "\n## Releasing\n"), [])

    def test_entries_out_of_order_fail(self):
        text = FIXTURE.replace(INSTALL_ENTRY + UPDATING_ENTRY, UPDATING_ENTRY + INSTALL_ENTRY)
        self.assertProblem(text, "out of document order")

    def test_duplicate_entry_fails(self):
        self.assertProblem(FIXTURE.replace(UPDATING_ENTRY, UPDATING_ENTRY * 2), "listed twice")

    def test_stale_label_fails(self):
        self.assertProblem(FIXTURE.replace("[Updating](#updating)\n<!--",
                                           "[Update](#updating)\n<!--"),
                           "label 'Update'")

    def test_malformed_entry_fails(self):
        self.assertProblem(FIXTURE.replace(UPDATING_ENTRY, "- Updating\n"),
                           "not a `- [Title](#anchor)` entry")

    def test_subsection_entry_fails(self):
        self.assertProblem(FIXTURE.replace(UPDATING_ENTRY, UPDATING_ENTRY
                                           + "- [Troubleshooting](#troubleshooting)\n"),
                           "not a `##` section")

    def test_missing_block_fails(self):
        self.assertProblem(FIXTURE.replace(TOC_START, ""), "expected one")

    def test_block_after_first_section_fails(self):
        block = FIXTURE[FIXTURE.index(TOC_START):FIXTURE.index(TOC_END) + len(TOC_END)]
        text = FIXTURE.replace(block, "").replace("See [Updating]", block + "\n\nSee [Updating]")
        self.assertProblem(text, "before the first section")

    def test_broken_in_page_link_fails(self):
        problems = link_problems(FIXTURE.replace("See [Updating](#updating)",
                                                 "See [Updating](#update)"))
        self.assertEqual(problems, ["line 19: link #update matches no heading"])


if __name__ == "__main__":
    unittest.main()
