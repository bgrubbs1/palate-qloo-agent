"""A small, deterministic *simulated* taste graph used for offline development.

This is NOT Qloo data. It is a synthetic fixture (fictional venue names, real
public cultural titles, invented affinity weights) that lets PALATE's agent
loop, tests and hosted demo run with no API key and no network. The mock
client implements the same three calls as the live client and computes
recommendations with a transparent tag-affinity model, so the agent's
behaviour changes meaningfully with the user's taste profile.

Cross-domain affinity is modelled with a curated ``taste_bridges`` table
(e.g. jazz <-> noir, ambient <-> gallery). Real Qloo learns such affinities
from billions of signals; here they are hand-authored so the demo is
deterministic and inspectable.
"""

from __future__ import annotations

import json
import math
import os

DEFAULT_FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "taste_graph.json")

_WEIGHTS = {
    "entity_similarity": 0.55,
    "tag_similarity": 0.35,
    "location_bonus": 0.22,
    "popularity": 0.05,
}

#: Cross-domain taste bridges: (tag id, tag id) -> strength 0..1.
#: Hand-authored for the simulated graph. Symmetric.
_BRIDGE_PAIRS = [
    # music <-> film/tv
    ("music:jazz", "media:noir", 0.60),
    ("music:jazz", "media:drama", 0.30),
    ("music:jazz", "media:romance", 0.35),
    ("music:soul", "media:romance", 0.40),
    ("music:neosoul", "media:romance", 0.40),
    ("music:rnb", "media:romance", 0.45),
    ("music:indierock", "media:indie", 0.70),
    ("music:indierock", "media:drama", 0.30),
    ("music:indierock", "media:comedy", 0.20),
    ("music:experimental", "media:scifi", 0.60),
    ("music:experimental", "media:horror", 0.35),
    ("music:experimental", "media:indie", 0.40),
    ("music:ambient", "media:scifi", 0.40),
    ("music:ambient", "media:drama", 0.30),
    ("music:electronic", "media:scifi", 0.40),
    ("music:folk", "media:indie", 0.50),
    ("music:folk", "media:documentary", 0.30),
    ("music:classical", "media:drama", 0.25),
    ("music:classical", "media:documentary", 0.20),
    ("music:hiphop", "media:drama", 0.30),
    ("music:hiphop", "media:thriller", 0.25),
    ("music:punk", "media:horror", 0.30),
    ("music:pop", "media:comedy", 0.40),
    ("music:neosoul", "media:indie", 0.30),
    # music <-> moods
    ("music:jazz", "mood:cozy", 0.40),
    ("music:jazz", "mood:romantic", 0.50),
    ("music:soul", "mood:cozy", 0.50),
    ("music:soul", "mood:nostalgic", 0.40),
    ("music:neosoul", "mood:cozy", 0.50),
    ("music:rnb", "mood:romantic", 0.40),
    ("music:electronic", "mood:highenergy", 0.70),
    ("music:electronic", "mood:adventurous", 0.40),
    ("music:hiphop", "mood:highenergy", 0.60),
    ("music:hiphop", "mood:adventurous", 0.30),
    ("music:punk", "mood:highenergy", 0.70),
    ("music:punk", "mood:weird", 0.30),
    ("music:pop", "mood:highenergy", 0.50),
    ("music:pop", "mood:nostalgic", 0.30),
    ("music:afrobeat", "mood:highenergy", 0.60),
    ("music:afrobeat", "mood:adventurous", 0.40),
    ("music:folk", "mood:lowkey", 0.50),
    ("music:folk", "mood:nostalgic", 0.30),
    ("music:ambient", "mood:lowkey", 0.60),
    ("music:ambient", "mood:brainy", 0.30),
    ("music:experimental", "mood:weird", 0.80),
    ("music:classical", "mood:brainy", 0.40),
    ("music:classical", "mood:romantic", 0.30),
    ("music:indierock", "mood:lowkey", 0.30),
    # music <-> venues
    ("music:jazz", "venue:cocktailbar", 0.70),
    ("music:jazz", "venue:winebar", 0.60),
    ("music:jazz", "venue:livemusic", 0.60),
    ("music:soul", "venue:winebar", 0.40),
    ("music:soul", "venue:livemusic", 0.40),
    ("music:ambient", "venue:cafe", 0.50),
    ("music:ambient", "venue:gallery", 0.50),
    ("music:classical", "venue:gallery", 0.40),
    ("music:folk", "venue:cafe", 0.50),
    ("music:folk", "venue:bookstore", 0.60),
    ("music:electronic", "venue:cocktailbar", 0.40),
    ("music:electronic", "venue:livemusic", 0.40),
    ("music:hiphop", "venue:livemusic", 0.40),
    ("music:punk", "venue:livemusic", 0.60),
    ("music:indierock", "venue:livemusic", 0.50),
    ("music:afrobeat", "venue:livemusic", 0.40),
    ("music:neosoul", "venue:winebar", 0.40),
    ("music:rnb", "venue:cocktailbar", 0.30),
    # music <-> cuisine
    ("music:jazz", "cuisine:italian", 0.30),
    ("music:soul", "cuisine:italian", 0.25),
    ("music:afrobeat", "cuisine:indian", 0.20),
    # film/tv <-> venues
    ("media:noir", "venue:cinema", 0.70),
    ("media:indie", "venue:cinema", 0.70),
    ("media:indie", "venue:bookstore", 0.40),
    ("media:indie", "venue:cafe", 0.30),
    ("media:scifi", "venue:cinema", 0.50),
    ("media:drama", "venue:cinema", 0.40),
    ("media:romance", "venue:winebar", 0.50),
    ("media:romance", "venue:cinema", 0.50),
    ("media:comedy", "venue:cinema", 0.40),
    ("media:horror", "venue:cinema", 0.40),
    ("media:documentary", "venue:bookstore", 0.40),
    ("media:documentary", "venue:cafe", 0.30),
    ("media:animation", "venue:cinema", 0.40),
    ("media:fantasy", "venue:gallery", 0.30),
    ("media:noir", "venue:cocktailbar", 0.40),
    # film/tv <-> cuisine
    ("media:romance", "cuisine:italian", 0.40),
    ("media:indie", "cuisine:japanese", 0.25),
    ("media:comedy", "cuisine:mexican", 0.25),
    # film/tv <-> moods
    ("media:experimental", "mood:weird", 0.60),
    ("media:scifi", "mood:weird", 0.40),
    ("media:horror", "mood:weird", 0.50),
    ("media:documentary", "mood:brainy", 0.70),
    ("media:scifi", "mood:brainy", 0.50),
    ("media:romance", "mood:romantic", 0.90),
    ("media:comedy", "mood:highenergy", 0.30),
    ("media:scifi", "mood:adventurous", 0.50),
    ("media:fantasy", "mood:adventurous", 0.50),
    ("media:noir", "mood:nostalgic", 0.30),
    ("media:comedy", "mood:cozy", 0.30),
    ("media:indie", "mood:lowkey", 0.40),
    ("media:drama", "mood:lowkey", 0.40),
    ("media:documentary", "mood:lowkey", 0.30),
    ("media:thriller", "mood:highenergy", 0.30),
    ("media:animation", "mood:highenergy", 0.25),
    # venues <-> moods
    ("venue:winebar", "mood:romantic", 0.60),
    ("venue:winebar", "mood:cozy", 0.60),
    ("venue:cocktailbar", "mood:highenergy", 0.50),
    ("venue:cocktailbar", "mood:nostalgic", 0.40),
    ("venue:cafe", "mood:lowkey", 0.60),
    ("venue:cafe", "mood:brainy", 0.50),
    ("venue:cafe", "mood:cozy", 0.40),
    ("venue:bookstore", "mood:brainy", 0.80),
    ("venue:bookstore", "mood:nostalgic", 0.40),
    ("venue:gallery", "mood:weird", 0.50),
    ("venue:gallery", "mood:brainy", 0.60),
    ("venue:livemusic", "mood:highenergy", 0.60),
    ("venue:cocktailbar", "mood:weird", 0.30),
    ("venue:cafe", "mood:nostalgic", 0.40),
    ("venue:winebar", "mood:lowkey", 0.40),
    # venues <-> cuisine
    ("venue:winebar", "cuisine:italian", 0.50),
    ("venue:winebar", "cuisine:tapas", 0.50),
    ("venue:winebar", "cuisine:seafood", 0.40),
    ("venue:winebar", "cuisine:japanese", 0.30),
    ("venue:cocktailbar", "cuisine:mexican", 0.40),
    ("venue:cocktailbar", "cuisine:indian", 0.30),
    ("venue:cafe", "cuisine:vegetarian", 0.30),
    ("venue:cafe", "cuisine:ramen", 0.20),
    # cuisine <-> moods
    ("cuisine:ramen", "mood:lowkey", 0.70),
    ("cuisine:ramen", "mood:cozy", 0.50),
    ("cuisine:tapas", "mood:highenergy", 0.40),
    ("cuisine:tapas", "mood:romantic", 0.40),
    ("cuisine:italian", "mood:romantic", 0.50),
    ("cuisine:italian", "mood:cozy", 0.50),
    ("cuisine:japanese", "mood:lowkey", 0.60),
    ("cuisine:vegetarian", "mood:lowkey", 0.50),
    ("cuisine:mexican", "mood:highenergy", 0.50),
    ("cuisine:indian", "mood:cozy", 0.40),
    ("cuisine:seafood", "mood:romantic", 0.40),
    # moods <-> moods
    ("mood:cozy", "mood:romantic", 0.60),
    ("mood:cozy", "mood:lowkey", 0.70),
    ("mood:weird", "mood:adventurous", 0.60),
    ("mood:nostalgic", "mood:cozy", 0.40),
    ("mood:highenergy", "mood:adventurous", 0.40),
    ("mood:brainy", "mood:adventurous", 0.30),
    ("mood:lowkey", "mood:brainy", 0.40),
    ("mood:weird", "mood:brainy", 0.30),
    ("mood:romantic", "mood:nostalgic", 0.30),
    ("mood:highenergy", "mood:nostalgic", 0.20),
    ("mood:adventurous", "mood:cozy", 0.20),
    # cuisine <-> cuisine
    ("cuisine:ramen", "cuisine:japanese", 0.50),
    ("cuisine:tapas", "cuisine:italian", 0.30),
    ("cuisine:japanese", "cuisine:seafood", 0.40),
    ("cuisine:italian", "cuisine:seafood", 0.30),
    ("cuisine:vegetarian", "cuisine:italian", 0.30),
    ("cuisine:mexican", "cuisine:tapas", 0.30),
]


