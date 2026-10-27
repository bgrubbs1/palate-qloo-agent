"""HTTP-level tests for the PALATE server (mock mode, ephemeral port)."""

import json
import threading
import unittest
import urllib.error
import urllib.request

import app as palate_app


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        palate_app.configure("mock")
        palate_app.RATE_BUCKETS.clear()
        cls.server = palate_app.build_server("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def fetch(self, path, method="GET", body=None, headers=None):
        data = None
        request_headers = dict(headers or {})
        if body is not None:
            if isinstance(body, (dict, list)):
                data = json.dumps(body).encode("utf-8")
                request_headers.setdefault("Content-Type", "application/json")
            else:
                data = body if isinstance(body, bytes) else str(body).encode("utf-8")
        request = urllib.request.Request(self.base + path, data=data, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.getcode(), response.read().decode("utf-8"), dict(response.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8"), dict(exc.headers)

    def test_healthz_reports_mock_mode(self):
        status, body, _ = self.fetch("/api/healthz")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "mock")
        self.assertEqual(payload["app"], "PALATE")

    def test_index_page_served(self):
        status, body, headers = self.fetch("/")
        self.assertEqual(status, 200)
        self.assertIn("PALATE", body)
        self.assertIn("text/html", headers.get("Content-Type", ""))

    def test_sample_profiles(self):
        status, body, _ = self.fetch("/api/sample")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertGreaterEqual(len(payload["profiles"]), 2)
        self.assertIn("New York", payload["cities"])

    def test_plan_endpoint_returns_full_agent_run(self):
        status, body, _ = self.fetch(
            "/api/plan",
            method="POST",
            body={
                "city": "New York",
                "mood": "cozy but a little weird",
                "loves": ["Kamasi Washington", "Everything Everywhere All at Once"],
            },
        )
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["mode"], "mock")
        self.assertEqual(len(payload["itinerary"]), 4)
        self.assertTrue(payload["trace"])
        self.assertIn("itinerary", payload)
        self.assertEqual(payload["request"]["city"], "New York")

    def test_plan_rejects_empty_signal(self):
        status, body, _ = self.fetch("/api/plan", method="POST", body={"city": "New York", "mood": "", "loves": []})
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

    def test_plan_rejects_invalid_json(self):
        status, body, _ = self.fetch("/api/plan", method="POST", body="not json at all")
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

    def test_plan_rejects_non_object_json(self):
        status, body, _ = self.fetch("/api/plan", method="POST", body=["nope"])
        self.assertEqual(status, 400)

    def test_unknown_api_route_is_404(self):
        status, _, _ = self.fetch("/api/does-not-exist")
        self.assertEqual(status, 404)

    def test_static_traversal_rejected(self):
        status, _, _ = self.fetch("/static/../app.py")
        self.assertEqual(status, 404)

    def test_plan_rejects_oversized_body(self):
        status, _, _ = self.fetch(
            "/api/plan",
            method="POST",
            body=json.dumps({"mood": "x" * (app_module_max() + 10)}),
        )
        self.assertEqual(status, 400)


def app_module_max():
    return palate_app.MAX_BODY_BYTES


if __name__ == "__main__":
    unittest.main()
