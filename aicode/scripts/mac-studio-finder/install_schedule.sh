#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LABEL="com.macstudio.finder"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3)}"
RUN_AT_HOUR="${RUN_AT_HOUR:-8}"
RUN_AT_MINUTE="${RUN_AT_MINUTE:-0}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "python3 not found. Set PYTHON_BIN to your interpreter." >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$HOME/.mac-studio-finder"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
      <string>${PYTHON_BIN}</string>
      <string>${PROJECT_DIR}/run_search.py</string>
      <string>--config</string>
      <string>${PROJECT_DIR}/config.yaml</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>StartCalendarInterval</key>
    <dict>
      <key>Hour</key>
      <integer>${RUN_AT_HOUR}</integer>
      <key>Minute</key>
      <integer>${RUN_AT_MINUTE}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${HOME}/.mac-studio-finder/launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>${HOME}/.mac-studio-finder/launchd.err.log</string>
    <key>RunAtLoad</key>
    <false/>
  </dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl enable "gui/$(id -u)/${LABEL}"
launchctl kickstart -k "gui/$(id -u)/${LABEL}" || true

echo "Installed daily schedule at ${RUN_AT_HOUR}:$(printf '%02d' "${RUN_AT_MINUTE}")"
echo "Plist: ${PLIST_PATH}"
echo "Logs:  ~/.mac-studio-finder/launchd.out.log"
