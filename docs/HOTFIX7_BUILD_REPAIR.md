# Hotfix 7 frontend build repair

The first Hotfix 7 package introduced `useSearchParams()` directly in the `/master-data` and `/exceptions` client pages for deep-link context. In Next.js 15 production builds this can trigger the prerender/Suspense build guard and stop `next build`.

The repaired Hotfix 7 package preserves the same deep-link behavior but reads query parameters inside the client-side effect through `window.location.search`, eliminating the production-build Suspense requirement while retaining the same UX.

Affected routes:
- `/master-data?domain=...`
- `/exceptions?code=...`

No database, API contract, or business calculation behavior was changed by this repair.
