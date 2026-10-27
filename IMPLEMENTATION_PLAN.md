# CastraVolt Implementation Plan


> Current internal scope (27 October 2026): shared demo login `admin` / `123`; no public registration, verification or password recovery. Everyone using this account shares its projects, sites and history. Database ownership/session/CSRF checks remain. Earlier individual-account requirements below describe retained future capability and are superseded for this prototype. Demo access is development-only; production rejects it.

Status: Implementation in progress; Stages 1–4 complete locally

Updated: 27 October 2026

References: PRD.md, TRD.md, DESIGN.md. Follow the Midnight Iris visual specification in DESIGN.md Section 13. This plan describes the selected adoption-enabled model and 3 km POI radius.

## 1. User journey at a glance

Login → Projects → Project workspace → New site estimator → Estimate result → Saved prediction/history.

EV adoption trends and Account are separate navigation destinations available after login. Account registration/verification and password recovery branch from Login.

The ML model runs only when the planner explicitly requests an estimate. It does not run during login, browsing projects, dragging a pin, viewing saved results or filtering registration trends.

## 2. Page-by-page behaviour

### Page 1: Login and account access

- Unauthenticated visitors open Login.
- Existing planner enters email/password and logs in. Successful verified login opens Projects.
- New planner follows Register → verify email → Login/Projects once verification and authentication succeed.
- Provide forgot-password/reset-password flows and useful loading/error feedback.
- Valid existing sessions may open Projects directly. Protected deep links may resume after authentication only when the destination is a valid internal route owned by the planner.
- Expired sessions prompt login; do not expose another account's resources or leave private content presented as accessible.

Backend: authentication, verification, session cookies, CSRF protection, expiry and rate limits. No ML or POI call.

### Page 2: Projects — first page after login

- Show only this planner's projects, with names and updated times.
- Empty account: show Create project as the clear next action.
- Creating a project requires a name; description is optional.
- Opening a project leads to its workspace.
- Navigation also offers EV adoption trends and Account/logout.

Backend: authenticated, owner-scoped project list/create/update/delete. No ML or POI call.

### Page 3: Project workspace

- Show project context and its saved sites, latest prediction information where available, and updated times.
- Primary action: Add proposed site.
- Opening a saved site shows its details and prediction history.
- Editing a site's name/location/category does not rewrite past predictions.
- The site estimator is reached from this workspace; the current project remains visible in the header.

Backend: authorised project/site reads and writes. No inference when opening the workspace.

### Page 4: New site estimator

- Main layout: map plus controls/detail panel following DESIGN.md.
- Planner searches an address or drops/moves a proposed-site pin.
- Show the selected address when available, coordinates, derived state and a 3 km circle.
- Suggest the host-site category only when reliable; planner confirms/corrects a category from the 23 source labels. Unknown is a fallback.
- A pin and confirmed category are required before estimation. Name the site before saving; an address-derived editable suggestion is acceptable.
- Primary action: Estimate charging points.
- On click, save the new site within the current owned project, then request a prediction. If the site already exists, persist the selected changes first.
- Pin/category edits invalidate the current result. Do not query all POIs or run ML on every movement.

Backend before estimate: validate project ownership and site fields; validate state/study coverage; persist the site. Map display and address search are separate from Overpass extraction.

### Page 5: Estimate result

Use the estimator's result panel on desktop and a readable stacked result on mobile. A separate result URL can open the saved prediction for later access; a forced new full page is not required after every estimate.

Display:

- Estimated total charging points, prominently as an integer.
- Original site location/category and state used for this prediction.
- Eight POI counts, 3 km radius and extraction timestamp.
- Configured adoption indicator: 2025 state registration count and its scope.
- Brief explanation of the planning estimate and its limits.
- Expandable model/data version information.
- Actions to inspect saved prediction history or change the site and estimate again.

A successful prediction is saved automatically. Do not add a misleading second Save prediction button. If saving fails, do not display an unsaved result as successfully stored.

### Page 6: Saved site and prediction history

