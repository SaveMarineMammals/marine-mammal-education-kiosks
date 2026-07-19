# Contributing to Marine Mammal Education Kiosks

Thank you for your interest in the Marine Mammal Education Kiosks project!

## Getting started

1. Read [docs/local-testing.md](docs/local-testing.md) for clone, Python tools, and Tier 1–3 quality checks.
2. Skim [docs/architecture.md](docs/architecture.md) and [docs/exhibit-authoring.md](docs/exhibit-authoring.md) for how content flows into Xibo.
3. Follow [docs/media-policy.md](docs/media-policy.md) for what may live in Git vs the external media store.
4. Check open issues or open a discussion before large changes.

## Development workflow

1. Fork and clone the repository (install [Git LFS](https://git-lfs.com/) and run `git lfs pull` after clone).
2. Create a feature branch from `main`.
3. Make focused changes (exhibits, framework templates, tools, or ops docs).
4. Run the same checks CI runs (see below).
5. Open a pull request — the [PR template](.github/pull_request_template.md) includes a test plan checklist.

## Pre-merge checks

CI must pass on every pull request. Run these locally from the repository root:

```powershell
python -m pip install -r tools/requirements.txt
python tools/validate_exhibits.py
python tools/catalog.py --check
```

When you change layouts or media, also run the Tier 2 timeline preview:

```powershell
python -m pip install -r ops/qa/requirements.txt
python -m playwright install chromium
python ops/qa/ci_timeline_preview.py --exhibit <slug>
```

Optional live Xibo player capture (Tier 3 — not required to merge):

```powershell
cd ops\qa
copy config.env.example config.env
python run_qa_pipeline.py -v --exhibit <slug>
```

See [docs/local-testing.md](docs/local-testing.md) and the workflows under `.github/workflows/` for the full pipeline.

## Code and content style

- Prefer YAML exhibit packages and framework templates that match existing exhibits (especially Glance & Match).
- Keep changes focused; prefer small, reviewable pull requests.
- Do not commit secrets, CMS credentials, video, or files ≥ 2 MB — use the media store.
- Timeline copy must be plain ASCII (no Markdown/emoji); CTA tickers use native Xibo marquee (see the exhibit-generator skill).
- Update documentation when authoring, ops, or CI behavior changes.

AI agents should read [AGENTS.md](AGENTS.md) before making substantive changes.

## Commit messages

Use clear, descriptive commit messages. Conventional prefixes are encouraged:

- `feat:` new feature or exhibit capability
- `fix:` bug fix
- `docs:` documentation
- `chore:` tooling or maintenance
- `test:` tests / QA pipeline only

## Pull requests

- Ensure required CI jobs pass (**Exhibit contract**, **Timeline preview**).
- Update documentation when behavior or setup changes.
- Link related issues when applicable.
- `main` is protected by a [repository ruleset](.github/rulesets/README.md): PR required, one non-pusher approval, resolved threads, and green CI. Enable **Allow auto-merge** and **Automatically delete head branches** in repository settings for the full workflow.

## Community

Please follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) in all project interactions.

## Questions

Open a GitHub Discussion or issue for questions about exhibit authoring, Xibo ops, media policy, or contribution scope.
