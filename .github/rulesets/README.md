# GitHub branch rulesets

This folder contains a **repository ruleset** you can import to protect the default branch (`main`).

## What the ruleset enforces

| Requirement | How |
| --- | --- |
| Changes land on `main` only via pull request | `update` + `pull_request` rules block direct pushes and require a PR to merge |
| All review conversations resolved | `required_review_thread_resolution: true` |
| At least one approval from someone other than the last pusher | `required_approving_review_count: 1` + `require_last_push_approval: true` |
| No extra approval for bot/app PRs (Dependabot, unattributed Copilot) | `require_extra_approval_for_unattributed_changes: false` (set explicitly; GitHub defaults omitted values to `true`) |
| CI must pass before merge | Required status checks for Exhibit contract and Timeline preview |
| Branch up to date with `main` before merge | `strict_required_status_checks_policy: true` |
| No force-push or branch deletion | `non_fast_forward` + `deletion` rules |
| Linear commit history on `main` | `required_linear_history` (merge commits disallowed; use squash or rebase) |
| Copilot code review on new PRs and pushes | `copilot_code_review` (auto-request; re-review on each push) |
| `jefftindall` can bypass all rules | Bypass actor (user id `10339968`, mode `always`) |

### Author self-approval

GitHub rulesets do not block the PR author from approving their own PR if they never push new commits after opening it. To prevent that at the organization level, enable **Prevent pull request authors from approving their own pull requests** under organization settings (if available). With `require_last_push_approval`, any new push requires approval from someone who did not push that commit.

### Unattributed / bot pull requests

GitHub enables **Require an additional approval for unattributed Copilot pull requests** (`require_extra_approval_for_unattributed_changes`) by default when the field is omitted from a ruleset. That raises the approval bar by one for PRs opened under a bot or app identity (including Dependabot), so a ruleset that asks for one approval effectively needs two write-access approvals. This repository sets the flag to `false` explicitly so Dependabot and similar bot PRs merge after the normal single non-pusher approval and required checks.

## Import the ruleset

1. Open **https://github.com/SaveMarineMammals/marine-mammal-education-kiosks/settings/rules**
2. Click **New ruleset** → **Import a ruleset**
3. Choose `.github/rulesets/main-branch-protection.json`
4. Review the preview (especially bypass actors and required checks)
5. Click **Create** (or update the existing **Protect main** ruleset to match)

After the first CI run on a pull request, confirm the required check names appear exactly as:

- `Exhibit contract`
- `Timeline preview`

If GitHub shows different names, edit the ruleset’s required checks to match the names under **Pull request → Checks** on a sample PR.

## Repository settings (not in the ruleset JSON)

These cannot be imported via ruleset JSON and must be enabled once per repository:

### Automatically delete head branches

**Settings → General → Pull Requests → Automatically delete head branches**

Deletes the feature branch after a PR is merged.

### Allow auto-merge

**Settings → General → Pull Requests → Allow auto-merge**

When enabled, pull requests can be queued for automatic merge once approvals and required checks pass.

## Verify

1. Open a test PR against `main`
2. Confirm direct push to `main` is rejected (except for `jefftindall`)
3. Confirm merge is blocked until CI passes, one approval is given, and conversations are resolved
4. After enabling auto-merge and delete-branch settings, confirm the PR merges when ready and the branch is removed
