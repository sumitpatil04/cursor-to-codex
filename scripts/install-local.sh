#!/usr/bin/env bash
# Local-try helper for the cursor-to-codex Codex plugin.
#
# Default: register this repo as a Codex marketplace so you can install the
# plugin from the /plugins directory.
#   ./scripts/install-local.sh
#
# --personal: also copy the plugin into ~/.codex/plugins and register a personal
# marketplace at ~/.agents/plugins/marketplace.json (useful when you want it
# available outside this repo).
#   ./scripts/install-local.sh --personal
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PERSONAL=0
[ "${1:-}" = "--personal" ] && PERSONAL=1

echo "Repo: $REPO_ROOT"

if ! command -v codex >/dev/null 2>&1; then
  echo "warning: 'codex' CLI not found on PATH. Install Codex, then re-run." >&2
fi

if command -v codex >/dev/null 2>&1; then
  echo "Registering local marketplace with Codex..."
  codex plugin marketplace add "$REPO_ROOT"
  echo "Done. Restart Codex, open /plugins, install 'cursor-to-codex'."
fi

if [ "$PERSONAL" -eq 1 ]; then
  DEST="$HOME/.codex/plugins/cursor-to-codex"
  echo "Copying plugin to $DEST ..."
  mkdir -p "$DEST"
  cp -R "$REPO_ROOT/plugins/cursor-to-codex/." "$DEST/"

  MP="$HOME/.agents/plugins/marketplace.json"
  mkdir -p "$(dirname "$MP")"
  cat > "$MP" <<JSON
{
  "name": "cursor-to-codex-personal",
  "plugins": [
    {
      "name": "cursor-to-codex",
      "source": { "source": "local", "path": "$DEST" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
JSON
  echo "Wrote personal marketplace: $MP"
fi

echo
echo "Manual CLI (no install required):"
echo "  python3 plugins/cursor-to-codex/skills/cursor-to-codex/scripts/cursor-to-codex.py --dry-run"
