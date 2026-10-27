# RULES-NOTES — verified requirements, quotes, and what remains UNVERIFIED

Research date: **2026-10-27** (America/New_York). All quotes below were fetched directly with `curl`
from the official pages and are reproduced verbatim, including the source's own typos. This file is the
evidence trail for every claim made in `README.md` and `SUBMISSION.md`.

Sources:

- Hackathon page: <https://qloo.devpost.com/> (fetched 2026-10-27, 159–142 KB HTML)
- Official rules: <https://qloo.devpost.com/rules> (fetched 2026-10-27)
- Qloo hackathon developer guide: <https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide>
  (fetched 2026-10-27) — includes the API-key request form link
- Insights API deep dive: <https://docs.qloo.com/reference/insights-api-deep-dive> (fetched 2026-10-27)
- Basic Insights use case (sample response body): <https://docs.qloo.com/reference/basic-insights-use-case>
- Search Entities: <https://docs.qloo.com/reference/get-search>
- Search Tags: <https://docs.qloo.com/reference/search-tags>

---

## 1. The two requirements that determine the build

### 1.1 What to build (rules §4 "Project Requirements")

> **What to Create:**
> Entrants must create a working software application that integrates the Qloo API and that either
> (a) functions as an agentic tool, (b) is built using an agent framework, or (c) integrates the Qloo API
> into an existing agent (each a “Project”).

> **Functionality:**
> The Project must be capable of being successfully installed and running consistently on the platform for
> which it is intended and must function as depicted in the video and/or expressed in the text description.

> **New & Existing:**
> Projects must be either newly created by the Entrant or, if the Entrant’s Project existed prior to the
> Hackathon Submission Period, must have Qloo 4after the start of the Hackathon Submission Period.
> Entrants should explain how their Project was significantly updated during the Submission Period.

*(The "Qloo 4after" text is a typo on the official page. PALATE is newly created, so this clause is
satisfied either way.)*

### 1.2 It must be hosted externally (hackathon page "What to Submit")

> **4. External hosting / fully published requirement**
> Your demo must be hosted and fully published externally, such as a live website or web app, or a hosted
> APK / TestFlight build. Submissions that only run locally or rely on private access will not qualify.

### 1.3 Videos are NOT required (hackathon page "What to Submit")

> **NOTE:**
> Demo videos are **not** required. Instead of asking for a recording, we're requiring something judges
> can actually use.

**Consequence:** the deliverable is a *deployed web app + public repo + text description*. A demo video is
optional; `SUBMISSION.md` therefore includes an optional <3-minute pitch script for the **finalist live
appearance** (Nov 5) rather than a mandatory recording script. Do not spend time recording unless it helps
the submission; the hosted demo is the requirement.

---

## 2. Submission requirements (rules §4 "Submission Requirements")

> Include a Project built with the required developer tools and meets the above Project Requirements.
> Provide a link to a functional demo application
> Provide a URL to your public code repository for judging and testing on either GitHub, GitLab or
> Bitbucket. The repository must contain all necessary source code, assets, and instructions required for
> the project to be functional. The repository must be public and open source by including an open source
> license file. This license should be detectable and visible at the top of the repository page (in the
> About section).
> Include a text description that should explain the features and functionality of your Project.

> **Testing**
> Access must be provided to an Entrant’s working Project for judging and testing by providing a link to a
> website, functioning demo, or a test build. If Entrant’s website is private, Entrant must include login
> credentials in its testing instructions. The Entrant must make the Project available free of charge and
> without any restriction, for testing, evaluation and use by the Sponsor, Administrator and Judges until
> the Judging Period ends. Judges are not required to test the Project and may choose to judge based solely
> on the text description, images, and video provided in the Submission.

> **Submission ownership**
> Be the original work of the Entrant, be solely owned by the Entrant, and not violate the IP rights of any
> other person or entity.

PALATE satisfies these with: a public MIT-licensed repo (license visible in the GitHub About section via the
`LICENSE` file), a free hosted web demo with no login, and the text description in `SUBMISSION.md`.

---

## 3. Dates, prizes, eligibility

> **1. Dates and Timing**
> Registration and Submission Period:
> September 30, 2026 (9:00 am Eastern Time) – October 30, 2026 (11:45 pm Eastern Time)
> (“Registration & Submission Period ”).
> **Judging Period:**
> November 2, 2026 (12:00 pm Eastern Time) – November 5, 2026 (11:45 pm Eastern Time).
> **Winners Announced:**
> On or around November 5, 2026 (3:00 pm Eastern Time).

Hackathon page countdown: "October 30 at 11:45pm EDT"; "Public"; "Online"; "$25,000 in cash";
"2,592 participants".

> **8. Prizes**
> 1st Place — $15,000 USD — 1 — All eligible submissions
> 2nd Place — $6,000 USD — 1 — All eligible submissions
> 3rd Place — $4,000 USD — 1 — All eligible submissions

Bonus from the hackathon page:

