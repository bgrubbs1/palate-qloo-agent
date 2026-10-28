"""PALATE's agent loop: plan -> resolve -> query Qloo -> critique -> recommend.

The loop is deliberately explicit and inspectable. Every decision the agent
makes is recorded as a trace event (phase, title, detail, structured data) so
the web UI can show *why* a recommendation appeared, not just the result.
"""

from __future__ import annotations

import datetime
import re
import time

from . import APP_NAME, __version__
from .qloo import MODE_LIVE, QlooError, SEARCH_SEED_TYPES

MAX_LOVES = 8
MAX_REVISIONS = 2
TAKE_PER_SLOT = 8

#: The four things an actual night out needs, in order.
SLOTS = (
    {
        "key": "dinner",
        "label": "Dinner",
        "time": "19:00",
        "filter_type": "urn:entity:place",
        "cue": "somewhere you'd actually want to eat",
        "use_location": True,
    },
    {
        "key": "film",
        "label": "Film",
        "time": "20:45",
        "filter_type": "urn:entity:movie",
        "cue": "the thing you'll still be talking about after",
        "use_location": False,
    },
    {
        "key": "music",
        "label": "Music",
        "time": "22:30",
        "filter_type": "urn:entity:artist",
        "cue": "your soundtrack for the walk home",
        "use_location": False,
    },
    {
        "key": "nightcap",
        "label": "Nightcap",
        "time": "23:45",
        "filter_type": "urn:entity:place",
        "cue": "one last stop that matches the mood",
        "use_location": True,
    },
)

#: Mood vocabulary -> the mood tags the agent will look for in Qloo's tag API.
MOOD_PROFILES = {
    "cozy": {
        "keywords": ("cozy", "cosy", "warm", "intimate", "snug", "rainy", "comfort"),
        "tags": ("Cozy", "Wine Bar", "Jazz", "Soul", "Cafe", "Ramen"),
    },
    "weird": {
        "keywords": ("weird", "strange", "surreal", "odd", "bizarre", "unusual", "offbeat"),
        "tags": ("Weird", "Experimental", "Gallery", "Sci-Fi", "Ambient"),
    },
    "romantic": {
        "keywords": ("romantic", "romance", "date", "date night", "candlelit"),
        "tags": ("Romantic", "Wine Bar", "Jazz", "Romance", "Italian"),
    },
    "high-energy": {
        "keywords": ("high-energy", "high energy", "energetic", "loud", "party", "dance", "dancing", "electric"),
        "tags": ("High-Energy", "Electronic", "Cocktail Bar", "Live Music", "Hip-Hop"),
    },
    "low-key": {
        "keywords": ("low-key", "lowkey", "chill", "quiet", "mellow", "relaxed", "calm"),
        "tags": ("Low-Key", "Cafe", "Ambient", "Bookstore", "Documentary"),
    },
    "brainy": {
        "keywords": ("brainy", "thoughtful", "nerdy", "intellectual", "ideas", "curious", "clever"),
        "tags": ("Brainy", "Documentary", "Bookstore", "Gallery", "Classical"),
    },
    "nostalgic": {
        "keywords": ("nostalgic", "retro", "vintage", "throwback", "old-school", "classic"),
        "tags": ("Nostalgic", "Cocktail Bar", "Soul", "Diner", "Romance"),
    },
    "adventurous": {
        "keywords": ("adventurous", "adventure", "bold", "new", "explore", "surprise", "unexpected"),
        "tags": ("Adventurous", "Sci-Fi", "Tapas", "Live Music", "Destination"),
    },
}

