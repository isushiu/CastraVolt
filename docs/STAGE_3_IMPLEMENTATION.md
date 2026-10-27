# Stage 3 — internal planning workspace

27 October 2026. User requested a shared internal demo login (`admin` / `123`) instead of public registration, followed by the existing Stage 3 contract.

Implementation decisions: retain database-backed hashed passwords, sessions, CSRF and owner-scoped data. Internal access is the default development mode; public account-creation/recovery endpoints are disabled in that mode. The admin row is inserted once on successful first login, preserving its ID and projects on subsequent starts. Existing individual-account code/data is retained for future use. Production configuration rejects this demo mode.

Deliver projects and manually saved sites with CRUD, validated fields, owner checks and cascading deletion (with visible confirmation). State stays unresolved until trusted map/boundary integration; never infer state from a browser input. Categories use the 23 agreed labels plus Unknown. History schemas/read endpoints preserve snapshots but no browser endpoint creates pretend predictions. Map selection is Stage 4, live inference Stage 6.

Execution: (1) test internal login and CRUD/isolation/validation; (2) implement migration and API; (3) connect Projects/workspace/site/history screens; (4) update PRD/TRD/README; (5) run PostgreSQL and frontend verification and review. Use disposable test databases and do not occupy user ports 8000/5173. No Git commit requested.

Complete for local development. User started Docker; integration suites used disposable databases. Final backend suite: 30 passed. Frontend: 11 passed; production build passed. Browser QA on 5174/8001 verified admin sign-in → new project → saved site/category/coordinates → reload persistence → empty history. Temporary services and their database were removed. Existing app ports were not used.

Verification also covers saved prediction snapshot preservation after site edits, real prediction ID isolation, deletion cascades, null/unknown-field validation, CSRF, Unicode incorrect passwords and production rejection of shared demo access. Test-only prediction rows were seeded directly in disposable databases; the application does not generate fake results.

Review finding fixed with a failing-then-passing regression test: workspace actions are disabled during a pending site save, preventing another editor's draft from being discarded. Remaining checks were completed inline after the user requested no subagents. No Git commit created.

Next: Stage 4 map/search/pin/3 km circle and trusted location validation. Actual inference remains Stage 6, subject to original POI extraction parity. Existing deployments must restart through start.cmd to apply migration 0003. Admin account is created on first successful login, without replacing an existing account.