> **BONUS CHALLENGE UNLOCKED!!!!!**
> Entrepreneur extraordinaire JASON CALACANIS -- JCal the Bestie himself -- will personally invest an
> additional $25,000 into his favorite entry.

Finalist stage:

> On November 5th, the Top 3 Finalists will appear on air with Jason Calacanis, Cedric the Entertainer, and
> Alex Elias, who will pick the winner!
> All three finalists will present their ideas to the judges, answer questions, and learn the results in
> real time. […] the finalists must be able to appear, and must be available for preparation prior to the
> appearance.

Eligibility: age of majority where the entrant resides; individuals, teams, organizations; standard
sanctioned-country exclusions (Brazil, Quebec, Russia, Crimea, Cuba, Iran, North Korea, etc.).

**Time left at research time:** ~3 days (deadline Fri 2026-10-30 23:45 ET).

---

## 4. Judging criteria (rules §6)

> **Stage Two)**
> All Submissions that pass Stage One will be evaluated in Stage Two based on the following equally
> weighted criteria:
> **Technological Implementation:** How thoroughly and skillfully does the project use Qloo? Does the code
> reflect genuine effort and a working, non-trivial implementation?
> **Design:** Does the project deliver a complete, coherent product experience, not just a technical proof
> of concept?
> **Potential Impact:** Does the project make a credible, specific case for solving a real problem for a
> real audience and does the solution actually address that problem based on what's demonstrated?
> **Quality of the Idea:** Is this a creative, non-obvious use of Qloo and does the team demonstrate
> genuine understanding of the problem space they're working in?

Stage One is pass/fail: *"whether the ideas meet a baseline level of viability, in that the Project
reasonably fits the theme and reasonably applies the required APIs/SDKs featured in the Hackathon."*

Hackathon page framing (also a judging signal):

> Agents are getting smarter, but they're culturally blind. […] Use our API and taste graph — 250M+
> entities across music, film, dining, fashion, and more — to give your agent something most never get:
> real cultural grounding.
> We're not looking for demos of what LLMs can already do. We're looking for the thing that only works
> because it knows what people love.
> If your submission would work the same without Qloo, you're building the wrong thing.

---

## 5. Qloo API access (what a third party cannot do for the user)

Rules §4:

> Entrants will be given access to the Qloo API by filling out the Google Form here:
> https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide#getting-your-api-key

Developer guide:

> **Getting Your API Key**
> Submit the API key request form to register for hackathon access. Once approved, you'll receive a
> personal API key by email. Keys are typically issued within a few business days.
> If you haven't received your key, check your spam or junk folder; keys often end up there.

The API-key request form URL embedded in that page: **<https://forms.gle/zz12orkLHTAneLGz6>**

> **FAQs — API Keys**
> How long does it take to receive my API key?
> Keys are provisioned manually, so please allow a few business days after submitting the form. […]
> Can I fill out the API key request form before I have a project idea?
> Yes. You do not need a finalized idea to request a key. Leave the project idea field blank or describe a
> general direction.

**Consequence:** the API key request should be submitted *immediately* (it is user-only — it involves
accepting terms and providing contact details), because provisioning takes days while the deadline is
Friday. The app ships with mock mode so deployment and judging can be prepared before the key arrives.

---

## 6. Qloo API contract implemented by PALATE (verified from the developer guide)

> Your key is valid only against the hackathon base URL:
> `https://hackathon.api.qloo.com`
> Hackathon API keys **do not work** against:
> Staging: `https://staging.api.qloo.com`
> Production: `https://api.qloo.com`

> Wrong API Key Header
> Error: 401 "No API key found in request"
> Pass your API key in the **X-Api-Key** request header. Do not pass it as a query parameter or as a Bearer
> token.

> # Correct
> `curl -H "X-Api-Key: YOUR_API_KEY" "https://hackathon.api.qloo.com/v2/insights?filter.type=urn:entity:movie"`

> Wrong HTTP Method
> `/v2/insights` is a **GET** request. Parameters go in the query string, not a JSON body.

> **Available Endpoints**
> During the hackathon, all Qloo API endpoints are available. The Insights API is the primary way to
> generate recommendations and insights. […] **Do not use** `/recommendations` or `/recs`. These are legacy
> endpoints and are not supported for the hackathon.

> **Supported Entity Types** — Every request to the Insights API must include `filter.type` […] Supported
> values are:
> `urn:entity:artist`, `urn:entity:book`, `urn:entity:brand`, `urn:entity:destination`, `urn:entity:movie`,
> `urn:entity:person`, `urn:entity:place`, `urn:entity:podcast`, `urn:entity:tv_show`, `urn:entity:video_game`

> If you are getting empty results with no error, verify your parameters […] invalid parameters are
> silently ignored rather than returning an error.

> **Quotas, Limits & Key Expiration**
> Hackathon API keys have rate and monthly quota limits set high enough to support typical hackathon
> projects. […] Keys remain active through the end of the judging period and are deactivated after the
> hackathon closes.

