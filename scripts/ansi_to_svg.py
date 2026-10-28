#!/usr/bin/env python3
"""Render a `tmux capture-pane -e` dump as an SVG terminal screenshot.

Only the SGR sequences Claude Code emits are understood: truecolour and 256-colour
foreground/background, bold, dim, italic, inverse and their resets. The default
foreground and background are the flavour's Text and Base, which is what a
terminal set up as the README recommends would show.

Usage:  python3 scripts/ansi_to_svg.py FLAVOUR CAPTURE.ansi OUT.svg
"""

from __future__ import annotations

import html
import json
import pathlib
import re
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
PALETTE = json.loads((HERE / "palette.json").read_text())

FONT_SIZE = 14
CELL_W = FONT_SIZE * 0.6
CELL_H = FONT_SIZE * 1.4
PAD = 20
TITLE_H = 34
SGR = re.compile(r"\x1b\[([0-9;:]*)m")
# Any escape that is not SGR: cursor movement, OSC titles and hyperlinks (BEL or
# ST terminated), charset selection.
OTHER_ESCAPE = re.compile(r"\x1b\[[0-9;:?]*[A-Za-ln-z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"
                          r"|\x1b[()][A-Z0-9]")


def xterm256(n):
    if n < 16:
        table = [(0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0),
                 (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
                 (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0),
                 (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255)]
        return "#%02x%02x%02x" % table[n]
    if n < 232:
        n -= 16
        steps = [0, 95, 135, 175, 215, 255]
        return "#%02x%02x%02x" % (steps[n // 36], steps[n // 6 % 6], steps[n % 6])
    level = 8 + (n - 232) * 10
    return "#%02x%02x%02x" % (level, level, level)


def apply_sgr(params, state):
    codes = [int(p) if p else 0 for p in re.split(r"[;:]", params)] or [0]
    i = 0
    while i < len(codes):
        c = codes[i]
        if c == 0:
            state.clear()
        elif c == 1:
            state["bold"] = True
        elif c == 2:
            state["dim"] = True
        elif c == 3:
            state["italic"] = True
        elif c == 7:
            state["inverse"] = True
        elif c == 22:
            state.pop("bold", None)
            state.pop("dim", None)
        elif c == 23:
            state.pop("italic", None)
        elif c == 27:
            state.pop("inverse", None)
        elif c in (38, 48):
            key = "fg" if c == 38 else "bg"
            if i + 1 < len(codes) and codes[i + 1] == 2 and i + 4 < len(codes):
                state[key] = "#%02x%02x%02x" % tuple(codes[i + 2:i + 5])
                i += 4
            elif i + 1 < len(codes) and codes[i + 1] == 5 and i + 2 < len(codes):
                state[key] = xterm256(codes[i + 2])
                i += 2
        elif c == 39:
            state.pop("fg", None)
        elif c == 49:
            state.pop("bg", None)
        elif 30 <= c <= 37 or 90 <= c <= 97:
            state["fg"] = xterm256(c - 30 if c < 90 else c - 90 + 8)
        elif 40 <= c <= 47 or 100 <= c <= 107:
            state["bg"] = xterm256(c - 40 if c < 100 else c - 100 + 8)
        i += 1


def parse(text):
    """Return rows of (char, style) cells."""
    # tmux only emits SGR on change, so attributes carry across line breaks.
    rows, state = [], {}
    for line in text.split("\n"):
        line = OTHER_ESCAPE.sub("", line)
        cells, pos = [], 0
        for m in SGR.finditer(line):
            for ch in line[pos:m.start()]:
                cells.append((ch, dict(state)))
                if unicodedata.east_asian_width(ch) in "WF":
                    cells.append(("", dict(state)))
            apply_sgr(m.group(1), state)
            pos = m.end()
        for ch in line[pos:]:
            cells.append((ch, dict(state)))
            if unicodedata.east_asian_width(ch) in "WF":
                cells.append(("", dict(state)))
        rows.append(cells)
    while rows and not "".join(c for c, _ in rows[-1]).strip():
        rows.pop()
    return rows


def render(flavour, rows, title):
    colours = PALETTE[flavour]["colors"]
    base, text, mantle = colours["base"], colours["text"], colours["mantle"]
    cols = max((len(r) for r in rows), default=80)
    width = round(cols * CELL_W + PAD * 2)
    height = round(len(rows) * CELL_H + PAD * 2 + TITLE_H)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" rx="10" fill="{base}"/>',
        f'<path d="M0 10a10 10 0 0 1 10-10h{width - 20}a10 10 0 0 1 10 10v{TITLE_H - 10}'
        f'h-{width}z" fill="{mantle}"/>',
    ]
    for i, name in enumerate(("red", "yellow", "green")):
        out.append(f'<circle cx="{20 + i * 20}" cy="{TITLE_H / 2}" r="6" '
                   f'fill="{colours[name]}"/>')
    out.append(f'<text x="{width / 2}" y="{TITLE_H / 2 + 5}" text-anchor="middle" '
               f'font-family="ui-sans-serif, system-ui, sans-serif" font-size="13" '
               f'fill="{colours["subtext0"]}">{html.escape(title)}</text>')
    out.append(f'<g font-family="ui-monospace, \'JetBrains Mono\', \'SF Mono\', Menlo, '
               f'Consolas, \'DejaVu Sans Mono\', monospace" font-size="{FONT_SIZE}" '
               f'xml:space="preserve">')

    top = PAD + TITLE_H
    for y, row in enumerate(rows):
        ty = top + y * CELL_H
        # Background runs first, so text paints over them.
        x = 0
        while x < len(row):
            fg, bg = resolve(row[x][1], text, base)
            end = x
            while end < len(row) and resolve(row[end][1], text, base)[1] == bg:
                end += 1
            if bg != base:
                out.append(f'<rect x="{PAD + x * CELL_W:.1f}" y="{ty:.1f}" '
                           f'width="{(end - x) * CELL_W:.1f}" height="{CELL_H:.1f}" '
                           f'fill="{bg}"/>')
            x = end
        # Text runs, each pinned to its column so glyph widths cannot drift.
        x = 0
        while x < len(row):
            style = row[x][1]
            end = x
            while end < len(row) and row[end][1] == style:
                end += 1
            chunk = "".join(c for c, _ in row[x:end])
            if chunk.strip():
                # Trim the run's edge spaces so textLength only stretches glyphs.
                start = x + len(chunk) - len(chunk.lstrip())
                chunk = chunk.strip()
                fg, _ = resolve(style, text, base)
                attrs = [f'x="{PAD + start * CELL_W:.1f}"', f'y="{ty + CELL_H * 0.72:.1f}"',
                         f'fill="{fg}"']
                if style.get("bold"):
                    attrs.append('font-weight="bold"')
                if style.get("italic"):
                    attrs.append('font-style="italic"')
                if style.get("dim"):
                    attrs.append('fill-opacity="0.6"')
                if len(chunk) > 1:
                    attrs.append(f'textLength="{len(chunk) * CELL_W:.1f}" '
                                 f'lengthAdjust="spacingAndGlyphs"')
                out.append(f'<text {" ".join(attrs)}>{html.escape(chunk)}</text>')
            x = end
    out.append("</g></svg>")
    return "\n".join(out) + "\n"


def resolve(style, text, base):
    fg, bg = style.get("fg", text), style.get("bg", base)
    if style.get("inverse"):
        fg, bg = bg, fg
    return fg, bg


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    flavour, capture, out = sys.argv[1:]
    rows = parse(pathlib.Path(capture).read_text())
    title = f"Claude Code · Catppuccin {PALETTE[flavour]['name']}"
    pathlib.Path(out).write_text(render(flavour, rows, title))


if __name__ == "__main__":
    sys.exit(main())
