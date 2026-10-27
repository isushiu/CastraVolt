# Integrate the verified 1 km POI/category/state model

User authorised updating the app and producing backlog/results. Implement inline without subagents. Preserve the current user app processes/ports and all historical prediction records.

- [x] Change current extraction/model feature contract to 1,000 m and ten inputs; keep the bundled catalogue intact and invalidate old-radius caches.
- [x] Bind the selected evaluated RF artifact to its 1 km rule hash and OSM snapshot; verify fixtures/runtime/parameters at startup. Update portable default and local model-path setting.
- [x] Remove adoption from new feature/prediction requests and snapshots. Make legacy prediction adoption columns nullable via migration; preserve older history.
- [x] Require matching extraction provenance before prediction. Keep research-model acknowledgement/development restrictions and honest capacity limitations; replace obsolete POI-parity wording.
- [x] Update map circle, context/results/history UI and generated API types.
- [x] Verify model fixtures, real site features, ownership/CSRF/retry/stale edit behaviour, frontend tests/build and isolated browser flow.
- [x] Produce BACKLOG.md and RESULTS.md with actual deliveries, checks, measured model limits and outstanding work.

Ruling: the OSM catalogue is spatially reusable at 1 km. Its existing build-rule identity must stay distinct from the new query-radius rule hash; changing the gzip merely to rename its metadata would break the training snapshot identity. No fabricated counts or fallback model.

Ruling: inference eligibility means feature-contract compatibility, not scientifically established optimal capacity. New snapshots record POI parity true only when radius, rule and snapshot match; model status remains research prototype.