- List prior predictions for an owned site, newest first.
- Opening a prediction retrieves its immutable snapshot, not newly extracted POIs or a fresh prediction.
- Clearly distinguish a historical snapshot from the current edited site.
- To recalculate, planner explicitly requests a new estimate using the current site fields.

Backend: owner-scoped historical reads. No inference/Overpass call merely to view history.

### Separate page: EV adoption trends

- Show monthly new electric motokar registrations from the filtered 2024, 2025 and vehicles_2026 sources.
- Default view: both states; January 2024–September 2026 coverage.
- Filters: state, year selection, month range, timeline/year-over-year comparison and reset.
- Update charts and period summaries together; show growth only for valid matching periods.
- 2026 October–December is unavailable, not zero. Explain that Rakan Niaga records are excluded and these are new registrations, not fleet stock.
- Filtering charts does not alter the fixed prediction adoption lookup or trigger ML.

Backend: query imported monthly summaries and coverage metadata. No raw-CSV processing on every page request.

## 3. Exactly when and how the ML model runs

On API startup:

1. Load the approved adoption-enabled Random Forest pipeline once per worker.
2. Verify artifact hash, environment compatibility, fitted preprocessing, 11-feature schema, adoption configuration and target metadata.
3. Mark inference ready only after checks pass. No retraining occurs in the application.

On Estimate charging points:

1. Browser saves/updates the owned site and sends `POST /api/v1/sites/{id}/predictions` with an idempotency key.
2. Backend authenticates the session, checks CSRF/ownership, and reads the current site fields.
3. Validate coordinates, category and supported state/study area. Preserve a snapshot for this request.
4. Check the successful, versioned POI cache. On a miss, query Overpass within 3,000 metres using training-compatible tags/geometry and deduplicate facilities.
5. Reject failed/incomplete extraction rather than creating zero counts.
6. Look up the configured 2025 state value: Selangor 560 or Kuala Lumpur 1,237, verified against the artifact/source manifest.
7. Build the eight POI counts plus category, state and state_ev_registrations. Coordinates are used for extraction, not direct model features.
8. Run the saved fitted preprocessing and Random Forest prediction.
9. Reject non-finite output; apply `max(minimum_count, floor(raw_prediction + 0.5))`, initial minimum one.
10. Save the immutable feature/location snapshot, raw result, displayed count, source/model versions and timestamps. Commit a successful stored result before reporting success.
11. Return the saved prediction. Browser shows it only if it still corresponds to the active site selection.

Do not hold a database transaction or connection open throughout a long external POI request. Read/validate scope, release the connection, perform provider work, then recheck ownership/site revision as needed before saving. Use the request snapshot consistently; if the current site changed, preserve the historical snapshot and tell the interface it is not the current selection.

Idempotency: repeated submission with the same key and same request snapshot must not create duplicate stored predictions. A key reused for different inputs returns a conflict. Disable duplicate clicks in the UI as well; do not rely on the UI alone.

## 4. Build order and completion checks

Each phase below is one implementation stage. Stage 0 corresponds to Phase 0, and so on. The stage contracts in Section 7 define deliverables and exit checks. Checkboxes record completion only after verification; a screen mockup alone does not complete a backend or integration stage.

### Phase 0 — model and data handoff

- [ ] Obtain the adoption-enabled full-run model parameters/artifact and metadata from Colab.
- [ ] Export the selected tuned pipeline, or explicitly refit with selected parameters; do not use the default notebook candidate accidentally.
- [ ] Verify 11-feature inference parity against recorded fixtures.
- [ ] Recover the original 3 km POI tags, geometry and facility-counting code. Keep provisional labelling until compatible extraction is established.
- [ ] Align notebook rounding/radius wording with current specifications; recalculate rounded metrics from saved predictions without claiming the old ceiling MAE belongs to half-up rounding.
- [ ] Prepare versioned 2024–2026 monthly summaries and 2025 adoption lookup.

Completion: model/data manifests exist; matching extraction is understood or its unresolved status is explicit. UI scaffolding can proceed in parallel with this preparation, but live model equivalence cannot be claimed until resolved.

