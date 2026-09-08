#!/usr/bin/env python3
"""Generate Catppuccin themes for Claude Code from the official palette.

Every value in the output is either an exact Catppuccin palette entry or a
deterministic function of one. Nothing is hand-picked.

Two derivation rules cover the roles Catppuccin's 26-colour spec does not
define:

  shimmer     accent blended 45% toward the flavour's lightest anchor
  background  accent's exact hue and saturation, lightness retargeted and
              then solved against a WCAG contrast floor

Alpha-blending an accent over `base` (the usual port technique) is deliberately
not used for backgrounds: Catppuccin's accents are pastel and its bases are
tinted, so blending collapses the hue -- red diffs come out purple.

Usage:  python3 scripts/generate.py [--check]
"""

from __future__ import annotations

import argparse
import colorsys
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
PALETTE = json.loads((HERE / "palette.json").read_text())

# The complete set of colour tokens Claude Code accepts in a custom theme.
# Keys outside this set are silently discarded by the application.
KEYS = [
    "autoAccept", "autoAcceptShimmer", "skill", "bashBorder", "claude",
    "claudeShimmer", "claudeBlue_FOR_SYSTEM_SPINNER",
    "claudeBlueShimmer_FOR_SYSTEM_SPINNER", "permission", "permissionShimmer",
    "planMode", "ide", "promptBorder", "promptBorderShimmer", "text",
    "inverseText", "inactive", "inactiveShimmer", "subtle", "suggestion",
    "remember", "background", "success", "error", "warning", "merged",
    "warningShimmer", "diffAdded", "diffRemoved", "diffAddedDimmed",
    "diffRemovedDimmed", "diffAddedWord", "diffRemovedWord",
    "red_FOR_SUBAGENTS_ONLY", "blue_FOR_SUBAGENTS_ONLY",
    "green_FOR_SUBAGENTS_ONLY", "yellow_FOR_SUBAGENTS_ONLY",
    "purple_FOR_SUBAGENTS_ONLY", "orange_FOR_SUBAGENTS_ONLY",
    "pink_FOR_SUBAGENTS_ONLY", "cyan_FOR_SUBAGENTS_ONLY", "professionalBlue",
    "chromeYellow", "clawd_body", "clawd_background", "userMessageBackground",
    "userMessageBackgroundHover", "composerSidebarBackground", "selectionBg",
    "bashMessageBackgroundColor", "memoryBackgroundColor", "rate_limit_fill",
    "rate_limit_empty", "fastMode", "fastModeShimmer", "effortUltra",
    "briefLabelYou", "briefLabelClaude", "rainbow_red", "rainbow_orange",
    "rainbow_yellow", "rainbow_green", "rainbow_blue", "rainbow_indigo",
    "rainbow_violet", "rainbow_red_shimmer", "rainbow_orange_shimmer",
    "rainbow_yellow_shimmer", "rainbow_green_shimmer", "rainbow_blue_shimmer",
    "rainbow_indigo_shimmer", "rainbow_violet_shimmer",
]

# Which palette colour plays each semantic role. Flavour-independent: the
# palette guarantees the same 26 names carry the same meaning in every flavour.
ROLES = {
    "text": "text", "inverseText": "base", "background": "base",
    "subtle": "surface2", "inactive": "subtext0", "inactiveShimmer": "subtext1",
    "promptBorder": "overlay1", "promptBorderShimmer": "overlay2",

    "claude": "peach", "claudeBlue_FOR_SYSTEM_SPINNER": "blue",
    "autoAccept": "mauve", "skill": "mauve", "bashBorder": "pink",
    "permission": "lavender", "planMode": "teal", "ide": "sapphire",
    "suggestion": "lavender", "remember": "lavender", "merged": "mauve",
    "effortUltra": "mauve", "fastMode": "peach",

    "success": "green", "error": "red", "warning": "yellow",

    "userMessageBackground": "surface0",
    "userMessageBackgroundHover": "surface1",
    "composerSidebarBackground": "mantle", "selectionBg": "surface1",
    "rate_limit_fill": "mauve", "rate_limit_empty": "surface1",

    "briefLabelYou": "blue", "briefLabelClaude": "peach",
    "clawd_body": "peach", "clawd_background": "base",
    "professionalBlue": "blue", "chromeYellow": "yellow",

    "red_FOR_SUBAGENTS_ONLY": "red", "blue_FOR_SUBAGENTS_ONLY": "blue",
    "green_FOR_SUBAGENTS_ONLY": "green", "yellow_FOR_SUBAGENTS_ONLY": "yellow",
    "purple_FOR_SUBAGENTS_ONLY": "mauve", "orange_FOR_SUBAGENTS_ONLY": "peach",
    "pink_FOR_SUBAGENTS_ONLY": "pink", "cyan_FOR_SUBAGENTS_ONLY": "teal",

    "rainbow_red": "red", "rainbow_orange": "peach", "rainbow_yellow": "yellow",
    "rainbow_green": "green", "rainbow_blue": "blue", "rainbow_indigo": "mauve",
    "rainbow_violet": "pink",
}

