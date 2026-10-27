# CastraVolt Technical Requirements Document


> Current internal scope (27 October 2026): shared demo login `admin` / `123`; no public registration, verification or password recovery. Everyone using this account shares its projects, sites and history. Database ownership/session/CSRF checks remain. Earlier individual-account requirements below describe retained future capability and are superseded for this prototype. Demo access is development-only; production rejects it.

Status: Implementation specification; infrastructure providers remain to be selected

Updated: 27 October 2026

Product specification: PRD.md

## 1. Architecture

- Frontend: React with TypeScript, built using Vite.
- Backend: Python FastAPI application serving authenticated JSON APIs and the saved ML pipeline.
- Database: PostgreSQL, accessed only by the backend through SQLAlchemy and a bounded connection pool. Use Alembic for schema migrations.
- ML: adoption-enabled Random Forest pipeline, with its fitted preprocessing, running inside the backend. No separate ML service is required initially.
- Local environment: Docker Compose for PostgreSQL and optional application services. Production uses HTTPS and a supported PostgreSQL deployment with backups.

Request flow: browser → FastAPI → authorised database operations, geocoding/POI provider requests, feature preparation, and model inference → JSON response → browser.

Technology versions must be pinned in lockfiles during implementation. The model-serving Python and ML library versions must match the verified artifact environment or pass compatibility tests. Do not load an artifact solely because its filename looks correct.

## 2. Internal account access

`CASTRAVOLT_INTERNAL_ACCESS=true` is the development default. User ID `admin`, password `123`; registration, verification and recovery endpoints are disabled. The admin row is inserted on first successful login with an Argon2id hash. Its ID and data persist across restarts. This username grants no additional administrative privileges.

Retain opaque sessions with hashed tokens, HttpOnly/SameSite cookies, login rate limits, CSRF/origin validation and logout revocation. Never store session tokens in localStorage. Owner-scope every project/site/history query. All users of the shared account see its records. Public account code remains available for future provisioning; production rejects demo access. Future hosted account provisioning and recovery require a separate decision.

## 3. Frontend responsibilities

- React/TypeScript pages for login/account recovery, project list, site estimator, saved site/prediction details, and registration trends.
- Map selection and address search; obtain coordinates and show a clear selected-location state.
- Suggest site category where reliable; require the planner to confirm or select it from the 23 PRD categories, with Unknown fallback.
- Display request progress, provider failures, unsupported locations, model errors, and retry actions.
- Invalidate displayed results when location or category changes. Ignore stale responses from earlier requests.
- Show total planned charging points, model/version context, POI counts/radius, adoption state/reference year, and estimate limitations.
- Render trend charts with state and date filters, matching-period comparisons, and 2026 January–September coverage labels.
- Use an API client with typed request/response contracts derived from FastAPI's OpenAPI schema. Validate authorisation server-side regardless of frontend controls.
- Support keyboard navigation, labelled inputs, readable contrast, responsive layouts, and a non-map way to inspect selected site details.

Use an OpenStreetMap-based map with a React-compatible renderer. Renderer, tile/geocoding providers and chart library are implementation selections still to be made. POI queries use Overpass API or a compatible managed service, independently of map tiles and geocoding. Keep provider credentials requiring secrecy on the backend. Apply each provider's attribution and usage requirements.

## 4. Backend boundaries

Separate account/session, project/site ownership, prediction orchestration, POI extraction/cache, registration lookup/trends, and model loading into clear modules within one application.

Load the approved model once per API worker at startup. Validate its feature manifest, target definition, adoption configuration, preprocessing, versions, and expected prediction behaviour. If validation fails, inference readiness fails; do not silently load another model.

Model inference is synchronous CPU work: run it through a bounded thread executor or synchronous route without blocking the async event loop. Use asynchronous HTTP clients for provider calls, with deadlines, bounded concurrency, and limited retries for transient failures. Bound database pools and worker counts; each worker holds its own model copy.

Do not retrain models in web requests. Offline notebook training produces a versioned artifact promoted deliberately after evaluation.

## 5. Core database schema

Use UUID primary keys and timezone-aware UTC timestamps. Use foreign keys, indexes and appropriate not-null/check constraints.

