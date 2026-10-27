# SUBMISSION — Qloo Agentic Hackathon 2026 (Devpost)

**Deadline: Friday 2026-10-30, 23:45 ET.** Judging: Nov 2–5. Winners announced on air **Nov 5**.
Everything in **Part 1** is ready to paste into the Devpost submission form. **Part 3** is the only part
that needs the user personally. Placeholders look like `<THIS>` — replace them once, then paste.

Verified rules/quotes live in [`RULES-NOTES.md`](RULES-NOTES.md). Two facts drive this checklist:

1. A **hosted, externally published demo is required**; a locally-running app will not qualify.
2. **Demo videos are NOT required** — so do not spend an hour recording one before the demo is deployed.

---

# PART 1 — Paste-ready Devpost submission copy

## Project name

```
PALATE
```

## Tagline / elevator pitch (devpost "elevator pitch" field)

```
An agentic culture concierge, grounded in the Qloo taste graph: it plans your night from your taste, critiques its own shortlist, and shows the exact Qloo request behind every pick.
```

## Inspiration

```
Every AI agent can plan now. Almost none of them have taste.

I kept watching assistants recommend the same five restaurants and the same three albums — competent, culturally blind. The Qloo hackathon brief said it perfectly: "Agents are getting smarter, but they're culturally blind." Taste isn't a prompt problem; it's a data problem. You need to know how audiences actually relate across music, film, food and place, not just what is popular.

So I built PALATE around the smallest, most human decision I could find: what should I do tonight? It's a decision that is entirely about taste — and one where generic recommendations are immediately, personally wrong. Qloo gives the agent real cultural grounding across domains. My job was to build the planning loop that uses it honestly.
```

## What it does

```
PALATE plans a real night out — dinner, film, music, a nightcap — from four inputs: a city, a mood, and a few things you already love.

The agent works in a visible loop:

1. Plan. It turns the free-text mood into concrete Qloo tag signals and splits the evening into four slots, each with its own entity type and intent.
2. Resolve. Each thing you love is resolved through Qloo /search to a real entity ID; the mood is grounded through Qloo /v2/tags. References Qloo can't resolve are logged and the agent adapts rather than failing.
3. Query. For every slot it asks the Qloo Insights API (/v2/insights) with signal.interests.entities, signal.interests.tags, signal.location.query for places, and feature.explainability on — so recommendations are ranked by cultural affinity, not popularity.
4. Critique. It evaluates its own shortlist: enough fresh candidates? a traceable tag thread with your profile? a mainstream tilt? If a slot is weak, it says so.
5. Revise. When a slot is thin it re-queries Qloo with a revised signal set — widen the city, rebalance references, switch to mood-only signals, loosen tags — up to three rounds, keeping the best.
6. Recommend. It returns a timed itinerary with a confidence level, the taste threads that connect each pick to you, runner-up candidates, and the exact Qloo request that produced the choice.

The UI shows the full agent trace, so a pick isn't a black box: you can open any step and see the data, including the /v2/insights query. When no data source is configured it runs on a clearly-labelled synthetic taste graph; when a QLOO_API_KEY is present it talks to the real Qloo API and the badge turns green — no key ever reaches the browser.
```

## How we built it

