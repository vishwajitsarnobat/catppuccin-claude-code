#!/usr/bin/env bash
#
# Install Catppuccin themes for Claude Code.
#
#   ./install.sh                     install every flavour
#   ./install.sh -f mocha            install one flavour
#   ./install.sh -f mocha -a         install it and make it active
#   ./install.sh -a mocha            install every flavour, activate Mocha
#
# Also works without a clone:
#   curl -fsSL https://raw.githubusercontent.com/vishwajitsarnobat/catppuccin-claude-code/main/install.sh | bash -s -- -a mocha

set -euo pipefail

RAW_BASE="https://raw.githubusercontent.com/vishwajitsarnobat/catppuccin-claude-code/main"
ALL_FLAVOURS=(latte frappe macchiato mocha)
CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
THEMES_DIR="$CONFIG_DIR/themes"
SETTINGS="$CONFIG_DIR/settings.json"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"

selected=()
activate=""
activate_requested=0

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
info() { printf '%s\n' "$*"; }

usage() {
  cat <<'USAGE'
Install Catppuccin themes for Claude Code.

Usage: install.sh [options]

Options:
  -f, --flavour NAME   install only this flavour (repeatable)
                       one of: latte, frappe, macchiato, mocha
  -a, --activate[=NAME] set the installed theme as active in settings.json;
                       NAME is optional when exactly one flavour is installed
  -d, --dir PATH       install into PATH instead of ~/.claude/themes
  -l, --list           list available flavours and exit
  -h, --help           show this help

Environment:
  CLAUDE_CONFIG_DIR    Claude Code config directory (default: ~/.claude)
USAGE
}

is_flavour() {
  local candidate=$1 flavour
  for flavour in "${ALL_FLAVOURS[@]}"; do
    [ "$flavour" = "$candidate" ] && return 0
  done
  return 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    -f|--flavour|--flavor)
      [ $# -ge 2 ] || die "$1 needs a flavour name"
      is_flavour "$2" || die "unknown flavour '$2' (want: ${ALL_FLAVOURS[*]})"
      selected+=("$2"); shift 2 ;;
    --flavour=*|--flavor=*)
      value=${1#*=}
      is_flavour "$value" || die "unknown flavour '$value' (want: ${ALL_FLAVOURS[*]})"
      selected+=("$value"); shift ;;
    -a|--activate)
      activate_requested=1
      if [ $# -ge 2 ] && is_flavour "${2:-}"; then activate=$2; shift 2; else shift; fi ;;
    --activate=*)
      value=${1#*=}
      is_flavour "$value" || die "unknown flavour '$value' (want: ${ALL_FLAVOURS[*]})"
      activate_requested=1; activate=$value; shift ;;
    -d|--dir)
      [ $# -ge 2 ] || die "$1 needs a path"
      THEMES_DIR=$2; shift 2 ;;
    --dir=*) THEMES_DIR=${1#*=}; shift ;;
    -l|--list)
      printf '%s\n' "${ALL_FLAVOURS[@]}"; exit 0 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option '$1' (try --help)" ;;
  esac
done

[ ${#selected[@]} -gt 0 ] || selected=("${ALL_FLAVOURS[@]}")

if [ "$activate_requested" = 1 ] && [ -z "$activate" ]; then
  if [ ${#selected[@]} -eq 1 ]; then
    activate=${selected[0]}
  else
    die "--activate needs a flavour name when installing more than one"
  fi
fi

if [ -n "$activate" ]; then
  found=0
  for flavour in "${selected[@]}"; do
    [ "$flavour" = "$activate" ] && found=1
  done
  [ "$found" = 1 ] || die "cannot activate '$activate': it is not being installed"
fi

fetch() {
  # fetch <url> <destination>
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$1" -o "$2"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$2" "$1"
  else
    die "need curl or wget to download themes"
  fi
}

valid_json() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$1" 2>/dev/null
  elif command -v jq >/dev/null 2>&1; then
    jq -e . "$1" >/dev/null 2>&1
  else
    return 0
  fi
}

mkdir -p "$THEMES_DIR"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

installed=()
for flavour in "${selected[@]}"; do
  file="catppuccin-$flavour.json"
  staged="$tmp/$file"
  if [ -n "$SOURCE_DIR" ] && [ -f "$SOURCE_DIR/themes/$file" ]; then
    cp "$SOURCE_DIR/themes/$file" "$staged"
  else
    fetch "$RAW_BASE/themes/$file" "$staged" \
      || die "could not download $file"
  fi
  valid_json "$staged" || die "$file is not valid JSON -- refusing to install"
  install -m 0644 "$staged" "$THEMES_DIR/$file"
  installed+=("$flavour")
  info "installed  $THEMES_DIR/$file"
done

if [ -n "$activate" ]; then
  ref="custom:catppuccin-$activate"
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$SETTINGS" "$ref" <<'PY'
import json, os, sys
path, ref = sys.argv[1], sys.argv[2]
try:
    with open(path) as fh:
        settings = json.load(fh)
    if not isinstance(settings, dict):
        raise ValueError("settings.json is not a JSON object")
except FileNotFoundError:
    settings = {}
settings["theme"] = ref
os.makedirs(os.path.dirname(path), exist_ok=True)
tmp = path + ".tmp"
with open(tmp, "w") as fh:
    json.dump(settings, fh, indent=2)
    fh.write("\n")
os.replace(tmp, path)
PY
  elif command -v jq >/dev/null 2>&1; then
    mkdir -p "$(dirname "$SETTINGS")"
    [ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"
    jq --arg t "$ref" '.theme = $t' "$SETTINGS" > "$SETTINGS.tmp" \
      && mv "$SETTINGS.tmp" "$SETTINGS"
  else
    info ""
    info "could not edit $SETTINGS (need python3 or jq)."
    info "set it by hand:  \"theme\": \"$ref\""
    activate=""
  fi
  [ -n "$activate" ] && info "activated  $ref"
fi

info ""
info "Done. ${#installed[@]} theme(s) in $THEMES_DIR"
if [ -z "$activate" ]; then
  info "Pick one with /theme inside Claude Code."
fi
info "Claude Code watches the themes directory, so a running session picks this up"
info "without a restart. For the intended contrast, set your terminal background to"
info "the flavour's base colour (Mocha #1e1e2e, Macchiato #24273a, Frappe #303446,"
info "Latte #eff1f5)."