def _tag_id(domain_key):
    domain, key = domain_key.split(":", 1)
    return "urn:tag:%s:%s" % (domain, key)


BRIDGES = {}
for _a, _b, _weight in _BRIDGE_PAIRS:
    BRIDGES[frozenset((_tag_id(_a), _tag_id(_b)))] = _weight


class MockTasteGraph:
    """In-memory synthetic affinity engine over the fixture JSON."""

    def __init__(self, payload):
        self.meta = payload.get("meta") or {}
        self.tags = {}
        self.tag_by_name = {}
        self.entities = []
        self.by_id = {}
        for tag in payload.get("tags") or []:
            tag = dict(tag)
            tag.setdefault("aliases", [])
            self.tags[tag["id"]] = tag
            names = [tag.get("name", "")] + list(tag.get("aliases") or [])
            for name in names:
                if name:
                    self.tag_by_name.setdefault(name.strip().lower(), []).append(tag["id"])
        for entity in payload.get("entities") or []:
            entity = dict(entity)
            entity.setdefault("type", "urn:entity")
            entity.setdefault("tags", [])
            entity.setdefault("properties", {})
            entity.setdefault("popularity", 0.5)
            entity.setdefault("description", "")
            self.entities.append(entity)
            self.by_id[entity["entity_id"]] = entity
        for entity in self.entities:
            entity["tag_names"] = [self.tags[t]["name"] for t in entity["tags"] if t in self.tags]

    # -- helpers ------------------------------------------------------------
    def tag_name(self, tag_id):
        tag = self.tags.get(tag_id)
        return tag["name"] if tag else tag_id.rsplit(":", 1)[-1].replace("_", " ").title()

    def tag_names(self, tag_ids, limit=None):
        names = [self.tag_name(t) for t in tag_ids]
        return names[:limit] if limit else names

    def entities_of_type(self, subtype, location=None):
        rows = [e for e in self.entities if e["subtype"] == subtype]
        if not location:
            return rows
        wanted = _normalise(location)
        return [e for e in rows if _city_matches(e, wanted)]

    # -- GET /search --------------------------------------------------------
    def search(self, query, types=None, take=5):
        """Token search over names, tag names and descriptions.

        Mirrors /search's behaviour closely enough for the agent: a hit needs a
        name or tag match, so a stray word in a description cannot "resolve" an
        unrelated entity.
        """
        tokens = set(_tokens(query))
        if not tokens:
            return []
        wanted_types = set(types) if types else None
        scored = []
        for entity in self.entities:
            if wanted_types and entity["subtype"] not in wanted_types:
                continue
            name_tokens = set(_tokens(entity["name"]))
            tag_tokens = set()
            for tag_name in entity.get("tag_names", []):
                tag_tokens.update(_tokens(tag_name.replace("_", " ")))
            desc_tokens = set(_tokens(entity.get("description", "")))
            name_overlap = tokens & name_tokens
            tag_overlap = tokens & tag_tokens
            if not name_overlap and not tag_overlap:
                continue
            desc_overlap = tokens & desc_tokens
            exact = 1.0 if _normalise(entity["name"]) == _normalise(query) else 0.0
            score = (
                exact
                + 1.0 * len(name_overlap)
                + 0.5 * len(tag_overlap)
                + 0.2 * len(desc_overlap)
                + 0.05 * entity.get("popularity", 0.5)
            )
            scored.append((score, entity))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
        return [_search_result(entity, self.tag_name) for _, entity in scored[:take]]

    # -- GET /v2/tags --------------------------------------------------------
    def search_tags(self, query, take=3):
        tokens = _tokens(query)
        scored = []
        for tag in self.tags.values():
            haystack = _normalise(tag.get("name", "") + " " + " ".join(tag.get("aliases") or []))
            overlap = sum(1 for token in tokens if token in haystack)
            if overlap:
                scored.append((overlap, tag))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
        return [{"id": tag["id"], "name": tag["name"]} for _, tag in scored[:take]]

    # -- GET /v2/insights ----------------------------------------------------
    def insights(self, filter_type, signal_entity_ids=None, signal_tag_ids=None, location=None, take=8):
        signal_entities = [self.by_id[eid] for eid in (signal_entity_ids or []) if eid in self.by_id]
        signal_tag_ids = [t for t in (signal_tag_ids or []) if t in self.tags]
        seed_tags = [tag for seed in signal_entities for tag in seed["tags"]]
        profile_tags = list(dict.fromkeys(seed_tags + signal_tag_ids))

        candidates = self.entities_of_type(filter_type, location)
        relaxed = False
        if location and len(candidates) < 2:
            candidates = self.entities_of_type(filter_type)
            relaxed = True

        scored = []
        for entity in candidates:
            if entity["entity_id"] in {seed["entity_id"] for seed in signal_entities}:
                continue  # never echo a seed back as a recommendation
            entity_score = (
                _mean(_affinity(entity["tags"], seed["tags"]) for seed in signal_entities)
                if signal_entities
                else 0.0
            )
            tag_score = _affinity(entity["tags"], signal_tag_ids) if signal_tag_ids else 0.0
            location_score = 1.0 if location and _city_matches(entity, _normalise(location)) else 0.0
            score = (
                _WEIGHTS["entity_similarity"] * entity_score
                + _WEIGHTS["tag_similarity"] * tag_score
                + _WEIGHTS["location_bonus"] * location_score
                + _WEIGHTS["popularity"] * entity.get("popularity", 0.5)
            )
            scored.append((round(score, 4), entity_score, tag_score, entity))
        scored.sort(key=lambda row: (-row[0], row[3]["name"]))

        results = []
        for score, entity_score, tag_score, entity in scored[:take]:
            matched_seed_tags = [t for t in entity["tags"] if t in set(seed_tags)]
            matched_mood_tags = [t for t in entity["tags"] if t in set(signal_tag_ids)]
            bridges = _bridges_between(entity["tags"], profile_tags, self.tags)
            item = dict(entity)
            item["mock_affinity"] = score
            item["tags"] = [{"id": tid, "name": self.tag_name(tid)} for tid in entity["tags"]]
            item["evidence"] = {
                "matched_seed_tags": matched_seed_tags,
                "matched_mood_tags": matched_mood_tags,
                "bridges": bridges,
                "entity_similarity": round(entity_score, 4),
                "tag_similarity": round(tag_score, 4),
            }
            if relaxed:
                item["evidence"]["location_relaxed"] = True
            results.append(item)
        return results