#: Small curated aliases so free-text mood words can hit tag names directly.
EXTRA_MOOD_TAGS = {
    "jazz": "Jazz",
    "hip-hop": "Hip-Hop",
    "hiphop": "Hip-Hop",
    "rap": "Hip-Hop",
    "electronic": "Electronic",
    "techno": "Electronic",
    "house": "Electronic",
    "ambient": "Ambient",
    "indie": "Indie",
    "rock": "Indie Rock",
    "folk": "Folk",
    "classical": "Classical",
    "soul": "Soul",
    "r&b": "R&B",
    "afrobeat": "Afrobeat",
    "punk": "Punk",
    "sci-fi": "Sci-Fi",
    "scifi": "Sci-Fi",
    "horror": "Horror",
    "noir": "Noir",
    "documentary": "Documentary",
    "romance": "Romance",
    "comedy": "Comedy",
    "thriller": "Thriller",
    "italian": "Italian",
    "japanese": "Japanese",
    "ramen": "Ramen",
    "tapas": "Tapas",
    "mexican": "Mexican",
    "indian": "Indian",
    "vegetarian": "Vegetarian",
    "seafood": "Seafood",
    "wine": "Wine Bar",
    "cocktails": "Cocktail Bar",
    "cafe": "Cafe",
    "coffee": "Cafe",
    "books": "Bookstore",
    "bookstore": "Bookstore",
    "gallery": "Gallery",
    "art": "Gallery",
    "cinema": "Cinema",
    "live music": "Live Music",
}


class InvalidRequest(ValueError):
    """Raised for user input the agent can't plan with."""


def validate_request(raw):
    """Normalise and sanity-check the JSON payload from the UI/CLI."""
    if not isinstance(raw, dict):
        raise InvalidRequest("Request body must be a JSON object.")
    city = _clean(raw.get("city"), 80) or "New York"
    mood = _clean(raw.get("mood"), 220)
    loves = raw.get("loves") or []
    if isinstance(loves, str):
        loves = re.split(r"[,\n]+", loves)
    if not isinstance(loves, (list, tuple)):
        raise InvalidRequest("`loves` must be a list of strings.")
    cleaned_loves = []
    for love in loves:
        value = _clean(love, 80)
        if value and value not in cleaned_loves:
            cleaned_loves.append(value)
    cleaned_loves = cleaned_loves[:MAX_LOVES]
    if not mood and not cleaned_loves:
        raise InvalidRequest("Give PALATE a mood or at least one thing you love.")
    return {"city": city, "mood": mood, "loves": cleaned_loves}


def _clean(value, limit):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def _trace_event(trace, phase, title, detail, data=None):
    event = {
        "step": len(trace) + 1,
        "phase": phase,
        "title": title,
        "detail": detail,
    }
    if data:
        event["data"] = data
    trace.append(event)
    return event


