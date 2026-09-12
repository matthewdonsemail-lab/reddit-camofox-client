"""Pre-push secret guard: block any push that would export credentials.

Checks:
  1. Secret-bearing paths are not tracked (state/cookies.json, .env.local, state/*).
  2. .gitignore covers state/cookies.json and .env.local.
  3. No tracked file contains secret material (Reddit JWT header,
     GitHub tokens, inline cookie jars).

Run manually:  python scripts/secret_scan.py
The .git/hooks/pre-push hook calls this; a non-zero exit blocks the push.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SECRET_PATHS = ["state/cookies.json", ".env.local", "state/storage_state.json"]
IGNORE_MUST_COVER = ["state/cookies.json", ".env.local"]

CONTENT_PATTERNS = {
    # Built via concatenation so this file never contains the contiguous
    # secret prefix it scans for (otherwise the scanner flags itself).
    "reddit JWT (token_v2/reddit_session value?)": re.compile("eyJhbGciOi" + "JSUzI1Ni"),
    "github token (gho_/ghp_)": re.compile(r"gh[op]_[A-Za-z0-9_]+"),
    "inline cookie jar with live JWT in env config": re.compile(r"REDDIT_COOKIES_JSON[^#\n]*eyJhbGci"),
}


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def check_untracked_secret_paths() -> list[str]:
    tracked = set(_git("ls-files").split())
    return [p for p in SECRET_PATHS if p in tracked]


def check_gitignore() -> list[str]:
    missing = []
    for path in IGNORE_MUST_COVER:
        proc = subprocess.run(["git", "check-ignore", path], cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            missing.append(path)
    return missing


def check_tracked_content() -> list[str]:
    violations: list[str] = []
    tracked = [line for line in _git("ls-files").split() if line]
    for rel in tracked:
        full = ROOT / rel
        if not full.is_file():
            continue
        try:
            text = full.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in CONTENT_PATTERNS.items():
            if pattern.search(text):
                violations.append(f"{rel}: {label}")
    return violations


def main() -> int:
    failures: list[str] = []
    for p in check_untracked_secret_paths():
        failures.append(f"secret path is TRACKED by git: {p} (git rm --cached {p})")
    for p in check_gitignore():
        failures.append(f".gitignore does not cover: {p}")
    failures.extend(check_tracked_content())
    if failures:
        print("SECRET SCAN FAILED - push blocked:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("secret scan OK: no secret paths tracked, no secret material in tracked files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
