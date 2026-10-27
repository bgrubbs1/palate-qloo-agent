# Devpost submission setup — Qloo Agentic Hackathon

**Your submission URL:** https://devpost.com/submit-to/31054-qloo-agentic-hackathon/manage/submissions
**Hackathon page:** https://qloo.devpost.com/ · **Deadline: Fri 2026-10-30, 23:45 ET** · Judging Nov 2–5 · winners **on air Nov 5** (top 3 pitch; Jason Calacanis adds a $25k investment to his favourite).
**Prizes:** $15,000 / $6,000 / $4,000 · Free · Judging criteria equally weighted: Technological Implementation, Design, Potential Impact, Quality of the Idea.

## ⚠ Two rules that drive everything
1. **A hosted, externally published demo is REQUIRED** — "Submissions that only run locally or rely on private access will not qualify." This is the one real blocker.
2. **A demo video is NOT required** — don't spend time recording one. (A <3-min finalist pitch script is in `SUBMISSION.md` Part 4, only for the on-air finals.)

## GitHub side — DONE ✅
- Public repository: **https://github.com/bgrubbs1/palate-qloo-agent** — all source + run instructions, MIT `LICENSE` at root, README rewritten as a project page (Inspiration / What it does / How we built it / Challenges / Accomplishments / Learned / Next / Built with), 1280×720 cover at `docs/cover.png` + real UI screenshot at `docs/screenshot.png`, repo description + topics set.
- Verified: `bash scripts/smoke.sh` passes; **62 tests pass**; live mode without a key fails safely; live API contract implemented from the official hackathon developer guide and contract-tested. No Qloo response data is committed — mock mode uses a clearly-labelled synthetic taste graph.
- Deploy config included: `render.yaml` (free Python web service, health check `/api/healthz`) and a `Dockerfile` (Hugging Face Spaces compatible).

## Only you can do these
1. **Request the Qloo hackathon API key — do it NOW if you haven't** (5 min): https://forms.gle/zz12orkLHTAneLGz6 (manual provisioning, "allow a few business days"; check spam). The submission can be honest without it, but the live Qloo path is the point of the hackathon.
2. **Deploy the hosted demo** (~10 min): Render → sign in with GitHub → **New + → Blueprint** → select `bgrubbs1/palate-qloo-agent` → Apply (it reads `render.yaml`) → wait for the URL. Open `https://<your-app>.onrender.com/?demo=1`.
   - Free tier **sleeps after inactivity** — the first request can take ~30–60 s. Open the URL once before judging / before you submit so it's warm; a $7 instance removes the cold start.
   - When the key arrives: Render dashboard → Environment → add **`QLOO_API_KEY`** (secret) → redeploy; open `https://<your-app>/api/healthz` and confirm `"ok": true, "mode": "live"`.
   - Alternative: Hugging Face Spaces (Docker SDK) using the included `Dockerfile` (port 7860).
3. **Devpost** (~20 min): see below. Do everything before **Friday 18:00 ET** to leave buffer before the 23:45 cutoff.

## Devpost click-through (~20 min after the demo URL exists)
1. Open the manage URL; log in with **GitHub** if prompted (you've registered).
2. **Create project → Import from GitHub** → authorize Devpost's GitHub app (read-only) → select `bgrubbs1/palate-qloo-agent`, **or** create manually and paste `SUBMISSION.md` Part 1.
3. Fill / verify:
   - **Project name:** `PALATE`
   - **Elevator pitch:** `An agentic culture concierge, grounded in the Qloo taste graph: it plans your night from your taste, critiques its own shortlist, and shows the exact Qloo request behind every pick.`
   - **About the project:** paste the Inspiration / What it does / How we built it / Challenges / Accomplishments / What we learned / What's next sections from `SUBMISSION.md` Part 1.
   - **Built with:** `python, python-stdlib, javascript, html5, css3, qloo, qloo-api, taste-graph, agentic-ai, ai-agents, multi-step-reasoning, rest-api, zero-dependencies, render, docker, hugging-face-spaces`
   - **GitHub repository:** `https://github.com/bgrubbs1/palate-qloo-agent`
   - **Hosted demo URL:** your Render URL (open `/?demo=1` for the fast path)
   - **Testing instructions:** hosted demo is free, no login; `/?demo=1` autofills a profile and runs the agent; badge/run banner states live vs simulated; expand any stop's "Qloo request behind this pick" and the agent trace.
   - **Gallery images:** `docs/screenshot.png` (keep the mode banner honest — amber simulated banner is fine if that's what's deployed) and optionally `docs/cover.png` as thumbnail.
   - **Video:** not required — leave empty.
4. **Submit** and verify the confirmation. Paste the hosted demo URL here if you want me to smoke-test it from my side before you submit.

## If your API key hasn't arrived by submit time (honest swap)
Use `SUBMISSION.md` § "Honest-swap paragraph": replace the sentence about the green live badge with the supplied paragraph that says the hosted demo currently runs in clearly-labelled simulated mode because keys are provisioned manually, and the live integration is implemented and contract-tested. **Do not claim a live Qloo run you haven't executed.**

## After submitting
- Optional: set the repo homepage to the Devpost project URL:
  `gh repo edit bgrubbs1/palate-qloo-agent --homepage <devpost-project-url>`
- Finalists present on air Nov 5; the optional <3-min pitch script is in `SUBMISSION.md` Part 4.
- Eligibility: 18+, worldwide where lawful; no purchase; prize paperwork only if you win.
