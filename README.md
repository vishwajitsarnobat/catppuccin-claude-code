# Catppuccin for Claude Code

Soothing pastel themes for the Claude Code terminal UI — all four Catppuccin
flavours, every colour token the application exposes, generated from the
official palette data (`catppuccin/palette` v1.8.0) rather than picked by eye.

## Flavours

| Flavour | Base | Slug | Background | Text | Accent | Auto-accept | Success | Error |
|---|---|---|---|---|---|---|---|---|
| Mocha | `dark` | `catppuccin-mocha` | `#1e1e2e` | `#cdd6f4` | `#fab387` | `#cba6f7` | `#a6e3a1` | `#f38ba8` |
| Macchiato | `dark` | `catppuccin-macchiato` | `#24273a` | `#cad3f5` | `#f5a97f` | `#c6a0f6` | `#a6da95` | `#ed8796` |
| Frappé | `dark` | `catppuccin-frappe` | `#303446` | `#c6d0f5` | `#ef9f76` | `#ca9ee6` | `#a6d189` | `#e78284` |
| Latte | `light` | `catppuccin-latte` | `#eff1f5` | `#4c4f69` | `#fe640b` | `#8839ef` | `#40a02b` | `#d20f39` |

## Install

One line, no clone:

```sh
curl -fsSL https://raw.githubusercontent.com/vishwajitsarnobat/catppuccin-claude-code/main/install.sh | bash -s -- -a mocha
```

Or from a clone:

```sh
git clone https://github.com/vishwajitsarnobat/catppuccin-claude-code.git
cd catppuccin-claude-code
./install.sh --activate mocha      # install all four, activate Mocha
./install.sh --flavour latte       # install just one
./install.sh --help
```

Or by hand — copy any file from `themes/` into `~/.claude/themes/` and pick it
with `/theme`.

The installer merges into `~/.claude/settings.json` rather than overwriting it,
and refuses to install a file that is not valid JSON. `CLAUDE_CONFIG_DIR` is
honoured if you keep your config somewhere other than `~/.claude`.

## Activating

Run `/theme` inside Claude Code and choose the flavour, or pass `--activate` to
the installer. Claude Code watches the themes directory, so a running session
picks up a new or edited theme without a restart.

**Set your terminal background to the flavour's base colour.** Claude Code
paints its own UI but not the terminal behind it, and the contrast figures below
assume the matching base:

| Flavour | Terminal background |
|---|---|
| Mocha | `#1e1e2e` |
| Macchiato | `#24273a` |
| Frappé | `#303446` |
| Latte | `#eff1f5` |

## What is covered

All **72 colour tokens** Claude Code accepts — diffs, permission and
plan-mode indicators, subagent labels, rate-limit meters, message backgrounds,
the spinner rainbow, and the rest.

This matters more than it sounds: Claude Code **silently discards** any override
key it does not recognise. No warning, no error — the colour just stays at its
built-in value. A theme that looks half-applied is usually a theme with typos.
`scripts/validate.py` exists to catch exactly that.

## How the colours are derived

Nothing here is hand-picked. Every value is either an exact palette entry or a
deterministic function of one, so all four flavours stay consistent and the
whole set regenerates when the upstream palette changes.

**51 tokens are exact palette entries.** Semantic roles map onto palette
names, and because the palette guarantees the same 26 names across flavours, one
mapping serves all four:

| Token | Palette colour |
|---|---|
| `text` | Text |
| `background` | Base |
| `claude` | Peach |
| `permission` | Lavender |
| `planMode` | Teal |
| `autoAccept` | Mauve |
| `bashBorder` | Pink |
| `success` | Green |
| `error` | Red |
| `warning` | Yellow |
| `ide` | Sapphire |
| `inactive` | Subtext0 |
| `promptBorder` | Overlay1 |
| `subtle` | Surface2 |
| `selectionBg` | Surface1 |
| `composerSidebarBackground` | Mantle |

…and so on; `scripts/generate.py` holds the full mapping.

**13 shimmer tokens** are the accent blended 45% toward the flavour's
lightest anchor. The anchor is chosen by luminance, which is what lets the same
rule work on Latte — there the base is lighter than Rosewater, so it wins and
shimmers brighten instead of darkening.

**8 background tokens** — diff bands, word highlights, message
backgrounds — have no palette equivalent, since Catppuccin's 26 colours are
foreground colours. These take the accent's exact hue and saturation and
retarget its luminance.

Notably *not* alpha-blending the accent over the base, which is the usual port
technique. Catppuccin's accents are pastel and its bases are tinted, so blending
collapses the hue: mixing Mocha's red `#f38ba8` over base `#1e1e2e` yields
`#4d3649`, which reads purple. A removed-line band that is not red is a bug.

Luminance is the target rather than lightness because green and red at equal
HSL lightness have very different perceived brightness — matching lightness
makes an added band and a removed band look unequally prominent. Matching
luminance makes them read as a pair.

Each background then has to satisfy two opposed constraints: text on it stays
readable, and the band itself stays visible against what surrounds it. A word
highlight is measured against the band it sits inside, not against the editor
base, and is pinned further from the base than that band so it always reads as
the more prominent of the two. Where both floors cannot hold — Latte's body text
is a muted `#4c4f69`, which caps how much contrast any light background can
offer — the generator reports the relaxation instead of hiding it.

## Measured contrast

Generated from the committed theme files:

| Flavour | Text on band | Text on word highlight | Band vs base | Word vs band |
|---|---|---|---|---|
| Mocha | 6.91:1 | 4.51:1 | 1.64:1 | 1.51:1 |
| Macchiato | 6.71:1 | 4.51:1 | 1.46:1 | 1.49:1 |
| Frappé | 5.53:1 | 4.53:1 | 1.46:1 | 1.22:1 |
| Latte | 4.51:1 | 3.42:1 | 1.56:1 | 1.32:1 |

The first two columns are WCAG contrast ratios for body text. The last two are
visibility margins, where 1.00:1 would mean indistinguishable.

Latte sits below 4.5:1 on word highlights by design. Its text colour caps the
achievable contrast, and the alternative — lightening the highlight until it
passes — makes it vanish into the band. Claude Code's own light theme makes the
same trade.

## Uninstall

```sh
./uninstall.sh                 # remove all four, revert active theme to `dark`
./uninstall.sh --keep-setting  # remove files, leave settings.json alone
```

Only the four files this project installs are touched.

## Development

```sh
python3 scripts/generate.py           # rebuild themes/ from the palette
python3 scripts/generate.py --check   # fail if committed themes are stale
python3 scripts/validate.py           # verify tokens, syntax, contrast, ladders
```

No dependencies beyond Python 3. `scripts/palette.json` is a trimmed copy of the
upstream palette, vendored so builds are reproducible and CI runs offline.

`validate.py` deliberately re-checks the output rather than trusting the
generator, so a hand edit to a theme file is caught too. CI runs both on every
push.

To retune, adjust the targets in `generate.py` — `ROLES` for semantic mapping,
`BACKGROUNDS` for luminance targets and contrast floors — and regenerate. Please
do not hand-edit files in `themes/`; they are build output and `--check` will
fail.

## Compatibility

Requires a Claude Code version with custom theme support: JSON files in
`~/.claude/themes/`, selected as `custom:<slug>`. Verified against 2.1.x.

## Credits

Palette by [Catppuccin](https://github.com/catppuccin/catppuccin), used under the
MIT licence.

## Licence

MIT — see [LICENSE](LICENSE).
