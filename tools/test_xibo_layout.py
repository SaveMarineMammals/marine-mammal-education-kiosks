"""Tests for Glance & Match layout hold + playlist fill behavior."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

import xibo_layout


class LayoutHoldSecondsTests(unittest.TestCase):
    def test_glance_loop_defaults_to_hour_hold(self) -> None:
        hold = xibo_layout.layout_hold_seconds(
            {"template": "glance-and-match", "durationSeconds": 24, "loop": True}
        )
        self.assertEqual(hold, 3600)

    def test_explicit_hold_wins(self) -> None:
        hold = xibo_layout.layout_hold_seconds(
            {
                "template": "glance-and-match",
                "durationSeconds": 24,
                "loop": True,
                "layoutHoldSeconds": 7200,
            }
        )
        self.assertEqual(hold, 7200)

    def test_layered_stills_uses_cycle(self) -> None:
        hold = xibo_layout.layout_hold_seconds(
            {"template": "layered-stills-loop", "durationSeconds": 90}
        )
        self.assertEqual(hold, 90)


class FillPlaylistTests(unittest.TestCase):
    def test_single_widget_stretched_to_hold(self) -> None:
        client = MagicMock()
        client.add_text_widget.return_value = 1
        widgets = [
            {
                "type": "text",
                "startSeconds": 0,
                "durationSeconds": 24,
                "effect": "tickerScroll",
                "copy": "Protect mangroves",
            }
        ]
        xibo_layout.fill_playlist_from_widgets(
            client, 9, widgets, media_ids={}, layout_duration=3600
        )
        client.add_text_widget.assert_called_once_with(
            9, "Protect mangroves", 3600, effect="tickerScroll"
        )
        client.add_spacer_widget.assert_not_called()

    def test_multi_widget_skips_trailing_spacer(self) -> None:
        client = MagicMock()
        client.assign_media_to_playlist.return_value = None
        widgets = [
            {
                "type": "image",
                "asset": "a",
                "startSeconds": 0,
                "durationSeconds": 6,
            },
            {
                "type": "image",
                "asset": "b",
                "startSeconds": 6,
                "durationSeconds": 6,
            },
        ]
        xibo_layout.fill_playlist_from_widgets(
            client,
            9,
            widgets,
            media_ids={"a": 1, "b": 2},
            layout_duration=3600,
        )
        self.assertEqual(client.assign_media_to_playlist.call_count, 2)
        client.add_spacer_widget.assert_not_called()


class PreviewLayoutNamingTests(unittest.TestCase):
    def test_preview_layout_is_stable_slot_not_per_slug(self) -> None:
        self.assertEqual(xibo_layout.preview_layout_name(), "mmek-preview")
        self.assertEqual(xibo_layout.PREVIEW_LAYOUT_NAME, "mmek-preview")
        self.assertNotEqual(
            xibo_layout.preview_layout_name(),
            xibo_layout.stable_layout_name("asian-small-clawed-otters"),
        )

    def test_stable_production_name_unchanged(self) -> None:
        self.assertEqual(
            xibo_layout.stable_layout_name("red-mangrove"),
            "mmek-red-mangrove",
        )

    def test_preview_dry_run_uses_preview_layout_name(self) -> None:
        result = xibo_layout.upsert_exhibit_layout(
            None,
            exhibit_slug="asian-small-clawed-otters",
            layout_name=xibo_layout.PREVIEW_LAYOUT_NAME,
            extra_tags=[xibo_layout.PREVIEW_TAG],
            dry_run=True,
        )
        self.assertEqual(result["layout_name"], "mmek-preview")
        self.assertNotEqual(result["layout_name"], "mmek-asian-small-clawed-otters")


if __name__ == "__main__":
    unittest.main()
