#!/usr/bin/env python3
"""Fail when a tracked Python file imports a name it never uses.

The gate runs no Python linter, and adding one would be the repository's
first dependency, so this stdlib check covers the one rule that has slipped
through: an import nothing reads. A name counts as used when it appears as an
identifier anywhere in the file, so `import a.b` is used by `a.b.c`.
"""

import ast
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def unused_imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported[(alias.asname or alias.name).split(".")[0]] = node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            for alias in node.names:
                imported[alias.asname or alias.name] = node.lineno
    used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    return sorted((line, name) for name, line in imported.items() if name not in used)


def main() -> int:
    files = subprocess.run(["git", "ls-files", "*.py"], cwd=REPO, capture_output=True,
                           text=True, check=True).stdout.split()
    problems = [f"{name}:{line}: `{module}` is imported but never used"
                for name in files for line, module in unused_imports(REPO / name)]
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print(f"OK: no unused imports in {len(files)} Python files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