```
- Agent loop: a small Python agent (palate/agent.py) with explicit phases and structured trace events. No framework magic — plan, tool calls, critique, revise, recommend, all inspectable in the response JSON.
- Qloo integration (palate/qloo.py): one client interface, two implementations.
  - LiveQlooClient: GET /search (resolve references), GET /v2/tags (mood → real Qloo tag IDs), GET /v2/insights (recommendations) against https://hackathon.api.qloo.com, authenticating with the X-Api-Key header and sending filter.type, signal.interests.entities, signal.interests.tags, signal.location.query, take and feature.explainability as documented. Designed for live 401/403/429/empty-result behaviour, with actionable error messages.
  - MockQlooClient: the same three methods over a bundled synthetic taste graph (56 entities, 48 tags, hand-authored cross-domain "taste bridges" such as jazz ↔ noir and ambient ↔ gallery). It is not Qloo data and the UI says so on every simulated run. Its affinity model is deterministic, so the agent, tests and demos run offline with zero secrets.
- Web app: a single dependency-free Python HTTP server (stdlib http.server) serving a hand-built single-page UI in vanilla JS/CSS, plus POST /api/plan and GET /api/healthz. Rate-limited, size-limited, no persistence, no accounts, no PII.
- Honesty engineering: the response carries its data source; a failed live call produces a clearly labelled simulated fallback instead of a fake "live" result; every recommendation carries confidence and its Qloo query.
- Tests and ops: 62 stdlib unittest tests covering the agent loop, the exact live API contract (via an injected fake transport), the mock graph, and the HTTP server; a one-command smoke test; a Dockerfile and a Render blueprint so the hosted demo deploys with no build step.

Stack: Python 3.9+ standard library only, vanilla HTML/CSS/JS, Qloo Insights + Lookup APIs. Zero runtime dependencies, zero build step, MIT licensed.
```

## Challenges we ran into

```
- No API key during development. Qloo hackathon keys are provisioned manually ("allow a few business days"), and I couldn't request one on someone else's behalf. So I built mock and live as one interface: the agent only ever sees a client, which means the offline mode exercises exactly the same code path. Contract tests pin the live request shape from the official developer guide, and flipping one environment variable switches to the real API.
- The Qloo docs have sharp edges. Hackathon keys only work against https://hackathon.api.qloo.com, not the staging/production URLs that appear in most doc examples; the key goes in X-Api-Key, not a Bearer header; /v2/insights is a GET with query parameters; and unsupported parameters are silently ignored rather than erroring. I encoded each of those as explicit behaviour and test cases, and made "thin result" an agent-critique trigger instead of an exception.
- Making a taste graph feel real offline. Random data produces nonsense. I hand-authored cross-domain affinity bridges so a jazz reference can legitimately lead to a neo-noir film and a wine bar. The agent's reasoning is only impressive if the underlying signal behaves like taste, even in simulation.
- Designing for trust. An agent that hides its reasoning is just a recommendation engine. Every phase emits a trace event with structured data; every recommendation carries confidence, matched threads and the request behind it — and the app refuses to label simulated data as live.
```

## Accomplishments that we're proud of

```
- A genuinely agentic loop where the critique and revise steps actually change the outcome — the agent re-queries Qloo when its own shortlist is weak instead of returning whatever came back first.
- A complete, polished product: a single-page UI with a visible agent trace, expandable Qloo requests, confidence badges and taste threads — not a CLI proof of concept.
- 62 tests, a one-command smoke test, zero dependencies, and a deployable hosted demo that runs on a free tier with no build step.
- An honest failure mode: clearly labelled mock mode, clearly labelled fallback, and no way to mistake simulated data for the real Qloo API.
- The whole integration is legible to a judge: the exact endpoint calls are in the UI and in the response JSON.
```

## What we learned

```
- Cultural intelligence is cross-domain. The interesting recommendations weren't "more of the same" — they came from the agent moving between music, film, food and place through taste, which is exactly what Qloo's taste graph is for.
- Self-critique is cheap and high-value for agents. A critique step with concrete signals (candidate count, matched threads, mainstream tilt, seed echoing) caught weak slots that a single-shot prompt would have confidently shipped.
- The boring parts of agent products are trust, labelling and cost control: what data produced this, how confident is it, and what happens when the API fails.
- Hackathon logistics are a dependency. Keys provisioned manually mean the integration work has to be testable without them; a mock/live interface boundary is the difference between a blocked weekend and a shipping one.
```

## What's next for PALATE