- `users`: id, normalised unique email, password hash, verification state, created/updated timestamps.
- `sessions`: id, user_id, unique token hash, created/expires/revoked timestamps. Index active-session lookups.
- `account_tokens`: id, user_id, token hash, purpose (verification or password reset), expires/used timestamps.
- `projects`: id, owner_id, name, optional description, created/updated timestamps. Index owner_id.
- `sites`: id, project_id, name, latitude, longitude, derived state, confirmed category, optional address, created/updated timestamps. Validate coordinate ranges.
- `predictions`: id, site_id, requester_id, immutable input snapshot, raw estimate, displayed total, model_version_id, extraction_rule_version, POI timestamp, adoption reference year/value, rounding policy, created timestamp, optional request idempotency key. Store the actual location/category in the snapshot so later site edits do not rewrite history.
- `model_versions`: id, version, artifact location/hash, feature-schema version, library/environment metadata, adoption mode/reference year, target formula, evaluation metadata, approval/activation metadata. Activation is an operator-controlled deployment operation.
- `registration_monthly`: state, month, new_registrations, source/import version. Unique state/month/import version; counts nonnegative. Store months as the first day of the month.
- `adoption_lookup`: state, reference_year, vehicle/fuel scope, new_registrations, source hash/version. Unique state/year/scope/version.
- `poi_cache`: request-location key, radius, extraction-rule version, provider/source, feature counts, fetched/expiry timestamps, response provenance. Cache only successful validated responses.

Use JSONB for prediction feature snapshots and model metadata; validate their schema in the backend. Use typed columns for frequently queried ownership keys, dates and numerical outputs. PostgreSQL geographic extensions are optional; add PostGIS if the selected implementation performs meaningful spatial queries or boundary checks in the database.

Prediction history is append-only in the normal interface. Editing a site creates a new prediction on the next request. Project deletion requires owner authentication and confirmation that all child sites and saved predictions are permanently deleted. Site deletion also cascades to its predictions. Foreign keys enforce this policy. Editing a site preserves existing prediction snapshots.

## 6. Ownership and access enforcement

- Every project query is scoped by authenticated owner_id.
- Every site/prediction lookup verifies ownership through its project, including nested routes, exports and mutations.
- Return a consistent not-found response for inaccessible resources without revealing another user's data.
- Never trust a user_id or owner_id sent by the browser. Derive ownership from the session.
- Static source data, registration summaries and model metadata can be shared internally across users; private saved results cannot.
- A shared POI cache must not expose which planner requested an area. Avoid provider debug payloads containing user information.
- Include cross-account isolation tests as a release requirement.

## 7. API contract

All application routes use `/api/v1`. Protected routes require an active verified planner session.

Authentication routes:

