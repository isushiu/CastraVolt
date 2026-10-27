# Stage 5 — feature preparation

27 October 2026. Implement inline without subagents.

Deliver an authenticated owner-scoped POST `/api/v1/sites/{id}/features` and an explicit Prepare site context UI action. Read coordinates/category from the saved site, derive state server-side, extract eight POI groups within 3,000 m, attach verified fixed-year 2025 adoption context, and return exactly the model's 11 feature fields with provenance. No ML prediction is generated.

The original extraction code is absent. Infrastructure may be implemented, but **training/live POI parity stays pending**. Use a clearly versioned provisional rule set and return `inference_eligible=false`; no setting silently certifies equivalence. This is an implementation decision to make progress, not a claim that the user supplied the exact mappings. Matching original rules or consistent regeneration/retraining is still necessary before validated inference.

Provisional rules: mall shop=mall; petrol amenity=fuel; hotel tourism=hotel/motel/resort; office office!=no/vacant or building=office; transit railway=station/halt or public_transport=station; university amenity=university; hospital amenity=hospital or healthcare=hospital; parking amenity=parking. Do not use the 23 host-site categories as POI tags. Query nodes/ways/relations with centre output. Count a node location or a way/relation bounding-box centre only if within the geodesic 3 km radius. This representative-point rule is not footprint intersection or a verified match to training.

Deduplicate exact type+ID. Across different types merge only an identical nonempty facility wikidata AND normalized name within 50 m, at most one element per type per facility. Brand tags and proximity alone never merge. Unidentified duplicate representations remain a documented conservative limitation. Groups are counted independently.

Overpass: configurable HTTPS endpoint, fixed tag-only query, server/client time/memory/response/element bounds, explicit complete-result validation, no zero filling of failures, application-wide provider reservation and per-account/IP quotas. Successful-count cache keys include exact coordinates, radius, rule fingerprint and provider; cache stores counts, source timestamp, payload hash and extraction time, with a TTL. Do not hold DB connections while waiting on the provider. Snapshot/recheck site revision and session after remote work.

Verify registration source using a reproducible standard-library script; package only the 2025 state summary/hash and fixed coverage metadata, not raw vehicle records. UI exposes counts/context and a scientific limitation. Clear it on edits. Tests cover classification, radius, duplicates, incomplete responses, adoption reconciliation, caching/errors, isolation and stale edits. Record actual verification and pending provenance before reporting deliverables.


## Delivered implementation

- `src/castravolt/features.py`: Overpass query/client, strict complete-response parser, eight-group classification, deduplication, typed 11-feature schema, adoption lookup and owned-site context endpoint. Successful provider results need a valid OSM timestamp and matching final `out count` sentinel; partial/error/truncated/malformed results cannot become zeros.
- `feature_models.py` and migration `0005_poi_cache`: successful counts/provenance cache with coordinate/radius/rules/provider keys and expiry. Global provider lease uses PostgreSQL across workers, plus account/IP quotas. Connection is returned before remote I/O. Session, ownership and site revision are rechecked after provider work.
- `scripts/prepare_adoption_context.py` and packaged `resources/adoption_2025.json`: reproducible reconciliation of filtered 2025 electric motokar, source SHA-256 and scope. Verified 560 Selangor / 1,237 W.P. Kuala Lumpur. No raw registration records need to be exposed to the browser.
- Frontend `FeatureContext.tsx` and estimator integration: after saving a site, explicitly prepare its context. Display eight facility counts, fixed-year state registrations, extraction source/time and cache provenance. Edits clear/cancel prior context. No ML model is called, and no prediction/history row is created.

## Scientific status

Infrastructure implemented; original training/live POI parity is **pending dependency**. Original tag/geometry/deduplication definitions were not found in the workspace. The user asked what those were; they were explained, not supplied or confirmed. Current rules remain a documented engineering proposal with `inference_eligible=false`. Do not change that flag to true based only on a successful request. To establish parity, recover original extraction definitions and reproduce genuine training-site fixtures, or regenerate training POIs with one consistent versioned method and retrain/re-evaluate.

`shop=mall` is not all shopping-related places; transit means station/halt rather than every bus stop. Bounding-box centres are not footprints or centroids. Cross-representation merging requires shared facility wikidata + normalized name within 50 m, never brand identity or proximity alone. Unidentified duplicates may remain; features can differ from engineered training counts and from real facility inventories. All source assumptions remain visible.

## Live provider verification

No successful live POI payload was obtained during this run. One request to overpass-api.de failed TLS certificate verification; certificate checks were not bypassed. The alternate OSM-listed Private.coffee instance timed out for the bounded extraction and a small diagnostic request. Default is configurable Private.coffee (TLS handshake did not fail); no automatic provider-hopping or repeated bulk retries. Service tests use explicit fixtures, not falsely labelled real data. End-to-end live availability and genuine training-site feature parity therefore remain unverified. No `STAGE_5_LIVE_CHECK.json` success record was fabricated.

