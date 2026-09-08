#!/usr/bin/env bash
#
# Remove Catppuccin themes for Claude Code.
#
# Only removes the four files this project installs. If the active theme is one
# of them, the setting is reverted to the built-in dark theme so Claude Code
# does not start up pointing at a theme that no longer exists.

set -euo pipefail

ALL_FLAVOURS=(latte frappe macchiato mocha)
CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
THEMES_DIR="$CONFIG_DIR/themes"
SETTINGS="$CONFIG_DIR/settings.json"
FALLBACK="dark"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
info() { printf '%s\n' "$*"; }

usage() {
  cat <<'USAGE'
Remove Catppuccin themes for Claude Code.

Usage: uninstall.sh [options]

Options:
  -d, --dir PATH        look in PATH instead of ~/.claude/themes
  -k, --keep-setting    do not touch the active theme in settings.json
  -b, --fallback NAME   built-in theme to fall back to (default: dark)
  -h, --help            show this help
USAGE
}

keep_setting=0
while [ $# -gt 0 ]; do
  case "$1" in
    -d|--dir) [ $# -ge 2 ] || die "$1 needs a path"; THEMES_DIR=$2; shift 2 ;;
    --dir=*) THEMES_DIR=${1#*=}; shift ;;
    -k|--keep-setting) keep_setting=1; shift ;;
    -b|--fallback) [ $# -ge 2 ] || die "$1 needs a theme name"; FALLBACK=$2; shift 2 ;;
    --fallback=*) FALLBACK=${1#*=}; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option '$1' (try --help)" ;;
  esac
done

removed=0
for flavour in "${ALL_FLAVOURS[@]}"; do
  file="$THEMES_DIR/catppuccin-$flavour.json"
  if [ -f "$file" ]; then
    rm -f "$file"
    info "removed  $file"
    removed=$((removed + 1))
  fi
done

[ "$removed" -eq 0 ] && info "nothing to remove in $THEMES_DIR"

if [ "$keep_setting" = 0 ] && [ -f "$SETTINGS" ]; then
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$SETTINGS" "$FALLBACK" <<'PY'
import json, os, sys
path, fallback = sys.argv[1], sys.argv[2]
try:
    with open(path) as fh:
        settings = json.load(fh)
except (OSError, ValueError):
    raise SystemExit(0)
if not isinstance(settings, dict):
    raise SystemExit(0)
theme = settings.get("theme", "")
ours = {f"custom:catppuccin-{f}" for f in
        ("latte", "frappe", "macchiato", "mocha")}
if theme in ours:
    settings["theme"] = fallback
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(settings, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)
    print(f"reverted active theme to '{fallback}'")
PY
  else
    info "note: could not check the active theme (need python3)."
    info "      if it was a Catppuccin theme, change it with /theme."
  fi
fi

info ""
info "Done."
