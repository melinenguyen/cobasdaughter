import os
import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse, parse_qs

from dashboard.connection_app import app


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "BRAND_PULSE_PASSWORD": "test-password", "BRAND_PULSE_PUBLIC_URL": "https://test.example",
            "TIKTOK_CLIENT_KEY": "test-client", "TIKTOK_CLIENT_SECRET": "private-client-secret",
            "BRAND_PULSE_DATABASE_URL": "postgresql://private-db", "BRAND_PULSE_TOKEN_KEY": "private-key"})
        self.env.start()
        self.addCleanup(self.env.stop)
        app.secret_key = "test-session-key"
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.auth = {"Authorization": "Basic Y29iYTp0ZXN0LXBhc3N3b3Jk"}

    def test_public_and_private_routes(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/setup").status_code, 401)
        response = self.client.get("/setup", headers=self.auth)
        self.assertIn(b"https://test.example/oauth/tiktok/callback", response.data)
        self.assertNotIn(b"private-client-secret", response.data)
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(self.client.get("/run").status_code, 404)

    def test_rejects_missing_state_and_csrf(self):
        self.assertEqual(self.client.get("/oauth/tiktok/callback?code=x&state=bad").status_code, 400)
        self.assertEqual(self.client.post("/connect/tiktok", headers=self.auth).status_code, 400)

    def test_setup_reload_does_not_invalidate_existing_form(self):
        self.client.get("/setup", headers=self.auth, base_url="https://test.example")
        with self.client.session_transaction(base_url="https://test.example") as sess:
            first_token = sess["form_token"]
        self.client.get("/setup", headers=self.auth, base_url="https://test.example")
        response = self.client.post("/connect/tiktok", headers=self.auth,
            data={"csrf": first_token}, base_url="https://test.example")
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.location.startswith("https://www.tiktok.com/v2/auth/authorize/?"))
        self.assertIn("form-action 'self' https://www.tiktok.com", response.headers["Content-Security-Policy"])

    def test_missing_cookie_is_explained_and_invalid_form_keeps_session(self):
        response = self.client.post("/connect/tiktok", headers=self.auth)
        self.assertIn(b"Browser session unavailable", response.data)
        self.client.get("/setup", headers=self.auth, base_url="https://test.example")
        response = self.client.post("/connect/tiktok", headers=self.auth,
            data={"csrf": "wrong"}, base_url="https://test.example")
        self.assertEqual(response.status_code, 400)
        with self.client.session_transaction(base_url="https://test.example") as sess:
            self.assertTrue(sess.get("form_token"))

    @patch("dashboard.connection_app.psycopg.connect")
    @patch("dashboard.connection_app.requests.post")
    def test_authorization_encrypts_and_prevents_replay(self, post, connect):
        self.client.get("/setup", headers=self.auth, base_url="https://test.example")
        with self.client.session_transaction(base_url="https://test.example") as sess:
            csrf = sess["form_token"]
        response = self.client.post("/connect/tiktok", data={"csrf": csrf}, headers=self.auth, base_url="https://test.example")
        state = parse_qs(urlparse(response.location).query)["state"][0]
        post.return_value.json.return_value = {"access_token": "secret-access", "refresh_token": "secret-refresh", "open_id": "owner"}
        response = self.client.get("/oauth/tiktok/callback", query_string={"state": state, "code": "private-code"}, base_url="https://test.example")
        self.assertEqual(response.status_code, 303)
        cursor = connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        saved = cursor.execute.call_args.args[1]
        self.assertNotIn("secret-access", saved[2])
        self.assertNotIn("secret-refresh", saved[2])
        self.assertEqual(self.client.get("/oauth/tiktok/callback", query_string={"state": state, "code": "private-code"}, base_url="https://test.example").status_code, 400)


if __name__ == "__main__":
    unittest.main()