# Shimmer tokens and the accent each brightens.
SHIMMERS = {
    "claudeShimmer": "peach",
    "claudeBlueShimmer_FOR_SYSTEM_SPINNER": "blue",
    "autoAcceptShimmer": "mauve",
    "permissionShimmer": "lavender",
    "warningShimmer": "yellow",
    "fastModeShimmer": "peach",
    "rainbow_red_shimmer": "red", "rainbow_orange_shimmer": "peach",
    "rainbow_yellow_shimmer": "yellow", "rainbow_green_shimmer": "green",
    "rainbow_blue_shimmer": "blue", "rainbow_indigo_shimmer": "mauve",
    "rainbow_violet_shimmer": "pink",
}

# Derived backgrounds.
#
# `lum` is a target relative luminance, not an HSL lightness. Catppuccin's green
# and red sit at very different luminances for the same lightness, so matching
# lightness makes an added band and a removed band look unequally prominent;
# matching luminance makes the pair read as siblings.
#
# `against` names what the band must stay distinguishable from: a band from the
# editor base, a word-level highlight from the band it is painted inside.
# Entries resolve in order, so a token may reference one defined above it.
#
# Floors differ by flavour. On a dark flavour a band can move away from the base
# and toward the body text at the same time, so both floors are cheap. On a
# light flavour they oppose each other -- Latte's body text is a muted
# #4c4f69, which caps how much contrast any light background can offer -- so the
# word highlights there trade text contrast for a visible distinction from
# their band, which is the same trade Claude Code's own light theme makes.
BACKGROUNDS = {
    "diffAdded": dict(accent="green", lum_dark=0.055, lum_light=0.45, sat=0.60,
                      text_dark=4.5, text_light=4.5, sep=1.45, against="base"),
    "diffRemoved": dict(accent="red", lum_dark=0.055, lum_light=0.45, sat=0.60,
                        text_dark=4.5, text_light=4.5, sep=1.45, against="base"),
    "diffAddedDimmed": dict(accent="green", lum_dark=0.032, lum_light=0.63, sat=0.35,
                            text_dark=4.5, text_light=4.5, sep=1.15, against="base"),
    "diffRemovedDimmed": dict(accent="red", lum_dark=0.032, lum_light=0.63, sat=0.35,
                              text_dark=4.5, text_light=4.5, sep=1.15, against="base"),
    "diffAddedWord": dict(accent="green", lum_dark=0.130, lum_light=0.40, sat=0.65,
                          text_dark=4.5, text_light=3.4, sep=1.25, against="diffAdded"),
    "diffRemovedWord": dict(accent="red", lum_dark=0.130, lum_light=0.40, sat=0.65,
                            text_dark=4.5, text_light=3.4, sep=1.25, against="diffRemoved"),
    "bashMessageBackgroundColor": dict(accent="pink", lum_dark=0.035, lum_light=0.68,
                                       sat=0.55, text_dark=4.5, text_light=4.5,
                                       sep=1.10, against="base"),
    "memoryBackgroundColor": dict(accent="blue", lum_dark=0.035, lum_light=0.68,
                                  sat=0.55, text_dark=4.5, text_light=4.5,
                                  sep=1.10, against="base"),
}

FLAVOURS = ["latte", "frappe", "macchiato", "mocha"]


def to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(t):
    return "#%02x%02x%02x" % t


def relative_luminance(h):
    out = []
    for c in (c / 255 for c in to_rgb(h)):
        out.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def contrast(a, b):
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def blend(fg, bg, alpha):
    f, b = to_rgb(fg), to_rgb(bg)
    return to_hex(tuple(round(f[i] * alpha + b[i] * (1 - alpha)) for i in range(3)))


def retone(hex_colour, lightness, sat_scale=1.0):
    """Keep a colour's hue and saturation, move only its lightness."""
    r, g, b = (c / 255 for c in to_rgb(hex_colour))
    h, _, s = colorsys.rgb_to_hls(r, g, b)
    rgb = colorsys.hls_to_rgb(h, max(0.0, min(1.0, lightness)),
                              max(0.0, min(1.0, s * sat_scale)))
    return to_hex(tuple(round(c * 255) for c in rgb))


