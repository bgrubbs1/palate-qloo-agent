"""Qloo API access layer.

Two interchangeable clients implement the same three-method interface:

    search(query, types, take)            -> [entity, ...]
    search_tags(query, take)              -> [{"id", "name"}, ...]
    insights(filter_type, signal_entities, signal_tags, location, take) -> [entity, ...]

* ``LiveQlooClient`` speaks the real documented Qloo contract (verified against
  https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide on
  2026-10-27): GET requests, ``X-Api-Key`` header, hackathon base URL
  ``https://hackathon.api.qloo.com``.
* ``MockQlooClient`` simulates the same surface over a small synthetic taste
  graph so the app, tests and demo work with no API key and no network.

Entity dicts normalised by both clients::

    {
      "entity_id": str,
      "name": str,
      "type": "urn:entity",
      "subtype": "urn:entity:place",
      "tags": [{"id": str, "name": str}, ...],
      "popularity": float,
      "properties": dict,
      "description": str,
      # optional, live only:
      "explainability": dict,
    }
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .mock_graph import MockTasteGraph, load_mock_graph

DEFAULT_BASE_URL = "https://hackathon.api.qloo.com"
DEFAULT_TIMEOUT = 15.0

#: Entity types accepted by ``GET /v2/insights`` as ``filter.type``.
#: Verified from the Qloo hackathon developer guide (2026-10-27).
SUPPORTED_INSIGHT_TYPES = (
    "urn:entity:artist",
    "urn:entity:book",
    "urn:entity:brand",
    "urn:entity:destination",
    "urn:entity:movie",
    "urn:entity:person",
    "urn:entity:place",
    "urn:entity:podcast",
    "urn:entity:tv_show",
    "urn:entity:video_game",
)

#: Types we use as ``/search`` seeds (search accepts a wider set than insights).
SEARCH_SEED_TYPES = (
    "urn:entity:artist",
    "urn:entity:movie",
    "urn:entity:book",
    "urn:entity:tv_show",
    "urn:entity:place",
)

MODE_AUTO = "auto"
MODE_MOCK = "mock"
MODE_LIVE = "live"
VALID_MODES = (MODE_AUTO, MODE_MOCK, MODE_LIVE)


class QlooError(Exception):
    """Base class for all Qloo access failures."""


class QlooConfigError(QlooError):
    """Live mode requested without a usable API key / base URL."""


class QlooAuthError(QlooError):
    """HTTP 401/403 — bad key, wrong environment, or unsupported entity type."""


class QlooRateLimitError(QlooError):
    """HTTP 429 — the hackathon key quota was exceeded."""


class QlooRequestError(QlooError):
    """Any other HTTP/transport failure."""

    def __init__(self, message, status=None, body=""):
        super().__init__(message)
        self.status = status
        self.body = body


def _env(env):
    return os.environ if env is None else env


def resolve_mode(requested=None, env=None):
    """Decide whether to run live or simulated, and why.

    Precedence: explicit ``requested`` argument > ``PALATE_MODE`` env var >
    auto-detect (live when ``QLOO_API_KEY`` is set, otherwise mock).
    """
    environ = _env(env)
    requested = (requested or "").strip().lower() or None
    env_mode = (environ.get("PALATE_MODE") or "").strip().lower() or None
    mode = requested or env_mode or MODE_AUTO
    if mode not in VALID_MODES:
        raise QlooConfigError(
            "Unknown mode %r. Use one of: auto, mock, live." % mode
        )
    has_key = bool((environ.get("QLOO_API_KEY") or "").strip())
    if mode == MODE_AUTO:
        if has_key:
            return MODE_LIVE, "QLOO_API_KEY is set"
        return MODE_MOCK, "no QLOO_API_KEY — running on the simulated taste graph"
    if mode == MODE_LIVE and not has_key:
        raise QlooConfigError(
            "Live mode requested but QLOO_API_KEY is not set. Request a key at "
            "https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide"
            "#getting-your-api-key then export QLOO_API_KEY=... "
            "(or run mock mode with PALATE_MODE=mock)."
        )
    return mode, "explicitly selected"


class LiveQlooClient:
    """Real Qloo API client. Never runs during tests (transport is injectable)."""

    mode = MODE_LIVE

    def __init__(self, api_key, base_url=None, timeout=DEFAULT_TIMEOUT, transport=None):
        api_key = (api_key or "").strip()
        if not api_key:
            raise QlooConfigError(
                "LiveQlooClient needs an API key. Set QLOO_API_KEY."
            )
        self.api_key = api_key
        self.base_url = (base_url or os.environ.get("QLOO_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = float(timeout)
        self.last_request = None
        self.last_status = None
        self._transport = transport or self._default_transport

    # -- public interface ---------------------------------------------------
    def search(self, query, types=None, take=5):
        params = {"query": query, "take": int(take)}
        if types:
            params["types"] = ",".join(types)
        payload = self._get("/search", params)
        return [self._normalize_entity(e) for e in self._entities(payload)]

    def search_tags(self, query, take=3):
        params = {"filter.query": query, "take": int(take)}
        payload = self._get("/v2/tags", params)
        results = payload.get("results") if isinstance(payload, dict) else None
        rows = []
        for bucket in (results or {}).values() if isinstance(results, dict) else []:
            if isinstance(bucket, list):
                rows.extend(bucket)
        if not rows:
            rows = self._entities(payload) or payload.get("tags") or []
        tags = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            tag_id = row.get("tag_id") or row.get("id")
            name = row.get("name") or row.get("tag") or ""
            if tag_id:
                tags.append({"id": tag_id, "name": name, "_raw": row})
        return tags[:take]

    def insights(
        self,
        filter_type,
        signal_entities=None,
        signal_tags=None,
        location=None,
        take=8,
        explainability=True,
        extra=None,
    ):
        if filter_type not in SUPPORTED_INSIGHT_TYPES:
            raise QlooConfigError("Unsupported filter.type for /v2/insights: %r" % (filter_type,))
        params = {"filter.type": filter_type, "take": int(take)}
        if signal_entities:
            params["signal.interests.entities"] = ",".join(signal_entities)
        if signal_tags:
            params["signal.interests.tags"] = ",".join(signal_tags)
        if location:
            # Fuzzy locality match; the API returns 400 for unknown localities,
            # so callers may retry without it.
            params["signal.location.query"] = location
        if explainability:
            params["feature.explainability"] = "true"
        if extra:
            for key, value in extra.items():
                if value is not None and value != "":
                    params[key] = value
        payload = self._get("/v2/insights", params)
        return [self._normalize_entity(e) for e in self._entities(payload)]

    # -- HTTP ---------------------------------------------------------------
    def _default_transport(self, url, headers, timeout):
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = response.getcode()
                body = response.read().decode("utf-8", "replace")
                return status, body
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", "replace")
        except urllib.error.URLError as exc:
            raise QlooRequestError("Network error calling Qloo: %s" % (exc.reason,)) from exc
        except Exception as exc:  # noqa: BLE001 - transport guard
            raise QlooRequestError("Unexpected transport error calling Qloo: %s" % (exc,)) from exc

    def _get(self, path, params):
        url = "%s%s?%s" % (self.base_url, path, urllib.parse.urlencode(params, doseq=True))
        headers = {
            "X-Api-Key": self.api_key,
            "Accept": "application/json",
            "User-Agent": "palate/1.0 (+https://github.com/)",
        }
        self.last_request = {"method": "GET", "path": path, "params": _redact(params)}
        status, body = self._transport(url, headers, self.timeout)
        self.last_status = status
        return self._handle_response(status, body, path)

    def _handle_response(self, status, body, path):
        if status in (401, 403):
            hint = ""
            if "hackathon.api.qloo.com" not in self.base_url:
                hint = (
                    " Hackathon keys only work against "
                    "https://hackathon.api.qloo.com — check QLOO_BASE_URL."
                )
            raise QlooAuthError(
                "Qloo returned HTTP %s for %s.%s %s"
                % (status, path, hint, body[:300])
            )
        if status == 429:
            raise QlooRateLimitError(
                "Qloo rate/quota limit hit (HTTP 429). Retry later or ask in the "
                "hackathon Discord #api-help for headroom."
            )
        if status >= 500:
            raise QlooRequestError("Qloo server error HTTP %s for %s" % (status, path), status=status, body=body[:300])
        if status >= 400:
            raise QlooRequestError(
                "Qloo rejected the request (HTTP %s) for %s: %s" % (status, path, body[:300]),
                status=status,
                body=body[:300],
            )
        try:
            payload = json.loads(body)
        except ValueError as exc:
            raise QlooRequestError(
                "Qloo returned non-JSON (HTTP %s) for %s: %s" % (status, path, body[:200])
            ) from exc
        if isinstance(payload, dict) and payload.get("success") is False:
            raise QlooRequestError("Qloo reported success=false for %s" % (path,))
        return payload

    # -- normalisation ------------------------------------------------------
    @staticmethod
    def _entities(payload):
        """Pull ``results.entities`` out of an Insights/Search response."""
        if not isinstance(payload, dict):
            return []
        results = payload.get("results")
        if isinstance(results, dict):
            entities = results.get("entities")
            if isinstance(entities, list):
                return entities
        entities = payload.get("entities")
        return entities if isinstance(entities, list) else []

    def _normalize_entity(self, raw):
        if not isinstance(raw, dict):
            return None
        tags = []
        for tag in raw.get("tags") or []:
            if isinstance(tag, dict) and tag.get("id"):
                tags.append({"id": tag["id"], "name": tag.get("name") or ""})
        entity = {
            "entity_id": raw.get("entity_id") or raw.get("id") or "",
            "name": raw.get("name") or raw.get("title") or "",
            "type": raw.get("type") or "urn:entity",
            "subtype": raw.get("subtype") or raw.get("type") or "",
            "tags": tags,
            "popularity": _safe_float(raw.get("popularity"), 0.5),
            "properties": raw.get("properties") or {},
            "description": (raw.get("properties") or {}).get("description") or "",
        }
        explainability = _extract_explainability(raw)
        if explainability:
            entity["explainability"] = explainability
        return entity


class MockQlooClient:
    """Offline client over the synthetic taste graph shipped in this repo."""

    mode = MODE_MOCK

    def __init__(self, graph=None):
        self.graph = graph if graph is not None else load_mock_graph()
        if not isinstance(self.graph, MockTasteGraph):
            raise QlooConfigError("MockQlooClient expects a MockTasteGraph")
        self.base_url = "mock://taste-graph"
        self.last_request = None
        self.last_status = 200

    def search(self, query, types=None, take=5):
        self.last_request = {"method": "GET", "path": "/search", "params": _redact({"query": query, "types": types, "take": take})}
        return self.graph.search(query, types=types, take=take)

    def search_tags(self, query, take=3):
        self.last_request = {"method": "GET", "path": "/v2/tags", "params": _redact({"filter.query": query, "take": take})}
        return self.graph.search_tags(query, take=take)

    def insights(
        self,
        filter_type,
        signal_entities=None,
        signal_tags=None,
        location=None,
        take=8,
        explainability=True,
        extra=None,
    ):
        self.last_request = {
            "method": "GET",
            "path": "/v2/insights",
            "params": _redact(
                {
                    "filter.type": filter_type,
                    "signal.interests.entities": signal_entities,
                    "signal.interests.tags": signal_tags,
                    "signal.location.query": location,
                    "take": take,
                }
            ),
        }
        return self.graph.insights(
            filter_type,
            signal_entity_ids=signal_entities or [],
            signal_tag_ids=signal_tags or [],
            location=location,
            take=take,
        )


def create_client(mode=None, env=None, transport=None):
    """Build a client for the resolved mode. Returns ``(client, info)``."""
    resolved, reason = resolve_mode(mode, env=env)
    environ = _env(env)
    if resolved == MODE_LIVE:
        client = LiveQlooClient(
            environ.get("QLOO_API_KEY"),
            base_url=environ.get("QLOO_BASE_URL"),
            timeout=float(environ.get("QLOO_TIMEOUT") or DEFAULT_TIMEOUT),
            transport=transport,
        )
    else:
        client = MockQlooClient()
    info = {
        "requested": mode or environ.get("PALATE_MODE") or MODE_AUTO,
        "resolved": resolved,
        "reason": reason,
        "base_url": client.base_url,
    }
    return client, info


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_explainability(raw):
    """Keep the documented explainability payload when present (shape tolerant)."""
    query = raw.get("query")
    if not isinstance(query, dict):
        return None
    explain = query.get("explainability")
    return explain if isinstance(explain, dict) else None


def _redact(params):
    """Metadata only — never include keys or full query payloads in traces."""
    cleaned = {}
    for key, value in params.items():
        if value is None or value == "":
            continue
        if isinstance(value, (list, tuple)):
            cleaned[key] = ",".join(str(v) for v in value)
        else:
            cleaned[key] = value
    return cleaned


__all__ = [
    "DEFAULT_BASE_URL",
    "MODE_AUTO",
    "MODE_LIVE",
    "MODE_MOCK",
    "SUPPORTED_INSIGHT_TYPES",
    "SEARCH_SEED_TYPES",
    "LiveQlooClient",
    "MockQlooClient",
    "QlooAuthError",
    "QlooConfigError",
    "QlooError",
    "QlooRateLimitError",
    "QlooRequestError",
    "create_client",
    "resolve_mode",
]