### Phase 1 — application foundation

- [ ] Create React/TypeScript frontend and FastAPI backend with PostgreSQL local configuration.
- [ ] Add SQLAlchemy models, Alembic migrations, environment templates and typed API contracts.
- [ ] Establish Midnight Iris tokens, sidebar/header, forms, buttons, panels and responsive behaviour.
- [ ] Add health/readiness checks, structured errors and request IDs.

Completion: local services start, migrations apply, and frontend/API communicate without embedded secrets.

### Phase 2 — individual accounts

- [x] Implement registration, verification, login/logout, current session and password reset.
- [x] Add opaque cookie sessions, Argon2id password hashing, CSRF and rate limits.
- [x] Build account screens and protected routes.
- [x] Test expiry, token reuse, reset revocation, generic account-recovery responses and authentication failure states.

Completion: each verified planner can enter/leave a private authenticated session.

### Phase 3 — private projects and sites

- [x] Implement project/site CRUD with owner-scoped queries and migrations.
- [x] Build Projects and Project workspace screens, including empty states and deletion confirmation.
- [x] Add prediction-history schema and immutable snapshots.
- [x] Verify planner A cannot access planner B's projects, sites or predictions by changing IDs.

Completion: login leads to the planner's own workspace and saved-site lifecycle works.

### Phase 4 — map and site selection

- [x] Select Leaflet/OSM/Nominatim and versioned state polygons; urban-only boundary remains an explicitly documented provisional limitation.
- [x] Build address search, pin movement, 3 km circle and selected-site summary.
- [x] Add confirmed category control and Save/update site behaviour.
- [x] Implement unsupported-location, map failure and stale-selection states.

Completion: a planner can save a valid proposed site in the correct project without yet running inference.

### Phase 5 — POI and registration feature services

- [ ] Implement bounded Overpass queries, original tag mappings, geometry handling and reproducible facility deduplication.
- [ ] Add versioned successful-result caching, expiry, concurrency limits and clear provider errors.
- [ ] Implement trusted state resolution and 2025 adoption lookup.
- [ ] Verify feature parity against source-engineered examples; do not replace failed requests with zeros.

Completion: a valid saved site produces the correct typed 11-feature vector with provenance.

### Phase 6 — predictions and saved results

- [ ] Load the approved pipeline with startup/schema checks.
- [ ] Implement inference, half-up rounding and configured minimum.
- [ ] Add idempotent prediction creation and immutable stored results.
- [ ] Connect Estimate action, progress/error feedback, result panel and history.
- [ ] Test model parity, retries, concurrent requests, site edits during extraction and cross-account access.

Completion: login → project → new pin/category → features → prediction → saved history works end to end with the intended model.

### Phase 7 — adoption dashboard

- [ ] Import source-versioned monthly summaries and coverage metadata transactionally.
- [ ] Implement state/year/month/comparison filters and summary API.
- [ ] Build charts, accessible monthly data view, legends, reset and coverage notes.
- [ ] Verify totals, complete-period growth, zero-denominator handling and no fabricated late-2026 zeros.

Completion: dashboard agrees with filtered sources and filters never alter the model's adoption configuration.

### Phase 8 — integration, accessibility and release

- [ ] Test responsive desktop/mobile flows, keyboard focus, forms, charts and map alternatives.
- [ ] Test loading, empty, stale, provider failure, model failure and expired-session states.
- [ ] Configure HTTPS, secrets, exact origins, provider attribution and private database access.
- [ ] Test backup restoration and controlled migration deployment.
- [ ] Agree a representative concurrent-planner workload and measure API/POI/database limits.
- [ ] Record model limitations, source assumptions and results in the FYP; do not claim production capacity or optimal recommendations without evidence.

Completion: acceptance criteria in PRD/TRD pass, with unresolved limitations explicitly documented.

## 5. Suggested repository organisation

