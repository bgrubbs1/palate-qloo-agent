"""Unit tests for the bundled synthetic taste graph."""

import unittest

from palate.mock_graph import MockTasteGraph, load_mock_graph


class MockGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = load_mock_graph()

    def test_fixture_loads(self):
        self.assertGreater(len(self.graph.entities), 40)
        self.assertGreater(len(self.graph.tags), 40)
        subtypes = {entity["subtype"] for entity in self.graph.entities}
        for required in ("urn:entity:artist", "urn:entity:movie", "urn:entity:place"):
            self.assertIn(required, subtypes)

    def test_search_resolves_known_entities(self):
        hits = self.graph.search("Kamasi Washington", types=["urn:entity:artist"], take=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["name"], "Kamasi Washington")
        self.assertIn("urn:entity:artist", hits[0]["subtype"])
        self.assertTrue(hits[0]["tags"])
        self.assertIn("id", hits[0]["tags"][0])

    def test_search_resolves_place_and_movie(self):
        movie = self.graph.search("Everything Everywhere All at Once", take=3)
        self.assertEqual(movie[0]["name"], "Everything Everywhere All at Once")
        place = self.graph.search("Ramen Tsubaki", take=3)
        self.assertEqual(place[0]["name"], "Ramen Tsubaki")

    def test_search_unknown_returns_empty(self):
        self.assertEqual(self.graph.search("zzzzzz not a real entity"), [])

    def test_search_does_not_match_single_letters(self):
        # Guards against the "at" in "animation" style false positives.
        hits = self.graph.search("Everything Everywhere All at Once", types=["urn:entity:movie"], take=3)
        self.assertEqual(hits[0]["name"], "Everything Everywhere All at Once")

    def test_search_tags_finds_aliases(self):
        hits = self.graph.search_tags("wine bar", take=3)
        self.assertTrue(any(hit["name"] == "Wine Bar" for hit in hits))
        jazz = self.graph.search_tags("jazz", take=2)
        self.assertTrue(any(hit["name"] == "Jazz" for hit in jazz))

    def test_insights_filters_entity_type(self):
        seed = self.graph.search("Kamasi Washington")[0]
        results = self.graph.insights("urn:entity:movie", signal_entity_ids=[seed["entity_id"]], take=5)
        self.assertTrue(results)
        self.assertTrue(all(row["subtype"] == "urn:entity:movie" for row in results))
        self.assertTrue(all(row["mock_affinity"] > 0 for row in results))

    def test_insights_never_echoes_seed(self):
        seed = self.graph.search("Kamasi Washington")[0]
        results = self.graph.insights("urn:entity:artist", signal_entity_ids=[seed["entity_id"]], take=8)
        self.assertNotIn(seed["entity_id"], [row["entity_id"] for row in results])

    def test_insights_respects_location_for_places(self):
        results = self.graph.insights(
            "urn:entity:place", signal_tag_ids=["urn:tag:cuisine:ramen"], location="Los Angeles", take=8
        )
        self.assertTrue(results)
        for row in results:
            self.assertEqual(row["properties"].get("city"), "Los Angeles")

    def test_insights_unknown_location_relaxes_but_labels_it(self):
        results = self.graph.insights(
            "urn:entity:place", signal_tag_ids=["urn:tag:venue:winebar"], location="Atlantis", take=5
        )
        self.assertTrue(results)
        self.assertTrue(any(row["evidence"].get("location_relaxed") for row in results))

    def test_insights_exposes_bridge_evidence(self):
        seed = self.graph.search("Kamasi Washington")[0]
        results = self.graph.insights(
            "urn:entity:movie",
            signal_entity_ids=[seed["entity_id"]],
            signal_tag_ids=["urn:tag:mood:weird"],
            take=8,
        )
        self.assertTrue(results)
        self.assertTrue(any(row["evidence"]["bridges"] for row in results))

    def test_affinity_model_is_deterministic(self):
        seed = self.graph.search("Kamasi Washington")[0]
        first = self.graph.insights("urn:entity:movie", signal_entity_ids=[seed["entity_id"]], take=5)
        second = self.graph.insights("urn:entity:movie", signal_entity_ids=[seed["entity_id"]], take=5)
        self.assertEqual([row["entity_id"] for row in first], [row["entity_id"] for row in second])

    def test_subtype_filter_on_custom_graph(self):
        payload = {
            "meta": {"name": "tiny"},
            "tags": [{"id": "urn:tag:mood:cozy", "name": "Cozy"}],
            "entities": [
                {"entity_id": "a", "name": "A", "subtype": "urn:entity:movie", "tags": ["urn:tag:mood:cozy"], "popularity": 0.5},
                {"entity_id": "b", "name": "B", "subtype": "urn:entity:artist", "tags": ["urn:tag:mood:cozy"], "popularity": 0.5},
            ],
        }
        graph = MockTasteGraph(payload)
        rows = graph.insights("urn:entity:artist", signal_tag_ids=["urn:tag:mood:cozy"])
        self.assertEqual([row["entity_id"] for row in rows], ["b"])


if __name__ == "__main__":
    unittest.main()