Provider references: https://wiki.openstreetmap.org/wiki/Overpass_API (public instances and usage), https://dev.overpass-api.de/command_line.html (query input), https://dev.overpass-api.de/overpass-doc/en/preface/commons.html (public resource limits). Private.coffee is listed at https://overpass.private.coffee/ . For wider use, provision an appropriate service. Provider failures return visible retry errors, not zero counts.


## Final verification

47 backend tests passed, including feature-order equality with the evaluated model manifest, classification/radius/duplicates, completeness checks, unknown adoption state, own-site cache reuse, provider failure without zero-cache poisoning, stale-site rejection and foreign-account access rejection before provider work. 22 frontend tests passed, including explicit-only preparation and clearing context after a pin change. Frontend production build passed. Registration preparation independently reproduced both configured state totals. `git diff --check` passed.

All PostgreSQL integration checks used uniquely named disposable databases. No application ports were occupied or user app processes stopped. No source CSV, model artifact or training POI values were changed. No charger prediction was produced. Restart the app with start.cmd to apply migration 0005 before trying Prepare site context. Stage remains pending the scientific/provider checks described above.


## Provider failure follow-up — 27 October 2026

Reproduced the user's failure: configured Private.coffee status endpoint times out before any POI query. Explicit IPv4 curl also timed out with HTTP 000/no response; the issue was not resolved by IPv4. overpass-api.de failed TLS certificate verification and an OSM-listed alternate status endpoint also timed out. External web status checks timed out too. No certificate validation was disabled and no successful live extraction is claimed.

Implementation now classifies network failures, socket timeouts (504), TLS verification failure, upstream overload and incomplete responses. Return only safe actionable messages; log exception class/status/request ID rather than raw sensitive details. Retry-After propagates to the client and the context button shows a countdown. Cached successes are checked before reservations.

The 35-second in-flight provider lease now has a random ownership token. Completion shortens it to two seconds; connection/timeouts/incomplete responses use a shorter ten-second retry, TLS failure thirty seconds and upstream overload respects the bounded reported delay (minimum thirty seconds). Blocked callers receive the actual remaining wait rather than a fixed 35 seconds. A late response cannot shorten a newer request's lease. Provider service availability remains an external unresolved limitation; these changes do not repair an unreachable endpoint or establish training-feature parity.


## Working local data source — 27 October 2026

Latest implementation supersedes the requirement to wait for public Overpass availability. The default `CASTRAVOLT_POI_SOURCE=local` reads the bundled `resources/poi_snapshot.json.gz`, containing 10,981 genuine OSM facility representations from Geofabrik's 25 October 2026 extract. The compact catalogue is 483,026 bytes; source/checksums/coverage/license are in poi_snapshot_manifest.json. It covers the two state geometries plus a >3 km buffer and rejects circles outside its coverage. Local requests make no provider call and do not use the global Overpass cooldown. Cache keys include the snapshot SHA-256; classification/radius/deduplication remain versioned as before.

The full 252,386,711-byte source PBF stays ignored under data/poi/source. Its published checksum was verified, and its SHA-256 is 92e10b7d3d6b415758fa8e5720411fcb20e431e1f7d7f3e1420a2703289edd23. The compact derived database ships in the application package under ODbL 1.0 with OpenStreetMap/Geofabrik attribution. Source timestamp: 2026-10-25T21:21:21Z. This is a dated snapshot, not a real-time facility inventory; rebuilding/restarting is a deliberate data update.

Way bounding boxes are resolved from source node coordinates. Relation bounds include source members and nested relations. Incomplete geometry affecting study coverage aborts the build; radius uses bounding-box centres, matching the documented provisional method. `scripts/build_local_pois.py` is optional build tooling using the separate poi-build group, not a runtime requirement. Native system TLS via truststore repairs the observed Python-vs-Windows validation mismatch while retaining certificate/hostname checks; optional Overpass and address clients use it. Production data/model parity is not certified by this repair.

Verified real catalogue queries: public KLCC and the user's reported saved pin return counts; the latter prepared in approximately 12 ms in a direct local check. Browser QA on isolated 5174/8001 confirmed Prepare site context displays the real eight counts and 560 Selangor registrations. No ML prediction was generated. Original training POI-rule parity remains pending, so inference_eligible stays false. App startup now defaults to source polling for reliable development reload on Windows drives.

Verification: 54 backend tests passed, 24 frontend tests and production build passed. Tests include source integrity/coverage, way/relation geometry, native TLS verification flags, no remote call for local preparation, and successful cache reuse. A wheel check verifies the snapshot/manifest are shipped. No user app process was stopped or app port occupied; temporary browser QA is cleaned up after verification. Existing user process needs one restart using start.cmd to activate the new source.
