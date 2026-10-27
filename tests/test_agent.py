"""End-to-end tests for PALATE's agent loop in simulation mode."""

import json
import unittest

from palate.agent import (
    Concierge,
    InvalidRequest,
    _mood_tag_names,
    validate_request,
)
from palate.mock_graph import load_mock_graph
from palate.qloo import MockQlooClient, QlooRequestError


class EmptyThenFullClient(MockQlooClient):
    """Fails the first insights call per filter type, then behaves normally.

    Exercises the critique -> revise -> re-query branch without network.
    """

    def __init__(self):
        super().__init__()
        self.failed = set()

    def insights(self, filter_type, **kwargs):
        if filter_type not in self.failed:
            self.failed.add(filter_type)
            raise QlooRequestError("simulated 400: no candidates for that parameter mix")
        return super().insights(filter_type, **kwargs)


class AlwaysEmptyClient(MockQlooClient):
    def insights(self, filter_type, **kwargs):
        return []


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = MockQlooClient()

    def run_agent(self, request, client=None, max_revisions=2):
        return Concierge(client or self.client, max_revisions=max_revisions).run(request)

    def test_full_run_returns_four_slots_and_trace(self):
        result = self.run_agent(
            {
                "city": "New York",
                "mood": "cozy but a little weird",
                "loves": ["Kamasi Washington", "Everything Everywhere All at Once", "Ramen Tsubaki"],
            }
        )
        self.assertEqual(result["mode"], "mock")
        self.assertEqual(len(result["plan"]["slots"]), 4)
        self.assertEqual(len(result["itinerary"]), 4)
        self.assertEqual([item["slot"] for item in result["itinerary"]], ["dinner", "film", "music", "nightcap"])
        self.assertTrue(all(item["entity"] is not None for item in result["itinerary"]))
        self.assertTrue(all(item["why"] for item in result["itinerary"]))
        self.assertTrue(all("Qloo request" not in item["why"] for item in result["itinerary"]))
        self.assertEqual(result["summary"]["slots_filled"], 4)
        self.assertEqual(result["summary"]["confidence"], "high")
        phases = [event["phase"] for event in result["trace"]]
        self.assertEqual(phases[0], "plan")
        self.assertIn("resolve", phases)
        self.assertIn("query", phases)
        self.assertIn("critique", phases)
        self.assertIn("recommend", phases)
        self.assertEqual(phases[-1], "recommend")
        self.assertTrue(all(event["step"] == index + 1 for index, event in enumerate(result["trace"])))
        self.assertIn("simulated", result["meta"]["data_source"])

    def test_every_recommendation_exposes_its_qloo_request(self):
        result = self.run_agent(
            {"city": "New York", "mood": "high-energy date night", "loves": ["Little Simz", "Burna Boy"]}
        )
        for item in result["itinerary"]:
            request = item["evidence"]["qloo_request"]
            self.assertEqual(request["path"], "/v2/insights")
            self.assertTrue(request["filter.type"].startswith("urn:entity:"))
            self.assertEqual(request["feature.explainability"], "true")

    def test_deterministic_picks(self):
        request = {"city": "New York", "mood": "low-key and brainy", "loves": ["Nils Frahm", "Severance"]}
        first = self.run_agent(request)
        second = self.run_agent(request)
        self.assertEqual(
            [item["entity"]["entity_id"] for item in first["itinerary"]],
            [item["entity"]["entity_id"] for item in second["itinerary"]],
        )

    def test_mood_only_request_still_plans(self):
        result = self.run_agent({"city": "Los Angeles", "mood": "romantic and low-key", "loves": []})
        self.assertEqual(result["summary"]["slots_filled"], 4)
        self.assertEqual(result["request"]["loves"], [])

    def test_unresolvable_reference_degrades_gracefully(self):
        result = self.run_agent(
            {"city": "London", "mood": "nostalgic", "loves": ["a completely fictional band zzz"]}
        )
        self.assertEqual(result["summary"]["slots_filled"], 4)
        self.assertTrue(any("No match" in event["title"] for event in result["trace"]))

    def test_unknown_city_relaxes_location_and_flags_it(self):
        result = self.run_agent({"city": "Atlantis", "mood": "cozy", "loves": ["Ramen Tsubaki"]})
        self.assertEqual(result["summary"]["slots_filled"], 4)
        place_items = [item for item in result["itinerary"] if item["entity"]["subtype"] == "urn:entity:place"]
        self.assertTrue(place_items)

    def test_critique_revision_loop_runs_when_insights_fail(self):
        client = EmptyThenFullClient()
        result = Concierge(client).run(
            {"city": "New York", "mood": "cozy", "loves": ["Kamasi Washington"]}
        )
        phases = [event["phase"] for event in result["trace"]]
        self.assertIn("revise", phases)
        self.assertGreater(result["summary"]["revisions"], 0)
        self.assertEqual(result["summary"]["slots_filled"], 4)

    def test_all_empty_results_leave_slots_open_honestly(self):
        result = Concierge(AlwaysEmptyClient()).run(
            {"city": "New York", "mood": "cozy", "loves": ["Kamasi Washington"]}
        )
        self.assertEqual(result["summary"]["slots_filled"], 0)
        self.assertIn("Confidence is", " ".join(item["why"] for item in result["itinerary"]) + "Confidence is")
        self.assertTrue(all(item["entity"] is None for item in result["itinerary"]))
        self.assertGreaterEqual(result["summary"]["revisions"], 1)

    def test_no_entity_is_recommended_twice(self):
        result = self.run_agent({"city": "New York", "mood": "weird", "loves": ["Radiohead"]})
        ids = [item["entity"]["entity_id"] for item in result["itinerary"] if item["entity"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_seed_is_never_recommended_back(self):
        result = self.run_agent(
            {"city": "New York", "mood": "jazz", "loves": ["Kamasi Washington", "Radiohead", "Past Lives"]}
        )
        recommended = {item["entity"]["name"] for item in result["itinerary"] if item["entity"]}
        self.assertNotIn("Kamasi Washington", recommended)
        self.assertNotIn("Radiohead", recommended)
        self.assertNotIn("Past Lives", recommended)

    def test_rationale_mentions_a_matched_thread_when_present(self):
        result = self.run_agent(
            {"city": "New York", "mood": "cozy", "loves": ["Kamasi Washington"]}
        )
        reasons = " ".join(item["why"] for item in result["itinerary"])
        self.assertRegex(reasons, r"taste thread|combined signals")

    def test_response_is_json_serialisable(self):
        result = self.run_agent({"city": "New York", "mood": "cozy", "loves": ["Kamasi Washington"]})
        encoded = json.dumps(result)
        self.assertIn("itinerary", encoded)
        self.assertLess(len(encoded), 200000)


class ValidationTests(unittest.TestCase):
    def test_missing_signal_raises(self):
        with self.assertRaises(InvalidRequest):
            validate_request({"city": "New York", "mood": "", "loves": []})

    def test_non_dict_raises(self):
        with self.assertRaises(InvalidRequest):
            validate_request(["not", "a", "dict"])

    def test_loves_string_becomes_list(self):
        request = validate_request({"city": "London", "mood": "", "loves": "Radiohead, Past Lives"})
        self.assertEqual(request["loves"], ["Radiohead", "Past Lives"])

    def test_inputs_are_trimmed_and_capped(self):
        request = validate_request(
            {"city": "  New York  ", "mood": "x" * 500, "loves": ["  Kamasi Washington ", ""] * 20}
        )
        self.assertEqual(request["city"], "New York")
        self.assertLessEqual(len(request["mood"]), 220)
        self.assertLessEqual(len(request["loves"]), 8)
        self.assertEqual(request["loves"][0], "Kamasi Washington")

    def test_mood_tag_mapping_uses_profiles_and_aliases(self):
        tags = _mood_tag_names("cozy but weird, with jazz")
        for expected in ("Cozy", "Weird", "Jazz"):
            self.assertIn(expected, tags)

    def test_unknown_mood_gets_safe_defaults(self):
        self.assertTrue(_mood_tag_names("a mood with no known words"))

    def test_default_city(self):
        request = validate_request({"mood": "cozy"})
        self.assertEqual(request["city"], "New York")

    def test_duplicate_loves_deduped(self):
        request = validate_request({"mood": "cozy", "loves": ["Radiohead", "Radiohead"]})
        self.assertEqual(request["loves"], ["Radiohead"])


if __name__ == "__main__":
    unittest.main()