- `frontend/`: React application, routing, screens, components, map and typed API client.
- `backend/app/`: FastAPI entry point, configuration, auth, database, projects/sites, predictions, POIs, registration services and model loading.
- `backend/migrations/`: Alembic migrations.
- `backend/tests/`: unit/integration tests, ownership and model/feature parity fixtures.
- `notebooks/`: offline training/evaluation notebooks and documentation.
- `data/ML Data/`: current prepared CSV inputs, not browser-accessible public assets.
- `model_artifacts/`: trusted versioned artifact manifests; large/private artifacts may live outside Git.
- `docs/`: supporting provider, extraction and deployment decisions.

Use one frontend, one backend application and PostgreSQL initially. Add queues, Redis or a separate model service only if measured requirements justify them.

## 6. Decisions still required before their build phases

- Map renderer, tile/geocoding/Overpass and email providers, hosting and urban boundaries.
- Selected tuned model artifact/parameters and compatible environment.
- Original extraction tags/geometry/deduplication for live feature parity.
- Production cache TTL, provider limits, session/token lifetimes, retention and recovery targets.
- Figma frames for the adopted design, especially account/project screens and the new-site estimator absent from the older PDF.

Resolve routine technical details during their implementation phase and record them. Do not reopen agreed product choices unnecessarily. Do not start deployment, publishing or external communications merely because they are listed here; this document is the implementation sequence, not execution of those actions.

## 7. Stage delivery contracts for Codex

### How to execute the stages

- Read PRD.md, TRD.md, DESIGN.md Section 13 and the relevant stage before implementation.
- Implement one stage at a time, keeping its deliverables concrete and reviewable. Continue through authorised local implementation without asking for routine approval between stages.
- Stage 0 data/model work can remain pending while independent foundation/account/project/UI work proceeds. Do not claim a blocked dependency is complete or use mock outputs as real predictions.
- Maintain Section 8 after each stage: status, files/artifacts delivered, checks run, results, limitations and next work.
- Use statuses Not started, In progress, Complete, or Pending dependency. Complete requires all mandatory deliverables and exit checks for that stage.
- If a required input is unavailable, identify the exact missing artifact and continue independent work. Mark affected integration pending.
- Keep source data unchanged, preserve account ownership and never silently change the target, model features, 3 km rules or rounding policy.
- Production publication, paid provisioning and other external actions follow the user's actual authorisation. Their presence in a future stage is not permission to execute them now.

### Stage 0 — model and data handoff

Deliverables:

- Versioned selected adoption-enabled Random Forest artifact and manifest identifying hash, features, fitted preprocessing, library versions and selected parameters.
- Model parity fixtures containing genuine prepared inputs and expected raw predictions.
- Documented original 3 km extraction mappings/geometry/deduplication, or an explicit unresolved provenance record.
- Reproducible registration-summary preparation and the configured 2025 state lookup with coverage/source hashes.
- Updated notebook export/radius/rounding configuration where necessary, with half-up metrics distinguished from historical ceiling metrics.

Exit checks: load the intended pipeline in the serving environment; verify all 11 inputs and fixture outputs; reconcile registration totals; identify whether live extraction parity is established. Unavailable selected model or unrecovered extraction rules remain pending dependencies, not fabricated replacements.

Dependencies: real Colab artifact/selected parameters and original POI engineering details. Independent later stages may begin while obtaining these.

### Stage 1 — foundation and design system

Deliverables:

- Runnable React/TypeScript frontend and FastAPI backend with explicit dependencies/lockfiles.
- PostgreSQL local service/configuration, initial migrations and environment-variable examples without secrets.
- Midnight Iris tokens, desktop/mobile shell, navigation, reusable controls and structured API client/error handling.
- Local setup instructions, health endpoints and basic automated build/API checks.

Exit checks: documented startup works; database migrations apply to a fresh local database; frontend builds and reaches API health; visible shell follows the adopted tokens. No account or prediction feature is claimed complete yet.

Dependencies: provider-independent scaffolding; use a local database. Stage 0 model is not required.

### Stage 2 — account access

Deliverables:

- Register, verification, login/logout, session inspection and password-recovery APIs and screens.
- User/session/token migrations, Argon2id hashing, secure cookie configuration, CSRF and account-endpoint rate limits.
- Development mail delivery/test mechanism and documented production email configuration requirement.
- Protected frontend routes with expired-session handling.

