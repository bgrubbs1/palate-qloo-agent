"""Tests for the Qloo API contract layer (live client uses a fake transport)."""

import json
import os
import unittest
import urllib.parse

from palate.qloo import (
    DEFAULT_BASE_URL,
    LiveQlooClient,
    QlooAuthError,
    QlooConfigError,
    QlooRateLimitError,
    QlooRequestError,
    create_client,
    resolve_mode,
)


class FakeTransport:
    """Captures requests and replays canned responses."""

    def __init__(self, status=200, body=None, error=None):
        self.status = status
        self.body = body
        self.error = error
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        if self.error:
            raise self.error
        return self.status, self.body if isinstance(self.body, str) else json.dumps(self.body)


INSIGHTS_PAYLOAD = {
    "success": True,
    "results": {
        "entities": [
            {
                "name": "Past Lives",
                "entity_id": "UUID-1",
                "type": "urn:entity",
                "subtype": "urn:entity:movie",
                "properties": {"release_year": 2023, "description": "Quiet romance."},
                "popularity": 0.75,
                "tags": [{"id": "urn:tag:media:drama", "name": "Drama", "type": "urn:tag:media"}],
                "query": {"explainability": {"contribution": 0.42}},
            }
        ]
    },
}

SEARCH_PAYLOAD = {
    "results": [
            {
                "name": "Kamasi Washington",
                "entity_id": "UUID-2",
                "types": ["urn:entity:artist"],
                "properties": {"short_description": "Jazz saxophonist."},
                "tags": [{"tag_id": "urn:tag:music:jazz", "name": "Jazz"}],
            }
    ],
}

TAGS_PAYLOAD = {
    "success": True,
    "results": {"tags": [{"id": "urn:tag:mood:cozy", "name": "Cozy", "type": "urn:tag:mood"}]},
}


