#!/usr/bin/env bash
# Install Claude Code (the Anthropic CLI) on Ubuntu.
#
# What it does:
#   1. Ensures Node.js >= 18 is present, installing it via NodeSource if not.
#   2. Installs the @anthropic-ai/claude-code npm package globally.
#   3. Prints the installed version so you can confirm it worked.
#
# Usage:
#   ./scripts/install_claude_code_ubuntu.sh
#
# Environment variables:
#   NODE_MAJOR   Node.js major version to install if Node is missing/too old
#                (default: 20).

set -euo pipefail

NODE_MAJOR="${NODE_MAJOR:-20}"
MIN_NODE_MAJOR=18

log() { echo "[install_claude_code] $*" >&2; }

if ! grep -qi ubuntu /etc/os-release 2>/dev/null; then
  log "warning: this doesn't look like Ubuntu (/etc/os-release didn't match) -- continuing anyway"
fi

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "[install_claude_code] error: need root or sudo to install packages" >&2
    exit 1
  fi
fi

node_major_version() {
  node --version 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/'
}

if command -v node >/dev/null 2>&1 && [ "$(node_major_version)" -ge "$MIN_NODE_MAJOR" ] 2>/dev/null; then
  log "found node $(node --version), skipping Node.js install"
else
  log "installing Node.js ${NODE_MAJOR}.x from NodeSource..."
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | $SUDO -E bash -
  $SUDO apt-get install -y nodejs
fi

log "node: $(node --version), npm: $(npm --version)"

log "installing @anthropic-ai/claude-code globally via npm..."
$SUDO npm install -g @anthropic-ai/claude-code

if command -v claude >/dev/null 2>&1; then
  log "done. installed: $(claude --version)"
  log "run 'claude' to get started."
else
  echo "[install_claude_code] error: 'claude' command not found on PATH after install" >&2
  exit 1
fi
