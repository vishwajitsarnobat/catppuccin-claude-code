#!/usr/bin/env bash
#
# Regenerate assets/<flavour>.svg from a real Claude Code session.
#
#   ./scripts/screenshots.sh              all four flavours
#   ./scripts/screenshots.sh mocha latte  just these
#
# Each flavour runs Claude Code in a private, detached tmux server against a
# throwaway project, asks it for a small edit, and captures the permission
# prompt with its diff. The theme is chosen with a one-off --settings flag, so
# your settings.json is never changed. The theme files themselves must exist in
# the themes directory, so they are installed there (not activated) first.
#
# Needs: claude (logged in), tmux, python3. Each run is one short request.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOCKET="catppuccin-shots"
COLS=100
ROWS=36
PROMPT='In greet.py, switch the string concatenation to an f-string and add a one-line docstring. Edit the file directly; do not run anything.'

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

for tool in claude tmux python3; do
  command -v "$tool" >/dev/null 2>&1 || die "need $tool"
done

flavours=("$@")
[ ${#flavours[@]} -gt 0 ] || flavours=(latte frappe macchiato mocha)

work=$(mktemp -d)
trap 'tmux -L "$SOCKET" kill-server 2>/dev/null || true; rm -rf "$work"' EXIT

"$ROOT/install.sh" >/dev/null

project="$work/greet"
mkdir -p "$project"
cat > "$project/greet.py" <<'EOF'
def greet(name):
    message = "Hello, " + name + "!"
    print(message)
    return message


if __name__ == "__main__":
    greet("world")
EOF

screen() { tmux -L "$SOCKET" capture-pane -p -t shot "$@"; }

# wait_for <regex> <seconds>
wait_for() {
  local i
  for ((i = 0; i < $2 * 2; i++)); do
    screen | grep -qE "$1" && return 0
    sleep 0.5
  done
  return 1
}

mkdir -p "$ROOT/assets"
for flavour in "${flavours[@]}"; do
  [ -f "$ROOT/themes/catppuccin-$flavour.json" ] || die "unknown flavour '$flavour'"
  printf '%-10s ' "$flavour"
  tmux -L "$SOCKET" kill-server 2>/dev/null || true

  # Claude Code drops to 256 colours when it sees tmux, which would misreport
  # every colour, so the tmux variables are hidden and truecolour is forced.
  # The parent session's variables are cleared so this runs as its own session.
  tmux -L "$SOCKET" -f /dev/null new-session -d -s shot -x "$COLS" -y "$ROWS" \
    -c "$project" -- env -u TMUX -u TMUX_PANE -u CLAUDECODE \
    -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_SESSION_ID \
    -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_MESSAGING_SOCKET \
    -u CLAUDE_CODE_MESSAGING_TOKEN -u CLAUDE_CODE_EXECPATH \
    -u CLAUDE_CODE_SESSION_ATTENDED -u CLAUDE_PID -u CLAUDE_EFFORT \
    TERM=xterm-256color COLORTERM=truecolor FORCE_COLOR=3 \
    claude --permission-mode default \
    --settings "{\"theme\":\"custom:catppuccin-$flavour\"}" "$PROMPT"

  wait_for 'trust this folder|Do you want' 60 || { screen >&2; die "$flavour: Claude Code did not start"; }
  if screen | grep -q 'trust this folder'; then
    sleep 1
    tmux -L "$SOCKET" send-keys -t shot Down Enter
  fi
  wait_for 'Do you want to make this edit' 180 || { screen >&2; die "$flavour: no edit prompt appeared"; }
  sleep 1

  # Drop the banner (version, plan, path) and keep from the prompt down.
  screen -e -N | python3 -c '
import sys
lines = sys.stdin.read().split("\n")
start = next((i for i, l in enumerate(lines) if "❯ " in l), 0)
sys.stdout.write("\n".join(lines[start:]))
' > "$work/$flavour.ansi"
  tmux -L "$SOCKET" kill-server

  python3 "$ROOT/scripts/ansi_to_svg.py" "$flavour" "$work/$flavour.ansi" \
    "$ROOT/assets/$flavour.svg"
  echo "assets/$flavour.svg"
done
