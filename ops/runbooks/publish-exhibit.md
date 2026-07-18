# Runbook: publish an exhibit

1. Complete [`framework/standards/content-checklist.md`](../../framework/standards/content-checklist.md).
2. Set `exhibit.yaml` `status` to `review`, then `published` after sign-off.
3. Sync media to Xibo Library ([media-sync.md](../cms/media-sync.md)).
4. Confirm layouts/playlists in CMS use the Library items for this slug.
5. Schedule campaigns onto the intended **display groups** from `schedule/intent.yaml`.
6. Spot-check on at least one physical Pi.
7. Update `exhibits/_catalog.yaml` status/version to match.
