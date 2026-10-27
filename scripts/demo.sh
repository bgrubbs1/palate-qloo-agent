#!/usr/bin/env bash
# Start PALATE locally for a demo, on a fixed port.
#   bash scripts/demo.sh            # mock mode (no key needed)
#   QLOO_API_KEY=... bash scripts/demo.sh   # live mode (auto-detected)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PORT="${DEMO_PORT:-8000}"
echo "PALATE starting on http://127.0.0.1:${PORT}"
python3 app.py --port "$PORT"