Exit checks: verified planner login reaches Projects; logout revokes access; expired/reused recovery tokens fail; password reset revokes existing sessions; authentication and CSRF tests pass. If production email is unconfigured, report that limitation rather than claiming deployed recovery works.

Dependencies: Stage 1 database/API foundation. No ML dependency.

### Stage 3 — private projects, sites and history storage

Deliverables:

- Project/site/prediction-snapshot schemas and migrations.
- Owner-scoped CRUD APIs and Projects/Project workspace screens.
- Empty states, edit/delete flows and prediction-history read interfaces.
- Cross-account isolation tests for reads, updates, deletes and nested-resource access.

Exit checks: two planners see only their own projects/sites; altered IDs do not disclose data; project/site operations persist across reloads. History can show a real empty state until Stage 6 creates predictions; do not invent history.

Dependencies: Stages 1–2. No trained model required for storage/UI.

### Stage 4 — map and proposed-site selection

Deliverables:

- Documented renderer/tile/geocoding choices and configured attribution.
- Address search, proposed-site pin, correct 3 km ground-radius circle, selected-location summary and category confirmation.
- Owned-site save/update connection, selection-change invalidation and responsive estimator layout.
- Supported-state validation and selected urban-boundary rule, or clear provisional urban-coverage limitation.

Exit checks: a planner selects/searches a site and saves it in the correct project; circle follows the pin; category can be corrected; dragging does not issue repeated full POI/inference requests; stale responses cannot overwrite the current selection. Provider/map errors are handled visibly.

Dependencies: Stage 3 and chosen map/geocoding configuration. Live ML is not required.

### Stage 5 — reproducible feature preparation

Deliverables:

- Server-side Overpass client with bounded queries, timeouts, incomplete-response detection and request limits.
- Eight-group classification/deduplication using original compatible rules.
- Versioned successful-result POI cache, state resolution and fixed 2025 adoption lookup.
- Typed 11-feature preparation service, provenance metadata and feature-parity tests.

Exit checks: genuine site fixtures produce expected feature values; provider failure is not zero-filled; wrong/missing state lookup fails clearly; cache keys include radius/rule version; counts match the agreed engineering method. If original rules are unresolved, live parity stays pending even if a provisional client works.

Dependencies: Stage 0 extraction/registration definitions and Stage 4 location contract.

### Stage 6 — model inference and saved results

Deliverables:

- Validated startup loading and readiness for the selected real model.
- Owner-authorised, idempotent prediction endpoint with finite-output checks and half-up rounding.
- Immutable prediction persistence including input snapshot, raw estimate, displayed count, model/extraction versions and adoption year/value.
- Connected Estimate action, result panel, history view and changed-selection/error states.

Exit checks: complete login → project → saved pin/category → real features → intended pipeline → saved result → history journey; model outputs agree with fixtures; 3.2 → 3, 3.5 → 4 and 3.9 → 4; duplicate retries do not create duplicate results; concurrent selection edits and cross-account prediction requests are handled correctly.

Dependencies: Stages 0, 3, 4 and 5. No placeholder model or default smoke artifact may satisfy this exit check.

### Stage 7 — monthly adoption dashboard

Deliverables:

- Versioned CSV import and active monthly-summary data for 2024–2026 coverage.
- Filter/summary API with state, years, month range and comparison mode.
- Trends screen with accessible chart data, active filters, reset, legends, period summaries and source notes.
- Reconciliation and edge-case tests for comparison periods and partial coverage.

Exit checks: displayed totals reconcile to filtered files; valid year-over-year comparisons use matching covered months; zero-denominator growth is unavailable; October–December 2026 are not fabricated zeros; trend filters do not alter prediction lookup values.

Dependencies: Stage 0 registration scope plus Stages 1–2. Can be implemented independently of Stage 6 once the shared API/account shell exists.

### Stage 8 — integrated quality and release readiness

Deliverables:

