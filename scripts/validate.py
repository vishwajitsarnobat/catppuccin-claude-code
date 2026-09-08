#!/usr/bin/env python3
"""Validate the committed theme files against what Claude Code accepts.

Checks each theme independently of the generator, so a hand edit that breaks a
theme is caught rather than silently discarded at runtime:

  * every token is one Claude Code recognises (unknown keys are dropped
    silently by the application, with no warning -- the failure mode this
    exists to catch)
  * all 72 tokens are present
  * every value matches the accepted colour syntax
  * `base` names a real built-in theme
  * diff bands stay readable and visibly distinct

Usage:  python3 scripts/validate.py
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from generate import KEYS, contrast, relative_luminance  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASES = {"dark", "light", "light-daltonized", "dark-daltonized",
         "light-ansi", "dark-ansi"}
COLOUR = re.compile(
    r"^(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}|rgb\(\s?\d{1,3},\s?\d{1,3},\s?\d{1,3}\s?\)"
    r"|ansi256\(\d{1,3}\)|ansi:[a-zA-Z]+)$")

TEXT_FLOOR = 3.4
SEP_FLOOR = 1.20
PAIRS = [("diffAdded", "diffAddedWord"), ("diffRemoved", "diffRemovedWord")]


def check(path):
    errors = []
    theme = json.loads(path.read_text())

    for field in ("name", "base", "overrides"):
        if field not in theme:
            errors.append(f"missing top-level field {field!r}")
    if errors:
        return errors

    if theme["base"] not in BASES:
        errors.append(f"base {theme['base']!r} is not a built-in theme")

    overrides = theme["overrides"]
    known = set(KEYS)
    for token in overrides:
        if token not in known:
            errors.append(f"{token}: not a Claude Code colour token "
                          f"(would be silently discarded)")
    for token in KEYS:
        if token not in overrides:
            errors.append(f"{token}: missing")
    for token, value in overrides.items():
        if not isinstance(value, str) or not COLOUR.match(value):
            errors.append(f"{token}: {value!r} is not an accepted colour")
    if errors:
        return errors

    text, base = overrides["text"], overrides["background"]
    dark = relative_luminance(base) < 0.5

    for band, word in PAIRS:
        for token in (band, word):
            ratio = contrast(overrides[token], text)
            if ratio < TEXT_FLOOR:
                errors.append(f"{token}: body text contrast {ratio:.2f}:1 "
                              f"below {TEXT_FLOOR}:1")
        ratio = contrast(overrides[word], overrides[band])
        if ratio < SEP_FLOOR:
            errors.append(f"{word}: only {ratio:.2f}:1 against {band}, "
                          f"below {SEP_FLOOR}:1")
        lb = relative_luminance(base)
        lband = relative_luminance(overrides[band])
        lword = relative_luminance(overrides[word])
        ordered = lword > lband > lb if dark else lword < lband < lb
        if not ordered:
            errors.append(
                f"{word}: luminance ladder wrong "
                f"(base {lb:.3f}, {band} {lband:.3f}, {word} {lword:.3f}) -- "
                f"a word highlight must sit further from the base than its band")
    return errors


def main():
    paths = sorted((ROOT / "themes").glob("*.json"))
    if not paths:
        raise SystemExit("no theme files found in themes/")

    failed = False
    for path in paths:
        errors = check(path)
        if errors:
            failed = True
            print(f"FAIL {path.name}")
            for error in errors:
                print(f"       {error}")
        else:
            theme = json.loads(path.read_text())
            print(f"ok   {path.name:32} {theme['name']:22} "
                  f"base={theme['base']:5} tokens={len(theme['overrides'])}")

    if failed:
        raise SystemExit(1)
    print(f"\n{len(paths)} themes valid")


if __name__ == "__main__":
    sys.exit(main())