```
- Verify and tune the live Qloo path end-to-end with the hackathon key, including explainability metadata surfaced directly in each card ("Qloo attributes this to…").
- More slots and formats: weekend escapes (destination entities), group taste merging (signal.interests.entities for a group profile), cities beyond the three demo presets.
- Optional accounts to save a taste profile and a history of nights; server-side caching of Qloo responses (permitted privately, never committed).
- A "why not the obvious pick?" comparison mode: show the top-affinity result next to a generic popularity-based baseline, so the Qloo difference is visible in the product itself.
- Better latency: parallel slot queries, with the same visible trace.
```

## Built with (Devpost tags)

```
python, python-stdlib, javascript, html5, css3, qloo, qloo-api, taste-graph, agentic-ai, ai-agents, multi-step-reasoning, rest-api, zero-dependencies, render, docker, hugging-face-spaces
```

## "Try it out" / testing instructions (paste into the form if a field exists)

```
Hosted demo: <HOSTED_DEMO_URL> — free, no login.

Fast path: open <HOSTED_DEMO_URL>/?demo=1 (autofills a profile and runs the agent), or pick a sample profile and press "Plan my night". The header badge and run banner state whether the run used the real Qloo API or the bundled simulated graph. Expand any stop's "Qloo request behind this pick" and the agent trace to see the /search, /v2/tags and /v2/insights calls.

No credentials are needed. The source repo has full run instructions, a mock mode that works offline, and a one-command smoke test.
```

## Gallery image

Use [`docs/screenshot.png`](docs/screenshot.png) (hosted-run screenshot) as the first gallery image, and
optionally a second screenshot of the agent trace. Avoid screenshots showing a simulated-mode banner if
you have captured a live-mode run; if your demo is still in mock mode when you submit, keep the screenshot
honest (the amber banner is fine — do not edit it out).

## Honest-swap paragraph (use ONLY if your API key has not arrived by submit time)

Replace the sentence *"when a QLOO_API_KEY is present it talks to the real Qloo API and the badge turns
green"* in **What it does** with:

```
The hosted demo currently runs in its clearly-labelled simulated mode because the hackathon API key is
provisioned manually; the live Qloo integration is implemented and contract-tested, and switches on by
setting QLOO_API_KEY with no code changes.
```

Do not claim a live Qloo run you have not actually executed. The code, tests and README carry the
integration either way; only the demo's badge changes.

---

# PART 2 — Judging-criteria cheat sheet (for the user, not for pasting)

Judges score these equally (verified from the official rules):

| Criterion | Where PALATE earns it | What to point at |
|---|---|---|
| **Technological Implementation** | Three documented Qloo endpoints used together; agent loop with real self-correction; live error handling; contract tests | Agent trace phases, `/v2/insights` request payload in each stop, `tests/test_qloo_client.py` |
| **Design** | Complete product: polished UI, confidence, taste threads, honest mode badges, responsive layout, no login | Hosted demo, `docs/screenshot.png` |
| **Potential Impact** | Real decision everyone makes weekly; taste-dependent and local; agent removes decision fatigue without flattening taste | Open with the "what should I do tonight" problem |
| **Quality of the Idea** | Non-obvious use: culture *concierge* not recommender widget; cross-domain taste threads; self-critique as a feature | Show a bridge like "jazz → noir film → wine bar" in one itinerary |

---

# PART 3 — EXACT user-only checklist (with time estimates)

Order matters: **request the API key first** (manual provisioning takes days), then repo, then deploy,
then submit. Target: finish everything **before Friday 2026-10-30 18:00 ET**, leaving ~5h45m buffer
before the 23:45 ET deadline.

| # | Action | Who | Est. | Done when |
|---|---|---|---|---|
| 0 | **Request the Qloo hackathon API key** — open <https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide#getting-your-api-key>, submit the API key request form (direct: <https://forms.gle/zz12orkLHTAneLGz6>). You can leave the idea field blank. Check spam for the email. | User (needs their contact details + terms acceptance) | **5 min** (+ a few business days waiting) | Confirmation page/email for the form; later an email containing the key |
| 1 | **Create a public GitHub repo** and push the contents of `contest-entries/qloo/` so its **root** contains `README.md`, `LICENSE`, `app.py`, etc. Then: repo → Settings → Public; add description + topics (`qloo`, `agentic-ai`, `hackathon`); confirm GitHub detects the MIT license (About panel shows "MIT license"). | User | **12 min** | Public repo URL loads; license visible in About |

