# Stage 7 adoption dashboard implementation plan

> Execute inline using superpowers:executing-plans; user requests no subagents.

Goal: deliver the approved option 2: Chart.js monthly registration dashboard plus optional cached Groq explanations.
Architecture: versioned packaged monthly import into PostgreSQL; authenticated filter API calculates all facts; React Chart.js displays timeline/year-over-year and accessible rows; explicit summary POST uses shared persistent cache.
Spec: PRD section 8, TRD monthly adoption contract, user-approved option 2.

- [x] Import scope: electric/motokar, Selangor/KL, 2024/2025 full years and 2026 Jan–Sep. Hash source files, zero-fill only covered months, reconcile counts. Package aggregate data only.
- [x] Add registration version/month tables and summary cache migration; active version publication is atomic. Add repeatable import command and seed current snapshot on migration.
- [x] Build validated filters (state, years, timeline dates or calendar months), monthly series, totals/averages and per-year matching-period growth. Test unknown coverage, zero denominator and invalid filters.
- [x] Groq backend configuration: secret key in ignored .env only, fixed HTTPS endpoint, configurable model, bounded response/time/tokens. Send aggregates only after explicit action. Cache key includes source version, canonical filters, model and prompt version; leases prevent duplicate concurrent calls. Failures leave charts usable and do not cache invented prose. Never log keys/provider bodies.
- [x] Replace placeholder with Chart.js line chart, filters/reset, comparison view, metric cards, source/coverage notes, data table and optional summary panel. Clear stale results and cancel requests on filter changes.
- [x] Verify data reconciliation, authenticated API, cache hits/concurrency/version invalidation/failures, frontend tests/build and isolated browser flow without user ports. Document deliverables, API-key setup and limitations.

Rulings: reuse across accounts is safe because only public state/month aggregates enter the summary. A summary does not expire merely because time passes; dataset/model/prompt/filter changes change its identity. LLM output is explanatory, never a source of numeric dashboard metrics. Missing model artifacts from Stage 6 do not block independent Stage 7 delivery.

Verification: 43 selected backend tests and 32 frontend tests passed; production build passed with Chart.js split into the trends route. Browser QA confirmed both chart modes and the Jan–Sep comparison. Temporary services/database cleaned up. Real Groq calls intentionally not made.
