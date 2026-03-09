# Release Checklist

Use this checklist for every release candidate and stable tag.

## Branch & Scope
- [ ] Release changes are merged into `main` from reviewed PRs.
- [ ] No direct, unreviewed commits on `main`.
- [ ] Scope is documented in `CHANGELOG.md` under the target version.

## Incremental Testing (Required)
- [ ] **Step test**: one topic with low limit (`--limit 1`) passes.
- [ ] **Path test**: affected contiguous phases pass end-to-end.
- [ ] **Batch test**: 2+ topics, mixed priority, queue behavior validated.
- [ ] **Regression test**: rerun completed topic; idempotent skip behavior validated.

## State & Artifacts
- [ ] State transitions are correct for each affected phase.
- [ ] Artifacts are generated in expected tiers (`.md`, `_seo.md`, `_final.md`).
- [ ] No unexpected file churn in `state/` and `outputs/` is committed.

## Docs & Governance
- [ ] `docs/ARCHITECTURE.md` updated if phase flow or module boundaries changed.
- [ ] `docs/ROADMAP.md` updated if milestone priorities changed.
- [ ] `docs/DEV_RULES.md` updated if process rules changed.
- [ ] `CHANGELOG.md` updated with user-visible changes.

## Tagging & Publish
- [ ] Create annotated tag (example: `git tag -a v0.2.0 -m "Release v0.2.0"`).
- [ ] Push branch and tags (`git push origin main ; git push --tags`).
- [ ] Verify release notes and tag are visible in GitHub.

## Post-Release
- [ ] Open/refresh next milestone under `Unreleased` in `CHANGELOG.md`.
- [ ] Confirm next planned incremental test in upcoming PR.