def _search_result(entity, tag_name):
    """Normalise a /search row to the same entity shape as an insights row."""
    item = dict(entity)
    item["tags"] = [{"id": tag_id, "name": tag_name(tag_id)} for tag_id in entity["tags"]]
    return item


def _bridges_between(candidate_tags, profile_tags, tags):
    found = []
    for candidate_tag in candidate_tags:
        for source_tag in profile_tags:
            weight = BRIDGES.get(frozenset((candidate_tag, source_tag)))
            if weight:
                found.append(
                    {
                        "candidate_tag": tags[candidate_tag]["name"] if candidate_tag in tags else candidate_tag,
                        "source_tag": tags[source_tag]["name"] if source_tag in tags else source_tag,
                        "weight": round(weight, 2),
                        "label": "%s ← %s"
                        % (
                            tags[candidate_tag]["name"] if candidate_tag in tags else candidate_tag,
                            tags[source_tag]["name"] if source_tag in tags else source_tag,
                        ),
                    }
                )
    found.sort(key=lambda row: -row["weight"])
    return found[:4]


def load_mock_graph(path=None):
    with open(path or DEFAULT_FIXTURE, "r", encoding="utf-8") as handle:
        return MockTasteGraph(json.load(handle))


# -- small math / matching helpers -----------------------------------------
def _tokens(text):
    if not text:
        return []
    cleaned = "".join(ch.lower() if ch.isalnum() or ch in "& " else " " for ch in str(text))
    return [t for t in cleaned.split() if len(t) > 1]