- `POST /auth/register`
- `POST /auth/verify-email`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`

Planner routes:

- `GET /projects`, `POST /projects`
- `GET /projects/{id}`, `PATCH /projects/{id}`, `DELETE /projects/{id}`
- `GET /projects/{id}/sites`, `POST /projects/{id}/sites`
- `GET /sites/{id}`, `PATCH /sites/{id}`, `DELETE /sites/{id}`
- `POST /sites/{id}/predictions`
- `GET /sites/{id}/predictions`, `GET /predictions/{id}`
- `GET /reference/site-categories`
- `GET /registrations/monthly` with state/year/month-range filters and comparison mode
- `GET /locations/search` with bounded query length and result count

Prediction requests reference an owned saved site and optionally supply a request idempotency key. Coordinates/category come from the server's current site record. The browser must not supply authoritative POI counts, adoption values, raw predictions, model versions, or totals.

Prediction response includes prediction ID, selected-site snapshot, eight POI counts, state/category, adoption year/value, raw estimate, rounded total, radius, extraction/model versions, creation time, and applicable provisional/limitation information.

Use pagination for lists and ISO 8601 timestamps. Use consistent structured errors with a request ID. Distinguish invalid inputs, unauthenticated access, missing resources, request limits, provider unavailability and inference unavailability. Do not expose stack traces or secrets.

Health routes: `/health/live` checks the process; `/health/ready` checks database connectivity and model readiness. An external POI provider outage must produce clear request errors without restarting otherwise healthy services.

## 8. Feature preparation and POIs

Use the user-confirmed **3,000 metre radius**. Reproduce training tags, geometry/distance handling, group mappings, and deduplication. Recover the original extraction implementation before claiming live feature equivalence.

### Pin, map and Overpass flow

1. Render map tiles and allow pin selection/movement in React. Draw a circle with a ground-distance radius of 3,000 metres; do not interpret a fixed screen-pixel radius as 3 km.
2. On estimate, persist/validate the selected location and confirmed category through the owned-site API, then request `POST /sites/{id}/predictions`. Do not send browser-generated counts as authoritative inputs.
3. FastAPI reads the current owned-site coordinates, validates location support, and checks the versioned POI cache.
4. On a cache miss, the backend constructs an Overpass query using `around:3000,latitude,longitude` and the original eight-group tag mappings. Include the relevant node, way and relation representations required by training; a nodes-only query can miss mapped buildings and complexes.
5. Check provider response status, errors, timeout/truncation indications and expected schema. Apply the training-compatible geometry/distance rules, classification and facility deduplication before calculating the eight counts. Do not assume returned polygon centres alone reproduce the original inclusion method.
6. Derive state, look up the configured 2025 adoption value, build all 11 typed features, and run the approved model/preprocessing pipeline. Apply half-up rounding and save the immutable prediction snapshot.
7. Return counts, prediction and provenance for display. Confirm the response still belongs to the current pin/category selection before presenting it.

The radius circle is visual feedback only; Overpass performs the data query. OSM coverage may omit real facilities, so counts describe mapped qualifying facilities rather than an exhaustive survey. Do not invent tag mappings from MEVnet's 23 site labels: site categories and the eight surrounding POI groups remain separate concepts.

Configure tile provider, geocoding endpoint and Overpass endpoint separately. Permit only configured backend provider URLs, not arbitrary user-supplied fetch targets. Enforce bounded query radius, timeout, response size and concurrency. Cache successful validated extractions and coalesce simultaneous identical lookups where practical. Do not cache a failed or incomplete extraction as eight zeros.

Public OSM tiles and public Overpass endpoints have distinct policies and limited shared capacity. Provider selection must account for expected concurrent planners; use a suitable managed service or dedicated deployment if public-service limits cannot be met. Map service availability is independent of POI service availability. Preserve attribution and avoid heavy automatic queries during dragging.

Deduplication principles: unique OpenStreetMap type/ID; merge clearly matching representations of one facility within a group using reproducible criteria; do not merge distinct facilities merely by proximity or shared coordinates. Never substitute failed requests with zero counts.

Derived state must come from a trusted boundary check or validated provider result, not an arbitrary browser string. Reject unsupported states. Select an explicit urban study boundary before enforcing urban-only support; until then do not claim that all supported-state coordinates are validated urban sites.

Cache keys include radius and extraction-rule version. Avoid rounding coordinates in a way that changes features silently; any cache-location approximation must be defined and tested. Configure TTL and invalidate cache entries when extraction rules change. Set provider request-size/result limits and detect incomplete responses.

## 9. Adoption and trends

Selected model: adoption-enabled Random Forest with 11 inputs:

1. nearby_mall_count
2. nearby_petrol_count
3. nearby_hotel_count
4. nearby_office_count
5. nearby_transit_count
6. nearby_university_count
7. nearby_hospital_count
8. nearby_parking_count
9. category
10. state
11. state_ev_registrations

Current state-context configuration: fixed 2025 totals from electric motokar registrations explicitly recorded in the requested states: SELANGOR 560 and W.P. KUALA LUMPUR 1,237. Validate these against the deployed artifact and source manifest. Missing lookup values fail clearly; do not use zero, another year, or the three-year sum automatically.

These values are filtered new registrations, not complete EV fleet counts. Do not describe the model as learning the full 2024–2026 adoption series or a causal growth response.

Trend imports use 2024/2025 full years and 2026 January–September. Exclude Rakan Niaga and other vehicle/fuel types as documented. Preserve repeated vehicle records. Import scripts validate scope, dates and counts and publish a versioned snapshot transactionally. Chart filters do not alter prediction lookup values.

### Monthly adoption dashboard contract

Reuse the three filtered registration CSVs to build monthly summaries once during a versioned import, not on each dashboard request. Normalise date formats explicitly, derive calendar months, and group by state/month. Track declared source coverage independently of the latest record date; absence of records alone does not establish whether a month is covered.

Add `registration_source_versions` metadata containing import version, per-source hash, fuel/type scope, excluded state policy and coverage start/end. Link monthly rows to this version. The dashboard queries a single active published version, not multiple historical imports together. Use indexes on source version/state/month.

`GET /registrations/monthly` accepts:

- `states`: selected states; default both supported states.
- `years`: selected years among 2024, 2025 and 2026; default all available years.
- `start_month` and `end_month`: optional inclusive YYYY-MM bounds for timeline mode.
- `comparison_mode`: `timeline` or `year_over_year`.
- `calendar_month_start` and `calendar_month_end`: 1–12 inclusive month window for year-over-year mode; default 1–12. Reject incompatible date-bound parameters rather than apply ambiguous filtering.

Validate states/years, bounds and start-before-end. An empty result is a valid response with coverage information, not a provider failure.

Return active filters, source version/scope, coverage per year/state, monthly series, selected-period totals, averages per covered month, and same-period previous-year growth with comparison dates and an availability/reason field. Growth uses `(current - previous) / previous * 100` only when both compared periods are completely covered and the previous count is greater than zero. Previous-period totals may be queried outside the selected display years but must come from the same source version and scope.

For multiple selected years, return growth per individual year/state and eligible common month window; do not apply one percentage to an arbitrary multi-year aggregate. If both states are displayed, return per-state metrics and an explicitly labelled combined total where useful. Every metric states its actual covered period. Averages use covered calendar months; a combined average uses distinct covered months, not the number of state/month rows.

Fill missing state/month rows with zero only inside verified coverage. Outside coverage, return unavailable/null or omit the point with coverage metadata; never zero-fill October–December 2026. Default timeline spans January 2024–September 2026. Year-over-year mode aligns calendar months and distinguishes state/year series. When comparing 2026 against earlier years, offer January–September as the common covered window and label it explicitly.

Frontend state/year/month controls, reset action, chart and summary metrics share one filter state. Cancel or ignore stale responses. Use labelled monthly axes and legends, hover/focus count details, and an accessible data list/table. Display incomplete coverage and unavailable growth reasons without implying zero adoption. The displayed dashboard title can say EV adoption trends, but metric labels must specify new electric motokar registrations.

## 10. Model artifact and rounding

Target: `total_planned_chargers = existing + proposed`, under the authorised additional-chargers assumption. Preserve this limitation in model metadata.

Recover the selected full-run Random Forest configuration for 80/20 plus five-fold training CV, with adoption enabled. Do not deploy the notebook's separately refitted default candidate as though it were the evaluated tuned pipeline. Export the evaluated fitted pipeline or deliberately refit with the selected parameters and retain the original evaluation context.

Use nearest-integer half-up rounding: `max(minimum_count, floor(raw_estimate + 0.5))`, with initial configurable minimum_count 1. Reject non-finite model outputs. The backend owns rounding; the frontend displays its returned integer. Python's ties-to-even `round` is not the agreed rule.

Tests include 3.2 → 3, 3.5 → 4, 3.9 → 4 and minimum handling. Recompute rounded metrics from saved predictions; historical ceiling MAE is not the new strategy's metric.

The current notebook still needs its rounding/radius defaults and provenance text aligned with the latest PRD before new exports. Loading an already trained compatible model does not require retraining solely to change rounding or record the correct existing POI radius.

Keep the artifact outside PostgreSQL as a read-only versioned deployment file or private object-storage object; store its hash and metadata in the database. Load only trusted artifacts because Python model serialisation can execute code during deserialisation.

## 11. Deployment and operations

- Separate development and production configuration. Secrets come from environment/secret storage, never committed files or frontend bundles.
- HTTPS reverse proxy serves the frontend and forwards API traffic. PostgreSQL is not publicly accessible from the browser or general internet.
- Apply migrations as a controlled release step, not simultaneously in every API worker.
- Enable database backups and test restoration. Set retention and recovery targets before production.
- Configure structured logs, request IDs, error monitoring, provider latency/error counts, inference latency, connection usage and resource limits.
- Never log authentication tokens. Avoid persistent precise-location logs unless required with defined retention.
- Start with one API deployment and bounded concurrency. Measure before increasing workers; worker replication duplicates model memory.
- Background queues and Redis are optional future additions if measured workloads require them. PostgreSQL-backed POI caching is sufficient for the initial architecture.

Hosting, map/geocoding/POI providers, email provider, backup recovery targets and numerical latency/concurrency targets remain deployment selections. Do not claim production capacity without a representative load test and provider-quota review.

## 12. Verification and release criteria

- Unit checks: state/adoption mapping, feature schema, target metadata, finite predictions, half-up rounding, cache versioning and registration aggregation.
- API/database integration: migrations, sessions, CSRF, token expiry/reuse, project/site CRUD, immutable prediction snapshots, failed provider handling and idempotent request behaviour.
- Ownership: planner A cannot read, edit, delete or predict against planner B's resources by altering IDs.
- ML parity: known prepared feature fixtures produce the expected raw pipeline outputs and rounded counts in the serving environment; no unapproved feature columns are added.
- Feature parity: application extraction matches the engineered training definitions or is explicitly marked provisional until reconciled.
- End-to-end: individual login → private project → site pin/category → server-side POI/adoption preparation → prediction → saved result → history retrieval.
- Trend verification: monthly totals reconcile with all three filtered sources; state/year/month filters and reset behave consistently; year-over-year alignment uses comparable periods; zero-denominator and missing-period growth are unavailable; genuine covered zero months count in averages; October–December 2026 are not fabricated zeros; active source versions are not double-counted.
- Failure checks: expired sessions, unsupported states, stale frontend requests, POI timeout/incomplete response, missing adoption lookup and unavailable model do not show fabricated successful estimates.
- Load test: exercise concurrent authenticated planners, database pooling and POI quota constraints against an agreed workload before claiming multi-user readiness.

## 13. Immediate implementation prerequisites

1. Obtain the selected adoption-enabled full-run artifact/parameters and its metadata from Colab.
2. Recover original 3 km POI extraction tags/geometry/deduplication for live feature parity.
3. Select urban boundaries, hosting and external providers.
4. Align notebook export configuration with the current rounding policy.
5. Implement individual accounts and ownership before exposing saved project data to multiple planners.


## Stage 4 implementation — 27 October 2026

The active estimator uses Leaflet 1.9.4 with OpenStreetMap tiles and visible attribution. Project workspace offers Add site on map and Open on map; the sidebar estimator starts with a project chooser. Planners can submit an address search, click the map, drag the pin or use numeric coordinates. A 3,000 metre Leaflet Circle follows the pin. Confirm the host-site category before saving; nearby POIs do not determine that category. Saving creates or updates an owned site without running ML.

State is derived server-side from bundled, hash-checked Selangor/Kuala Lumpur state polygons (geoBoundaries MYS ADM1, OSM/Wambacher, 2017, ODbL 1.0). Unsupported/ambiguous boundary points are rejected, including Putrajaya. This is a reproducible research boundary with provisional urban-only coverage, not current cadastral verification. User-supplied state fields are forbidden. Moving the pin invalidates prior validation/saved state, clears the stale address, and requests category reconfirmation.

Address search uses a configurable server-side Nominatim endpoint, explicit submission only, bounded time/response size, provider identification, seven-day successful-result caching and a PostgreSQL global 1.1-second reservation. No autocomplete, searches on every keystroke, or POI/inference on map movement. Search/map failures expose retry/manual alternatives. Browser generation/abort guards prevent late responses replacing current selections. Standard tile requests retain provider attribution, browser caching and origin referrers.

Public OSM/Nominatim endpoints are low-volume development defaults, not a production capacity promise. Configure suitable providers for wider use. Provider details, source hashes, licensing and checks are recorded in docs/STAGE_4_IMPLEMENTATION.md. Existing-site records with unresolved state remain unchanged until a coordinate update; Stage 5/6 must independently validate state before using adoption context.


### Map-only refinement — 27 October 2026

User decision supersedes earlier manual-coordinate alternatives: create and edit sites through the map only. Remove the separate Add site form and inline site editor. Project workspace offers Add site on map and Open on map. Coordinates are displayed read-only; state is derived on the server from the selected pin. Address is reverse-geocoded automatically after the pin settles (1.2 second debounce), or reused from an address search. Name and host-site category remain planner inputs; category is not inferred from nearby facilities.

Reverse lookup shares the existing global provider quota/cache, uses local state polygons rather than the provider's state label, aborts/discards stale responses and can be retried. Save waits for pending address lookup; if lookup fails, address remains optional and the valid pin/state can still be saved. POI/adoption feature extraction remains Stage 5. The observed Not Found response was traced to an older running backend with no location routes; restart once via start.cmd. Local startup now enables source-directory backend reload. User app ports/processes were inspected but not stopped or occupied.


## Stage 5 feature preparation — 27 October 2026

After saving a site, Prepare site context explicitly requests server-side facilities within 3,000 metres. The backend reads the owned site's pin/category, derives its state, gathers eight counts (mall, petrol, hotel, office, transit, university, hospital, parking), and appends fixed 2025 registrations (Selangor 560, KL 1,237), category and state: 11 model fields. Registration context is reconciled from the filtered CSV and packaged with source hash/scope. The 2024–2026 series remains available for the later trends dashboard; it is not dynamically substituted into the model lookup.

Counts/provenance are cached by exact location, radius, rule fingerprint and provider. Provider failures/incomplete results are errors, not zero facilities. Changes cancel or clear displayed context, and backend rechecks site revision/session/ownership after extraction. No inference or saved charger prediction happens at this stage.

Original training extraction definitions are still unavailable. New counting rules are explicitly provisional, with inference_eligible=false; they cannot be claimed equivalent to the training POIs. Original rules plus genuine site parity checks, or consistent POI regeneration and retraining, remain necessary. Live provider availability also remains unverified after TLS/timeout failures. See docs/STAGE_5_IMPLEMENTATION.md for exact tags, geometry, deduplication, cache/error behavior and evidence. Stage 5 is pending that dependency, despite the implemented service/UI.


## Working local data source — 27 October 2026

Latest implementation supersedes the requirement to wait for public Overpass availability. The default `CASTRAVOLT_POI_SOURCE=local` reads the bundled `resources/poi_snapshot.json.gz`, containing 10,981 genuine OSM facility representations from Geofabrik's 25 October 2026 extract. The compact catalogue is 483,026 bytes; source/checksums/coverage/license are in poi_snapshot_manifest.json. It covers the two state geometries plus a >3 km buffer and rejects circles outside its coverage. Local requests make no provider call and do not use the global Overpass cooldown. Cache keys include the snapshot SHA-256; classification/radius/deduplication remain versioned as before.

The full 252,386,711-byte source PBF stays ignored under data/poi/source. Its published checksum was verified, and its SHA-256 is 92e10b7d3d6b415758fa8e5720411fcb20e431e1f7d7f3e1420a2703289edd23. The compact derived database ships in the application package under ODbL 1.0 with OpenStreetMap/Geofabrik attribution. Source timestamp: 2026-10-25T21:21:21Z. This is a dated snapshot, not a real-time facility inventory; rebuilding/restarting is a deliberate data update.

Way bounding boxes are resolved from source node coordinates. Relation bounds include source members and nested relations. Incomplete geometry affecting study coverage aborts the build; radius uses bounding-box centres, matching the documented provisional method. `scripts/build_local_pois.py` is optional build tooling using the separate poi-build group, not a runtime requirement. Native system TLS via truststore repairs the observed Python-vs-Windows validation mismatch while retaining certificate/hostname checks; optional Overpass and address clients use it. Production data/model parity is not certified by this repair.

Verified real catalogue queries: public KLCC and the user's reported saved pin return counts; the latter prepared in approximately 12 ms in a direct local check. Browser QA on isolated 5174/8001 confirmed Prepare site context displays the real eight counts and 560 Selangor registrations. No ML prediction was generated. Original training POI-rule parity remains pending, so inference_eligible stays false. App startup now defaults to source polling for reliable development reload on Windows drives.

Verification: 54 backend tests passed, 24 frontend tests and production build passed. Tests include source integrity/coverage, way/relation geometry, native TLS verification flags, no remote call for local preparation, and successful cache reuse. A wheel check verifies the snapshot/manifest are shipped. No user app process was stopped or app port occupied; temporary browser QA is cleaned up after verification. Existing user process needs one restart using start.cmd to activate the new source.


## Stage 6 experimental serving — 27 October 2026

User-selected layout: prediction output sits directly beneath the map, with facility inputs on the right. Save site → Prepare site context → Generate experimental estimate. The backend uses the selected verified Random Forest and all 11 server-derived features. Display total planned charging points using nearest-half-up and minimum one; retain raw output. No automatic inference on pin movement and no retraining in the application.

Every saved estimate includes immutable site/features/source/adoption/rule/model provenance and the unverified POI status. Request UUID and site revision prevent duplicate/conflicting retries; database uniqueness and final ownership/session/revision checks cover concurrency. Results clear when the draft changes. Site history retains the experimental label and calculation/input details. Model startup checks exact hash/runtime/features/selected parameters and reproduces ten saved fixtures; missing/incompatible models fail visibly.

Original live/training POI-rule parity remains unresolved. The development action explicitly requests an experimental result; it does not change inference_eligible=false or claim model accuracy for the new counts. Production rejects these unverified inputs. Stage 6 validated completion remains pending that dependency. Experimental local workflow passed 66 backend / 27 frontend tests, build and genuine browser-to-history verification. See docs/STAGE_6_IMPLEMENTATION.md.
