"""Regression checks for Xibo library edit payloads."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import xibo_client


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
