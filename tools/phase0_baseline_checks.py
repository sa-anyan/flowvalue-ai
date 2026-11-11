"""Read-only checks over Git-tracked source; never print suspected secret values.

This is a narrow guard, not a comprehensive credential/security audit.
Untracked user files are deliberately excluded. No imports of application modules.
"""

import ast
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = (
    re.compile(r"(?<![\w-])sk-(?:proj-)?[A-Za-z0-9_-]{40,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?<!\w)gh[pousr]_[A-Za-z0-9]{36,}"),
)


def check(root=ROOT):
    files = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
        .decode()
        .split("\0")
    )
    issues = []
    count = 0
    for name in filter(None, files):
        path = root / name
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix not in {
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".json",
            ".yml",
            ".yaml",
            ".md",
            ".txt",
            ".cjs",
            ".mjs",
        }:
            continue
        try:
            text = path.read_text()
        except UnicodeError:
            continue
        if path.suffix == ".py":
            count += 1
            try:
                ast.parse(text, filename=name)
            except SyntaxError as exc:
                issues.append(f"{name}:{exc.lineno}: Python syntax error")
        for line, value in enumerate(text.splitlines(), 1):
            if any(pattern.search(value) for pattern in PATTERNS):
                issues.append(f"{name}:{line}: possible credential; value suppressed")
    return count, issues


if __name__ == "__main__":
    count, issues = check()
    print(f"Parsed {count} tracked Python files; {len(issues)} findings")
    for issue in issues:
        print(issue)
    raise SystemExit(bool(issues))