- End-to-end test coverage for core planner flow and adoption dashboard.
- Responsive/accessibility review with fixed actionable issues.
- Deployment configuration, secret/origin/provider setup documentation and controlled migration process.
- Backup/restore procedure with local/staging evidence, monitoring configuration and representative concurrency test report.
- Handoff notes identifying environment setup, model/data versions, operational limits and unresolved scientific limitations.

Exit checks: PRD/TRD acceptance criteria pass for the environment actually tested. Record exact workload and measurements; do not invent performance targets/results. An authorised deployed environment must be checked before claiming a live release. Local release readiness is distinct from published production deployment.

Dependencies: completed integrated features and selected deployment/provider configuration. External publication requires applicable user authorisation.

## 8. Stage progress ledger

Initial state: planning documents and a training notebook exist. These do not mean the application stages are complete.

- Stage 0 — Pending dependency. The uploaded default candidate differs from the selected tuned RF. Reconstructed `model/verified_rf80_cv5/evaluated_pipeline.joblib` reproduces all 153 saved test predictions (max difference 1.78e-15); manifest and ten fixtures saved. Original POI tag/geometry/deduplication parity is still pending. See docs/STAGE_0_HANDOFF.md.
- Stage 1 — Complete. React/TypeScript foundation, typed FastAPI connection, bounded PostgreSQL setup, migrations, lockfiles and setup/start/check launchers delivered. Live startup verified on 26 October 2026: PostgreSQL healthy on host port 55432, migration baseline applied, API database readiness passed and frontend started. Current backend/launcher suite: 18 passing tests. Original application build and four frontend tests passed. Account/project CRUD and live prediction serving remain later stages.
- Stage 2 — Complete for local development. Added account/session/token/rate-limit migration, Argon2id password hashing, hashed opaque sessions, CSRF/origin protection, expiring single-use email/reset tokens, generic recovery responses, session revocation, protected navigation and Midnight Iris account screens. Development email capture is private under tmp/mailbox; SMTP is configurable, not externally tested. PostgreSQL integration tests use disposable databases, including concurrent verification consumption. Browser QA on isolated 8001/5174 verified register → local email → verification → login → Projects → logout and password recovery/reset; user ports 8000/5173 were not used. Review fixes cover consistent token/user locking, post-response delivery and browser session revalidation. Project CRUD remains Stage 3.
- Stage 2 verification record: final backend/account/launcher suite 25 passed; frontend suite 8 passed; production frontend build passed. Code review findings addressed. Temporary 8001/5174 services were stopped and their disposable browser-test database removed. No real email was sent. Main application migrations run on the user's next start.
- Stage 3 — Complete for local development. Migration 0003, owner-scoped project/site CRUD, read-only prediction history, typed client and Projects/workspace screens delivered. Internal shared admin/123 replaces public account UI by user request. State awaits trusted map validation; sites use manual coordinates for now. Deletes confirm cascading removal. Map selection and inference remain Stages 4 and 6. Final verification: 30 backend tests, 11 frontend tests and production build passed. Browser QA on isolated ports 5174/8001 verified admin login, project creation, site/category saving, reload persistence and empty history. Temporary services and disposable database removed; user ports untouched. See docs/STAGE_3_IMPLEMENTATION.md.
- Stage 4 — Complete for local development, with explicit research coverage limits. Leaflet/OSM map, 3,000 metre circle, click/drag pin, submitted Nominatim address search, manual coordinates, project chooser, category confirmation and owned-site create/update/reopen delivered. PostgreSQL cache migration 0004 and global provider throttling added. Server derives supported state using hash-checked geoBoundaries 2017 polygons; Putrajaya/unsupported locations rejected. Urban-only coverage remains provisional and visible. Final checks: 35 backend tests, 17 frontend tests, production build passed. Live browser on isolated 5174/8001 verified real search/tiles, save, drag invalidation, same-row update and reopening. No POI/inference called. Temporary preview/database removed. See docs/STAGE_4_IMPLEMENTATION.md.
- Stage 5 — Pending dependency; service/UI infrastructure implemented. Added bounded Overpass extraction, provisional versioned eight-group rules, conservative deduplication, successful-count cache/migration 0005, verified packaged 2025 adoption lookup and typed 11-feature context endpoint. Explicit Prepare site context action shows counts and sources; edits invalidate context. Inference eligibility stays false because original training POI definitions are unavailable. Live provider probes failed (TLS on one endpoint, timeout on alternate); no live feature-parity or availability claim. Final local checks: 47 backend tests, 22 frontend tests and production build passed; filtered registration summary reconciled. Restart applies migration 0005. See docs/STAGE_5_IMPLEMENTATION.md.
- Stage 6 — Pending dependency for validated recommendations; complete experimental local workflow. Verified selected model serving, immutable saved inference, nearest-half-up/minimum-one rounding, idempotent/concurrent request handling, ownership/session/CSRF checks, under-map output card and labelled history delivered. Explicit experimental request action is development-only; production rejects unverified POIs and feature eligibility remains false. 66 backend / 27 frontend tests and production build passed. Isolated real-browser flow produced and saved 5 total points from the genuine model/local inputs. No user ports/processes touched. See docs/STAGE_6_IMPLEMENTATION.md.
- Stage 7 — Implemented: versioned monthly import, Chart.js filters/comparisons, accessible data, calculated metrics and optional cached Groq explanations. See docs/STAGE_7_IMPLEMENTATION.md for verification and API-key setup.
- Stage 8 — Not started.

