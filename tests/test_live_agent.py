"""Full agent run against a stubbed *live* transport (no network).

This exercises the same wiring the hosted live demo uses: LiveQlooClient speaking
the real documented HTTP contract, feeding the agent loop end to end.
"""

import json
import unittest
import urllib.parse

from palate.agent import Concierge
from palate.qloo import LiveQlooClient


def _entity(entity_id, name, subtype, tags):
    return {
        "name": name,
        "entity_id": entity_id,
        "type": "urn:entity",
        "subtype": subtype,
        "properties": {"description": "A stubbed live result."},
        "popularity": 0.7,
        "tags": [{"id": tag_id, "name": tag_name} for tag_id, tag_name in tags],
    }


class StubbedQlooTransport:
    """Minimal stand-in for the Qloo hackathon API."""

    def __init__(self):
        self.calls = []

    def __call__(self, url, headers, timeout):
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        self.calls.append({"path": parsed.path, "query": query, "headers": headers})
        if parsed.path == "/search":
            term = (query.get("query") or [""])[0]
            return 200, json.dumps(
                {
                    "success": True,
                    "results": {
                        "entities": [
                            _entity("LIVE-ARTIST-1", "Kamasi Washington", "urn:entity:artist", [("urn:tag:music:jazz", "Jazz")]),
                        ]
                    },
                }
            )
        if parsed.path == "/v2/tags":
            return 200, json.dumps({"success": True, "results": {"tags": [{"id": "urn:tag:mood:cozy", "name": "Cozy"}]}})
        if parsed.path == "/v2/insights":
            filter_type = (query.get("filter.type") or [""])[0]
            subtype = filter_type
            name_by_type = {
                "urn:entity:place": "Live Wine Bar",
                "urn:entity:movie": "Live Film",
                "urn:entity:artist": "Live Artist",
            }
            base = name_by_type.get(subtype, "Live Entity")
            entities = [
                _entity(
                    "LIVE-INSIGHT-%s-1" % subtype.rsplit(":", 1)[-1].upper(),
                    base,
                    subtype,
                    [("urn:tag:mood:cozy", "Cozy")],
                ),
                _entity(
                    "LIVE-INSIGHT-%s-2" % subtype.rsplit(":", 1)[-1].upper(),
                    base + " II",
                    subtype,
                    [("urn:tag:mood:cozy", "Cozy")],
                ),
            ]
            return 200, json.dumps({"success": True, "results": {"entities": entities}})
        return 404, "{}"


class LiveAgentWiringTests(unittest.TestCase):
    def test_agent_runs_end_to_end_against_live_contract(self):
        transport = StubbedQlooTransport()
        client = LiveQlooClient("test-key", base_url="https://hackathon.api.qloo.com", transport=transport)
        result = Concierge(client).run(
            {"city": "New York", "mood": "cozy", "loves": ["Kamasi Washington"]}
        )

        self.assertEqual(result["mode"], "live")
        self.assertIn("live Qloo API", result["meta"]["data_source"])
        self.assertEqual(result["summary"]["slots_filled"], 4)
        self.assertEqual(len(result["itinerary"]), 4)
        self.assertTrue(all(item["entity"] for item in result["itinerary"]))
        self.assertEqual(result["meta"]["qloo_errors"], 0)

        paths = [call["path"] for call in transport.calls]
        self.assertIn("/search", paths)
        self.assertIn("/v2/tags", paths)
        self.assertEqual(paths.count("/v2/insights"), 4)
        for call in transport.calls:
            self.assertEqual(call["headers"]["X-Api-Key"], "test-key")
            self.assertNotIn("api_key", call["query"])  # key never in the URL
            self.assertNotIn("key", call["query"])
        insight_calls = [call for call in transport.calls if call["path"] == "/v2/insights"]
        for call in insight_calls:
            self.assertIn("filter.type", call["query"])
            self.assertIn("signal.interests.entities", call["query"])
            self.assertEqual(call["query"]["feature.explainability"], ["true"])

    def test_live_agent_reflects_real_entity_names(self):
        transport = StubbedQlooTransport()
        client = LiveQlooClient("test-key", base_url="https://hackathon.api.qloo.com", transport=transport)
        result = Concierge(client).run({"city": "New York", "mood": "cozy", "loves": ["Kamasi Washington"]})
        names = [item["entity"]["name"] for item in result["itinerary"]]
        self.assertIn("Live Wine Bar", names)
        self.assertIn("Live Film", names)
        self.assertIn("Live Artist", names)


if __name__ == "__main__":
    unittest.main()