class Concierge:
    """The agent. One instance = one reasoning run (cheap; holds no user data)."""

    def __init__(self, client, max_revisions=MAX_REVISIONS):
        self.client = client
        self.max_revisions = int(max_revisions)
        self.trace = []
        self._qloo_calls = 0
        self._revisions = 0
        self._qloo_errors = []

    # -- public entry point -------------------------------------------------
    def run(self, raw_request):
        started = time.time()
        request = validate_request(raw_request)
        self.trace = []
        self._qloo_calls = 0
        self._revisions = 0
        self._qloo_errors = []

        plan = self._plan(request)
        needs = self._resolve_signals(request, plan)
        picks = []
        for slot in plan["slots"]:
            picks.append(self._fill_slot(request, plan, needs, slot))
        itinerary = self._assemble(request, plan, picks)
        summary = self._summarise(request, plan, picks, itinerary)
        meta = self._meta(started)
        return {
            "app": APP_NAME,
            "version": __version__,
            "mode": getattr(self.client, "mode", "unknown"),
            "request": request,
            "plan": plan,
            "needs": needs,
            "trace": self.trace,
            "itinerary": itinerary,
            "summary": summary,
            "meta": meta,
        }

    # -- 1. PLAN ------------------------------------------------------------
    def _plan(self, request):
        mood_tags = _mood_tag_names(request["mood"])
        threads = _mood_families(request["mood"])
        plan = {
            "intent": _intent_sentence(request),
            "slots": [
                {
                    "key": slot["key"],
                    "label": slot["label"],
                    "time": slot["time"],
                    "filter_type": slot["filter_type"],
                    "cue": slot["cue"],
                    "use_location": slot["use_location"],
                }
                for slot in SLOTS
            ],
            "mood_tags": mood_tags,
            "mood_threads": threads,
            "signal_strategy": "entity seeds from your loves + tag signals from your mood",
        }
        _trace_event(
            self.trace,
            "plan",
            "Read the room",
            "Parsed intent: %s I mapped the mood to %d tag signals and will use %d reference%s as Qloo entity signals."
            % (
                _intent_sentence(request),
                len(mood_tags),
                len(request["loves"]),
                "" if len(request["loves"]) == 1 else "s",
            ),
            {
                "intent": plan["intent"],
                "slots": [slot["key"] for slot in plan["slots"]],
                "mood_tags": mood_tags,
                "mood_threads": threads,
                "loves": request["loves"],
            },
        )
        return plan

    # -- 2. RESOLVE ---------------------------------------------------------
    def _resolve_signals(self, request, plan):
        seeds = []
        unresolved = []
        for love in request["loves"]:
            try:
                hits = self.client.search(love, types=list(SEARCH_SEED_TYPES), take=3)
                self._qloo_calls += 1
            except QlooError as exc:
                self._qloo_errors.append(str(exc))
                _trace_event(self.trace, "resolve", "Search failed", "/search hit an error for %r: %s" % (love, exc), {"query": love})
                unresolved.append({"love": love, "reason": str(exc)})
                continue
            hit = _pick_seed(hits)
            if not hit:
                unresolved.append({"love": love, "reason": "no Qloo entity matched"})
                _trace_event(
                    self.trace,
                    "resolve",
                    "No match for “%s”" % love,
                    "Qloo had no entity close enough; PALATE will lean on your mood tags for this thread.",
                    {"query": love},
                )
                continue
            seeds.append(
                {
                    "love": love,
                    "entity_id": hit.get("entity_id", ""),
                    "name": hit.get("name", love),
                    "subtype": hit.get("subtype", ""),
                    "tags": [tag.get("id") for tag in hit.get("tags", []) if tag.get("id")],
                    "tag_names": [tag.get("name") for tag in hit.get("tags", []) if tag.get("name")],
                }
            )
            _trace_event(
                self.trace,
                "resolve",
                "Anchored “%s”" % love,
                "/search resolved your reference to %s (%s, id %s)."
                % (hit.get("name"), hit.get("subtype", "entity").rsplit(":", 1)[-1], hit.get("entity_id", "")[:18] or "n/a"),
                {
                    "query": love,
                    "matched": {"entity_id": hit.get("entity_id"), "name": hit.get("name"), "subtype": hit.get("subtype")},
                    "tags": [tag.get("name") for tag in hit.get("tags", []) if tag.get("name")][:8],
                    "qloo_request": self._last_request(),
                },
            )

        mood_tag_ids = []
        mood_tag_labels = []
        for name in plan["mood_tags"]:
            try:
                hits = self.client.search_tags(name, take=2)
                self._qloo_calls += 1
            except QlooError as exc:
                self._qloo_errors.append(str(exc))
                _trace_event(self.trace, "resolve", "Tag lookup skipped", "Qloo /v2/tags errored on %r: %s" % (name, exc), {"query": name})
                continue
            for hit in hits[:1]:
                if hit.get("id") and hit["id"] not in mood_tag_ids:
                    mood_tag_ids.append(hit["id"])
                    mood_tag_labels.append(hit.get("name") or name)
        _trace_event(
            self.trace,
            "resolve",
            "Built the taste signal set",
            "%d entity anchor%s + %d tag signal%s are feeding the Qloo insights calls."
            % (
                len(seeds),
                "" if len(seeds) == 1 else "s",
                len(mood_tag_ids),
                "" if len(mood_tag_ids) == 1 else "s",
            ),
            {
                "seed_entities": [seed["name"] for seed in seeds],
                "mood_tags": mood_tag_labels,
                "unresolved": [item["love"] for item in unresolved],
            },
        )
        needs = {
            "seeds": seeds,
            "mood_tag_ids": mood_tag_ids,
            "mood_tags": mood_tag_labels,
            "unresolved": unresolved,
        }
        return needs

    # -- 3./4. QUERY + CRITIQUE (+ REVISE) ----------------------------------
    def _fill_slot(self, request, plan, needs, slot):
        attempt = 0
        best = None
        while True:
            attempt += 1
            needs_snapshot = _copy_needs(needs)
            query = _build_query(request, plan, needs, slot, attempt)
            try:
                candidates = self.client.insights(
                    filter_type=slot["filter_type"],
                    signal_entities=query["signal_entities"],
                    signal_tags=query["signal_tags"],
                    location=query["location"],
                    take=TAKE_PER_SLOT,
                )
                self._qloo_calls += 1
                error = None
            except QlooError as exc:
                candidates = []
                error = str(exc)
                self._qloo_errors.append(error)

            fresh = _slot_candidates(_fresh_candidates(candidates, needs["seeds"]), slot)
            critique = self._critique(slot, fresh, needs, query, error)

            _trace_event(
                self.trace,
                "query",
                "%s insights for %s" % (slot["filter_type"].rsplit(":", 1)[-1].title(), slot["label"].lower()),
                "Queried the taste source for %d %s%s. Returned %d candidate%s%s."
                % (
                    TAKE_PER_SLOT,
                    slot["filter_type"].rsplit(":", 1)[-1].replace("_", " ") + "s",
                    " near %s" % request["city"] if query["location"] else "",
                    len(candidates),
                    "" if len(candidates) == 1 else "s",
                    " (error: %s)" % error if error else "",
                ),
                {
                    "qloo_request": _redacted_request(self.client, slot["filter_type"], query),
                    "returned": len(candidates),
                    "top": [c.get("name") for c in candidates[:3]],
                    "error": error,
                },
            )
            _trace_event(
                self.trace,
                "critique",
                "Critiqued the %s shortlist" % slot["label"].lower(),
                critique["headline"],
                {
                    "verdict": critique["verdict"],
                    "confidence": critique["confidence"],
                    "notes": critique["notes"],
                    "signals": critique["signals"],
                },
            )

            if best is None or _better(critique, best["critique"]):
                best = {
                    "candidates": fresh,
                    "critique": critique,
                    "query": query,
                    "error": error,
                    "needs": needs_snapshot,
                }

            if critique["verdict"] != "weak" or attempt > self.max_revisions:
                break

            revision = _revision_plan(attempt, slot, query, needs, fresh, error)
            self._revisions += 1
            _trace_event(
                self.trace,
                "revise",
                "Self-correcting: %s" % revision["label"],
                revision["detail"],
                {"attempt": attempt + 1, "change": revision["change"]},
            )
            needs = self._apply_revision(needs, revision, slot)

        pick = _choose(best["candidates"])
        return {
            "slot": slot,
            "candidates": best["candidates"],
            "pick": pick,
            "critique": best["critique"],
            "query": best["query"],
            "needs": best["needs"],
            "revisions": max(0, attempt - 1),
        }

    def _critique(self, slot, fresh, needs, query, error):
        notes = []
        signals = {
            "candidates": len(fresh),
            "has_entity_signals": bool(query["signal_entities"]),
            "has_tag_signals": bool(query["signal_tags"]),
            "has_location": bool(query["location"]),
        }
        if error:
            notes.append("Qloo returned an error: %s" % error)
        if not fresh:
            notes.append("No usable candidates — the signal set was too narrow.")
            return {
                "verdict": "weak",
                "confidence": "low",
                "headline": "Too thin to recommend from — I'll widen the net and ask Qloo again.",
                "notes": notes,
                "signals": signals,
            }

        profile_tags = _profile_tag_ids(needs)
        evidence_hits = 0
        for candidate in fresh[:3]:
            if _candidate_evidence(candidate, profile_tags):
                evidence_hits += 1
        popularity = [c.get("popularity") or 0 for c in fresh[:5]]
        mainstream = bool(popularity) and all(p >= 0.88 for p in popularity)
        if mainstream:
            notes.append("Results skew mainstream (all above 0.88 popularity) — a safe-but-obvious night.")
        if evidence_hits:
            notes.append("%d of the top 3 share a traceable tag thread with your profile." % evidence_hits)
        else:
            notes.append("Qloo ranked these on learned affinity rather than shared tags; confidence is correspondingly lower.")
        if len(fresh) >= 3:
            notes.append("Shortlist is deep enough to choose from without padding.")

        if evidence_hits >= 2 or (evidence_hits >= 1 and len(fresh) >= 3):
            verdict, confidence = "ok", "high"
        elif evidence_hits >= 1 or len(fresh) >= 3:
            verdict, confidence = "ok", "medium"
        else:
            verdict, confidence = "ok", "low"
        return {
            "verdict": verdict,
            "confidence": confidence,
            "headline": "Shortlist is usable — %d candidates, %d with a visible taste thread."
            % (len(fresh), evidence_hits),
            "notes": notes,
            "signals": signals,
        }

    def _apply_revision(self, needs, revision, slot):
        revised = {
            "seeds": list(needs["seeds"]),
            "mood_tag_ids": list(needs["mood_tag_ids"]),
            "mood_tags": list(needs["mood_tags"]),
            "unresolved": list(needs["unresolved"]),
        }
        change = revision["change"]
        if change == "drop_location":
            revised["skip_location_slots"] = revised.get("skip_location_slots", []) + [slot["key"]]
        elif change == "drop_weakest_seed" and revised["seeds"]:
            revised["seeds"] = revised["seeds"][:-1]
        elif change == "tags_only":
            revised["seeds"] = []
        elif change == "drop_half_tags" and revised["mood_tag_ids"]:
            revised["mood_tag_ids"] = revised["mood_tag_ids"][: max(1, len(revised["mood_tag_ids"]) // 2)]
        _trace_event(
            self.trace,
            "revise",
            "Revised signal set",
            "New signal mix: %d entity anchor(s), %d tag(s), location %s."
            % (
                len(revised["seeds"]),
                len(revised["mood_tag_ids"]),
                "off for this slot" if slot["key"] in revised.get("skip_location_slots", []) else "on",
            ),
            {"change": change},
        )
        return revised

    # -- 5. RECOMMEND -------------------------------------------------------
    def _assemble(self, request, plan, picks):
        itinerary = []
        used = set()
        for pick in picks:
            slot = pick["slot"]
            candidate = pick["pick"]
            confidence = pick["critique"]["confidence"]
            if not candidate:
                itinerary.append(
                    {
                        "slot": slot["key"],
                        "label": slot["label"],
                        "time": slot["time"],
                        "entity": None,
                        "confidence": "none",
                        "why": "No Qloo candidate cleared the bar for this slot — better to leave the evening open than pad it with a weak pick.",
                        "evidence": {"qloo_request": _redacted_request(self.client, slot["filter_type"], pick["query"])},
                    }
                )
                continue
            # Avoid recommending the same entity in two slots.
            if candidate.get("entity_id") in used:
                runner_up = next((c for c in pick["candidates"] if c.get("entity_id") not in used), None)
                candidate = runner_up
            if not candidate:
                continue
            used.add(candidate.get("entity_id"))
            itinerary.append(
                {
                    "slot": slot["key"],
                    "label": slot["label"],
                    "time": slot["time"],
                    "entity": _public_entity(candidate),
                    "confidence": confidence,
                    "why": _rationale(slot, candidate, pick, request),
                    "evidence": _evidence(candidate, pick),
                }
            )
        _trace_event(
            self.trace,
            "recommend",
            "Assembled the night",
            "Locked %d of %d slots with a coherent through-line: %s."
            % (
                len([item for item in itinerary if item["entity"]]),
                len(plan["slots"]),
                ", ".join(item["label"].lower() for item in itinerary if item["entity"]),
            ),
            {
                "slots": [
                    {
                        "slot": item["slot"],
                        "pick": (item["entity"] or {}).get("name"),
                        "confidence": item["confidence"],
                    }
                    for item in itinerary
                ]
            },
        )
        return itinerary

    def _summarise(self, request, plan, picks, itinerary):
        filled = [item for item in itinerary if item["entity"]]
        threads = []
        seen = set()
        for item in filled:
            for name in item["evidence"].get("matched_tags", []):
                if "←" in name or "→" in name:
                    continue  # bridge evidence, surfaced on the stop itself
                if name.lower() not in seen:
                    seen.add(name.lower())
                    threads.append(name)
        for family in plan["mood_threads"]:
            label = family.replace("-", " ").title()
            if label.lower() not in seen:
                seen.add(label.lower())
                threads.append(label)
        confidence_rank = {"high": 2, "medium": 1, "low": 0, "none": 0}
        avg_conf = (
            sum(confidence_rank.get(item["confidence"], 0) for item in filled) / float(len(filled))
            if filled else 0.0
        )
        return {
            "headline": "A %s night in %s, in four moves." % (request["mood"] or "taste-led", request["city"]),
            "taste_threads": threads[:6],
            "confidence": ["low", "medium", "high"][int(round(avg_conf))],
            "slots_filled": len(filled),
            "slots_total": len(plan["slots"]),
            "revisions": self._revisions,
            "qloo_calls": self._qloo_calls,
        }

    def _meta(self, started):
        now = datetime.datetime.now(datetime.timezone.utc)
        return {
            "generated_at": now.isoformat(timespec="seconds"),
            "duration_ms": int((time.time() - started) * 1000),
            "qloo_errors": len(self._qloo_errors),
            "qloo_error_sample": self._qloo_errors[0] if self._qloo_errors else None,
            "mode": getattr(self.client, "mode", "unknown"),
            "data_source": (
                "live Qloo API"
                if getattr(self.client, "mode", "") == MODE_LIVE
                else "simulated taste graph (offline fixture — not Qloo data)"
            ),
            "base_url": getattr(self.client, "base_url", ""),
        }

    # -- helpers ------------------------------------------------------------
    def _last_request(self):
        request = getattr(self.client, "last_request", None)
        return dict(request) if isinstance(request, dict) else None


# ---------------------------------------------------------------------------
# Pure helpers (kept module-level so they are unit-testable without a client)
# ---------------------------------------------------------------------------
def _intent_sentence(request):
    mood = request["mood"] or "taste-led"
    city = request["city"]
    if request["loves"]:
        return "Plan a %s evening in %s built around %s." % (mood, city, ", ".join(request["loves"][:3]))
    return "Plan a %s evening in %s with no fixed references — mood only." % (mood, city)


def _mood_families(mood):
    lowered = mood.lower()
    families = []
    for family, profile in MOOD_PROFILES.items():
        if any(keyword in lowered for keyword in profile["keywords"]):
            families.append(family)
    return families


def _mood_tag_names(mood):
    lowered = mood.lower()
    names = []
    for family in _mood_families(mood):
        for tag in MOOD_PROFILES[family]["tags"]:
            if tag not in names:
                names.append(tag)
    for phrase, tag in EXTRA_MOOD_TAGS.items():
        if phrase in lowered and tag not in names:
            names.append(tag)
    if not names:
        names = ["Cozy", "Live Music", "Cafe"]
    return names[:8]


def _pick_seed(hits):
    """Take the client's best match; /search already ranks by match quality."""
    return hits[0] if hits else None


def _profile_tag_ids(needs):
    tag_ids = set(needs["mood_tag_ids"])
    for seed in needs["seeds"]:
        tag_ids.update(seed.get("tags") or [])
    return tag_ids


#: When Qloo returns venue-type metadata (``properties.kind``), respect what
#: the slot is for: a cafe is not dinner, a diner is not a gallery.
_SLOT_KINDS = {
    "dinner": ("restaurant", "wine_bar", "diner", "seafood", "tapas"),
    "nightcap": ("cocktail_bar", "wine_bar", "cafe", "diner", "live_music_venue", "bookstore"),
}


def _slot_candidates(candidates, slot):
    allowed = _SLOT_KINDS.get(slot["key"])
    if not allowed:
        return candidates
    typed = [c for c in candidates if (c.get("properties") or {}).get("kind")]
    if len(typed) < 2:
        return candidates  # live API rows may not expose venue kinds
    filtered = [c for c in typed if c["properties"]["kind"] in allowed]
    return filtered if filtered else candidates


def _fresh_candidates(candidates, seeds):
    seed_ids = {seed["entity_id"] for seed in seeds if seed.get("entity_id")}
    return [c for c in candidates if c.get("entity_id") not in seed_ids]


def _candidate_evidence(candidate, profile_tag_ids):
    """Return matched tag names for a candidate, mock fixture or live payload."""
    matched = []
    for tag in candidate.get("tags") or []:
        if tag.get("id") in profile_tag_ids and tag.get("name"):
            matched.append(tag["name"])
    evidence = candidate.get("evidence") or {}
    for name in evidence.get("matched_seed_tags") or []:
        tag = _lookup_tag_name(candidate, name)
        if tag and tag not in matched:
            matched.append(tag)
    for name in evidence.get("matched_mood_tags") or []:
        tag = _lookup_tag_name(candidate, name)
        if tag and tag not in matched:
            matched.append(tag)
    for bridge in evidence.get("bridges") or []:
        label = bridge.get("label") if isinstance(bridge, dict) else None
        if label and label not in matched:
            matched.append(label)
    if not matched and candidate.get("explainability"):
        matched.append("Qloo explainability")
    return matched


def _lookup_tag_name(candidate, tag_id):
    for tag in candidate.get("tags") or []:
        if tag.get("id") == tag_id:
            return tag.get("name") or tag_id.rsplit(":", 1)[-1].replace("_", " ").title()
    if isinstance(tag_id, str) and ":" in tag_id:
        return tag_id.rsplit(":", 1)[-1].replace("_", " ").title()
    return tag_id


def _copy_needs(needs):
    return {
        "seeds": [dict(seed) for seed in needs.get("seeds", [])],
        "mood_tag_ids": list(needs.get("mood_tag_ids", [])),
        "mood_tags": list(needs.get("mood_tags", [])),
        "unresolved": list(needs.get("unresolved", [])),
        "skip_location_slots": list(needs.get("skip_location_slots", [])),
    }


def _build_query(request, plan, needs, slot, attempt):
    signal_entities = [seed["entity_id"] for seed in needs["seeds"] if seed.get("entity_id")][:6]
    signal_tags = list(needs["mood_tag_ids"])[:8]
    location = None
    if slot["use_location"] and slot["key"] not in needs.get("skip_location_slots", []):
        location = request["city"]
    if attempt > 2 and signal_entities:
        signal_entities = signal_entities[:2]
    return {
        "signal_entities": signal_entities,
        "signal_tags": signal_tags,
        "location": location,
    }


def _revision_plan(attempt, slot, query, needs, fresh, error):
    if query["location"] and not fresh:
        return {
            "change": "drop_location",
            "label": "widening the search area",
            "detail": "Nothing convincing in the requested city for this slot. Dropping the location signal and re-querying so distance doesn't hide a better match.",
        }
    if len(needs["seeds"]) > 1:
        return {
            "change": "drop_weakest_seed",
            "label": "rebalancing your references",
            "detail": "One reference is pulling the %s shortlist off-course. Dropping the last anchor and letting the rest of your profile speak."
            % slot["label"].lower(),
        }
    if needs["seeds"] and needs["mood_tag_ids"]:
        return {
            "change": "tags_only",
            "label": "switching to mood-only signals",
            "detail": "Your references alone left this slot thin; re-querying on tag signals so the mood still grounds the pick.",
        }
    return {
        "change": "drop_half_tags",
        "label": "loosening the mood filter",
        "detail": "The signal set is over-constrained. Trimming the tag signals and asking Qloo again for a broader pool.",
    }


def _better(critique, current):
    rank = {"high": 3, "medium": 2, "low": 1}
    return rank.get(critique["confidence"], 0) > rank.get(current["confidence"], 0)


def _choose(candidates):
    return candidates[0] if candidates else None


def _public_entity(candidate):
    return {
        "entity_id": candidate.get("entity_id", ""),
        "name": candidate.get("name", ""),
        "subtype": candidate.get("subtype", ""),
        "tags": [tag.get("name") for tag in candidate.get("tags", []) if tag.get("name")][:8],
        "popularity": candidate.get("popularity"),
        "properties": _public_properties(candidate.get("properties") or {}),
    }


def _public_properties(properties):
    keep = ("city", "neighborhood", "price_level", "kind", "release_year", "scene", "era")
    return {key: properties[key] for key in keep if key in properties}


def _rationale(slot, candidate, pick, request):
    matched = _evidence(candidate, pick)["matched_tags"]
    name = candidate.get("name", "this pick")
    props = candidate.get("properties") or {}
    where = props.get("neighborhood") or props.get("city")
    genre_names = [tag.get("name") for tag in candidate.get("tags", []) if tag.get("name")][:3]
    parts = []
    if slot["key"] == "dinner":
        parts.append("Start the night at %s%s." % (name, " in %s" % where if where else ""))
    elif slot["key"] == "nightcap":
        parts.append("End at %s%s." % (name, " \u2014 %s" % where if where else ""))
    elif slot["key"] == "film":
        parts.append("Queue up %s." % name)
    else:
        parts.append("Put %s on the walk-home playlist." % name)
    if matched:
        parts.append("It shares a taste thread with you: %s." % ", ".join(matched[:3]))
    elif genre_names:
        parts.append("The taste source ranked it highest for your combined signals (%s)." % ", ".join(genre_names))
    else:
        parts.append("The taste source ranked it highest for your combined signals.")
    if pick["critique"]["confidence"] != "high":
        parts.append("Confidence is %s \u2014 a slightly bigger leap, flagged honestly." % pick["critique"]["confidence"])
    return " ".join(parts)


def _evidence(candidate, pick):
    needs = pick.get("needs") or {"mood_tag_ids": [], "seeds": []}
    profile_tag_ids = _profile_tag_ids(needs)
    return {
        "matched_tags": _candidate_evidence(candidate, profile_tag_ids),
        "matched_seeds": [seed["name"] for seed in needs.get("seeds", [])],
        "mood_tags": list(needs.get("mood_tags") or []),
        "candidate_count": len(pick["candidates"]),
        "confidence": pick["critique"]["confidence"],
        "qloo_request": _redacted_request(None, pick["slot"]["filter_type"], pick["query"]),
        "qloo_returned": [c.get("name") for c in pick["candidates"][:3]],
        "explainability": candidate.get("explainability"),
        "affinity": candidate.get("mock_affinity"),
    }


def _redacted_request(client, filter_type, query):
    return {
        "path": "/v2/insights",
        "filter.type": filter_type,
        "signal.interests.entities": ",".join(query["signal_entities"]) if query["signal_entities"] else None,
        "signal.interests.tags": ",".join(query["signal_tags"]) if query["signal_tags"] else None,
        "signal.location.query": query["location"],
        "feature.explainability": "true",
    }

