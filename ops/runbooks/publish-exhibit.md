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
6. Merge to `main`. CMS content sync (self-hosted runner + daily timer) uploads
   Library media and upserts layout **`mmek-<slug>`** automatically — see
   [cms-content-sync.md](cms-content-sync.md). Manual fallback:
   [media-sync.md](../cms/media-sync.md).
7. Confirm layout `mmek-<slug>` exists in CMS and regions look correct.
8. **Locally in CMS**, schedule the `mmek-<slug>` campaign onto the intended
   **display groups** (use `schedule/intent.yaml` as human intent only — sync
   never mutates schedules).
9. Spot-check on at least one physical Pi.
10. Update `exhibits/_catalog.yaml` status/version to match (`python tools/catalog.py --write`
    after editing `exhibit.yaml`, or edit the catalog by hand).
