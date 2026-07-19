# Runbook: publish an exhibit

1. Complete [`framework/standards/content-checklist.md`](../../framework/standards/content-checklist.md).
2. Run **Tier 1** locally (same as the required `Exhibit contract` check):

   ```powershell
   python -m pip install -r tools/requirements.txt
   python tools/validate_exhibits.py --exhibit <slug>
   python tools/catalog.py --check
   ```

3. Run **Tier 2** timeline preview for the slug (non-black still + regions):

   ```powershell
   python -m pip install -r ops/qa/requirements.txt
   python -m playwright install chromium
   python ops/qa/ci_timeline_preview.py --exhibit <slug>
   ```

4. Run **Tier 3** live player capture before flipping to `published` (local Docker
   or GitHub Actions → **QA player capture** / PR label `qa-player`):

   ```powershell
   cd ops\qa
   copy config.env.example config.env
   python run_qa_pipeline.py -v --exhibit <slug>
   ```

   Review `ops/qa/artifacts/` stills/video. Treat a black frame or empty `regions`
   as a publish blocker even though this job is not a required merge check yet.
5. Set `exhibit.yaml` `status` to `review`, then `published` after sign-off.
6. Sync media to Xibo Library ([media-sync.md](../cms/media-sync.md)).
7. Confirm layouts/playlists in CMS use the Library items for this slug.
8. Schedule campaigns onto the intended **display groups** from `schedule/intent.yaml`.
9. Spot-check on at least one physical Pi.
10. Update `exhibits/_catalog.yaml` status/version to match (`python tools/catalog.py --write`
    after editing `exhibit.yaml`, or edit the catalog by hand).
