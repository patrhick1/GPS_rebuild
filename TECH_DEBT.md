# GPS Platform — Tech Debt Sweep

**Date started:** 2026-04-29
**Stack:** FastAPI (Python) + React/TypeScript (Vite) + PostgreSQL on Render
**Cross-references:** [SECURITY_ASSESSMENT.md](./SECURITY_ASSESSMENT.md), [GAP_ANALYSIS.md](./GAP_ANALYSIS.md)

> **Row format:** `[severity] [subsystem] [file:line] — issue → proposed fix → effort`
> **Severity:** `P0` blocks launch · `P1` pre-launch window · `P2` post-launch · `[fp]` false positive (give reason) · `[noise]` known harmless (give reason) · `[TBD]` not yet triaged
> **Effort:** `S` <1h · `M` ~½ day · `L` 1+ day

---

## 1. Summary

161 tech-debt findings, **14 of them P0 (blocking launch)**. The P0 cluster is small but high-impact: a one-line privilege-escalation in `MemberUpdate`, a missing `FRONTEND_URL` in render.yaml that breaks every email link in production, an HTML-injection vector in every email template, no Stripe webhook idempotency (double-charges + silent event drops on retry), the Stripe SDK 14 API change silently writing `None` to subscription period dates, slowapi seeing only Render's proxy IP (so login rate-limit is global instead of per-user), CSV exports unprotected against formula injection, and the access token sitting in localStorage with no CSP. A decoy in the codebase is well covered: existing audit-log decorator, password-policy validator, and rate-limit module are good — the gaps are in **using** them consistently. The recommended fix sequence is 8 batched commits (≈1-1.5 person-weeks for all P0s); P1 work groups into ~12 named batches that map cleanly to PRs. Cross-references: this document supersedes neither `SECURITY_ASSESSMENT.md` nor `GAP_ANALYSIS.md`; the `Fix Before Production` items in SECURITY_ASSESSMENT are subsumed here as P0/P1 with concrete fix proposals.

**Pass status:**
- [x] Pass 1 — Tooling (38 [TBD], 7 [fp], 3 [noise])
- [x] Pass 2 — Manual sweep across 11 subsystems (123 [TBD], 5 [fp], 11 [noise])
- [x] Pass 3 — Triage (14 P0 / ~80 P1 / ~67 P2)