> **Can I cache Qloo API responses in my app?**
> Private server-side caching is fine and there is no time limit on how long you can keep cached responses.
> Do not store Qloo response data in a public repository — that makes the data publicly accessible outside
> the terms of your API key.

PALATE therefore: keeps the key server-side, implements `X-Api-Key`, `GET /v2/insights` with query
parameters, `GET /search`, `GET /v2/tags`; never uses `/recs`; does not cache or commit any Qloo response
data (the mock fixture is synthetic and labelled as such).

### Insights request parameters used (documented in the deep dive)

- `filter.type` (required) — entity category
- `signal.interests.entities` — comma-separated entity IDs that influence affinity
- `signal.interests.tags` — comma-separated tag IDs (must be real tag IDs from `/v2/tags`, not freeform)
- `signal.location.query` — named locality for geospatial results; *"If no locality is found, the API will
  return a 400 error."* When no locality is found PALATE retries without the location signal.
- `feature.explainability` — *"When set to `true`, the response includes explainability metadata for each
  recommendation and for the overall result set."*
- `take` — result count (1–50, default 20)

### Sample response shape used for parsing (verified from the basic use case page)

```json
{
  "success": true,
  "results": {
    "entities": [
      {
        "name": "Everything Everywhere All at Once",
        "entity_id": "F0D354AA-…",
        "type": "urn:entity",
        "subtype": "urn:entity:movie",
        "properties": { "release_year": 2022, "description": "…" },
        "popularity": 0.998,
        "tags": [{ "id": "urn:tag:…", "name": "…", "type": "urn:tag:…" }]
      }
    ]
  }
}
```

---

## 7. UNVERIFIED — do not treat these as facts

1. **Live Qloo API behaviour was not exercised from this environment.** No hackathon key was available (and
   obtaining one is a user-only action). The live client is implemented from the official developer guide and
   covered by contract tests with an injected transport; the deployed live demo is the end-to-end proof.
2. **`GET /search` and `GET /v2/tags` sample response bodies are not shown verbatim in the public docs.**
   The docs list parameters and status codes only. PALATE parses these defensively (tags extracted from
   `results.tags`, `results.entities`, or top-level `tags`). Exact production shape: **UNVERIFIED**.
3. **`feature.explainability` response shape**: documented as returning per-result and aggregate influence
   metadata, but no example JSON was captured. PALATE consumes it only if present and never depends on its
   shape. **UNVERIFIED**.
4. **`urn:entity:video_game` vs `urn:entity:videogame`**: the hackathon developer guide lists
   `urn:entity:video_game`, while the Insights deep-dive enum shows `urn:entity:videogame`. PALATE never
   uses this type; if extending the app, verify against the live API first. **UNVERIFIED**.
5. **Exact `/v2/insights` base URL in the deep-dive examples** shows `https://api.qloo.com` (generic docs),
   while the hackathon guide says hackathon keys only work against `https://hackathon.api.qloo.com`.
   PALATE defaults to the hackathon URL but keeps it configurable via `QLOO_BASE_URL`. Verified by guide
   text; effective behaviour against the live hackathon environment **UNVERIFIED**.
6. **Rate/quota numbers** are not published; the guide says limits are high and can be raised on request.
7. **Devpost submission form fields** are only visible to signed-in participants. The rules require repo
   URL, demo URL, text description; additional fields (e.g. optional video, built-with tags, "try it out"
   URL) are standard Devpost but their exact labels are **UNVERIFIED** until the user joins.
8. **Hosting free-tier behaviour** (Render free web service cold starts, Hugging Face Spaces availability,
   required account/terms) was not verified by deploying — that requires the user's accounts. Estimated
   times in `SUBMISSION.md` are conservative guesses, not measured.
9. **API-key approval time** is stated as "typically … a few business days" but not guaranteed. If the key
   does not arrive by the deadline, the hosted demo still runs in clearly-labelled mock mode; the
   submission would then be honest about the live path not being demonstrable. Request the key immediately.
10. **Finalist appearance logistics** (remote vs in-person, preparation schedule) are unspecified beyond
    "must be able to appear". **UNVERIFIED**.
11. **Video requirement**: the hackathon page says videos are not required, but the Devpost submission form
    may still show an optional video field. Treat a recorded video as optional; do not block on it.
12. **"New & Existing" clause** contains a typo ("must have Qloo 4after"); the intended meaning is assumed
    to be that pre-existing projects must have added the Qloo integration during the submission period.
    PALATE is new, so this does not affect it. **UNVERIFIED interpretation.**

---

## 8. User-only actions (cannot be done by a third party)

- Request the Qloo hackathon API key (Google Form, accepting terms + personal contact data).
- Create/own the public GitHub repo and make it public with the MIT license visible in the About section.
- Create hosting accounts and deploy the demo (Render/HF/etc.).
- Sign into Devpost, join the hackathon, and submit.
- Any winner affidavit / tax form if selected.
- Optional: record a demo video if desired (not required).

No accounts, keys, registrations, or personal data were created, used, or transmitted while building this
package.
