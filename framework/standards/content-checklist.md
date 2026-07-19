# Content checklist (before `published`)

- [ ] `exhibit.yaml` complete; status at least `review`
- [ ] Catalog entry in `exhibits/_catalog.yaml` matches slug/version/status
- [ ] `python tools/validate_exhibits.py --exhibit <slug>` passes (Tier 1)
- [ ] Timeline preview still is non-black (`ops/qa/ci_timeline_preview.py`) (Tier 2)
- [ ] Live player capture reviewed (`run_qa_pipeline.py` or `qa-player` label) (Tier 3)
- [ ] Learning goals and sources in exhibit `README.md`
- [ ] Visitor copy reviewed for accuracy and reading level
- [ ] `media/manifest.yaml` hashes match in-repo assets or media-store objects
- [ ] Media uploaded to Xibo Library under folder `exhibits/<slug>` with tag `exhibit:<slug>`
- [ ] Layout built from a framework template; previewed on a Pi or test display
- [ ] Schedule intent recorded; bound to display groups in CMS
- [ ] Attribution/credits present where required
- [ ] No secrets; no files ≥ 2 MB (or video) committed to Git — those use the media store