Commands for step 1 (from `contest-entries/qloo/`, repo root = this folder):

```bash
git init -b main
git add .
git commit -m "PALATE — agentic culture concierge on the Qloo taste graph"
# create an empty PUBLIC repo named "palate" on github.com first, then:
git remote add origin https://github.com/bgrubbs1/palate-qloo-agent.git
git push -u origin main
```

Never commit `.env` or the API key (`.gitignore` already excludes them).
| 2 | **Deploy the hosted demo (mock mode works immediately)**. Follow `RUNBOOK.md §3 Option A (Render)` or Option B (HF Spaces). Add `PALATE_MODE=auto`, `QLOO_BASE_URL=https://hackathon.api.qloo.com` now; leave `QLOO_API_KEY` empty until it arrives. Open the URL and run a plan. | User | **10 min** | Public `https://…` URL serves PALATE; `/api/healthz` returns ok |
| 3 | *(When the key email arrives)* Add `QLOO_API_KEY` as a **secret env var** on the host (and `PALATE_MODE=auto`), redeploy/restart. Open `/api/healthz` → `"mode": "live"`; open the app → green **LIVE QLOO API** badge; run one live plan. | User | **5 min** | Live badge + one successful live run |
| 4 | **Join the hackathon on Devpost**: <https://qloo.devpost.com/> → "Join hackathon" (free Devpost account; email verification). | User | **5 min** | "My projects"/submission page shows the hackathon |
| 5 | **Create the Devpost project**: title `PALATE`, tagline, paste all Part 1 fields, set repo URL + hosted demo URL, paste "Try it out" instructions, add built-with tags, upload `docs/screenshot.png` as gallery image, set project as submitted to Qloo Agentic Hackathon. | User | **15 min** | Project preview looks complete |
| 6 | **Final verification + submit**: check the 8 boxes in Part 5 below; press Submit; confirm the confirmation email and that the project shows as submitted before the deadline. | User | **5 min** | Devpost shows submitted; confirmation received |
| 7 | *(Optional, not required)* Record a <3-minute demo video and add it to the project. Only do this after 0–6 are done. | User | 45 min | Optional |

**Total mandatory user time: ~55–60 minutes of hands-on work, plus waiting for the Qloo key.**
Do not wait for the key to do steps 1, 2, 4, 5 — they are independent. If the key is late, still submit
(steps 0/1/2/4/5/6) and use the honest-swap paragraph; add the key and flip the demo to live before the
deadline if it arrives in time.

**If selected as a finalist:** the rules state finalists must be able to appear (on air, Nov 5) and be
available for preparation beforehand. Keep Nov 5 free and check the email/baseline availability. Prize
winners must complete an affidavit/Required Forms within 10 business days.

---

# PART 4 — Optional finalist pitch script (<3 minutes, on air Nov 5)

Videos are not required for submission; **finalists present live**, so rehearse this only after the
submission is in. Target 2:40. Screenshots: use the hosted demo, live mode if possible.

