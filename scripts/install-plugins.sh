#!/usr/bin/env bash
# Wrapper kept for the old name. The work is done by install_plugins.py.
# Usage: bash scripts/install-plugins.sh "/path/to/vault" [--smart-connections] [--obsidian-skills]
set -euo pipefail
exec python3 "$(cd "$(dirname "$0")" && pwd)/install_plugins.py" "$@"
