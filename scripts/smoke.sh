#!/usr/bin/env bash
# PALATE smoke test — proves the app, agent and server work offline (mock mode).
# Usage: bash scripts/smoke.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
PORT="${SMOKE_PORT:-8791}"
TMP="$(mktemp -d)"
SERVER_PID=""
cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -rf "$TMP"
}
trap cleanup EXIT

step() { printf '\n\033[1;33m== %s ==\033[0m\n' "$1"; }

step "1/5 unit + integration tests (stdlib unittest, no network)"
"$PY" -m unittest discover -s tests -v

step "2/5 CLI agent run (mock mode)"
"$PY" -m palate.cli \
  --city "New York" \
  --mood "cozy but a little weird" \
  --love "Kamasi Washington" \
  --love "Everything Everywhere All at Once" \
  --json > "$TMP/run.json"
"$PY" - "$TMP/run.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
assert data["mode"] == "mock", "expected mock mode without QLOO_API_KEY"
assert len(data["plan"]["slots"]) == 4
assert len(data["itinerary"]) == 4
assert data["summary"]["slots_filled"] == 4, "agent should fill all four slots in mock mode"
phases = [event["phase"] for event in data["trace"]]
for required in ("plan", "resolve", "query", "critique", "recommend"):
    assert required in phases, "missing trace phase: %s" % required
assert phases[0] == "plan" and phases[-1] == "recommend"
for item in data["itinerary"]:
    assert item["entity"] and item["why"], "every stop needs an entity and a rationale"
    assert item["evidence"]["qloo_request"]["path"] == "/v2/insights"
print("  ✓ agent run valid: %d slots, %d trace events, %d Qloo calls"
      % (len(data["itinerary"]), len(data["trace"]), data["summary"]["qloo_calls"]))
PY

step "3/5 CLI digest renders"
"$PY" -m palate.cli --quiet-trace > /dev/null
echo "  ✓ digest renders"

step "4/5 HTTP server + API (mock mode)"
"$PY" app.py --port "$PORT" > "$TMP/server.log" 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 50); do
  if "$PY" - "$PORT" <<'PY' 2>/dev/null
import json, sys, urllib.request
port = sys.argv[1]
with urllib.request.urlopen("http://127.0.0.1:%s/api/healthz" % port, timeout=2) as response:
    payload = json.load(response)
assert payload["ok"] is True, payload
PY
  then break; fi
  sleep 0.15
done
"$PY" - "$PORT" <<'PY'
import json, sys, urllib.request
port = sys.argv[1]
base = "http://127.0.0.1:%s" % port

with urllib.request.urlopen(base + "/", timeout=5) as response:
    html = response.read().decode("utf-8")
assert "PALATE" in html and "/api/plan" in html, "index page missing"
print("  ✓ GET / serves the app")

body = json.dumps({
    "city": "New York",
    "mood": "high-energy date night",
    "loves": ["Little Simz", "Burna Boy"],
}).encode("utf-8")
request = urllib.request.Request(base + "/api/plan", data=body, headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(request, timeout=20) as response:
    data = json.load(response)
assert response.getcode() == 200
assert data["mode"] == "mock"
assert len(data["itinerary"]) == 4
assert data["summary"]["qloo_calls"] >= 4
print("  ✓ POST /api/plan returns a full agent run (mode=%s, %d slots)"
      % (data["mode"], len(data["itinerary"])))

# Input validation returns 400, not a traceback.
bad = urllib.request.Request(base + "/api/plan", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
try:
    urllib.request.urlopen(bad, timeout=5)
    raise SystemExit("expected HTTP 400 for empty payload")
except urllib.error.HTTPError as exc:
    assert exc.code == 400, exc.code
print("  ✓ invalid payload rejected with HTTP 400")
PY

step "5/5 live-mode guard (no key => clear failure, never silent)"
if QLOO_API_KEY="" PALATE_MODE=live "$PY" app.py --port "$((PORT + 1))" > "$TMP/nokey.log" 2>&1; then
  echo "  ✗ expected a non-zero exit without a key"
  exit 1
fi
grep -q "QLOO_API_KEY" "$TMP/nokey.log"
echo "  ✓ live mode without a key exits with an actionable message"

printf '\n\033[1;32mSMOKE TEST PASSED\033[0m — PALATE runs offline in mock mode and refuses live mode without a key.\n'
