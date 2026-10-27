# RUNBOOK — run, demo, deploy and troubleshoot PALATE

Everything here runs with the Python standard library (Python 3.9+). No `pip install`, no Node, no build
step, no Docker required for local use.

Paths assume the repo root, i.e. `contest-entries/qloo/` (the folder containing `app.py`).

---

## 0. One-time local verification (2 minutes)

```bash
cd contest-entries/qloo

# Full proof that the app works offline
bash scripts/smoke.sh
```

Expected tail:

```
SMOKE TEST PASSED — PALATE runs offline in mock mode and refuses live mode without a key.
```

Then:

```bash
python3 -m unittest discover -s tests -v   # 62 tests
```

If both pass, the package is healthy. Every command below has been exercised locally except the
hosting-provider steps (those need the user's accounts).

---

## 1. Mock-mode demo (no API key, no network)

```bash
cd contest-entries/qloo
python3 app.py
# PALATE 1.0.0 — An agentic culture concierge, grounded in taste.
#   data source : mock (no QLOO_API_KEY — running on the simulated taste graph)
#   listening   : http://127.0.0.1:8000
```

Open <http://127.0.0.1:8000>. The header badge reads **SIMULATED TASTE GRAPH** and each run shows a banner
saying the data is synthetic. This is the mode to use for UI work, screenshots and rehearsals — it needs no
key and always works.

Sample profiles in the UI:

1. **Cozy but a little weird** — New York
2. **High-energy date night** — Los Angeles
3. **Low-key brainy Sunday** — New York

Shareable deep link that autofills and runs a profile:
`http://127.0.0.1:8000/?demo=1` (or `?demo=2`, `?demo=3`).

Terminal demo:

```bash
python3 -m palate.cli \
  --city "New York" \
  --mood "cozy but a little weird" \
  --love "Kamasi Washington" \
  --love "Everything Everywhere All at Once" \
  --love "Ramen Tsubaki"
```

Full JSON (same payload as `POST /api/plan`):

```bash
python3 -m palate.cli --city "New York" --mood "cozy" --love "Radiohead" --json | python3 -m json.tool | head -40
```

Force mock even when a key is present:

```bash
PALATE_MODE=mock python3 app.py
```

---

## 2. Real-mode demo (needs a Qloo hackathon API key)

### 2.1 Get the key (user-only, do this first)

1. Open <https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide#getting-your-api-key>.
2. Submit the **API key request form** (link on that page; direct form:
   <https://forms.gle/zz12orkLHTAneLGz6>). You do not need a finalized idea.
3. Wait for the email — **keys are provisioned manually; allow a few business days**. Check spam.
4. The key only works against `https://hackathon.api.qloo.com`.

### 2.2 Run locally in live mode

```bash
cd contest-entries/qloo
export QLOO_API_KEY="paste-your-key-here"
export QLOO_BASE_URL="https://hackathon.api.qloo.com"   # default, explicit for clarity
export PALATE_MODE="live"
python3 app.py
```

Verify:

```bash
curl -s http://127.0.0.1:8000/api/healthz | python3 -m json.tool
# "mode": "live", "live_configured": true
```

Then open the app: the badge must read **LIVE QLOO API**, and a run must show the green "Live Qloo API"
banner. If you see the amber simulated banner while expecting live, see §6.

> The key never reaches the browser. Do not put it in the URL, the repo, or JS.
> `.env` is git-ignored; `.env.example` documents every variable.

---

## 3. Deploy the hosted demo (required for submission)

The rules require a **hosted, externally published demo** — "Submissions that only run locally or rely on
private access will not qualify." Deploy in mock mode first (it works immediately), then add the key.

### Option A — Render free web service (recommended, ~8 minutes)

1. Push this folder as the root of a **public GitHub repo** (see `SUBMISSION.md` checklist).
2. Go to <https://render.com> → sign up (user-only) → **New → Web Service** → connect the repo.
3. Settings:
   - Runtime: **Python**
   - Build command: leave empty or `python3 -c "import sys; print(sys.version)"`
   - Start command: `python3 app.py`
   - Health check path: `/api/healthz`
   - Instance type: **Free**
4. Add environment variables (Environment tab):
   - `PALATE_MODE` = `auto`
   - `QLOO_BASE_URL` = `https://hackathon.api.qloo.com`
   - `QLOO_API_KEY` = your key (**Secret** type) — optional until the key arrives; add later and redeploy.
5. Deploy. Wait for "Live" state, then open the `.onrender.com` URL. Visit `/api/healthz` to confirm
   `"ok": true` and the expected `mode`.
6. Render injects `PORT`; `app.py` binds `0.0.0.0:$PORT` automatically. Free instances spin down when idle,
   so expect a ~30–60 s cold start on the first visit — the app itself needs no warm-up state.
7. Copy the public URL into the Devpost "demo application" field, and optionally into this repo's
   **About → Website** field.

`render.yaml` in the repo root describes the same service; on Render you can also use
**New → Blueprint** and point it at the repo.

### Option B — Hugging Face Spaces with Docker (~10 minutes)

1. Create a **Docker** Space (user-only) at <https://huggingface.co/new-space>.
2. Push this repo to the Space's git remote (or upload the files through the web UI).
3. In **Settings → Variables and secrets**, add `QLOO_API_KEY` as a **secret**; add `PALATE_MODE=auto`
   and `QLOO_BASE_URL=https://hackathon.api.qloo.com` as variables.
4. The included `Dockerfile` listens on `$PORT` (default 7860, which Spaces expects) and exposes a
   healthcheck at `/api/healthz`.
5. Open the Space URL and verify the live badge.

### Option C — any Docker host / VPS

```bash
docker build -t palate .
docker run -p 8000:8000 -e PORT=8000 -e QLOO_API_KEY="..." palate
```

Any host that runs `python3 app.py` with `PORT` set works. No database, no volumes, no build artifacts.

---

## 4. Post-deploy verification (5 minutes)

Run through this before submitting:

```bash
DEMO_URL="https://your-demo.onrender.com"

curl -s "$DEMO_URL/api/healthz" | python3 -m json.tool
# expect: ok=true, mode="live" (or "mock" before the key is added), live_configured

curl -s -X POST "$DEMO_URL/api/plan" \
  -H 'Content-Type: application/json' \
  -d '{"city":"New York","mood":"cozy but a little weird","loves":["Kamasi Washington","Ramen Tsubaki"]}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["mode"], len(d["itinerary"]), "slots", d["summary"]["qloo_calls"], "qloo calls")'
```

Browser checklist:

- [ ] Header badge matches the configured mode (green **LIVE QLOO API** after the key is added).
- [ ] Clicking a sample profile fills the form.
- [ ] "Plan my night" returns four stops within a few seconds.
- [ ] Each stop shows confidence, taste threads, and an expandable **Qloo request behind this pick**.
- [ ] The agent trace lists plan → resolve → query → critique → recommend.
- [ ] Reload the page on a phone-sized viewport; layout collapses to one column.

---

## 5. Demo script for a screen recording or live pitch

1. Open the hosted demo (`/?demo=1` autofills the "cozy but a little weird" profile).
2. Point at the mode badge: "this is talking to the real Qloo API — no key in the browser."
3. Click **Plan my night →**. While it loads, name the loop: plan → query Qloo → critique → recommend.
4. Walk one stop, e.g. dinner: "Qloo ranked this place for my actual references, and here is the exact
   `/v2/insights` request it used."
5. Change the mood to "high-energy" and add a reference; run again; show how the itinerary shifts.
6. Expand a **revise** step if present (or the critique notes) and explain the self-correction.
7. Close on the full agent trace and the summary counts.

No video is required for this hackathon — this script is for a live finalist pitch if selected
(see `SUBMISSION.md`).

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Badge says **SIMULATED TASTE GRAPH** but you set a key | Server started before the env var was set, or the key is empty/whitespace | Restart the server (hosting: redeploy after adding the env var). Check `/api/healthz` → `live_configured` |
| `PALATE cannot start: Live mode requested but QLOO_API_KEY is not set` | `PALATE_MODE=live` with no key | Export `QLOO_API_KEY` or use `PALATE_MODE=auto` |
| Amber banner **Simulated fallback** with a reason | The live call failed (401/403/404/429/network) and fallback is on | Read the reason in the banner/trace. Verify key, `QLOO_BASE_URL=https://hackathon.api.qloo.com`, and that the hackathon key is active. Set `PALATE_MOCK_FALLBACK=0` to make failures hard errors |
| `Qloo returned HTTP 401` (trace/banner) | Wrong base URL, expired/deactivated key, or key not yet approved | Hackathon keys only work on `hackathon.api.qloo.com`. Re-check the email; request a new key if needed |
| `Qloo returned HTTP 403` | Entity type not supported by the account/endpoint | PALATE only uses `place`, `movie`, `artist`; check for typos if you extended it |
| `Qloo returned HTTP 429` | Rate/quota limit | Wait, reduce requests, or ask in the hackathon Discord `#api-help` for headroom (per the Qloo guide) |
| Empty `entities`, HTTP 200 | Qloo silently ignores unsupported parameters for the chosen `filter.type` | Check parameter support in the Qloo entity-type guide; try a broader query. PALATE's critique loop already re-queries, but a live mismatch is worth logging |
| `HTTP 400` from `/api/plan` | Missing mood/loves, bad JSON, or body > 32 KB | The error message in the UI/response explains it; send valid JSON with `mood` or at least one `loves` entry |
| `HTTP 429` from PALATE itself | 40 requests/minute per IP limit | Wait a minute. Tune `RATE_LIMIT_REQUESTS` in `app.py` if needed |
| Render: "Application failed to respond" | App crashed at startup (usually `PALATE_MODE=live` without key) | Check Render logs; use `PALATE_MODE=auto` or set the secret |
| Render free instance slow on first hit | Free tier spins down when idle (~30–60 s cold start) | Expected; warm it up before a live demo or record a video |
| `Address already in use` locally | Another demo server is running | `lsof -ti :8000 \| xargs kill` (macOS/Linux), or use `--port 8001` |
| `ModuleNotFoundError: palate` | Ran from the wrong directory | `cd contest-entries/qloo` and run `python3 app.py` / `python3 -m palate.cli` |

Logs: the server prints one concise line per request to stderr (no query strings, no keys). Hosted
platforms show these in their log viewer.

---

## 7. Rollback / reset

- There is no database or persistent state; redeploying or restarting is a full reset.
- To return a hosted demo to safe offline behaviour quickly: set `PALATE_MODE=mock` and redeploy.
- To remove the key: delete `QLOO_API_KEY` from the host's environment and redeploy.

---

## 8. What was verified locally

- [x] `bash scripts/smoke.sh` passes (62 unittest tests + CLI + HTTP API + live-mode guard).
- [x] `python3 app.py` starts on Python 3.9.6 with zero dependencies.
- [x] Mock-mode UI run renders a full four-stop itinerary with trace (screenshot in `docs/screenshot.png`).
- [x] `POST /api/plan` returns 200 and a complete JSON payload; invalid input returns 400.
- [x] Live-mode start without a key exits with an actionable message.
- [x] Live-mode network failure falls back to a clearly labelled `mock-fallback` run.
- [ ] Real Qloo API call with a valid hackathon key — requires the user's key.
- [ ] Hosted deployment on Render/HF — requires the user's accounts.
