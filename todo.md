# AI Content Engine

## Phase 1 — MVP
- [x] Setup project structure
- [x] Install dependencies
- [x] Create strategist agent
- [x] Generate topic cluster
- [x] Save cluster to file

## Phase 2 — Article Writing
- [x] Outline agent
- [x] Writer agent
- [x] Save article output

## Phase 3 — SEO
- [x] SEO optimizer
- [x] Internal linking agent
- [x] Generate SEO reports & Linking strategy

## Phase 4 — Intelligence
- [x] Website crawler tool (ScrapeWebsiteTool integration)
- [x] Intelligence agents & tasks defined
- [x] Content gap detection run

## Phase 5 — Automation & Polish (Completed)
- [x] **Gap-to-Spoke Loop**: Automatically add detected gaps back into the production queue.
- [x] **Link Injection**: Automatically insert suggested internal links into the Markdown files.
- [x] **Multi-Topic Batching**: Support running multiple topics from a single queue file.
- [x] **UI/Dashboard (Streamlit)**: Primary infrastructure and monitor.
- [x] **CMS Integration**: Direct "Export to WordPress" functionality via REST API.

## Phase 6 — Industrial Power (Completed)
- [x] **Industrial Batching (v2)**:
    - [x] Upgrade to `topics_queue.json` with metadata (Priority, URL).
    - [x] **Global Anchor Mapping**: Allow cross-topic linking (e.g., Invisalign links to Teeth Whitening).
    - [x] **Pipelined Execution**: Complete a specific phase for *all* topics before moving to the next phase.
- [x] **Advanced Dashboard Features**:
    - [x] **Connect Input Control**: Add topics/URLs directly to the queue from the UI.
    - [x] **Cluster Preview & Approval**: Approve/Edit the strategist's cluster before writing starts.
    - [x] **Manual Phase Triggering**: Start/Reset specific phases (SEO, Writing, Intel) for any topic.

## Phase 7 — Dashboard Pro Upgrades (Completed)
- [x] **1. Architecture Refactor**: Extract CSS into a separate file and shift state logic to `tools/state_manager.py`.
- [x] **2. Run Kill-Switch**: Add a `[ STOP RUN ]` button to safely terminate an active subprocess from the UI.
- [x] **3. Error Traceback Visibility**: Automatically surface the last 15 lines of the terminal output if a run fails instead of failing silently.
- [x] **4. Autopilot Mode**: Add a global toggle to run pending queue items sequentially without requiring manual "Authorize & Run" clicks for each one.

## Future Refinements
- [ ] **Token Optimization**: Refine prompt length and history management to reduce costs.
- [ ] **Multi-User Support**: Add authentication for the dashboard.
- [ ] **Image Generation**: Automatically generate SEO-optimized hero images for articles.
