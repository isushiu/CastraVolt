# Stage 4 — proposed site on a map

27 October 2026. Execute the existing Stage 4 contract inline; no subagents.

Choices: Leaflet 1.9.4 with standard OpenStreetMap HTTPS tiles and visible attribution. Use a server-side Nominatim proxy for explicit submitted address searches only, no autocomplete or search on map movement. Apply application-wide PostgreSQL coordination, bounded requests, identifying User-Agent and persisted successful-result caching to respect the public service's maximum one request/second. Providers are configurable; public endpoints are a low-volume development default, not a production capacity promise.

Derive Selangor / W.P. Kuala Lumpur from versioned, bundled state polygons on the server. Do not trust a browser-supplied state or use a rectangular approximation as a state boundary. Document source, license and hash. Urban-only validation remains provisional: administrative boundaries do not establish urban land use.

UI: project-aware estimator with search results, click-to-select map, draggable accessible marker, Leaflet Circle radius=3000 metres, manual coordinate alternative, confirmed host-site category, selected address/state summary and save/update. Existing project/site editor remains available; add map links for new/existing sites. Sidebar estimator asks the planner to select a project. Changes clear saved/validation status immediately; generation/abort guards prevent stale searches, validation or saves from overwriting a newer selection. No Overpass or inference call in Stage 4.

Checks: state/geometry fixtures including holes and unsupported points; authenticated and owner-scoped APIs; missing/failed geocoder handling and rate/cache behavior; editor stale-response tests; frontend production build; real local browser flow on alternate ports. Preserve previous data, never create fake ML results. Update plan/PRD/TRD and record limitations on completion.

Implementation delivered: Leaflet/SVG pin/metre-radius circle, project chooser and new/existing site estimator, explicit search and coordinate alternative, confirmed category, state validation and owner-scoped save/update. Moving a pin clears the address, saved status and confirmation. Search and validation requests are cancelled/guarded against stale responses. Repeated edits after first save update the same site instead of adding duplicates.

Boundary source: geoBoundaries `MYS-ADM1-15666254`, pinned commit 9469f09, 2017 geometry built December 2023. Bundled Selangor/Kuala Lumpur subset is 167,166 bytes, with original/subset SHA-256, hash check on load and source/license metadata in src/castravolt/resources. Original license is ODbL 1.0 (OpenStreetMap/Wambacher); retain attribution. State geometry is a research boundary, not current cadastral or urban-land-use certification.

Geocoder: Nominatim HTTPS search, Malaysia and Klang Valley view box, max eight results filtered by actual state polygons, 8-second socket timeout and 256 KB response limit. PostgreSQL atomic global reservation allows at most one outgoing search per 1.1 seconds across workers. Successful results (including genuine empty lists) cache for seven days; errors return 503 and are not cached as success. Per-IP/account quotas remain. No DB connection is held during the provider call. Migration 0004 adds the cache. Browser tile requests honor normal caching and strict-origin-when-cross-origin referrers; no prefetch or bulk download.

Complete for local development: final 35 backend tests and 17 frontend tests passed; production build passed. Live browser confirmed real KLCC search, OSM tiles, pin/circle, server-derived KL state, category confirmation, save, drag invalidation, same-site update (still one row), and reopening saved geometry. No POI or inference endpoint called. Temporary QA uses disposable PostgreSQL and ports 5174/8001.

Remaining scientific/operational limitations: urban-only polygon unselected; boundary represents 2017; public tile/search endpoints have no production SLA. Provision an appropriate service before larger usage. No current-location/geolocation permission or external model/data upload is involved. Stage 5 remains dependent on original POI feature parity.


Final inline review fixed a login return-link race: both authenticated redirect and successful-submit navigation now use the same validated internal destination, preserving estimator project/site query parameters and rejecting external origins. Regression tests cover both cases. Boundary JSON integrity is checked before state resolution. Existing ownership and snapshot tests continue to pass. Responsive CSS is included; separate mobile-browser accessibility checks remain Stage 8.

QA preview and disposable database cleaned up; ports 8000/5173 untouched. No Git commit or external deployment created. Next is Stage 5, which must recover original POI extraction definitions before claiming live feature parity.


### Map-only refinement — 27 October 2026

User decision supersedes earlier manual-coordinate alternatives: create and edit sites through the map only. Remove the separate Add site form and inline site editor. Project workspace offers Add site on map and Open on map. Coordinates are displayed read-only; state is derived on the server from the selected pin. Address is reverse-geocoded automatically after the pin settles (1.2 second debounce), or reused from an address search. Name and host-site category remain planner inputs; category is not inferred from nearby facilities.

Reverse lookup shares the existing global provider quota/cache, uses local state polygons rather than the provider's state label, aborts/discards stale responses and can be retried. Save waits for pending address lookup; if lookup fails, address remains optional and the valid pin/state can still be saved. POI/adoption feature extraction remains Stage 5. The observed Not Found response was traced to an older running backend with no location routes; restart once via start.cmd. Local startup now enables source-directory backend reload. User app ports/processes were inspected but not stopped or occupied.


### Pin name refresh — 27 October 2026

Moving or reselecting the pin clears the previous site name and refreshes it from the new search/reverse-geocoding result. No name is carried across locations. A name entered manually while the current pin lookup is pending is preserved. If no name is returned (or lookup fails), show a small indication asking the planner to enter one; saving still requires a nonblank name. Existing saved names are preserved when opening a site until its pin is moved. Regression coverage checks moving between named places and then to an unnamed spot.
