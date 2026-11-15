"""Tests for CMS branch-preview media naming and orphan purge selection."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import sync_cms
import sync_media
import xibo_layout


class PreviewMediaNamingTests(unittest.TestCase):
    def test_preview_library_name_is_prefixed(self) -> None:
        asset = {"id": "hero-still"}
        self.assertEqual(
            sync_media.library_name_for("otters", asset, preview=True),
            "preview-otters-hero-still",
        )
        self.assertEqual(
            sync_media.library_name_for("otters", asset, preview=False),
            "otters-hero-still",
        )

    def test_preview_folder_segments(self) -> None:
        self.assertEqual(
            sync_media.library_folder_segments("otters", preview=True),
            ["exhibits-preview", "otters"],
        )
        self.assertEqual(
            sync_media.library_folder_segments("otters", preview=False),
            ["exhibits", "otters"],
        )

    def test_preview_tags_include_preview_marker(self) -> None:
        digest = "a" * 64
        tags = sync_media.library_tags("otters", [], digest, preview=True)
        self.assertIn("exhibit:otters", tags)
        self.assertIn("mmek:managed", tags)
        self.assertIn(sync_media.PREVIEW_TAG, tags)
        prod = sync_media.library_tags("otters", [], digest, preview=False)
        self.assertNotIn(sync_media.PREVIEW_TAG, prod)


class OrphanPreviewMediaTests(unittest.TestCase):
    def test_selects_ids_not_in_keep_set(self) -> None:
        tagged = [
            {"mediaId": 10, "name": "keep"},
            {"mediaId": 11, "name": "orphan"},
            {"id": 12, "name": "also-orphan"},
            {"name": "missing-id"},
        ]
        orphans = sync_media.orphan_preview_media_ids(tagged, {10})
        self.assertEqual(orphans, [11, 12])

    def test_empty_keep_marks_all_as_orphans(self) -> None:
        tagged = [{"mediaId": 1}, {"mediaId": 2}]
        self.assertEqual(
            sync_media.orphan_preview_media_ids(tagged, set()),
            [1, 2],
        )


class SyncOnePreviewTests(unittest.TestCase):
    def test_preview_path_uses_preview_layout_and_purges_orphans(self) -> None:
        client = MagicMock()
        client.list_media_by_tag.return_value = [
            {"mediaId": 100},
            {"mediaId": 200},
            {"mediaId": 300},
        ]

        with (
            patch.object(sync_cms, "validate_exhibit"),
            patch(
                "sync_media.sync_exhibit_media",
                return_value={
                    "media_ids": {"hero": 100, "copy": 200},
                    "uploaded": 0,
                    "reused": 2,
                },
            ) as mock_media,
            patch(
                "xibo_layout.upsert_exhibit_layout",
                return_value={"layout_name": xibo_layout.PREVIEW_LAYOUT_NAME},
            ) as mock_layout,
        ):
            result = sync_cms.sync_one(
                "otters", client=client, dry_run=False, preview=True
            )

        mock_media.assert_called_once()
        self.assertTrue(mock_media.call_args.kwargs["preview"])
        mock_layout.assert_called_once()
        self.assertEqual(
            mock_layout.call_args.kwargs["layout_name"],
            xibo_layout.PREVIEW_LAYOUT_NAME,
        )
        self.assertEqual(
            mock_layout.call_args.kwargs["extra_tags"],
            [sync_media.PREVIEW_TAG],
        )
        client.delete_media.assert_called_once_with(300)
        self.assertEqual(result["purged_media_ids"], [300])
        self.assertEqual(result["layout"]["layout_name"], "mmek-preview")

    def test_production_path_does_not_purge_or_use_preview_layout(self) -> None:
        client = MagicMock()
        with (
            patch.object(sync_cms, "validate_exhibit"),
            patch(
                "sync_media.sync_exhibit_media",
                return_value={"media_ids": {"hero": 1}},
            ) as mock_media,
            patch(
                "xibo_layout.upsert_exhibit_layout",
                return_value={"layout_name": "mmek-otters"},
            ) as mock_layout,
        ):
            result = sync_cms.sync_one(
                "otters", client=client, dry_run=False, preview=False
            )

        self.assertFalse(mock_media.call_args.kwargs.get("preview", False))
        self.assertNotIn("layout_name", mock_layout.call_args.kwargs)
        client.list_media_by_tag.assert_not_called()
        client.delete_media.assert_not_called()
        self.assertEqual(result["purged_media_ids"], [])


if __name__ == "__main__":
    unittest.main()