| Time | On screen | Say (approx.) |
|---|---|---|
| 0:00–0:20 | Title card / app hero | "Every agent can plan. Almost none of them have taste. PALATE is an agentic culture concierge powered by Qloo — give it a mood and a few things you love, and it plans your night." |
| 0:20–0:45 | Hosted demo, empty state | "Here's the problem I care about: what should I do tonight? It's entirely a taste question, and generic assistants fail it. The Qloo hackathon brief said agents are culturally blind. Taste isn't a prompt problem — it's a data problem." |
| 0:45–1:10 | Click a sample profile, run | "PALATE plans dinner, film, music and a nightcap. First it resolves my references through Qloo /search and grounds the mood with /v2/tags — then it asks the Qloo Insights API, per slot, with entity and tag signals. This is a real /v2/insights call, server-side; the key never touches the browser." |
| 1:10–1:40 | Expand a stop + its Qloo request | "Every pick is explainable. Here's the exact request Qloo received, and here's the taste thread it found between my references and this pick — a jazz reference leading to a neo-noir film, for example. That cross-domain leap is the thing only Qloo makes possible." |
| 1:40–2:05 | Show agent trace critique/revise | "This isn't a prompt wrapper. The agent critiques its own shortlist — candidate count, matched threads, mainstream tilt — and when a slot is weak it re-queries Qloo with a revised signal set. You can see the self-correction in the trace." |
| 2:05–2:30 | Change mood, run again | "Change the mood and the whole night changes, because the cultural grounding changes. This is the difference between 'technically functional' and 'actually good' — the bar this hackathon is about." |
| 2:30–2:45 | Close on app + repo | "PALATE is MIT-licensed, zero-dependency Python, 62 tests, deployed live at the URL judges have, with the Qloo integration in the repo. Agents, but with taste. Thank you." |

Q&A prep (likely questions):

- *What happens without Qloo?* The agent still plans structurally, but every ranking signal comes from Qloo
  (`/search` IDs, `/v2/tags` tag IDs, `/v2/insights` affinity). Without it, the picks lose their cultural
  grounding — that's the point.
- *How do you know it isn't just popularity?* Each stop carries confidence, matched tag threads, and the
  Qloo request; the agent penalises seed echoes and flags mainstream tilt.
- *What's the production path?* Same interface: add auth/accounts, cache Qloo responses privately (allowed),
  parallelise slot queries, expand entity types (destination, podcast, video game).

---

# PART 5 — Pre-submit verification checklist (8 boxes)

Run the two commands first, then tick:

```bash
curl -s "<HOSTED_DEMO_URL>/api/healthz" | python3 -m json.tool
# expect: "ok": true, "mode": "live" (or "mock" only if the key truly hasn't arrived)

cd contest-entries/qloo && bash scripts/smoke.sh
# expect: SMOKE TEST PASSED
```

- [ ] Hosted demo URL opens from a browser **not logged into anything** (incognito window) and a plan runs end-to-end.
- [ ] `/api/healthz` on the hosted URL reports the expected `mode` (`live` if the key is configured).
- [ ] If mode is `live`, one browser run shows the green **Live Qloo API** banner and the header badge is green.
- [ ] Public GitHub repo URL loads; the MIT license is detected and visible in the repo About panel; `README.md` renders.
- [ ] Repo contains **no secrets and no Qloo response data**: no `.env`, no API key, no cached Qloo payloads (`git grep -i "ql_api\|x-api-key"` shows only code/example placeholders; `git status` clean).
- [ ] Devpost project: repo URL, hosted demo URL and text description all filled; built-with tags added; screenshot uploaded.
- [ ] Devpost project is **actually submitted to the Qloo Agentic Hackathon** (not just saved as a draft), before Fri 2026-10-30 23:45 ET.
- [ ] Confirmation email received; project appears in the hackathon's project gallery.

---

# PART 6 — Honesty guardrails (do not overclaim)

- The repo's **mock mode is synthetic**, not Qloo data. The UI labels it. Never present a mock-run
  screenshot/recording as a live Qloo run.
- Until the live path has been executed with a real key, say "the live integration is implemented and
  contract-tested; the hosted demo shows it when configured" — not "we validated against Qloo production."
- Do not state that videos are required (they are not) or that a local-only demo qualifies (it does not).
- Do not commit, publish or screenshot raw Qloo API responses in the public repo (the Qloo guide forbids
  storing response data publicly; private server-side caching is allowed).
- Prize/finalist details: finalists appear on air Nov 5 and must be available; winners complete
  affidavits/Required Forms within 10 business days. Unverified specifics stay unverified — see
  `RULES-NOTES.md §7`.
