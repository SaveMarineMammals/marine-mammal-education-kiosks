"""Regression checks for Xibo library edit payloads."""

from __future__ import annotations

import os
import unittest
from unittest import mock
from unittest.mock import MagicMock, patch

import xibo_client


class ResolveBaseUrlTests(unittest.TestCase):
    def test_loopback_http_uses_tls_host_when_set(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"XIBO_CMS_TLS_HOST": "cms.example.test"},
            clear=False,
        ):
            resolved = xibo_client.resolve_cms_base_url("http://127.0.0.1:8080")
        self.assertEqual(resolved, "https://cms.example.test")

    def test_loopback_http_unchanged_without_tls_host(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            resolved = xibo_client.resolve_cms_base_url("http://127.0.0.1:8080")
        self.assertEqual(resolved, "http://127.0.0.1:8080")

    def test_rewrite_loopback_https_redirect(self) -> None:
        out = xibo_client._rewrite_loopback_https(
            "https://127.0.0.1/api/authorize/access_token"
        )
        self.assertTrue(out.startswith("https://server.kiosks.local"))
        self.assertIn("/api/authorize/access_token", out)


class RedirectRequestTests(unittest.TestCase):
    def test_follows_redirect_with_rewritten_loopback_target(self) -> None:
        client = xibo_client.XiboClient("http://127.0.0.1:8080")
        redirect = MagicMock()
        redirect.status_code = 302
        redirect.headers = {
            "Location": "https://127.0.0.1/api/authorize/access_token",
        }
        redirect.content = b'{"access_token":"tok"}'
        redirect.headers_get = redirect.headers.get

        ok = MagicMock()
        ok.status_code = 200
        ok.content = redirect.content
        ok.headers = {"Content-Type": "application/json"}
        ok.text = '{"access_token":"tok"}'
        ok.json.return_value = {"access_token": "tok"}

        with patch.object(
            client.session, "request", side_effect=[redirect, ok]
        ) as mock_request:
            payload = client.request("POST", "/api/authorize/access_token")

        self.assertEqual(payload, {"access_token": "tok"})
        self.assertEqual(mock_request.call_count, 2)
        second_url = mock_request.call_args_list[1][0][1]
        self.assertIn("server.kiosks.local", second_url)


class EditMediaTests(unittest.TestCase):
    def test_edit_sends_existing_duration_and_retired(self) -> None:
        client = xibo_client.XiboClient("http://cms.example")
        calls: list[tuple[str, str, dict]] = []

        def fake_request(method: str, path: str, **kwargs):
            calls.append((method, path, kwargs))
            if method == "GET":
                return [
                    {
                        "mediaId": 3,
                        "name": "red-mangrove-graphic-mangrove-id",
                        "duration": 10,
                        "retired": 0,
                        "enableStat": "Inherit",
                    }
                ]
            return {"mediaId": 3}

        with patch.object(client, "request", side_effect=fake_request):
            client.edit_media(
                3,
                name="red-mangrove-graphic-mangrove-id",
                tags=["exhibit:red-mangrove", "mmek:managed"],
            )

        self.assertEqual(calls[0][0], "GET")
        put = calls[1]
        self.assertEqual(put[0], "PUT")
        self.assertEqual(put[1], "/api/library/3")
        body = put[2]["data"]
        self.assertEqual(body["duration"], 10)
        self.assertEqual(body["retired"], 0)
        self.assertEqual(body["enableStat"], "Inherit")
        self.assertEqual(body["name"], "red-mangrove-graphic-mangrove-id")
        self.assertIn("exhibit:red-mangrove", body["tags"])

    def test_edit_uses_duration_default_when_lookup_fails(self) -> None:
        client = xibo_client.XiboClient("http://cms.example")

        puts: list[dict] = []

        def fake_request(method: str, path: str, **kwargs):
            if method == "GET":
                raise xibo_client.XiboError("lookup failed")
            puts.append(kwargs["data"])
            return {"mediaId": 3}

        with patch.object(client, "request", side_effect=fake_request):
            client.edit_media(3, name="still", tags=["mmek:managed"])

        self.assertEqual(puts[-1]["duration"], 10)
        self.assertEqual(puts[-1]["retired"], 0)


if __name__ == "__main__":
    unittest.main()