def _normalise(text):
    return " ".join(_tokens(text))


def _jaccard(a, b):
    a, b = set(a or []), set(b or [])
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def _affinity(tags_a, tags_b):
    """Direct tag overlap plus curated cross-domain bridges, in 0..1."""
    tags_a = list(dict.fromkeys(tags_a or []))
    tags_b = list(dict.fromkeys(tags_b or []))
    if not tags_a or not tags_b:
        return 0.0
    direct = _jaccard(tags_a, tags_b)
    bridge_total = 0.0
    for tag_a in tags_a:
        for tag_b in tags_b:
            bridge_total += BRIDGES.get(frozenset((tag_a, tag_b)), 0.0)
    bridge_norm = min(1.0, bridge_total / math.sqrt(len(tags_a) * len(tags_b)))
    return min(1.0, direct + 0.85 * bridge_norm)


def _mean(values):
    values = list(values)
    if not values:
        return 0.0
    return sum(values) / float(len(values))


def _city_matches(entity, want):
    props = entity.get("properties") or {}
    candidates = {_normalise(props.get("city", ""))}
    candidates.update(_normalise(city) for city in props.get("cities", []) or [])
    candidates.discard("")
    return bool(want) and any(want == city or want in city or city in want for city in candidates)


__all__ = ["MockTasteGraph", "load_mock_graph", "DEFAULT_FIXTURE", "BRIDGES"]