For each update, add: stage/status; delivered file paths or artifact versions; verification performed and results; unresolved dependency/limitation; next stage or independent task. Check the matching Phase checkboxes as work is verified. Do not mark an entire stage complete based on a partial screenshot or successful command alone.


### Map-only follow-up — 27 October 2026

Removed the separate manual Add site form and inline site editor; creation/editing now use the estimator map. Coordinates are read-only. Pin state is validated locally and address is reverse-geocoded after the pin settles, using the shared cache/provider quota. Save waits for pending address resolution and permits an absent address after a visible lookup failure. Name/category remain planner-confirmed inputs.

Diagnosed the user's 404 against the actual running API: port 8000's OpenAPI had no location routes, and the frontend proxy returned the same 404. This was an older backend process. No user process was stopped. Restart once through start.cmd; the updated launcher enables backend source reload for subsequent code changes. Missing location routes now produce an explicit restart instruction instead of bare Not Found.

Verified: 36 backend tests, 17 frontend tests and frontend build passed. Isolated real-browser check confirmed map-only creation, dropped-pin coordinates/state/address derivation and saved site. Temporary preview/database cleaned up. Model/POI extraction remains Stage 5/6.


### Stage 5 local-source repair — 27 October 2026

Facility availability is now verified using a bundled genuine Geofabrik OSM snapshot, dated 25 October 2026: 10,981 node/way/relation representations, 483 KB compressed, state coverage plus 3 km buffer. Default local mode bypasses public-service requests/cooldowns; source hash is part of the successful-count cache key. No raw 240 MB download is needed on another computer. Native certificate verification is used for remaining external HTTP calls. Real-browser context preparation at the reported pin succeeds. Verified 54 backend / 24 frontend tests and production build. Original training counting-rule parity remains the Stage 5 dependency; do not conflate resolved availability with model validity.


## Current model integration — 27 October 2026

This decision supersedes earlier 3 km/adoption prediction specifications. The estimator uses eight POI counts within **1 km**, the confirmed host-site category and boundary-derived state. EV registration numbers are excluded from prediction; keep 2024–2026 data for the future monthly trends dashboard.

The selected evaluated Random Forest is `model/verified_poi_state_rf80_cv10` (80/20 with training-only CV10). Results appear below the map, estimate total planned charging points, and use nearest whole number with halves upward and minimum one. Exact model, query-rule and OSM snapshot compatibility is required. New history stores no adoption context; old history is preserved. Research prototype wording reflects measured capacity accuracy limits, not a placeholder model. See BACKLOG.md and RESULTS.md for implementation status and validation.