def solve_background(accent, target_lum, sat_scale, text_floor, sep_floor,
                     body_text, reference, base_colour, away_from=None):
    """Pick the colour closest to `target_lum` that stays readable (vs body
    text) and visible (vs `reference`).

    Scans the whole lightness range rather than walking one direction: the two
    floors are opposed -- lightening a band to gain text contrast on a light
    flavour washes it into the base -- so the feasible window is bounded on both
    sides and a directional walk can step straight past it.

    `away_from` pins a band the result must sit beyond, so a word-level
    highlight always reads as more prominent than its band rather than sinking
    back toward the base.

    If nothing satisfies every floor they relax in fixed steps, separation
    yielding before readability, and the relaxation is reported rather than
    hidden."""
    steps = [i / 400 for i in range(401)]
    bound = relative_luminance(away_from) if away_from else None
    # Direction is measured from the editor base, never from `reference` --
    # for a word highlight those are the same colour and the test would be inert.
    base_lum = relative_luminance(base_colour)
    relaxations = [
        (text_floor, sep_floor),
        (text_floor, sep_floor * 0.85),
        (text_floor, sep_floor * 0.70),
        (text_floor, sep_floor * 0.55),
        (text_floor - 0.5, sep_floor * 0.55),
        (3.0, 1.05),
    ]
    for tf, sf in relaxations:
        feasible = []
        for lightness in steps:
            candidate = retone(accent, lightness, sat_scale)
            lum = relative_luminance(candidate)
            if bound is not None:
                # Must lie further from the base than the band it highlights.
                if base_lum < bound and lum <= bound:
                    continue
                if base_lum > bound and lum >= bound:
                    continue
            if (contrast(candidate, body_text) >= tf
                    and contrast(candidate, reference) >= sf):
                feasible.append((abs(lum - target_lum), candidate))
        if feasible:
            _, best = min(feasible, key=lambda x: x[0])
            return best, (tf, sf)
    return retone(accent, 0.5, sat_scale), None


def build(flavour):
    meta = PALETTE[flavour]
    colours = meta["colors"]
    is_dark = meta["dark"]
    body_text = colours["text"]

    # Lightest palette entry, used as the anchor every shimmer brightens toward.
    anchor = max((colours["rosewater"], colours["base"]), key=relative_luminance)

    theme = {}
    for token, role in ROLES.items():
        theme[token] = colours[role]
    for token, accent in SHIMMERS.items():
        theme[token] = blend(anchor, colours[accent], 0.45)
    relaxed = {}
    for token, spec in BACKGROUNDS.items():
        against = spec["against"]
        reference = colours["base"] if against == "base" else theme[against]
        text_floor = spec["text_dark"] if is_dark else spec["text_light"]
        colour, used = solve_background(
            accent=colours[spec["accent"]],
            target_lum=spec["lum_dark"] if is_dark else spec["lum_light"],
            sat_scale=spec["sat"],
            text_floor=text_floor,
            sep_floor=spec["sep"],
            body_text=body_text,
            reference=reference,
            base_colour=colours["base"],
            away_from=None if against == "base" else theme[against])
        theme[token] = colour
        if used is None or used != (text_floor, spec["sep"]):
            relaxed[token] = used

    missing = [k for k in KEYS if k not in theme]
    extra = [k for k in theme if k not in KEYS]
    if missing or extra:
        raise SystemExit(f"{flavour}: missing={missing} unexpected={extra}")

    return {
        "name": f"Catppuccin {meta['name']}",
        "base": "dark" if is_dark else "light",
        "overrides": {k: theme[k] for k in KEYS},
    }, relaxed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed themes differ from a fresh build")
    args = ap.parse_args()

    out_dir = ROOT / "themes"
    out_dir.mkdir(exist_ok=True)
    stale = []

    for flavour in FLAVOURS:
        theme, relaxed = build(flavour)
        path = out_dir / f"catppuccin-{flavour}.json"
        rendered = json.dumps(theme, indent=2) + "\n"
        if args.check:
            if not path.exists() or path.read_text() != rendered:
                stale.append(path.name)
        else:
            path.write_text(rendered)
        o = theme["overrides"]
        worst_text = min(contrast(o["text"], o[k]) for k in BACKGROUNDS)
        worst_base = min(
            contrast(o["background"] if spec["against"] == "base"
                     else o[spec["against"]], o[k])
            for k, spec in BACKGROUNDS.items())
        print(f"{theme['name']:22} base={theme['base']:5} tokens={len(o)} "
              f"text>={worst_text:.2f}:1  sep>={worst_base:.2f}:1"
              + (f"  relaxed={sorted(relaxed)}" if relaxed else ""))

    if stale:
        raise SystemExit(f"out of date, re-run generate.py: {', '.join(stale)}")
    print("\npalette:", PALETTE["version"], "(catppuccin/palette)")


if __name__ == "__main__":
    sys.exit(main())
