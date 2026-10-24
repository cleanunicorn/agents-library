#!/usr/bin/env python3
"""Check that no fenced block in the repository's Markdown holds two slash commands.

A reader copies a fenced block whole. Pasted into a Claude Code prompt, two
slash-command lines arrive as one command whose argument is everything after
the first word, so `/plugin marketplace add owner/repo` followed by
`/plugin install …` fails as an invalid owner/repo (issue #78). Each slash
command a reader is meant to paste gets its own block.

Only lines that open with a bare command word count (`/plugin …`, `/review-pr`);
a path such as `/path/to/install.py` does not.
"""

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# Any indentation: a fence nested under a list item or a blockquote is still
# one copyable block, and so is a fence indented into an indented code block.
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
BLOCKQUOTE = re.compile(r"^\s*(>\s?)+")
SLASH_COMMAND = re.compile(r"^\s*/[a-z][a-z0-9:_-]*(\s|$)")


def fenced_blocks(text):
    """Yield (opening line number, [lines]) for each fenced code block.

    Blockquote markers are stripped first so a quoted fence is seen as one. A
    fence left open at the end of the file still renders as code to the end,
    so it is yielded too.
    """
    fence, start, body = None, 0, []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = BLOCKQUOTE.sub("", raw)
        if fence is None:
            opener = FENCE.match(line)
            if opener:
                fence, start, body = opener.group(1), number, []
            continue
        closer = line.strip()
        if closer and set(closer) == {fence[0]} and len(closer) >= len(fence):
            yield start, body
            fence = None
            continue
        body.append(line)
    if fence is not None:
        yield start, body


def paste_problems(text):
    return [f"line {start}: one block holds {count} slash commands; "
            f"give each its own block so pasting one cannot merge them"
            for start, body in fenced_blocks(text)
            for count in [sum(1 for line in body if SLASH_COMMAND.match(line))]
            if count >= 2]


def markdown_files():
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    return [ROOT / path for path in listed if (ROOT / path).is_file()]


class LiveMarkdownTests(unittest.TestCase):
    def test_no_block_holds_two_slash_commands(self):
        files = markdown_files()
        self.assertIn(ROOT / "README.md", files)
        for path in files:
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertEqual(paste_problems(path.read_text(encoding="utf-8")), [])


class PasteProblemTests(unittest.TestCase):
    def test_two_plugin_commands_in_one_block_fail(self):
        # The README block issue #78 reported, verbatim.
        text = ("```\n"
                "/plugin marketplace add cleanunicorn/agents-library\n"
                "/plugin install agents-library@agents-library\n"
                "```\n")
        self.assertEqual(len(paste_problems(text)), 1)

    def test_any_two_slash_commands_fail_in_tilde_and_tagged_fences(self):
        text = "~~~text\n/review-pr\n  /agents-library:manager go\n~~~\n"
        self.assertEqual(len(paste_problems(text)), 1)

    def test_one_command_per_block_passes(self):
        text = ("1. Add the marketplace:\n\n   ```\n   /plugin marketplace add o/r\n   ```\n\n"
                "2. Install:\n\n   ```\n   /plugin install p@p\n   ```\n")
        self.assertEqual(paste_problems(text), [])

    def test_fence_left_open_at_end_of_file_fails(self):
        text = "```\n/plugin marketplace add o/r\n/plugin install p@p\n"
        self.assertEqual(len(paste_problems(text)), 1)

    def test_fence_inside_blockquote_fails(self):
        text = "> Install:\n>\n> ```\n> /plugin marketplace add o/r\n> /plugin install p@p\n> ```\n"
        self.assertEqual(len(paste_problems(text)), 1)

    def test_fence_indented_four_spaces_under_list_item_fails(self):
        text = ("1.  Install:\n\n    ```\n    /plugin marketplace add o/r\n"
                "    /plugin install p@p\n    ```\n")
        self.assertEqual(len(paste_problems(text)), 1)

    def test_paths_and_shell_commands_are_not_slash_commands(self):
        text = ("```sh\n/path/to/agents-library/install.py --project\n"
                "/usr/bin/env python3\nclaude plugin install p\n```\n")
        self.assertEqual(paste_problems(text), [])

    def test_commands_in_separate_blocks_are_not_counted_together(self):
        text = "```\n/plugin a\n```\n\nprose /plugin b\n\n```\n/plugin c\n```\n"
        self.assertEqual(paste_problems(text), [])


if __name__ == "__main__":
    unittest.main()