class LiveClientTests(unittest.TestCase):
    def make_client(self, transport):
        return LiveQlooClient("test-key", base_url="https://hackathon.api.qloo.com", transport=transport)

    def test_insights_request_matches_documented_contract(self):
        transport = FakeTransport(200, INSIGHTS_PAYLOAD)
        client = self.make_client(transport)
        rows = client.insights(
            "urn:entity:movie",
            signal_entities=["UUID-2"],
            signal_tags=["urn:tag:mood:cozy"],
            location="New York",
            take=8,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Past Lives")
        self.assertEqual(rows[0]["subtype"], "urn:entity:movie")
        self.assertEqual(rows[0]["tags"][0]["name"], "Drama")
        self.assertIn("explainability", rows[0])
        call = transport.calls[0]
        self.assertTrue(call["url"].startswith("https://hackathon.api.qloo.com/v2/insights?"))
        parsed = urllib.parse.urlparse(call["url"])
        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(query["filter.type"], ["urn:entity:movie"])
        self.assertEqual(query["signal.interests.entities"], ["UUID-2"])
        self.assertEqual(query["signal.interests.tags"], ["urn:tag:mood:cozy"])
        self.assertEqual(query["signal.location.query"], ["New York"])
        self.assertEqual(query["feature.explainability"], ["true"])
        self.assertEqual(query["take"], ["8"])
        self.assertEqual(call["headers"]["X-Api-Key"], "test-key")

    def test_search_request_uses_search_path_and_types(self):
        transport = FakeTransport(200, SEARCH_PAYLOAD)
        client = self.make_client(transport)
        rows = client.search("Kamasi Washington", types=["urn:entity:artist", "urn:entity:movie"], take=3)
        self.assertEqual(rows[0]["entity_id"], "UUID-2")
        self.assertEqual(rows[0]["subtype"], "urn:entity:artist")
        self.assertEqual(rows[0]["tags"], [{"id": "urn:tag:music:jazz", "name": "Jazz"}])
        self.assertEqual(rows[0]["description"], "Jazz saxophonist.")
        parsed = urllib.parse.urlparse(transport.calls[0]["url"])
        self.assertEqual(parsed.path, "/search")
        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(query["query"], ["Kamasi Washington"])
        self.assertEqual(query["types"], ["urn:entity:artist,urn:entity:movie"])

    def test_search_tags_parses_tag_buckets(self):
        transport = FakeTransport(200, TAGS_PAYLOAD)
        client = self.make_client(transport)
        tags = client.search_tags("cozy", take=2)
        self.assertEqual(tags[0]["id"], "urn:tag:mood:cozy")
        self.assertEqual(transport.calls[0]["url"].split("?")[0], "https://hackathon.api.qloo.com/v2/tags")

    def test_auth_error_is_actionable_and_mentions_environment(self):
        client = LiveQlooClient("bad", base_url="https://api.qloo.com", transport=FakeTransport(401, "{}"))
        with self.assertRaises(QlooAuthError) as caught:
            client.insights("urn:entity:movie")
        self.assertIn("hackathon.api.qloo.com", str(caught.exception))

    def test_rate_limit_error(self):
        client = self.make_client(FakeTransport(429, "{}"))
        with self.assertRaises(QlooRateLimitError):
            client.search("x")

    def test_bad_request_error(self):
        client = self.make_client(FakeTransport(400, {"error": "unsupported parameter"}))
        with self.assertRaises(QlooRequestError) as caught:
            client.insights("urn:entity:movie")
        self.assertEqual(caught.exception.status, 400)

    def test_non_json_response_is_a_request_error(self):
        client = self.make_client(FakeTransport(200, "<html>gateway</html>"))
        with self.assertRaises(QlooRequestError):
            client.search("x")

    def test_unsupported_insight_type_rejected_before_network(self):
        transport = FakeTransport(200, INSIGHTS_PAYLOAD)
        client = self.make_client(transport)
        with self.assertRaises(QlooConfigError):
            client.insights("urn:entity:food_and_drink")
        self.assertEqual(transport.calls, [])

    def test_empty_results_are_handled(self):
        client = self.make_client(FakeTransport(200, {"success": True, "results": {"entities": []}}))
        self.assertEqual(client.insights("urn:entity:movie"), [])


class ModeTests(unittest.TestCase):
    def test_auto_without_key_is_mock(self):
        mode, reason = resolve_mode(env={"PALATE_MODE": "auto"})
        self.assertEqual(mode, "mock")
        self.assertIn("no QLOO_API_KEY", reason)

    def test_auto_with_key_is_live(self):
        mode, _ = resolve_mode(env={"QLOO_API_KEY": "abc"})
        self.assertEqual(mode, "live")

    def test_live_without_key_raises(self):
        with self.assertRaises(QlooConfigError) as caught:
            resolve_mode("live", env={})
        self.assertIn("QLOO_API_KEY", str(caught.exception))

    def test_explicit_mock_wins_over_key(self):
        mode, _ = resolve_mode("mock", env={"QLOO_API_KEY": "abc"})
        self.assertEqual(mode, "mock")

    def test_env_mode_is_honoured(self):
        mode, _ = resolve_mode(env={"PALATE_MODE": "mock", "QLOO_API_KEY": "abc"})
        self.assertEqual(mode, "mock")

    def test_unknown_mode_rejected(self):
        with self.assertRaises(QlooConfigError):
            resolve_mode("staging", env={})

    def test_create_client_live_uses_base_url_env(self):
        client, info = create_client(env={"QLOO_API_KEY": "abc", "QLOO_BASE_URL": "https://example.test/"})
        self.assertEqual(client.mode, "live")
        self.assertEqual(client.base_url, "https://example.test")
        self.assertEqual(info["resolved"], "live")

    def test_create_client_defaults_to_qloo_hackathon_url(self):
        old = os.environ.pop("QLOO_BASE_URL", None)
        try:
            client, _ = create_client(env={"QLOO_API_KEY": "abc"})
            self.assertEqual(client.base_url, DEFAULT_BASE_URL)
        finally:
            if old is not None:
                os.environ["QLOO_BASE_URL"] = old


if __name__ == "__main__":
    unittest.main()