**Top P0s, one-line each:**
1. ~~Admin can promote member to "master" via PUT /admin/members~~ ([2.5](#25-admin--master)). **(DONE: B3)**
2. ~~Production emails link to `localhost` — `FRONTEND_URL` not set in render.yaml~~ ([2.9](#29-background-jobs--external-services)). **(DONE: B1)**
3. ~~Production emails sent from `noreply@giftpassionstory.com` — Resend domain on `disciplesmade.com`~~ ([2.3](#23-notifications--email)). **(DONE: B1)**
4. HTML injection in every email template via raw f-string interpolation ([2.3](#23-notifications--email)).
5. ~~Account deletion has no password reauth~~ ([2.1](#21-auth)). **(DONE: B3)**
6. ~~Rate limiter sees Render proxy IP — every limit is one global bucket~~ ([2.1](#21-auth)). **(DONE: B2)**
7. ~~Stripe webhook has zero idempotency — duplicate Payment rows on every retry~~ ([2.2](#22-payments--stripe)). **(DONE: B5)**
8. ~~Stripe webhook returns 200 on handler errors — silently drops events~~ ([2.2](#22-payments--stripe)). **(DONE: B5)**
9. ~~Subscribe is non-atomic across double-click — orphan Stripe sub keeps charging~~ ([2.2](#22-payments--stripe)). **(DONE: B5)**
10. Stripe SDK v14 broke `current_period_*` access — silent None writes throughout billing ([2.2](#22-payments--stripe), [2.1](#21-auth)).
11. CSRF via cookie-fallback auth on Form-encoded endpoints ([2.1](#21-auth)).
12. Access token stored in localStorage despite "memory only" comment + no CSP ([2.10](#210-ui-patterns)).
13. CSV exports unprotected against formula injection — `sanitize_for_csv` defined but never called ([1c](#1c-unused-code--deps), [2.5](#25-admin--master)).
14. ~~`require_master` uses `memberships[0]` — non-deterministic master check~~ ([2.1](#21-auth), [2.5](#25-admin--master)). **(DONE: B3)**

---

## 2. Pass 1 — Tooling

### 1a. Typecheck

**Web** — `npx tsc --noEmit` from `web/`. **Clean, 0 errors.** TypeScript 5.6, project uses strict mode via `tsconfig.json`. (Note: `npm run build` also runs `tsc` first, so this is enforced today.)

**API** — `python -m mypy --ignore-missing-imports --no-strict-optional --check-untyped-defs api/app`. **437 errors in 16 files.** Categorization:

- `[noise]` [api/typecheck] api/app/**/*.py — ~410 errors of shape `Incompatible types: Column[X] vs X` and `Argument has type Column[X], expected X` → SQLAlchemy 2.0 ORM descriptors are typed as `Column[T]` without the `sqlalchemy.ext.mypy.plugin`; at runtime descriptor protocol returns the unwrapped value. **Why noise:** runtime is correct; pure type-system gap. → fix later by adding `mypy_path` + `plugins = ["sqlalchemy.ext.mypy.plugin"]` to a new `mypy.ini` (M effort, post-launch). → S
- `[TBD]` [api/billing] api/app/services/stripe_service.py:93-94 — `Subscription` has no attribute `current_period_start`/`current_period_end` (also at `services/stripe_service.py:180`, `dependencies/auth.py:360-362`, `routers/billing.py:137-139`, `routers/billing.py:170+` — 8 sites total). Stripe Python SDK 14 removed these top-level attrs; they moved to `subscription["items"]["data"][0]["current_period_start"]`. Code uses `subscription.get("current_period_start")` truthy-check which now silently returns `None`, so DB row gets `current_period_start=None` and the period-end check in subscription gating returns the wrong value. → Read period from `subscription["items"]["data"][0]` (or `subscription.items.data[0]`), update all 8 sites, add a regression test mocking the v14 payload → M
- `[TBD]` [api/billing] api/app/services/stripe_service.py:180 — `type[Invoice]` has no attribute `upcoming_preview`. Stripe SDK 14 renamed `Invoice.upcoming` to `Invoice.upcoming_preview`? Verify against current SDK; either way the attr access here will `AttributeError` at runtime. → Verify SDK ref + update. → S
- `[TBD]` [api/billing] api/app/services/stripe_service.py:130 — `Incompatible return value type (got "T", expected "Subscription")`. Generic-bound mismatch. → Investigate, likely just an annotation fix. → S
- `[TBD]` [api/auth] api/app/dependencies/auth.py:377 — `get_optional_user` is sync `def`, returns `User | None`, but its body returns `get_current_user(request, credentials, db)` which is `async def`. Returning a coroutine where a `User | None` is expected. **Today FastAPI auto-awaits via `Depends()` so the bug is masked**, but any direct call (tests, internal code) gets a coroutine instead of a User and will misbehave. → Make `get_optional_user` `async` and `await` the inner call → S
- `[TBD]` [api/auth] api/app/services/auth_service.py:433 — Returning `ColumnElement[bool]` instead of `bool`. Likely a `User.is_active == True` comparison returned without scalar evaluation. → Verify; if comparing column expression instead of attribute, fix with `bool(user.is_active)` or proper attribute access → S
- `[TBD]` [api/admin] api/app/routers/admin.py:342-366 — `MyImpactGradedResult` no attr `gifts/passions/abilities/people/causes/stories/top_gifts/top_passions` errors. Caused by mypy not narrowing through the `if instrument == "myimpact"` branch (the `else` branch correctly uses `ScoringService` and `GradedAssessmentResult`). **Runtime is correct.** → Refactor to two functions or use `cast(ScoringService, ...)`/`assert isinstance` for type narrowing → S [fp on runtime, real on type debt]
- `[TBD]` [api/assessments] api/app/routers/assessments.py:533-574 — Same type-narrowing issue as admin.py:342-366 in `submit_assessment`. → Same fix pattern → S [fp on runtime]
- `[TBD]` [api/master] api/app/routers/master.py:190, 259 — `List comprehension has incompatible type List[dict[str, Any]]; expected List[ChurchAdmin]`. Response model expects `ChurchAdmin` Pydantic objects but code returns raw dicts. **At runtime FastAPI will validate dict→ChurchAdmin so this likely works**, but the annotation drift hides whether all required fields are present. → Construct `ChurchAdmin(...)` explicitly or use `model_validate` → S
- `[TBD]` [api/admin] api/app/routers/admin.py:669 — `failed: list[dict[str, str]]` returned where `list[FailedInvite]` expected. Same dict→Pydantic implicit-validation pattern. → Same fix → S
- `[TBD]` [api/data] api/app/db_seed.py:167 — `"object" has no attribute "id"`. Untyped variable from a generic helper. → Add type annotation → S
- `[TBD]` [api/assessments] api/app/routers/assessments.py:168 — Returning `Column[int]` from a function expecting `SupportsDunderLT[Any]`. Likely `return query.scalar()` returning the column rather than the value. → Verify scalar extraction → S
- `[noise]` [api/main] api/app/main.py:23 — `add_exception_handler` signature mismatch with `slowapi.RateLimitExceeded`. Known starlette/slowapi typing gap. **Why noise:** documented slowapi pattern, runtime is correct. → No fix.

**Action item from this pass:** the Stripe `current_period_start/end` cluster is the most concerning real finding — bumped to Pass 2 payments review.

### 1b. Lint

**Web** — `npx eslint src --ext .ts,.tsx` (config: `web/.eslintrc.cjs`, new). **126 problems: 46 errors, 94 warnings.**

- `[TBD]` [web/ui] web/src/pages/Dashboard.tsx:29, AdminDashboard.tsx:121, MasterDashboard.tsx:223, VerifyEmailCallback.tsx:15 — `react-hooks/set-state-in-effect`. Synchronous `setState` inside `useEffect` body causes cascading renders. Not a bug but a perf smell. → Refactor to derived state or move to event handlers → S each
- `[TBD]` [web/ui] web/src/pages/AssessmentResults.tsx:128, MyImpactResults.tsx:76, UpdateLocale.tsx:26 — `react-hooks/exhaustive-deps`. Effects with missing deps. **UpdateLocale.tsx:26 uses `user, updateLocale, searchParams, navigate` with `[]` deps — design intent is one-shot mount handler so this is `[fp]` for behavior, but the rule is right that the closure could go stale if React invalidates.** AssessmentResults/MyImpactResults are likely real (missing `navigate` could fail on retry). → Add `// eslint-disable-next-line react-hooks/exhaustive-deps` with justification on UpdateLocale, fix the others. → S
- `[TBD]` [web/ui] ~30 sites use `any` (Dashboard, MasterDashboard, BillingDashboard, AuditLog, Forms) — type debt. → Replace with proper API response interfaces (most match existing schemas in `web/src/data/`); `M` overall to clean
- `[TBD]` [web/ui] ~10 `react/no-unescaped-entities` errors (apostrophes in JSX text) — cosmetic. → `--fix` or escape manually → S
- `[TBD]` [web/ui] Unused vars in Login.tsx:32, Register.tsx:69-72, ChurchRegister.tsx:58, SystemExport.tsx:90 — destructured form fields not yet wired. **Suggests incomplete features** (`confirmPassword`, `country`, `city`, `state` in `Register.tsx` — verify whether registration form sends these but server ignores, or vice versa). → Pass 2 will check; flag for now → S to investigate

**API** — `python -m ruff check api/app --output-format=concise`. **74 errors found.**

- `[TBD]` [api/cleanup] api/app/**/*.py — 19× `F401 imported but unused` across security.py, auth.py, models/*.py, routers/*.py, services/*.py, schemas/*.py. → `ruff check --fix` resolves all 19 → S
- `[fp]` [api/cleanup] api/app/**/*.py — 18× `E712 Avoid equality comparisons to True/False` flagged in `dependencies/auth.py:248,267`, `auth_service.py:316,454`, `routers/admin.py:477,496`, `routers/billing.py:80,104,223,322,405,462,526,559`, `routers/master.py:569`, `routers/auth.py:77`. **Why fp:** SQLAlchemy filter DSL requires `Column == True/False` to compile to SQL — switching to `if not Membership.is_primary_admin:` would generate broken queries. → No fix; add `# noqa: E712` or set ruff config to ignore E712 in `routers/`/`services/`
- `[TBD]` [api/cleanup] api/app/routers/dashboard.py:560 — `E711 Comparison to None should be cond is not None`. Need to verify whether this is in a filter (then [fp]) or in regular Python (then real). → Inspect → S
- `[noise]` [api/cleanup] api/app/routers/assessments.py:7-35 — 18× `E402 Module level import not at top of file`. Caused by `logger = logging.getLogger(__name__)` placed before the bulk of imports. **Why noise:** harmless ordering issue. → Move logger declaration after imports → S
- `[TBD]` [api/cleanup] api/app/db_seed.py:178 — `F811 Redefinition of unused Question from line 14`. Variable shadowing the imported `Question` model. → Investigate → S
- `[TBD]` [api/cleanup] api/app/routers/master.py:1156 — `F841 Local variable year_start is assigned to but never used`. Suggests an incomplete feature (year-bucket metric not wired). → Pass 2 will revisit → S
- `[TBD]` [api/billing] api/app/routers/billing.py:80,104,223,322,405,462,526,559 — `E712` cluster on `is_primary_admin == True`. **All in queries — fp** (see above). Pattern repeats 8× — sign that the gating check should be a helper function. → Extract `_user_is_primary_admin(user_id, org_id)` helper → S

### 1c. Unused code / deps

**Web — `npx knip` (knip 4.6 — knip 5 not tested; pinned to 4 per plan precaution).**

- `[TBD]` [web/cleanup] web/src/components/AssessmentHistory.tsx + AssessmentHistory.css — entire component unreferenced anywhere. Note `DashboardContext.tsx` defines a `type AssessmentHistoryItem` (different thing); no imports of this component file. → Delete file + matching `.css` → S
- `[TBD]` [web/cleanup] web/src/components/ChurchLinking.tsx + ChurchLinking.css — same. → Delete → S
- `[fp]` [web/cleanup] web/package.json devDeps `depcheck`, `rollup-plugin-visualizer` flagged unused — **why fp:** newly added in this sweep, visualizer wired in 1f, depcheck is a CLI used in ad-hoc audits.

**Web — `npx depcheck --json`.**

- `[fp]` [web/build] devDeps `autoprefixer`, `postcss`, `tailwindcss` flagged unused — **why fp:** consumed via `postcss.config.js` + `tailwind.config.js` (not direct imports).
- `[TBD]` [web/build] web/tsconfig.json:10 — file contains JSON5-style comments (`/* Bundler mode */`, `/* Linting */`). `tsc` tolerates them (TS-flavored JSON), but **strict JSON parsers reject the file** (depcheck's parser broke here). Affects any tooling that reads tsconfig as plain JSON (CI, deployment manifest validators). → Either rename to `tsconfig.jsonc` (and update any references) or strip the comments → S
- No missing deps. Good.

**API — `python -m vulture api/app --min-confidence 60`.**

- `[fp]` [api/cleanup] api/app/routers/admin.py:69-984, master.py, billing.py, assessments.py — ~70 "unused function" hits — **why fp:** all are FastAPI route handlers registered via `@router.<verb>(...)` decorators; vulture can't see the call graph through the registration.
- `[fp]` [api/cleanup] api/app/models/*.py — many "unused variable" hits on Column / relationship attrs — **why fp:** SQLAlchemy ORM attrs accessed via descriptor protocol from queries.
- `[TBD]` [api/security] api/app/core/sanitization.py:37 — `sanitize_for_csv` is **defined but never imported or called anywhere in the codebase**. This means **CSV exports have no protection against CSV injection** — a malicious display name like `=cmd|'/c calc'!A1` would render as a formula in Excel/LibreOffice when the church admin opens the export. → Audit every CSV export endpoint and apply `sanitize_for_csv` to any string field that could come from user input (names, emails, notes, story answers) → M (Pass 2 confirms exact endpoints — see 'Tests / data export' subsystem)
- `[TBD]` [api/auth] api/app/dependencies/auth.py:370 — `get_optional_user` defined but never used. Same function flagged in 1a as buggy (returns coroutine instead of awaiting it). → Delete the function entirely; if optional-auth pattern is needed later, build it correctly → S
- `[TBD]` [api/cleanup] api/app/core/exceptions.py:35 — `handle_exception` defined but never imported (also flagged by ruff F401 in billing.py). → Delete or wire it up → S
- `[TBD]` [api/cleanup] api/app/core/password_policy.py:287 — `validate_password` (the standalone function, separate from class method) — verify usage. → Inspect → S
- `[TBD]` [api/cleanup] api/app/routers/master.py:721 — unused local `http_request` (vulture 100% confidence). → Remove → S
- `[noise]` [api/cleanup] api/app/models/question.py:17,19,21 — `passion_type_es`, `default_text_es`, `summary_es` unused. **Why noise:** Spanish localization is deferred per GAP_ANALYSIS / open risk in Phased Plan; columns intentionally retained for future enablement.
- `[TBD]` [api/billing] api/app/models/subscription.py:19,35,36 — `unit_amount`, `stripe_payment_intent_id`, `stripe_invoice_id` columns declared but never written. → Decide if these will be populated (e.g., from invoice.paid webhook) or dropped via Alembic migration → S
- `[TBD]` [api/data] api/app/models/user.py:25 — `onboarding_completed` flagged unused by vulture; recent commit `f7a8b9c0d1e2` added it. Verify it's actually written somewhere (frontend uses `user?.onboarding_completed`). → Pass 2 confirms write-side → S

### 1d. Runtime vuln scan

**Web — `npm audit --omit=dev --json`. 2 moderate vulnerabilities (prod chain).**

- `[TBD]` [web/security] web/package.json `axios: ^1.7.0` — **CVE GHSA-3p68-rc4w-qgx5** (NO_PROXY hostname normalization bypass → SSRF, CVSS 4.8) + **GHSA-fvcv-3m26-pcqx** (Cloud metadata exfiltration via header injection chain, CVSS 4.8). Fixed in 1.15.0. Direct dep, used by `web/src/context/AuthContext.tsx` for all API calls. → Bump to `axios@^1.15.0` in `web/package.json` → S
- `[TBD]` [web/security] web/node_modules/follow-redirects (transitive via axios) — **GHSA-r4q5-vmmm-2653** (custom auth headers leaked to cross-domain redirect targets). Fixed by the axios bump above (transitive). → No direct action, resolves via axios bump → S [combined with axios fix]

**API — `python -m pip_audit -r api/requirements.txt --no-deps`. 1 known vulnerability.**

- `[TBD]` [api/security] api/requirements.txt `python-multipart==0.0.22` — **GHSA-mj87-hwqh-73pj** (DoS via malformed multipart payloads). Fixed in 0.0.26. Used by FastAPI for form/file uploads — touched whenever an upload endpoint is hit (CSV invite upload, etc.). → Bump to `python-multipart>=0.0.26` → S

**Other deps clean:** stripe 14.4.1, resend 2.26.0, pyjwt 2.12.1, fastapi 0.135.1, sqlalchemy 2.0.48, react 18.3, react-router-dom 6.26 — no advisories at scan time.

### 1e. Production-build secrets scan

Created [scripts/scan-build-for-secrets.sh](scripts/scan-build-for-secrets.sh) — bash script greps `web/dist/**/*.{js,css,html,map}` for word-boundaried Stripe (`sk_live_`, `sk_test_`, `rk_*`), Resend (`re_*`), AWS (`AKIA*`), SendGrid (`SG.*`), Slack (`xox*`), GitHub PAT (`github_pat_*`), raw JWT (`eyJ*.*.*`), and DB URL (`postgres://user:pass@host`) patterns. Exits 1 on hit.

Ran after `npm run build` in `web/`:

```
OK: no secret patterns matched in /c/Users/ebube/Documents/GPS Rebuild/web/dist
```

- **No findings.** Production bundle is clean. The frontend reads only `VITE_API_URL` (verified in `web/.env.example`), no secret keys are inlined.
- `[TBD]` [build/deploy] `web/dist` is in `.gitignore` but no CI step runs this scanner today. → Wire `scan-build-for-secrets.sh` into a Render postbuild hook OR a future CI workflow (see Pass 2 / CI subsystem) → S

### 1f. Bundle analyzer

Wired `rollup-plugin-visualizer` into `web/vite.config.ts` behind `ANALYZE=true`. Build with `ANALYZE=true npm run build` writes `dist/bundle-stats.html` (treemap, gzip + brotli sizes).

**Build output (single-bundle, no splitting):**

| Asset | Raw | Gzip |
|---|---:|---:|
| `assets/index-sU7PFL1A.js` | 910.46 kB | **251.70 kB** |
| `assets/index-zo3beq81.css` | 52.80 kB | 10.35 kB |
| `assets/MyImpact Logo-…svg` | 151.57 kB | 109.47 kB |
| `assets/hex-background-…webp` | **2,213.77 kB** | (binary, served as-is) |
| `assets/Disciples_Made_Logo_Horizontal-…svg` | 76.69 kB | 57.07 kB |

**Findings:**

- `[TBD]` [web/perf] web/src/App.tsx:13-33 — **Zero code-splitting.** Every page is statically imported, so the single 251.70 KB gzip bundle ships to every visitor on first load. Admin-only code (`AdminDashboard`, `MasterDashboard`, `AuditLog`, `SystemExport`, `BillingDashboard`, `recharts` chart lib, `@stripe/stripe-js`, `@stripe/react-stripe-js`) goes out to every regular member who never visits those routes. **User-facing route first-load JS is technically under the 300 KB budget but only because the budget is for a single bundle**; once admin/master pages grow further this will break it. → Convert page imports to `React.lazy()` + `<Suspense>`. Three logical chunks: (a) auth/public, (b) authenticated user (Dashboard, Account, Assessment*, MyImpact*), (c) admin/master/billing. Expected user-facing route to drop ~80-120 KB gzip. → M
- `[TBD]` [web/perf] web/dist/assets/hex-background-Qn64QiaS.webp — **2.21 MB single-asset** (background image). Imported somewhere as a static asset (since it landed in the build). Slow on mobile / cellular. → Resize to actual on-screen pixels (likely 1920×1080 max), serve responsive variants via `<picture>` or CSS `image-set(...)`, or replace with a CSS gradient if visually possible → S
- `[TBD]` [web/perf] web/dist/assets/MyImpact Logo-BDV9iV1N.svg — 151.57 kB raw / 109.47 kB gzip. **An SVG logo this large suggests embedded raster bitmap data inside the SVG**. → Run through SVGO (`svgo MyImpact\ Logo.svg`); if still huge, the raster fallback is hidden inside the SVG and the file should be split into a real raster (webp) plus a small svg → S
- `[TBD]` [web/perf] web/src/pages/MasterDashboard.tsx — sole consumer of `recharts` (per depcheck output earlier). When code-splitting is added, `recharts` should be confined to the master/admin chunk so users never download it. → Same fix as the App.tsx code-splitting row → covered by that row
- `[TBD]` [web/perf] web/src/pages/BillingDashboard.tsx — sole consumer of `@stripe/stripe-js` and `@stripe/react-stripe-js`. Same: should not ship to non-admin users. → covered by App.tsx code-splitting row
- `[TBD]` [web/build] web/vite.config.ts — current `build:` block has only `outDir: 'dist'`. No `rollupOptions.output.manualChunks`, no `chunkSizeWarningLimit` adjustment. Vite warning fires every build because of the 500 KB ceiling. → Add `manualChunks` after splitting (e.g. `{ vendor: ['react','react-dom','react-router-dom'], stripe: ['@stripe/stripe-js','@stripe/react-stripe-js'], charts: ['recharts'] }`) → S (after code split is done)

**Note on per-route budget:** the project doesn't have a stated bundle budget. Plan defaulted to 300 KB gzip user-facing / 500 KB gzip admin-only — confirm this with the user during triage. Today the all-in bundle is 251.70 KB gzip — under the user-facing budget, but only because there's no separation. Once split, user-facing should land ~150-180 KB gzip and admin ~280-350 KB gzip.

---

## 3. Pass 2 — Manual sweep

### 2.1. Auth

- `[TBD]` [auth/csrf] api/app/dependencies/auth.py:65-66 + api/app/main.py:40-48 — `get_current_user` falls back to the `access_token` cookie when no `Authorization` header is present. Combined with `cookie_samesite="none"` (auth.py:169 prod) and `allow_credentials=True` in CORS, this opens **CSRF on any state-changing endpoint where the attacker can submit a same-content-type request without preflight** — primarily Form-encoded POSTs (e.g., `/auth/password-strength` accepts Form, others use JSON which preflight-blocks). The risk is heavily contingent on `CORS_ORIGINS` being properly restricted in prod (the code does block `*` with credentials at startup, line 30, ✓), but the pattern is fragile. → Drop cookie auth for any non-GET request: only accept the cookie token on safe methods, or require an `X-CSRF-Token` header for mutating verbs that allow cookie auth. Alternative: change cookies to `samesite=lax` if the prod frontend is on the same registrable domain (NOT the case today: `gps-web.onrender.com` vs `gps-api.onrender.com` are cross-site per PSL, so SameSite=Lax wouldn't ship the cookie at all — confirmed in the code comment at auth.py:166). → M
- `[DONE: B2]` [auth/rate-limit] api/app/core/rate_limits.py:17 — `Limiter(key_func=get_remote_address)` uses `request.client.host`, which on Render (or any reverse-proxy deployment) is the **load balancer IP**, not the real client. Effectively, *all rate limits collapse to one bucket per Render front-end IP*, meaning thousands of users share the bucket. Login rate limit (`5/minute`) is therefore not effective — an attacker sees ~5 attempts/min globally, not per-attacker. → Switch `key_func` to extract from `X-Forwarded-For` (parse the leftmost IP) when behind a trusted proxy. SlowAPI's docs recommend a custom key_func that pulls `request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.client.host`. Also enable Render's `trusted_hosts` config / FastAPI's `ProxyHeadersMiddleware`. → S
- `[DONE: B3]` [auth/account-deletion] api/app/routers/auth.py:382-420 + services/auth_service.py:443 — `DELETE /auth/account` only requires the literal string `"DELETE"` (line 398-402) as confirmation. **No password reauth.** A stolen access token (XSS, malware, public-computer leftover session) can permanently soft-delete the account — anonymizes name/email, revokes tokens, removes memberships. The `_no_impersonation` dependency blocks impersonation tokens, ✓, but doesn't address stolen-real-token scenarios. → Require password in `AccountDeleteRequest` schema; verify via `verify_password(data.password, user.password_hash)` before proceeding. Industry standard for destructive account ops. → S
- `[DONE: B4]` [auth/billing-sync] api/app/dependencies/auth.py:351-365 — Stripe v14 broke `current_period_start/end`. Block is wrapped in `try/except Exception: pass`, so the auto-sync of "incomplete" subscriptions silently fails. New subscribers that haven't yet had their webhook fire stay in `incomplete` status indefinitely from this code's perspective. → Combined fix with the broader Stripe SDK v14 cluster (see 2.2 Payments). → covered there
- `[DONE: B3]` [auth/rate-limit-coverage] api/app/routers/auth.py — endpoints **without** `@limiter.limit(...)`: `/auth/refresh` (line 195), `/auth/logout` (line 238), `/auth/change-password` (line 344) (auth required but no per-bucket limit), `/auth/me` (line 423) (GET, low concern), `/auth/onboarding-complete` (line 468), `/auth/org/{org_key}` (line 479) (public — usable for org-key enumeration), `/auth/password-strength` (line 491) (public Form endpoint). → Add `AUTHENTICATED_RATE` to refresh, logout, change-password, onboarding-complete; add `PUBLIC_AUTH_RATE` to org/{org_key} and password-strength. Bundle into one commit. → S _(/auth/me left as GET-only, low concern.)_
- `[TBD]` [auth/token-rotation] api/app/services/auth_service.py:302-335 — `refresh_access_token` validates the old refresh token, then calls `create_tokens(user.id)` which inserts a NEW refresh-token row. **The old refresh token is never marked `revoked=True` on rotation.** So a stolen refresh token remains valid for 7 days even after the legitimate user "rotated" by refreshing. Token rotation should be one-shot. → Inside `refresh_access_token`, after fetching `db_token` and verifying validity, set `db_token.revoked = True` before issuing new tokens (in same transaction). Also detect rotation reuse (a revoked token presented again) and fully revoke the user's session family per OWASP guidance. → S core fix; M with reuse-detection
- `[DONE: B3]` [auth/master] api/app/dependencies/auth.py:217 + 231 — `require_master` and `require_master_no_impersonation` use `current_user.memberships[0]` (insertion-order first), unlike `require_admin` which uses `_get_active_membership` (most recent active). For a master who once was a member of a church and was later promoted, the first membership might be the OLD member role, causing the master check to fail despite being legitimately master. → Either use `_get_active_membership(current_user)` and check role, or query memberships filtered by `role.name=='master'` directly. → S _(Used the direct query approach via new `_has_master_membership` helper.)_
- `[TBD]` [auth/password-reset] api/app/services/auth_service.py:368-393 — `reset_password` does not validate the new password against `PasswordPolicy.validate(...)`. A user can reset to a weak password (e.g., `"a"`) via the reset flow, bypassing the policy enforced on register/change-password. → Add `is_valid, errors = PasswordPolicy.validate(new_password, ...)` and raise 400 with the errors before hashing → S
- `[TBD]` [auth/password-reset] api/app/services/auth_service.py:347-366 — `create_password_reset_token` does not invalidate previous unused reset tokens for the same user. Multiple valid reset tokens can coexist (e.g., user clicks "Forgot password" 5 times, all 5 emails contain valid tokens). If one of those emails is forwarded/leaked, the attacker has 24h to reset. → Mirror the pattern from `create_email_verification_token` (line 397-401) which uses an UPDATE to mark existing tokens used="Y" before issuing a new one. → S
- `[TBD]` [auth/token-storage] api/app/services/auth_service.py:360, 407 + models/password_reset.py + models/email_verification.py — Reset and verification tokens stored as **plaintext** in `password_reset_tokens.token` / `email_verification_tokens.token`. A read-only DB dump leaks live tokens. Refresh tokens are correctly hashed (line 289 `get_token_hash(...)`); these two should be too. → Switch storage to `token_hash` (sha256), look up by hash, and continue to email the plaintext to the user. → M (requires Alembic migration)
- `[TBD]` [auth/account-deletion] api/app/services/auth_service.py:487 — `delete_account` HARD-DELETES memberships (`Membership.user_id == user.id).delete()`). Since user records are soft-deleted (status=`deleted`, anonymized), but membership rows are gone, the audit trail loses "user X was a member of org Y at time T". → Soft-delete memberships (e.g., set `status="deleted"` + `deleted_at=now()`) instead of hard delete, OR write an `audit_log` row capturing the membership state before deletion. → S (audit-log approach is simpler)
- `[TBD]` [auth/registration] api/app/services/auth_service.py:42-48 — `register_user` does case-insensitive existence check on email, but the email column may not have a unique index on `lower(email)`. Two near-simultaneous registrations of `Foo@bar.com` and `foo@BAR.com` could both pass the check, then both inserts succeed (creating two accounts that resolve to the same email after `.lower()`). Pass 2.7 confirms whether such an index exists. → If no functional unique index on `lower(email)`, add one in Alembic. → S after data-layer pass
- `[TBD]` [auth/email-format] api/app/models/user.py + services — `email_verified` is a string column with values `"Y"/"N"` rather than a boolean. Routers compare with `== "Y"` (e.g., auth.py:331). Mixing string Y/N with Python `bool` values in code creates subtle bugs (e.g. `if user.email_verified` is always True for non-empty string). → Migrate to a boolean column with proper default → M (Alembic migration + code touchups)
- `[DONE: B3]` [auth/get_optional_user] api/app/dependencies/auth.py:370 — sync function calling async `get_current_user` without await. Already logged in 1a + 1c as **dead AND buggy**. → Delete (already noted) → S
- `[TBD]` [auth/me] api/app/routers/auth.py:435-437 — `/auth/me` falls back to `current_user.memberships[0]` if no membership has an organization. For a master admin (who may have no org membership), the order of `memberships` matters and is not deterministic. Same brittleness as `require_master`. → Use `_get_active_membership` consistently. → S
- `[noise]` [auth/cookie-redundant] api/app/routers/auth.py:183-190 — Login also sets the access_token in a cookie even though the frontend uses `Authorization: Bearer`. **Why noise:** the cookie is httpOnly and adds defense-in-depth; only redundancy, not a bug. (See CSRF row above for the security implication of cookie auth.)

### 2.2. Payments / Stripe

- `[DONE: B5]` [billing/webhook] api/app/routers/billing.py:618-660 — **Webhook handler has zero idempotency.** Stripe retries delivery on any error and sometimes delivers duplicates anyway. Every `event.id` is processed unconditionally. → Add a `webhook_events` table with `stripe_event_id` PK, INSERT-on-receipt with `ON CONFLICT DO NOTHING`, and only call the handler if the insert returned a new row. Same pattern protects `handle_invoice_payment_succeeded`/`failed` which currently create duplicate `Payment` rows on every retry. → M
- `[DONE: B5]` [billing/webhook] api/app/routers/billing.py:657-660 — Handler returns 200 OK even when `handle_*` raises. Stripe interprets 200 as "delivered, no need to retry", so a transient DB blip silently drops the event. → After dedupe is in place (above), let exceptions propagate as 5xx so Stripe retries. With the dedupe table the duplicate-protected handler is a cheap no-op on retry. → S (after the dedupe table exists)
- `[DONE: B5]` [billing/atomicity] api/app/routers/billing.py:199-307 — `POST /billing/subscribe` is **not atomic across user-double-click**. Two near-simultaneous requests both pass the `existing` check, both call Stripe, and end up with two active Stripe subscriptions on the same Stripe customer — but the local DB only tracks the second. The first orphan keeps charging the customer monthly. → Wrap in a `with_for_update()` lock on the existing Subscription row (or use a unique partial index on `(organization_id) WHERE status IN ('active','trialing','past_due')`). Also check `stripe.Subscription.list(customer=customer.id, status='active')` before creating. → M
- `[DONE: B4]` [billing/stripe-v14] api/app/services/stripe_service.py:226,227,247,248 — `handle_subscription_updated` uses bracket subscript `sub["current_period_start"]` / `sub["current_period_end"]`. In Stripe API version 2026-02-25+ those fields moved to `subscription.items.data[0].current_period_*`. **When Stripe rolls the API version forward (or if the org was already on the new version), every webhook crashes with KeyError**, the outer `try/except` in billing.py:657-658 swallows it and returns 200, so events are silently dropped. → Read from `sub.get("items",{}).get("data",[])[0].get("current_period_start")` with safe default; remove the silent `except Exception` fallback. → S
- `[DONE: B4]` [billing/stripe-v14] api/app/services/stripe_service.py:93-94 — same problem in `create_subscription` reading `subscription.current_period_start` from the `Subscription.create` response. **Today this silently writes `None` to the DB row** (because of `subscription.get("current_period_start")` falsy check), so subscriptions get a row with no period dates → subsequent gating checks behave incorrectly. → Same fix: read from `items.data[0]`. → S [bundle with previous row]
- `[DONE: B4]` [billing/stripe-v14] api/app/services/stripe_service.py:180 — `stripe.Invoice.upcoming_preview(...)` — verify against Stripe SDK 14.4.1; current SDK exposes `Invoice.create_preview(...)`. The wrapped `try/except: return None` (line 181-182) means the upcoming-invoice card on `/admin/billing` simply shows nothing, silently. → Update to `stripe.Invoice.create_preview(...)`. → S
- `[DONE: B5]` [billing/race] api/app/services/stripe_service.py:38-46 — `get_or_create_customer` race: two concurrent calls for the same org with `stripe_id=None` both fall through to `create_customer`, creating two Stripe customers; the second overwrites `organization.stripe_id` and the first is orphaned. → Either lock the Organization row (`SELECT … FOR UPDATE`) or use Stripe's idempotency keys on the create call. → S
- `[TBD]` [billing/audit] api/app/routers/billing.py:276-288 — Audit log is written AFTER Stripe call succeeds and AFTER local DB commit. If the audit-log commit fails (DB blip), Stripe sub exists, local sub exists, but no audit trail. → Move audit-log write into the same transaction as the subscription write. → S
- `[TBD]` [billing/limit] api/app/routers/billing.py:551 — `GET /billing/invoices?limit=N` — `limit` is unbounded by the API. Frontend currently sends 10 but a malicious admin could pass `limit=10000` and force a slow Stripe enumeration. → Cap server-side: `min(limit, 50)`. → S
- `[DONE: B4]` [billing/timeout] api/app/services/stripe_service.py — no timeout configured for the Stripe client. Stripe SDK default is 80s; an upstream Stripe stall blocks the API request for 80s holding a DB connection. → Set `stripe.max_network_retries=2; stripe.api_request_timeout=10` at module load. → S
- `[TBD]` [billing/event-order] api/app/services/stripe_service.py:204-252 — `handle_subscription_updated` writes received state without checking `event.created` against any local timestamp. Stripe events can be delivered out of order; an old "active" can overwrite a newer "canceled". → Compare `event.created` (or webhook payload's `created`) against `db_subscription.updated_at` and skip stale events. → S
- `[fp]` [billing/admin-rate] api/app/routers/billing.py:80-559 — 8× `Membership.is_primary_admin == True` in `.filter(...)`. **Why fp:** SQLAlchemy DSL requirement (already noted in 1b). The repetition does suggest extracting a helper, see 1b row.
- `[noise]` [billing/audit-log] api/app/routers/billing.py:276-287, 353-360, 431-436 — subscribe/cancel/reactivate all write `AuditLog` rows. **Why noise:** good hygiene, no issue. Cited here as positive evidence for audit-log subsystem (Pass 2.6) — billing IS audited, unlike some other admin actions.

### 2.3. Notifications & Email

- `[DONE: B1]` [email/branding] api/app/services/email_service.py — every email template references `giftpassionstory.com` in the footer (lines 85, 140, 191, 308, 449-450, 498, 545, 588, 632) and `settings.EMAIL_FROM` defaults to `noreply@giftpassionstory.com` in core/config.py:52. **Per project memory, transactional sender should be `noreply@disciplesmade.com`.** If production env doesn't override `EMAIL_FROM`, every email currently goes out from the wrong domain — likely also failing DKIM/SPF if disciplesmade.com is the verified Resend sender. → Update `EMAIL_FROM` default + replace all `giftpassionstory.com` references with `disciplesmade.com`. Confirm Resend domain verification status. → S
- `[TBD]` [email/injection] api/app/services/email_service.py:65-88, 120-143, 174-194, 276-312, 393-454, 478-501, 525-548, 572-591, 615-635 — every email body uses raw f-string interpolation of user-controlled fields (`first_name`, `last_name`, `org_name`, `admin_name`, `member_name`, `org_key`). **No HTML escaping.** A malicious church admin who names their church `<a href="https://phish.example.com">Click here</a>` triggers HTML injection in every member-facing email. **Email-borne phishing vector — credible against church admins because they control org_name and member display names visible to other members.** → Wrap every interpolated user-controlled field with `html.escape(value or "")`. → M (~10 sites)
- `[TBD]` [email/silent-failure] api/app/services/email_service.py:98-99, 153-154, 207-208, 322-323, 464-465, 511-512, 558-559, 601-602, 645-646 — every send wraps Resend in `try/except: logger.error(...)`. Module docstring even brags "All send methods are non-fatal: exceptions are logged but never bubble up to callers." For password-reset and primary-admin-welcome flows, **a Resend outage means the user gets no email and the API returns success** — they can never log in. → For "must-deliver" sends (password-reset, primary-admin-welcome, email-verification), surface failure to the caller; for nice-to-have sends (assessment notification), keep current behavior but add structured error metric (Sentry/CloudWatch). → M
- `[TBD]` [email/no-retry] api/app/services/email_service.py — no retry policy. Resend 5xx or rate-limit = email lost. Resend recommends client-side retry with exponential backoff for 5xx. → Add a small retry helper (3 attempts, 1s/2s/4s backoff, only for transient errors), or queue sends async via FastAPI `BackgroundTasks` with retry. → M
- `[TBD]` [email/timeout] api/app/services/email_service.py — no explicit HTTP timeout on Resend client. Resend Python SDK uses `requests` under the hood with no timeout by default. A hung Resend connection could block the API request indefinitely. → Configure Resend client timeout. → S
- `[TBD]` [email/unsubscribe] api/app/services/email_service.py:157-208 (`send_assessment_notification_email`) — emails to church admins on every member assessment. **This is the only email that could be considered marketing-adjacent** (digest-style notification) and lacks an unsubscribe / digest-preference link. Pure-transactional emails (verification, reset, invite, result) don't need one. → Confirm classification with stakeholder; if marketing-adjacent, add `notifications=daily/weekly/per-event` preference to admin profile + unsubscribe link in the email. NDPA/GDPR has weaker requirements for transactional but documenting consent is still best practice. → M
- `[TBD]` [notify/in-app] api/app/services/notification_service.py:46-69 — `get_notifications` issues 3 separate COUNT/SELECT queries per request (filtered, total_count, unread_count). Frontend `NotificationContext` polls `/notifications/unread-count` regularly. → Cache the unread count per user in-memory with short TTL (or compute total/unread in a single query using SQL CASE). → S
- `[TBD]` [notify/in-app] api/app/routers/notifications.py — no rate limits on any of the 4 endpoints. Frontend polling = unbounded request rate from a misbehaving client. → Add `AUTHENTICATED_RATE` to `list_notifications`/`mark_*`; consider a tighter cache-friendly limit on `unread_count` (e.g., 60/min for poll-frequency). → S
- `[TBD]` [notify/in-app] api/app/services/notification_service.py:49, 81-92 — `is_read` stored as `"Y"/"N"` string instead of boolean. Same anti-pattern as `email_verified`. → Migrate to bool column → S (combined Alembic with email_verified migration)
- `[TBD]` [notify/in-app] api/app/services/notification_service.py:81-92 — `mark_read` is read-modify-write (query, mutate, commit). Two concurrent calls mark the same notification read = both succeed (idempotent), but the unread-count derived elsewhere could double-decrement if there's also a counter cache. **Today there is no counter cache, so this is `[fp]` — but if one is added (per row above), the read-modify-write becomes a real race.** → Use `UPDATE … WHERE is_read='N' RETURNING id` to get atomic transition + count change. → S
- `[fp]` [notify/owner-check] api/app/services/notification_service.py:85 — `Notification.id == notification_id, Notification.user_id == user_id` ownership check inside the query. **Why fp:** correct pattern, no IDOR risk.
- `[noise]` [email/blocked-domains] api/app/services/email_service.py:15-36 — `_BLOCKED_DOMAINS` denylist for test/disposable emails. **Why noise:** good defense, no issue.

### 2.4. Assessments / Scoring

- `[TBD]` [assessment/atomicity] api/app/routers/assessments.py:264-405 — `POST /assessments/{id}/submit` is not atomic. Two near-simultaneous submits both pass `assessment.status == "completed"` check (line 294), both write answers, both invoke scoring, both create `AssessmentResult`/`MyImpactResult` rows, both send result emails to the user. → Wrap in `db.query(Assessment).with_for_update().filter(...).first()` before the status check, OR add a unique index on `assessment_results.assessment_id` (so duplicate insert raises IntegrityError). → S
- `[TBD]` [assessment/idempotency] api/app/services/scoring_service.py:262-319 — `create_assessment_result` always inserts a new row — no upsert / dedupe. Combined with the submit race above, a double-click creates two `AssessmentResult` rows for the same assessment. **The `result_id` foreign keys elsewhere become ambiguous.** → Same fix: unique constraint on `assessment_results.assessment_id` + UPSERT (`ON CONFLICT (assessment_id) DO UPDATE`). → S
- `[TBD]` [assessment/answer-race] api/app/routers/assessments.py:198-261 + 300-321 — `save_progress` and `submit` both do read-modify-write per answer (line 236-256, line 302-320). Two concurrent `save-progress` requests for the same `(assessment_id, question_id)` can both pass the `existing` check and both INSERT, creating duplicate Answer rows. → Add UNIQUE(assessment_id, question_id) to `answers` (Pass 2.7 confirms whether this constraint exists). With it, the second INSERT fails atomically. → S
- `[TBD]` [assessment/incomplete-submit] api/app/routers/assessments.py:332-333, 372-373 — Submit only **prints** when answers are missing (`print(f"... submitted with {validation['missing_count']} missing answers")`) and proceeds anyway. A user with 1 answer to a 76-question GPS gets a "result" treating 75 questions as 0 — that result is permanent and visible on dashboards. → Reject submission with 4xx if `missing_count > 0` (or > some tolerance), OR mark the result with `is_partial=true` and refuse to render it as canonical. Also replace `print(...)` with `logger.warning(...)`. → S
- `[TBD]` [assessment/result-email] api/app/routers/assessments.py:354-364, 394-404 — Notification creation wrapped in `try/except: pass` (BARE PASS — no logger). If notification creation crashes, the user gets the email but no in-app bell badge. Silent inconsistency between dashboard and email. → Replace bare `pass` with `logger.exception(...)`. → S
- `[TBD]` [assessment/admin-grade] api/app/routers/assessments.py:497, 614 — `/grade` and `/pdf` admin-fallback path checks `Membership.role.has(name="admin")`. **Master role is "master", not "admin", so masters cannot preview grades or download PDFs across churches via these endpoints** even though they otherwise have full system visibility. Probably fine for a privacy-by-default posture, but worth confirming product intent. → Decide: include `["admin", "master"]` if masters should view, or document the deliberate exclusion. → S
- `[TBD]` [assessment/admin-grade] api/app/routers/assessments.py:493-510, 609-623 — Admin grade/pdf cross-membership check is correct (verifies the assessment owner's membership matches the admin's org), but **does not check whether the admin's role membership is `is_primary_admin` or whether the org is comp/active**. A secondary admin demoted yesterday can still pull grades via this endpoint until their membership row's `role` is changed. Verify the demote flow updates the role correctly. → Pass 2.5 admin will dig in. → S
- `[TBD]` [assessment/data-format] api/app/services/scoring_service.py:293-295 — `result.people = ','.join(graded.people)`, `result.cause = ','.join(graded.causes)`, `result.abilities = ','.join(graded.abilities)`. **Comma-separated lists in a single VARCHAR column.** If any selected ability/people/cause name contains a comma (could happen as data evolves), parsing breaks. Filtering/aggregating across this dimension is also impossible without LIKE. → Migrate to JSONB column or a join table → M (Alembic + code touchups)
- `[TBD]` [assessment/grade-cost] api/app/routers/assessments.py:469-583 — `GET /assessments/{id}/grade` recomputes scoring on every call. Frontend may poll while the wizard is submitting. → Cheap today (basic arithmetic) but should still cache for the duration of the session, or skip the route in favor of the saved `AssessmentResult`. → S
- `[TBD]` [assessment/scoring-validation] api/tests/test_scoring.py — only test file in `api/tests/`. Pass 2.11 will check; this is a hard blocker per `GAP_ANALYSIS.md` (needs Brian's 3 sample assessments — IDs 549, 1911, 26169 — for parity validation). → Add fixtures + test cases comparing engine output against legacy values. → M
- `[fp]` [assessment/answer-ownership] api/app/routers/assessments.py:216-219 — `Assessment.id == assessment_uuid AND Assessment.user_id == current_user.id` ownership check at every assessment-by-id endpoint. **Why fp:** correct pattern, no IDOR risk on user-self routes.
- `[noise]` [assessment/print] api/app/routers/assessments.py:333, 373 — `print(...)` instead of `logger.info(...)` for missing-answer warnings. **Why noise:** ruff also flagged this (1b). Roll into the same cleanup commit.

### 2.5. Admin & Master

- `[DONE: B3]` [admin/priv-escalation] api/app/routers/admin.py:404-410 + api/app/schemas/admin.py:57-59 — **Privilege escalation:** `MemberUpdate.role: Optional[str] = None` accepts any string, and the router does `db.query(Role).filter(Role.name == update.role).first()` without restricting allowed values. **A church admin can `PUT /admin/members/{member_id}` with `{"role": "master"}` and grant a member system-wide master access** (since `require_master` checks any membership with `role.name == "master"` — see auth.py:217). Confirmed exploitable via the schema. → Restrict `role` to `Literal["user","member","admin"]` in the Pydantic schema; explicitly reject "master". Add a server-side guard in the router as defense-in-depth. → S
- `[TBD]` [admin/get-org] api/app/routers/admin.py:53-66 — `get_admin_organization` queries `Membership.role.has(name="admin")` first match without ordering. If a user is admin of multiple orgs (theoretically possible if the single-church business rule isn't enforced at DB level — see Pass 2.7), behavior is non-deterministic. Master role excluded entirely. → Restrict to single match, raise on >1, OR pass org via path parameter. Also document whether masters should access admin endpoints. → S
- `[TBD]` [admin/invite-storage] api/app/routers/admin.py:576-589 + models/invitation.py — Invitation `sign_up_key` token is 32 chars random alphanumeric (entropy fine) but stored **plaintext** in the DB. Same anti-pattern as password-reset / verification tokens (see auth/token-storage in 2.1). → Store hash, email plaintext to user. → M (Alembic + email_service tweak — bundle with auth token-storage migration)
- `[TBD]` [admin/invite-dup] api/app/routers/admin.py:562-606 — `create_invite` doesn't check whether an open invite for the same `(email, organization_id)` already exists. Admin can spam invites; multiple valid tokens coexist for the same recipient. → Add UNIQUE(organization_id, email) WHERE status='sent', or update existing invite in place. → S
- `[TBD]` [admin/remove-member] api/app/routers/admin.py:421-457 — Removing a member sets `membership.organization_id = None` (makes them independent) but keeps their existing `role_id` (could still be "admin" or "member"). After removal they're an "independent admin" — semantically nonsense. → On removal, also reset `role_id` to the "user" role. → S
- `[TBD]` [admin/audit-coverage] api/app/routers/admin.py:371-418 (PUT `/members/{id}`), 956-981 (PUT `/settings`), 805-924 (approve/decline pending) — **Member role/status updates and church settings updates do NOT write `audit_log` rows.** Only the decorated routes (`@audit_action(...)`) and explicitly-coded ones (transfer-primary-admin) are audited. So a church admin demoting/promoting members or renaming the org leaves no trail. → Add `@audit_action(...)` decorator to the missing routes (Pass 2.6 rolls these up). → S each
- `[TBD]` [master/csv-injection] api/app/routers/master.py:846-1053 + dashboard.py:318+ + admin.py:1091, 1348 — All CSV exports write `user.email`, `user.first_name`, `user.last_name`, `org.name`, audit `details`, and free-text answer fields **without calling `sanitize_for_csv`** (which is defined but never imported — see 1c). A user named `=cmd|'/c calc'!A1` causes Excel formula execution when a master admin opens the export. → Apply `sanitize_for_csv` to every string cell across ALL CSV writers. → M
- `[TBD]` [master/export-size] api/app/routers/master.py:846-1053 — `system_export("full")` does `db.query(User).all()` (line 956), `db.query(Organization).all()` (line 977), `db.query(Assessment, User, AssessmentResult).all()` (line 993), `db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()` (line 1033) — **all unbounded.** Per legacy data: 31K users, 42K assessments, 4.6M answers, 27K results — pulling all into memory then formatting CSV will OOM the Render instance. → Stream rows via SQLAlchemy `yield_per(N)` + `StreamingResponse`, OR move to async background job that emails the export. Today the export rate-limit is `5/hour`, so the load is bounded but a single call can still kill the worker. → L
- `[TBD]` [master/export-audit] api/app/routers/master.py:1033 — full export dumps the entire audit log unbounded — also the most sensitive data (impersonation reasons, IP addresses, login_failed details). → Add date-range filter (default last 90 days), require explicit `?include_audit=true` flag, or split into a separate endpoint with stricter rate limit. → S
- `[TBD]` [master/n+1] api/app/routers/master.py:817-835 — `get_audit_log` loops over entries and runs `db.query(User).filter(User.id == entry.user_id).first()` per row (line 823). 50 entries = 51 queries (1 + 50). → Use `joinedload(AuditLog.user)` or do an in-clause IN-query upfront. → S
- `[TBD]` [master/n+1] api/app/routers/master.py:917-933, 957-987 — Export loops issue per-row queries: `db.query(Membership).filter(Membership.user_id == user.id).first()` (line 918), `db.query(GiftsPassion).filter(GiftsPassion.id == result.gift_1_id).first()` (line 926-929) × 4 per row. For 42K assessments, that's 200K+ queries. → Eager load via `joinedload`/`selectinload` once. → M
- `[TBD]` [master/welcome-email] api/app/routers/master.py:386-397 — `create_church` creates a password-reset-style token via `auth_service.create_password_reset_token(...)` to send a "welcome / set password" email. Uses the same 24h expiry as a password-reset. **For an admin who's invited but goes on vacation, the welcome link expires before they ever click.** → Use a longer-lived "primary admin setup" token (e.g., 7 days) distinct from password-reset; OR auto-resend on expiry. → M
- `[TBD]` [master/dashboard-stats] api/app/routers/master.py:1145+ + ruff F841 master.py:1156 — `year_start` local declared but never used (per Pass 1b). Suggests an incomplete year-bucket metric. → Either wire it up or delete. → S
- `[TBD]` [master/impersonate] api/app/routers/master.py:721 — `http_request: Request` parameter declared but never used in the function body. Vulture flagged it 100% confidence. → Remove the parameter (it's only kept for the `@limiter.limit` decorator, in which case it must be `request: Request`). **Verify that the rate limiter actually picks up the `Request`** — it relies on a parameter named `request`. Currently the parameter is `http_request`, which means **slowapi may not be recognizing the Request and the rate limit is silently disabled**. → Rename to `request` (and rename the body's `request: ImpersonateRequest` to something else). → S
- `[noise]` [admin/transfer] api/app/routers/admin.py:460-525 — `transfer_primary_admin` is correctly atomic (single commit for both flips) and audit-logged. **Why noise:** good code, no fix.

### 2.6. Audit Log

- `[DONE: B2]` [audit/ip-spoof] api/app/core/audit.py:62-63 — `request.client.host` is captured as the audit IP, but on Render this is the load balancer IP. Combined with the same gap in rate limits (2.1), **every audit row records the same proxy IP** and provides no forensic value for "who did this from where". → Same fix family as rate-limit row: pull from `X-Forwarded-For[0]`. Bundle into one commit. → S
- `[TBD]` [audit/swallow] api/app/core/audit.py:74-76 + 124-125 — Both `audit_action` decorator and `log_audit_event` wrap the audit write in `try/except: rollback()`. Action succeeds even when audit fails. For sensitive operations (impersonation, role change, member removal, billing change) this is a **compliance anti-pattern** — actions occur without trail. → For sensitive-action paths, treat audit failure as fatal (raise 500 to roll back the user-visible action); for low-sensitivity paths keep current behavior but emit an alert metric. → M
- `[TBD]` [audit/coverage] api/app/routers/auth.py — no audit on `register` (success), `logout`, `refresh`, `password-reset-request`, `password-reset` (the actual reset, not the email send), `verify-email`, `update-profile`. Login is audited (3 paths) ✓. → Add `log_audit_event(...)` calls. The most important to add: **password-reset confirm** (knowing when a password was changed via reset is critical for "was that me?"), **email verification** and **profile update**. → S each, bundle into "auth-audit batch"
- `[TBD]` [audit/coverage] api/app/routers/admin.py:956-981 (PUT `/settings`), 776-803 (DELETE `/invites/{id}`), 739-774 (POST `/invites/{id}/resend`), 673-737 (POST `/invites/csv`) — These mutating admin actions don't write `audit_log` rows. → Add `@audit_action(...)` to each. → S, bundle into "admin-audit batch"
- `[TBD]` [audit/coverage] api/app/routers/billing.py:449-496 (POST `/payment-method`), 499-513 (DELETE `/payment-method/{id}`) — Add/remove payment method is not audited; subscribe/cancel/reactivate are. → Add audit. → S, bundle into "billing-audit batch"
- `[TBD]` [audit/coverage] api/app/routers/dashboard.py:544+ (`upgrade-to-admin`), 671+ (`link-request`), 729+ (`leave-organization`) — These mutate membership state but I'll verify in Pass 2.7 / 2.8 whether they write audit rows. → Add audit if missing. → S
- `[TBD]` [audit/coverage] api/app/routers/assessments.py — only `submit` is audited (line 266). `save-progress` not audited (less critical), but **admin-fallback PDF and grade routes (which let admins read another user's data, see admin/grade/pdf rows in 2.4) ARE NOT AUDITED**. A church admin could quietly browse every member's spiritual gift profile leaving no trail. → Audit `/grade` and `/pdf` when accessed via the admin path. → S
- `[TBD]` [audit/depth] api/app/core/audit.py:65-71 — Audit row only stores `{"ip_address": ip_address}` in `details`. **No before/after state, no diff, no actor's role, no impersonation context.** A `member_updated` audit row tells you a member was updated, not what was changed. → Capture before/after for state-changing routes; add `impersonated_by` and `impersonation_reason` from `request.state` (already populated by `get_current_user` per dependencies/auth.py:128-130). → M
- `[TBD]` [audit/append-only] api/app/models/audit_log.py — No DB-level enforcement that audit rows are immutable. A compromised app credential or rogue DBA can `UPDATE audit_log SET …` to rewrite history. → On Render Postgres, create a separate role with INSERT-only on `audit_log`, or add a trigger that raises on UPDATE/DELETE. Alternatively keep the application-layer convention but document it. → M
- `[TBD]` [audit/retention] no policy in code — audit_log table grows unbounded. With 31K legacy users + ongoing activity, this is fine for years but should have a documented retention. → Document retention (legal requirement?), add an Alembic migration to set up a partitioning scheme or archival job. → M (deferrable)
- `[noise]` [audit/login] api/app/routers/auth.py:116-162 — login flow audits success / locked / failed (3 distinct outcomes), captures email + IP. **Why noise:** thorough; no fix.

### 2.7. Data layer & indexes

**Audit method:** Examined every `Column(... ForeignKey(...))` in `api/app/models/` and cross-referenced with `op.create_index` in `api/alembic/versions/`. PostgreSQL does NOT auto-index foreign keys, so each FK that's used as a filter / join target needs an explicit index.

- `[TBD]` [data/missing-index] api/app/models/membership.py + alembic — no indexes on `memberships.user_id` or `memberships.organization_id`. **These columns are filtered on every authenticated request** (auth dependencies, admin endpoints, billing endpoints all do `Membership.user_id == current_user.id`). At scale (after migration: 31K users with multiple memberships each), every request becomes a sequential scan. → Alembic migration: `op.create_index('ix_memberships_user_id', 'memberships', ['user_id']); op.create_index('ix_memberships_organization_id', 'memberships', ['organization_id'])`. → S
- `[TBD]` [data/missing-index] api/app/models/assessment.py — no index on `assessments.user_id`, `assessments.completed_at`, or `assessments.status`. Dashboard `/dashboard/assessments` filters by `user_id`; admin dashboards filter by `(organization_id, completed_at)` joined; submit / save-progress filter by `(user_id, status='in_progress')`. → `op.create_index('ix_assessments_user_id', 'assessments', ['user_id']); op.create_index('ix_assessments_user_status_created', 'assessments', ['user_id', 'status', 'created_at'])`. → S
- `[TBD]` [data/missing-index] api/app/models/answer.py — no indexes on `answers.assessment_id`, `answers.question_id`, or `answers.user_id`. **Most painful at scale**: legacy data has 4.6M answers. Every scoring read does `WHERE assessment_id = X` + per-question lookups. Without an index, scoring an assessment becomes O(N) over the whole answers table. → `op.create_index('ix_answers_assessment_id', 'answers', ['assessment_id']); op.create_index('ix_answers_user_id', 'answers', ['user_id'])`. → S
- `[TBD]` [data/missing-unique] api/app/models/answer.py — no UNIQUE on `(assessment_id, question_id)`. The save-progress race row in 2.4 depends on this constraint to be exploitable. Adding the unique index also serves the lookup pattern. → `op.create_unique_constraint('uq_answers_assessment_question', 'answers', ['assessment_id', 'question_id'])`. **Caveat:** existing duplicates from race-condition writes (if any) must be deduped before this can be added. → S, M with dedup migration
- `[TBD]` [data/missing-unique] api/app/models/assessment_result.py + myimpact_result.py — no UNIQUE on `assessment_id`. Two result rows for the same assessment is undefined behavior (which one wins on the dashboard?). Pairs with the submit race in 2.4. → `op.create_unique_constraint('uq_assessment_results_assessment_id', 'assessment_results', ['assessment_id'])`. Already-present `ix_myimpact_results_assessment_id` in alembic a9872764336e is non-unique — should be unique. → S
- `[TBD]` [data/missing-unique] api/app/models/membership.py — no UNIQUE on `(user_id, organization_id)`. Multi-membership-per-user-per-org has no DB enforcement; race in `auth_service.upgrade_to_church_admin` could create duplicates. → `op.create_unique_constraint('uq_memberships_user_org', 'memberships', ['user_id', 'organization_id'])`. **Caveat:** dedup existing rows first; legacy import may have duplicates per the phased plan's "Multi-church vs single-church" risk register. → M
- `[TBD]` [data/email-collation] api/app/models/user.py:15 — `email` is `String(255), unique=True`. Postgres unique index is case-sensitive by default. Application code lowercases via `.lower()` before lookup but races can still create case-different duplicates (auth/registration row in 2.1). → `op.create_unique_constraint(...)` with `func.lower(email)`, OR set the column collation to `citext`. Today's data: assume mostly clean since `register_user` does `.lower()` consistently. → S
- `[TBD]` [data/missing-index] api/app/models/subscription.py — no indexes on `subscriptions.organization_id` or `subscriptions.stripe_subscription_id`. Webhook handler at stripe_service.py:220 does `WHERE stripe_subscription_id = ?`; gating dependency at dependencies/auth.py:304 does `WHERE organization_id = ?`. Webhook latency matters because it's on Stripe's retry budget. → `op.create_index('ix_subscriptions_organization_id', 'subscriptions', ['organization_id']); op.create_index('ix_subscriptions_stripe_subscription_id', 'subscriptions', ['stripe_subscription_id'])`. → S
- `[TBD]` [data/missing-index] api/app/models/audit_log.py — no indexes on `audit_log.created_at`, `audit_log.user_id`, or `audit_log.action`. `/master/audit-log` orders by `created_at DESC` and filters by user/action — full table scan at scale. → `op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at']); op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'])`. → S
- `[TBD]` [data/missing-index] api/app/models/refresh_token.py — no indexes. `auth_service.refresh_access_token` (line 314) does `WHERE token_hash = ? AND revoked = false AND expires_at > now()` — full scan unless `token_hash` is indexed. Login + every refresh do this lookup. → `op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash']); op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])`. → S
- `[TBD]` [data/missing-index] api/app/models/assessment_result.py — no indexes on FK columns `(user_id, gift_1_id, …)`. Admin dashboards aggregate over user_id; would benefit. → `op.create_index('ix_assessment_results_user_id', 'assessment_results', ['user_id'])` at minimum. → S
- `[TBD]` [data/comma-separated] api/app/models/assessment_result.py + scoring_service.py:293-295 — `people`, `cause`, `abilities` stored as comma-separated VARCHAR. (Already noted in 2.4 — repeated here as the data-layer dimension.) → JSONB or join table.
- `[TBD]` [data/spanish-cols] api/app/models/question.py:17,19,21 — Spanish-translation columns (`passion_type_es`, `default_text_es`, `summary_es`) declared but never populated/read (already noted in 1c as `[noise]` — Spanish localization deferred). **Why this matters here:** they take up storage and confuse readers. Document the deferral in a comment, OR drop them via migration if Spanish is permanently out of scope. → S
- `[TBD]` [data/render-ssl] no obvious enforcement of `sslmode=require` on Render Postgres connection. Render's Postgres connection string includes it by default; check `DATABASE_URL` in render.yaml / Render UI to confirm. Worth a one-line verification in `core/database.py`. → S
- `[noise]` [data/notifications-index] api/alembic/versions/f7a8b9c0d1e2_add_notifications.py:33 — composite index on notifications already in place. **Why noise:** correctly indexed.
- `[noise]` [data/myimpact-index] api/alembic/versions/a9872764336e_add_myimpact_support.py:108-109 — myimpact_results indexed on `assessment_id` and `user_id`. **Why noise:** correctly indexed (though `assessment_id` should also be UNIQUE — see row above).

### 2.8. Cross-cutting API & Dashboard

- `[DONE: B3]` [api/duplicate-flow] api/app/routers/auth.py:52-86 (`/auth/upgrade/church`) vs api/app/routers/dashboard.py:544-634 (`/dashboard/upgrade-to-admin`) — **Two endpoints implement nearly the same flow** (user creates a new org, becomes its primary admin). The auth path properly handles the existing-membership-with-org case (other admins, transfer, Stripe cancel) per `auth_service.upgrade_to_church_admin`. The dashboard path is simpler and **misses Stripe cancellation, transfer logic, and audit logging.** A user could call the dashboard path even when they're a primary admin elsewhere, leaving an orphan Stripe subscription. → Delete `/dashboard/upgrade-to-admin` and route the frontend to `/auth/upgrade/church`. → S _(grep confirmed no web callers; replaced with a NOTE comment pointing future readers to /auth/upgrade/church.)_
- `[TBD]` [api/truncating-list] api/app/routers/admin.py:545 — `GET /admin/invites` returns `query.order_by(...).all()` — no pagination. For a long-running church with thousands of historical invites, returns the entire history per request. → Add `?page=&per_page=` like the members endpoint. → S
- `[TBD]` [api/truncating-list] api/app/routers/master.py:265-301 — `GET /master/churches/{church_id}/members` `.all()` — no pagination. Large churches (1000+ members) return everything in one response. → Paginate. → S
- `[TBD]` [api/truncating-list] api/app/routers/admin.py:819 — `GET /admin/pending` `.all()` — pending members list unbounded. Probably small in practice but possible to spam. → Cap with explicit `LIMIT 200` server-side or paginate. → S
- `[TBD]` [api/truncating-list] api/app/routers/assessments.py:803 — `GET /assessments/my-assessments` `.all()` — full assessment history per user. Per-user is bounded (most users < 10 assessments) so currently fine, but the API contract has no max. → Add a `LIMIT 200` server-side. → S
- `[TBD]` [api/truncating-list] api/app/routers/dashboard.py:340 — `GET /dashboard/export/csv` returns `.all()` of all completed assessments for a user. Per-user is bounded; OK. → No fix needed for current data; revisit if a user's history exceeds dozens.
- `[TBD]` [api/n+1] api/app/routers/dashboard.py:650-666 — `search_churches` issues a separate `db.query(Membership).filter(...).count()` inside the loop for each of the 10 returned churches (line 656). 11 queries to render a single search response. → Use a single GROUP BY query: `SELECT org.id, COUNT(m.id) FROM organizations org LEFT JOIN memberships m ON m.organization_id = org.id WHERE org.name ILIKE ? GROUP BY org.id LIMIT 10`. → S
- `[TBD]` [api/seq-scan] api/app/routers/dashboard.py:650 — `Organization.name.ilike(f"%{query}%")` — leading wildcard prevents B-tree index use. PostgreSQL needs `pg_trgm` GIN/GiST index for that predicate. **Today the org count is small (per phased plan ~169) so no problem; flag for the post-launch growth path.** → If org count grows past ~10K, add `CREATE EXTENSION pg_trgm; CREATE INDEX … USING gin (name gin_trgm_ops)`. → S deferred
- `[TBD]` [api/race] api/app/routers/dashboard.py:558-619 — `upgrade_to_admin` reads existing membership, then creates org, then creates/updates membership in separate steps. Two concurrent calls from the same user could create two orgs and end up with the second's membership pointing to the second org while the first is orphaned. → Wrap in `with_for_update()` lock on the user's membership rows, OR delete this endpoint as recommended above. → S (subsumed by delete-this-endpoint fix)
- `[TBD]` [api/cors-headers] api/app/main.py:46 — `expose_headers=[]` means custom response headers (e.g., `X-Request-ID`, `X-RateLimit-Remaining`) won't be readable from the frontend. Not critical today but blocks any future ID-tracing UI. → Add `["X-Request-ID", "X-RateLimit-Remaining"]` once those headers exist. → S deferred
- `[TBD]` [api/error-handler] api/app/main.py — only handler is for `RateLimitExceeded`. No `@app.exception_handler(Exception)` for unhandled errors. With `DEBUG=False` FastAPI returns generic 500 with no body, so debugging prod issues requires log diving for stack traces. → Add a generic exception handler that logs with structured fields (request_id, user_id, path, method) and returns a sanitized 500 to the client. → S
- `[TBD]` [api/observability] api/app/main.py — no request-ID middleware, no structured logging setup, no Sentry/equivalent SDK. Logs are stdlib `logging` only. For a production app, errors will be hard to investigate. → Add `python-json-logger` for structured logs + a simple request-ID middleware that adds `X-Request-ID` header and stuffs it into log records. Sentry SDK is a 5-line install. → M
- `[TBD]` [api/cors-origins] api/app/core/config.py:41 — `CORS_ORIGINS` default is `["http://localhost:3000", "http://localhost:5173"]`. **Confirm production env actually overrides this with the real frontend origin** — if not, browsers will block all calls. The startup check at main.py:30 only blocks `*`, not localhost. → Add a startup validator: in non-DEBUG mode, reject `localhost`/`127.0.0.1` entries. → S
- `[TBD]` [api/options] api/app/main.py:44 — `allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]` — missing `OPTIONS`. CORS preflight requires OPTIONS, FastAPI's CORSMiddleware adds it automatically when present in allow_methods, but explicit list is better practice. **Today preflight likely works because CORSMiddleware always handles OPTIONS for itself.** → No fix needed but document. → no-op
- `[TBD]` [api/health] api/app/routers/health.py:13-18 — `db.execute("SELECT 1")` — passes a literal string, not `text("SELECT 1")`. SQLAlchemy 2 deprecated string-execute. Today produces a warning; future versions may break. → Wrap in `from sqlalchemy import text; db.execute(text("SELECT 1"))`. → S
- `[fp]` [api/admin-pagination] api/app/routers/admin.py:125, master.py:145, master.py:626, master.py:819 — properly paginated lists. **Why fp:** correct.

### 2.9. Background jobs & External services

**Audit method:** grep for `BackgroundTasks|apscheduler|celery|asyncio.create_task|cron` across `api/app`. **No matches.** The application has zero asynchronous job infrastructure. Confirmed via render.yaml — only one `web` service is provisioned, no worker service.

- `[TBD]` [bg/sync-emails] api/app/services/email_service.py + every router that triggers email — **All Resend calls run synchronously inside the request.** Combined with no timeout (2.3 row), no retry (2.3 row), and Resend's default 30s+ HTTP behavior, **a slow Resend response stretches user request latency by tens of seconds**. The submit-assessment flow (assessments.py:264-405) sends the result email AND a notification AND fires admin notifications — three sequential Resend calls in the request hot path. → Move email sends to FastAPI `BackgroundTasks` (runs after response is sent on the same worker) for nice-to-have sends; for must-deliver sends, queue to a real job system. → M
- `[TBD]` [bg/no-scheduler] api/app/ — no scheduled tasks. Specific things that should run on a schedule but don't: 
  - **Expired refresh tokens** never cleaned up. `refresh_tokens` table grows monotonically; even a soft-deleted user's tokens stay forever (revoked=true).
  - **Expired password-reset / email-verification tokens** stay in DB indefinitely.
  - **Past-due subscription reminders** — Stripe webhook updates state, but nothing follows up by emailing the admin. Account silently locks at 14 days per phased plan.
  - **Audit log archival / partition rotation.**
  → Add either an external cron pinging `/internal/cleanup` (rate-limited, IP-allowlisted, header-secret) OR provision a Render Background Worker running APScheduler. → L
- `[TBD]` [bg/sub-grace] api/app/dependencies/auth.py:28 — `_ACTIVE_SUBSCRIPTION_STATUSES = {"active","trialing","past_due"}`. Per phased plan Phase 6, "past_due" + 14 days = read-only. **This 14-day grace is enforced ONLY by Stripe's retry schedule** (Stripe transitions `past_due → unpaid → canceled` after retries exhaust). The app doesn't have a separate timer. If Stripe's behavior changes or the Stripe webhook misses an event (and per 2.2 webhooks can crash silently), the org can stay in `past_due` indefinitely. → After webhook idempotency + dedupe is in place (2.2), add a periodic check that compares `subscription.current_period_end + 14d` to `now()` and force-locks if exceeded. → M
- `[DONE: B1]` [render/env-frontend-url] render.yaml — **`FRONTEND_URL` is not set in render.yaml.** `core/config.py:55` defaults to `http://localhost:5173`. **In production, every email link points to localhost.** Password resets, verification, invites, results — all broken. → Add `FRONTEND_URL: https://assessments.giftpassionstory.com` (or the real prod URL) to the `gps-api` envVars block. → S
- `[DONE: B1]` [render/env-email-from] render.yaml — `EMAIL_FROM` not set. Defaults to `noreply@giftpassionstory.com`. Per 2.3 this should be `noreply@disciplesmade.com`. → Add to render.yaml. → S _Resolved by changing the code default in `core/config.py` instead — render.yaml stays clean and prod picks up the right default automatically._
- `[TBD]` [render/env-stripe] render.yaml — Stripe / Resend secrets not declared. Must be set in Render UI as `sync: false`. **Confirm they're set in production.** → Audit Render UI; ideally add `sync: false` placeholders so the manifest documents them. → S
- `[DONE: B1]` [render/cors-domain] render.yaml:14 — `CORS_ORIGINS: "https://gps-web.onrender.com,https://assessments.giftpassionstory.com"`. The second origin uses the wrong domain (per memory: should be disciplesmade.com). **Either the production domain is actually `assessments.giftpassionstory.com` and the memory is stale, or the env is wrong.** → Confirm with stakeholder; update either render.yaml or the memory note. → S _Stakeholder confirmed: rebrand to disciplesmade.com, prod URL will be `dashboard.disciplesmade.com`. CORS_ORIGINS now lists Render staging + that future prod URL._
- `[DONE: B1]` [render/healthcheck] render.yaml — no `healthCheckPath` declared. Render uses default (`/`); the API has `/health` and `/health/db` which would be more informative. Without explicit healthcheck, instance failure detection is delayed. → Add `healthCheckPath: /health` to gps-api block. → S
- `[TBD]` [docker/dockerignore] api/ — no `.dockerignore`. `COPY . .` pulls `gps_local.db`, `tests/`, `__pycache__/`, etc. into the image. Bloat (acceptable today, ~10s of MB) and minor data hygiene (gps_local.db could contain test data). → Add `.dockerignore` excluding `*.db`, `tests/`, `__pycache__/`, `*.pyc`. → S
- `[TBD]` [docker/non-root] api/Dockerfile — runs as root. → Add `RUN useradd -m runtime; USER runtime` after `pip install`. → S
- `[TBD]` [stripe/timeout] api/app/services/stripe_service.py — already noted in 2.2. Re-flagged here as the only outbound HTTP service besides Resend. No timeout / retry policy / circuit breaker. Stripe outages directly translate to GPS outages.
- `[TBD]` [resend/timeout] api/app/services/email_service.py — same shape as Stripe. No timeout. Already noted in 2.3.
- `[noise]` [docker/python-version] api/Dockerfile:1 — `python:3.12-slim` pin. **Why noise:** explicit pin, well-supported version.

### 2.10. UI patterns

- `[TBD]` [ui/access-token-storage] web/src/context/AuthContext.tsx:85-105 — Access token stored in `localStorage`. Comment at line 238 explicitly says "Store in memory only - NOT localStorage" but the immediately-following `setAccessToken(access_token)` triggers a `useEffect` (line 97-105) that writes to localStorage. **The comment is a lie.** A successful XSS exfiltrates the token instantly. Refresh token IS in httpOnly cookie (good), but the access token defeats the protection. → True memory-only: store the access token in a module-scope variable + React state, drop localStorage; rely on the refresh-cookie path to re-auth on cold loads (the code already supports this — see `checkAuthStatus` line 107-144). → M
- `[TBD]` [ui/auth-bypass-context] web/src/pages/AdminDashboard.tsx:189, 270 + AuditLog.tsx:17 + SystemExport.tsx:67 — These pages read `localStorage.getItem('access_token')` directly and use it in their own fetch calls instead of using the shared `api` axios instance from `AuthContext`. **Bypasses the auto-refresh interceptor**, so if the access token expires mid-session in those pages, the user gets a 401 with no recovery — the app sends them to /login without refreshing. → Refactor to import `api` from AuthContext (already exported at line 365). → S each, M total
- `[TBD]` [ui/error-boundary] web/src/ — **No React `ErrorBoundary` anywhere in the codebase.** A render error in any page (e.g., a malformed API response) = white screen and the user must hard-refresh. → Add a top-level `ErrorBoundary` component in `App.tsx` that renders a friendly error + "Try again" / "Sign out" buttons. → S
- `[TBD]` [ui/csp] web/index.html + render.yaml — **No Content-Security-Policy** anywhere. With the access token in localStorage (XSS-reachable) and no CSP, the attacker model is wide open. → Add a CSP via render.yaml `headers:` block on the static site (or a `public/_headers` file): `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' fonts.googleapis.com; font-src 'self' fonts.gstatic.com; img-src 'self' data:; connect-src 'self' https://gps-api-4q4m.onrender.com https://api.stripe.com; frame-src https://js.stripe.com;` (tune based on Stripe Elements actual needs). → M
- `[TBD]` [ui/security-headers] render.yaml + index.html — No `X-Frame-Options`, `Strict-Transport-Security`, `Referrer-Policy`, `Permissions-Policy` set. Render typically adds STS by default; verify. → Add to render.yaml static site headers. → S
- `[TBD]` [ui/duplicate-api-url] web/src/context/AuthContext.tsx:4 + components/PasswordInput.tsx:27 — `const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'` declared twice. Inconsistent if either gets edited. → Move to `web/src/lib/config.ts` (or similar) and import. → S
- `[TBD]` [ui/effects] web/src/pages/Dashboard.tsx:29, AdminDashboard.tsx:121, MasterDashboard.tsx:223, VerifyEmailCallback.tsx:15 — Already noted in 1b. Setting state inside `useEffect` body causes cascading renders. Tiny perf cost, not a bug. → covered in 1b.
- `[TBD]` [ui/locale] web/index.html:2 — `<html lang="en">` hardcoded. App supports a `preferred_locale` per user but the HTML never reflects it. Screen readers and browser translation use `lang` to choose voice/dictionary. → Add a small effect that updates `document.documentElement.lang` when locale changes. → S
- `[TBD]` [ui/external-font] web/index.html:8-10 — Google Fonts loaded externally (Mulish family). For US users this is unproblematic, but each visit sends user IP to Google. **GDPR caselaw in 2022-2024 has held that this is a violation in EU.** If platform might serve EU users (church partners abroad?), self-host the font. → Confirm scope; if non-trivial EU usage, vendor the woff2. → S
- `[TBD]` [ui/loading-states] web/src/ — most pages handle `isLoading` but inconsistently. Some show a skeleton, some a spinner, some nothing. → Adopt a single `<Loading />` component. Cosmetic. → S deferred
- `[fp]` [ui/no-eval] web/src/ — no `dangerouslySetInnerHTML`, no `eval(...)`, no `new Function(...)`. **Why fp:** scanned and clean.

### 2.11. Build / Deploy / Env / Tests / CI

**.env.example parity (audit method:** grepped all `import.meta.env.VITE_*` and `os.getenv(...)` / `settings.<NAME>` references):

- `[TBD]` [env/parity-web] web/.env.example only declares `VITE_API_URL`. ✓ matches the only `import.meta.env.VITE_*` reference in the code (AuthContext.tsx:4 + PasswordInput.tsx:27).
- `[DONE: B1]` [env/parity-api] api/.env.example — Verified. Has `DEBUG`, `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, all 5 Stripe vars, `RESEND_API_KEY`, `EMAIL_FROM`, `FRONTEND_URL`. **Missing:** `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `ALGORITHM`. These have safe code defaults (30 min / 7 days / HS256) so prod still works, but operators tuning lifetimes have no template. → Add them as commented entries showing the defaults. → S
- `[DONE: B1]` [env/email-from-mismatch] api/.env.example:23 says `EMAIL_FROM=noreply@disciplesmade.com` (correct per memory) but `api/app/core/config.py:52` defaults to `noreply@giftpassionstory.com`. **A prod env that's missing this var picks up the wrong domain.** Local devs who copy `.env.example` are fine. → Update the code default to match the .env.example, OR set EMAIL_FROM in render.yaml. → S
- `[TBD]` [env/secret-default] api/.env.example:3 — `SECRET_KEY=your-super-secret-key-change-in-production` is in the BLOCKED_SECRETS set (config.py:8-19), so the validator at config.py:57-85 will reject it on startup if accidentally used in prod. ✓ defensive, no fix needed. → noise actually
- `[noise]` [env/secret-validator] api/app/core/config.py:57-85 — startup validator blocks weak/default `SECRET_KEY`s and enforces 32-char minimum. **Why noise:** good defense, no fix.
- `[TBD]` [env/db-default] api/app/core/config.py:38 — `DATABASE_URL: str = "sqlite:///./gps_local.db"`. **In production, if the env var is missing, the API silently uses SQLite** — losing all data and possibly causing race-condition crashes on concurrent writes. → Add a startup validator: if `DEBUG=False`, require the URL to start with `postgresql://`. → S
- `[TBD]` [env/cors-default] api/app/core/config.py:41 — Already noted in 2.8.
- `[TBD]` [env/render-vars] render.yaml — Already noted in 2.9 (`FRONTEND_URL`, `EMAIL_FROM` missing → defaults are wrong for prod).

**Tests:**

- `[TBD]` [tests/coverage] api/tests/ — only `test_scoring.py` and `conftest.py` exist (per Phase 1 file list). **Phase 2 of `GAP_ANALYSIS.md` flags scoring engine validation tests as MISSING (blocked by needing Brian's 3 sample assessments).** Beyond scoring, there are NO tests for: auth, billing webhook, admin role mutations, audit-log writes, idempotency, race conditions, CSV export sanitization, password policy. → Build out a test suite. The race + idempotency findings in 2.1, 2.2, 2.4 each need a regression test that fails today against the unfixed code. → L
- `[TBD]` [tests/no-test-runner] api/requirements.txt — `pytest` was not declared as a dep until this sweep added it to `requirements-dev.txt`. **`api/tests/test_scoring.py` exists but had no declared test runner** (anyone running `pytest` in a fresh venv would see ModuleNotFoundError). → ✓ resolved by `requirements-dev.txt` written in this sweep. → done
- `[TBD]` [tests/web-none] web/ — no test runner installed (no Vitest, no Jest, no Playwright dev deps in `web/package.json`). The `e2e/` folder exists at repo root and is gitignored — likely a Playwright setup that isn't part of CI. → Decide: vitest for unit tests on critical client logic (token handling, role-based redirects, form validation) + add a thin smoke test. e2e is more valuable but heavier. → M
- `[TBD]` [tests/legacy-validation] api/tests/test_scoring.py — needs to assert against Brian's 3 sample assessments per `GPS_Rebuild_Phased_Plan.md` (IDs 549, 1911, 26169). Currently empty per `GAP_ANALYSIS.md`. → Add fixtures + parameterized test cases. → M

**CI:**

- `[TBD]` [ci/none] `.github/workflows/` — **No workflow files exist.** No CI runs typecheck, lint, build, test, or audit on PRs or main. Every regression in this sweep could ship undetected. → Add `.github/workflows/ci.yml` running, on push to main + PRs: web (`npm install && npx tsc --noEmit && npx eslint src && npm run build`), api (`pip install -r requirements-dev.txt && ruff check && mypy --ignore-missing-imports api/app && pytest`), audit (`npm audit --omit=dev` + `pip-audit -r api/requirements.txt`). Fail the job on errors, warn on audit-residuals. → M
- `[TBD]` [ci/secret-scan] no CI hook calls `scripts/scan-build-for-secrets.sh`. → Wire into the same `ci.yml` after the web build step. → S
- `[TBD]` [ci/branch-protection] no documented branch protection on main. → Configure GitHub branch protection (require PR + CI green); not a code change. → S manual

**Build / deploy:**

- `[TBD]` [build/render-buildcommand] render.yaml:20 — `cd web && npm install && npm run build` does not run typecheck or lint as a deploy gate. `npm run build` IS `tsc && vite build` per `package.json` so typecheck IS enforced ✓. ESLint is not. **A failing eslint won't block deploy.** → After the eslint warnings in 1b are addressed, add `npm run lint` to the build command. → S
- `[TBD]` [build/api-no-migrations] render.yaml — no Alembic `upgrade head` step in the API service start command. Migrations are applied via `Base.metadata.create_all(...)` in `main.py:12` which **only creates missing tables** and never alters existing schemas. **Adding a column via Alembic locally won't apply on Render.** → Two options: (a) explicit `alembic upgrade head` in Dockerfile CMD (`sh -c "alembic upgrade head && uvicorn …"`), or (b) Render `preDeployCommand` (paid feature). Today, schema drift between Alembic versions and prod DB is a real risk. → S
- `[noise]` [build/web-build-cmd] render.yaml:20 — proper build command for static site. **Why noise:** correct.

## 4. Pass 3 — Triage

**Note on tagging:** Rows in Passes 1 + 2 retain their `[TBD]` discovery tags. This section is the authoritative severity assignment and fix sequence — refer here for what blocks launch.

---

### Findings by severity

**Total findings:** 161 (`[TBD]` discovery rows that need a decision) + 16 `[fp]/[noise]` (already adjudicated). Severity assigned below.

- **P0 (blocks launch):** 14 findings.
- **P1 (pre-launch window):** ~80 findings.
- **P2 (post-launch backlog):** ~67 findings.

---

### P0 — Blocks launch

These either expose a security vulnerability, cause silent data loss, or render a core flow non-functional. None of them have viable workarounds short of the proposed fix.

1. **Privilege escalation via member-role update.** `PUT /admin/members/{id}` with `{"role":"master"}` grants any user system-wide master access. (2.5 admin/priv-escalation; effort S)
2. **Production emails link to localhost.** `FRONTEND_URL` not set in render.yaml; default `http://localhost:5173`. Password reset, verification, invite, result emails all broken in prod. (2.9 render/env-frontend-url; effort S)
3. **Production emails sent from wrong domain.** `EMAIL_FROM` not set in render.yaml; default `noreply@giftpassionstory.com` while Resend domain verification (per memory) is on `disciplesmade.com`. Mail likely fails DKIM/SPF and lands in spam. (2.3 email/branding + 2.9 render/env-email-from; effort S)
4. **HTML injection in every email template.** Raw f-string interpolation of user-controlled `first_name`/`last_name`/`org_name`/`member_name`/`org_key`. A malicious church admin or member name acts as a phishing payload to other recipients. (2.3 email/injection; effort M)
5. **Account deletion has no password reauth.** `DELETE /auth/account` only requires confirmation string `"DELETE"`. A stolen/leaked access token permanently deletes the account. (2.1 auth/account-deletion; effort S)
6. **Rate limiter sees only Render's proxy IP.** All slowapi limits collapse to one bucket per Render front-end IP. Login `5/minute` is effectively `5/minute total`. (2.1 auth/rate-limit + 2.6 audit/ip-spoof — same fix; effort S)
7. **Stripe webhook has zero idempotency.** Stripe retries cause duplicate `Payment` rows + duplicate audit entries. (2.2 billing/webhook idempotency; effort M)
8. **Stripe webhook returns 200 on handler errors.** Transient DB blip silently drops the event; Stripe doesn't retry. (2.2 billing/webhook 200-on-error; effort S, after dedupe)
9. **Subscribe is non-atomic across double-click.** Two requests create two Stripe subscriptions; first orphan keeps charging the customer monthly. (2.2 billing/atomicity; effort M)
10. ~~**Stripe SDK v14 broke `current_period_*` — silent None writes.** `subscription.current_period_start/end` removed from top level; code uses `.get()` with falsy fallback so DB rows get `None` for period dates. Webhook handlers also crash silently when API version rolls forward.~~ (2.2 billing/stripe-v14 cluster — 3 sites, 2.1 auth/billing-sync; effort S total bundle) **(DONE: B4)**
11. **CSRF via cookie-fallback auth.** `get_current_user` accepts cookie token + `samesite=none` + `allow_credentials=True` = state-changing Form POST endpoints (e.g. `/auth/password-strength`) are CSRF-vulnerable from any origin allowed by CORS. (2.1 auth/csrf; effort M)
12. **Access token stored in localStorage.** Comment claims "memory only" but `useEffect` writes to localStorage. XSS exfiltrates the token immediately; no CSP to slow the attacker. (2.10 ui/access-token-storage; effort M)
13. **CSV exports unprotected against formula injection.** `sanitize_for_csv` exists but is never imported. Master export, admin per-member export, dashboard self-export all write user-controlled strings raw. Excel/LibreOffice render `=cmd|...` as a formula on download. (1c api/security + 2.5 master/csv-injection; effort M)
14. **Master role check uses `memberships[0]`.** A user with multiple memberships can pass or fail master check non-deterministically. Combined with #1 above, escalation can be hidden behind the membership-order brittleness. (2.1 auth/master + 2.5 admin/get-org pattern; effort S)

**P0 effort total:** ~1.5 person-weeks (sum of efforts, with some bundling discounts).

---

### Recommended fix sequence

Do in this order. Each batch is a single PR — fixes within a batch share the same fix pattern and code area, making review concise.

#### Batch 1 — env-config (S, ½ day)

Fixes P0s #2, #3 + several P1 env-parity findings. Lowest risk, unblocks downstream testing.

- Set `FRONTEND_URL` and `EMAIL_FROM` in render.yaml.
- Update code default `EMAIL_FROM` in `core/config.py:52` to match `.env.example` (disciplesmade.com).
- Replace `giftpassionstory.com` text in all 9 email templates → `disciplesmade.com`.
- Add `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `ALGORITHM` as commented entries in `.env.example`.
- Confirm CORS_ORIGINS in render.yaml uses the right production domain.
- Add `healthCheckPath: /health` to render.yaml.

#### Batch 2 — proxy-IP (S, ½ day)

Fixes P0 #6 + powers correct audit logging.

- New `core/rate_limits.py` `key_func` that reads leftmost `X-Forwarded-For`, falls back to `request.client.host`.
- Same logic in `core/audit.py:62-63` for `ip_address`.
- Add a single helper in `core/network.py` (`def get_client_ip(request) -> str:`) used from both.

#### Batch 3 — auth-gap (S, 1 day)

Fixes P0 #1, #5, #14 + several P1 auth findings.

- `schemas/admin.py:57` change `MemberUpdate.role` to `Literal["user","member","admin"]`.
- `routers/admin.py:404` add server-side guard: `if update.role == "master": raise 403`.
- `dependencies/auth.py:217, 231` change `require_master` to use `_get_active_membership` or query memberships filtered by role name.
- `routers/auth.py:382` add `password: str` to `AccountDeleteRequest`; verify in `services/auth_service.py:443`.
- Add `@limiter.limit(...)` to refresh, logout, change-password, onboarding-complete, org/{key}, password-strength.
- Delete `dependencies/auth.py:370` `get_optional_user` (dead + buggy).
- Delete `dashboard.py:544 /upgrade-to-admin` (duplicate of /auth/upgrade/church).

#### Batch 4 — Stripe-v14 (S, 1 day)

Fixes P0 #10 entirely.

- `services/stripe_service.py` — replace 3 sites of `subscription.current_period_*` / `subscription.get("current_period_*")` with `subscription["items"]["data"][0]["current_period_*"]`.
- Same in `dependencies/auth.py:351-365` and `routers/billing.py:131-142`.
- `services/stripe_service.py:180` rename `Invoice.upcoming_preview` → `Invoice.create_preview` per current SDK.
- Set `stripe.api_request_timeout = 10; stripe.max_network_retries = 2` at module load.
- Remove the silent `try/except Exception: pass` in `dependencies/auth.py:351-365` (let errors raise; handle at router boundary).

#### Batch 5 — billing-atomicity (M, 1.5 days)

Fixes P0 #7, #8, #9 + several P1 billing findings.

- New table `webhook_events(stripe_event_id PK, processed_at)` via Alembic migration.
- `routers/billing.py:618` rewrite handler to INSERT-on-receipt with `ON CONFLICT DO NOTHING`; only call `handle_*` if insert created a new row.
- Let exceptions propagate from handler → 5xx so Stripe retries.
- `routers/billing.py:199` wrap `subscribe` body in `db.query(Subscription).with_for_update().filter(...)` lock; pre-check `stripe.Subscription.list(customer=customer.id, status='active')`.
- `services/stripe_service.py:38` add idempotency key on `Customer.create` OR lock the Organization row.

#### Batch 6 — XSS / token-storage (M, 1 day)

Fixes P0 #11, #12 + the CSP/security-headers P1.

- `routers/auth.py:65-66`: only honor cookie token on safe (GET/HEAD/OPTIONS) methods; for mutating verbs, require `Authorization` header.
- Add `web/public/_headers` (Render static-site header rules) with CSP, HSTS, X-Frame-Options, Referrer-Policy, Permissions-Policy.
- `web/src/context/AuthContext.tsx`: drop the `useEffect` that writes to localStorage; rely on the refresh-cookie path on cold load.
- Refactor `AdminDashboard.tsx`, `AuditLog.tsx`, `SystemExport.tsx` to use shared `api` axios instance (no localStorage reads).

#### Batch 7 — email-safety (M, 1 day)

Fixes P0 #4 + several P1 email findings.

- `services/email_service.py`: add `_safe(text)` helper (`html.escape(text or "")`) and use in every f-string interpolation across all 9 templates.
- Add `requests.post(..., timeout=10)` (or wrap Resend calls) — needs Resend SDK doc check.
- For password-reset and primary-admin-welcome, propagate Resend exceptions (let the API raise 503 instead of silent success).
- Move all sends to FastAPI `BackgroundTasks` so they don't block the user request.

#### Batch 8 — csv-injection (M, ½ day)

Fixes P0 #13.

- Import `sanitize_for_csv` in `routers/master.py`, `routers/dashboard.py`, `routers/admin.py`.
- Wrap every `writer.writerow([... user.email, user.first_name, ... ])` arg with `sanitize_for_csv(...)` for any field that could contain user input.
- Add a unit test that writes a row with `=cmd|...` and asserts the output is escaped.

After Batch 1-8, **all P0s are closed**. Estimated total: 1-1.5 person-weeks.

---

### P1 batches (post-P0, pre-launch)

Group by fix-pattern so each PR stays small. Each batch is 1 commit / 1 PR.

#### atomicity-batch

UNIQUE constraints + locks for the read-modify-write races flagged across subsystems.

- `answers.(assessment_id, question_id)` UNIQUE — closes the save-progress race.
- `assessment_results.assessment_id` UNIQUE — closes submit double-result.
- `myimpact_results.assessment_id` UNIQUE — same.
- `memberships.(user_id, organization_id)` UNIQUE — closes upgrade-to-admin race.
- `users.email` UNIQUE on `lower(email)` (or `citext`) — closes case-different-email race.
- `submit_assessment` wraps in `with_for_update()` lock on the Assessment row.
- Each constraint addition needs an Alembic dedup migration first (count + report duplicates, then INSERT-or-UPDATE consolidate).

#### index-batch

All missing indexes from 2.7. Single Alembic migration adding ~12 indexes. No code change. Low risk because indexes can be created with `CONCURRENTLY` to avoid locking.

#### audit-batch

- Add `@audit_action(...)` to: `/admin/settings PUT`, `/admin/invites/{id} DELETE`, `/admin/invites/{id}/resend POST`, `/admin/invites/csv POST`.
- Add `log_audit_event(...)` calls in: register success, logout, password-reset (consume), email-verify, profile-update.
- Add audit on `/billing/payment-method` POST/DELETE.
- Add audit on admin-fallback `/grade` and `/pdf` (assessment/admin reads).
- Capture `before/after` state in audit `details` for state-changing routes.
- Decorator: re-raise on sensitive-action audit failure (don't swallow).

#### token-storage-batch

- Switch password-reset, email-verification, invite tokens to hashed storage (Alembic migration adds `token_hash` columns, drops plaintext after a backfill).
- Token rotation: in `refresh_access_token`, mark the old refresh-token row `revoked=true` before issuing new ones.

#### email-policy-batch

- Validate new password against `PasswordPolicy` in `reset_password`.
- Invalidate existing unused reset tokens on new request.
- Block role="master" via schema (already in P0 batch 3).
- Soft-delete memberships on account-delete (or write audit row capturing pre-delete state).

#### bundle-batch (web)

- Convert `App.tsx` page imports to `React.lazy()` + `<Suspense>`. Three chunks: public, member, admin.
- Add `manualChunks` config in `vite.config.ts`.
- Resize `hex-background.webp` (2.2MB → ~200KB).
- SVGO the MyImpact Logo.
- Drop the duplicate `API_URL` constant in `PasswordInput.tsx`.

#### env-validators-batch

- `core/config.py`: validator that rejects `sqlite://` `DATABASE_URL` when `DEBUG=False`.
- Validator that rejects `localhost` in `CORS_ORIGINS` when `DEBUG=False`.
- Generic exception handler in `app/main.py` returning sanitized 500.
- Request-ID middleware + structured logging.

#### ci-batch

- New `.github/workflows/ci.yml` running typecheck + lint + audit + test on web AND api on every PR + push to main.
- Wire `scripts/scan-build-for-secrets.sh` after the web build.
- Branch protection on main (manual GitHub UI step).
- Add `npm run lint` to render.yaml `gps-web` build command (after eslint warnings cleared).
- Add `alembic upgrade head` to api Dockerfile CMD so migrations apply on deploy.

#### test-batch

- Scoring engine validation tests using Brian's 3 sample assessments (IDs 549, 1911, 26169).
- Regression tests for each P0 race / idempotency fix (test should fail against unfixed code).
- Web vitest setup + smoke test on auth flow + role-redirect.

#### export-streaming-batch

- `master/system_export("full")` — switch to `StreamingResponse` + `yield_per()`. OR move to background job that emails the file.
- Date-range filter on full-export audit log section.
- Cap `/billing/invoices?limit` to 50 server-side.
- Cap `/admin/pending`, `/master/churches/{id}/members`, `/admin/invites`, `/assessments/my-assessments` with pagination or hard `LIMIT`.

#### subscription-grace-batch

- Periodic check (cron-like via APScheduler in a Render Background Worker, OR in-process with Render Cron Job add-on): for any subscription where `current_period_end + 14d < now()`, force-lock.
- Email template for past-due reminder + 7-day-warning + lock notification.
- Auto-cleanup expired refresh tokens / password-reset tokens.

#### error-boundary-batch (web)

- Add top-level `ErrorBoundary` in `App.tsx`.
- Fix the 4 `react-hooks/set-state-in-effect` errors flagged in 1b.
- Audit-bypass-localStorage refactor (the 4 pages reading the token directly).

---

### P2 — Post-launch backlog (1-line each)

Cleanup, optimization, hardening that doesn't block launch.

**Code hygiene:**
- ruff `--fix` on the 19 unused imports + ordering fixes (1b).
- Delete `web/src/components/AssessmentHistory.tsx` + `ChurchLinking.tsx` and matching CSS (1c).
- Delete unused `validate_password`, `handle_exception`, `master.py:721 http_request` if rate-limit verification clears (1c, 2.5).
- Strip JSON5 comments from `web/tsconfig.json` (or rename to `.jsonc`) for downstream tools (1c).
- Fix `web/src/pages/MasterDashboard.tsx`, `Dashboard.tsx`, `AdminDashboard.tsx` `react/no-unescaped-entities` errors (1b cosmetic).
- Replace `~30` `any` types with proper interfaces matching API responses (1b).
- Remove unused destructured form fields in `Register.tsx`, `ChurchRegister.tsx` (or wire them into the API call — Pass 2 confirm).
- `print(...)` → `logger.info(...)` in `assessments.py` (already in 1b).
- Fix `db_seed.py:178` `Question` shadowing (1b).
- Remove `master.py:1156 year_start` unused local (1b).
- Fix `services/auth_service.py:433` `ColumnElement[bool]` → `bool` (1a).
- Health endpoint `db.execute("SELECT 1")` → `text("SELECT 1")` (2.8).

**Performance / scale:**
- N+1 in `/master/audit-log` (joinedload AuditLog.user).
- N+1 in master CSV exports (joinedload).
- N+1 in `/dashboard/churches/search` (single GROUP BY).
- Notification unread-count caching.
- `pg_trgm` index on `organizations.name` once org count grows.
- Comma-separated columns → JSONB or join table (assessment_results.people/cause/abilities).
- `reportlab` is heavy; consider lazy-import.

**Security hardening:**
- Audit-log append-only DB enforcement (revoke UPDATE/DELETE on the table or trigger).
- Audit-log retention policy (legal-confirmed).
- Dockerfile non-root user + multi-stage build + `.dockerignore`.
- Self-host Mulish font (GDPR for any EU users).
- Update `<html lang>` based on user locale.
- Drop unused billing `unit_amount`/`stripe_payment_intent_id`/`stripe_invoice_id` columns OR wire them to invoice webhook.

**UX:**
- Loading-state component consolidation.
- Email unsubscribe link for assessment-notification (if reclassified marketing).
- Notification rate limits (currently unbounded poll).
- `[fp]` UpdateLocale.tsx exhaustive-deps disable comment with reason.

**Type/static-analysis:**
- Address mypy `Column[X]` noise via `sqlalchemy.ext.mypy.plugin` config.
- The mypy type-narrowing issues in `admin.py` and `assessments.py` myimpact branches (2 sites).
- `master.py:190, 259` and `admin.py:669` Pydantic dict→model construction.

**Data:**
- `email_verified` and `is_read` `"Y"/"N"` → boolean migration.
- Drop unused Spanish-translation columns OR document deferral.

---

### Notes on `[fp]` and `[noise]`

`[fp]` and `[noise]` rows are documented inline in Passes 1 + 2 with their reasons. None of them require action. The most important to remember when re-running this sweep:

- The mypy `Column[X] vs X` cluster is SQLAlchemy 2.0 + mypy without the plugin. Real fix in a P2.
- Ruff E712 `== True/False` in `.filter(...)` calls is REQUIRED for SQLAlchemy DSL. Don't auto-fix.
- ESLint `react-hooks/exhaustive-deps` on `UpdateLocale.tsx:26` is a deliberate one-shot — keep with disable comment + reason.
- Knip flagging `depcheck` and `rollup-plugin-visualizer` as unused devDeps — they ARE used, just not via direct imports.
