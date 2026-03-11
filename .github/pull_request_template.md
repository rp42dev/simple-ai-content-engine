## Summary
- What changed:
- Why this change:

## Type of Change
- [ ] `feat:`
- [ ] `fix:`
- [ ] `refactor:`
- [ ] `docs:`

## Pipeline Impact
- [ ] Phase 1: Cluster Map Generation
- [ ] Phase 2: Cluster Strategy
- [ ] Phase 3: SERP Analysis
- [ ] Phase 4: Pillar Generation
- [ ] Phase 5: Spoke Generation
- [ ] Phase 6: SEO Optimization
- [ ] Phase 7: Intelligence Gap Detection
- [ ] Phase 8: Cluster Scaling
- [ ] Phase 9: Final Link Injection
- [ ] Phase 10: Humanization & Readability
- [ ] Phase 11: Article Quality Assurance
- [ ] No pipeline behavior change

## Incremental Testing (Required)
### Tested now
- Step test:
- Path test:
- Batch test:
- Regression/idempotency test:

### Recommended next test
- Next incremental test to run:

## Validation Checklist
- [ ] State transitions validated for affected phases
- [ ] Artifact progression validated (`.md`, `_seo.md`, `_final.md`)
- [ ] Rerun behavior is idempotent for completed work
- [ ] Queue scoping validated via `engine/pipeline/phase_registry.apply_scope`
- [ ] No queue filtering in runner or phases (registry is source of truth)
- [ ] Run summaries present (`outputs/run_summaries/`) with expected topics and queue_size

## Docs & Changelog
- [ ] `docs/ARCHITECTURE.md` updated (if architecture changed)
- [ ] `docs/ROADMAP.md` updated (if roadmap changed)
- [ ] `docs/DEV_RULES.md` updated (if workflow rules changed)
- [ ] `CHANGELOG.md` updated under `Unreleased`

## Risk & Rollback
- Risk level: Low / Medium / High
- Rollback plan:
