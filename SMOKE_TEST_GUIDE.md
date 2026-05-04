# GPS Platform v2.1 Addendum — Smoke Test Guide

This is the **manual** test plan for things I couldn't run from the dev environment — anything requiring a real browser, a logged-in user, real Stripe/Resend credentials, or real time-passing (e.g., the 60-second notification poll, the 1-minute retry cron).

## Automated suite — already run

44 backend smoke tests across three scripts. Last run: 2026-05-01, all green against the live Render Postgres DB.

| Script | Tests | Status | Coverage |
|---|---|---|---|
| [smoke_pure.py](api/scripts/smoke_pure.py) | 22 | ✅ 22/22 | Pydantic locale validation, payload builders (GPS, MyImpact, user_registered, test), SSRF guard (8 URL types), HMAC determinism, backoff constants |
| [smoke_live.py](api/scripts/smoke_live.py) | 12 | ✅ 12/12 | Live HTTP delivery (httpbin), DB schema integrity (notifications, webhook tables, gifts_passions, MyImpact backfill row count + UTF-8 intact), retry runner SQL parses + returns 0, translations.ts coverage, useTranslation hook exists |
| [smoke_e2e.py](api/scripts/smoke_e2e.py) | 10 | ✅ 10/10 | Notification service round-trip (create / read / mark-read / mark-all-read), webhook config CRUD with secret rotation, UNIQUE constraint enforcement, SSRF guard at save-time, `fire()` success + no-op + failure-with-retry-scheduling, `test_delivery()` doesn't pollute log |

Run them on Windows with UTF-8 output (CP1252 doesn't render the `→` arrows in the test names):

```bash
cd api
PYTHONIOENCODING=utf-8 python -u scripts/smoke_pure.py
PYTHONIOENCODING=utf-8 python -u scripts/smoke_live.py
PYTHONIOENCODING=utf-8 python -u scripts/smoke_e2e.py
```

`smoke_e2e.py` creates transient test rows (a `SmokeTest Church <hex>` org with two test users) and cleans them up at the end. Re-running is safe.

**What the automated suite confirms:**
- Phase A — notifications schema migrated, service round-trips with Boolean `is_read`, mark-all-read endpoint works.
- Phase B — webhook tables on Render with all constraints and indexes; SSRF guard blocks 6 private/loopback ranges; HMAC sign/verify; UNIQUE (org, event_type) prevents dup configs; `fire()` writes log rows and schedules retries with the correct backoff.
- Phase D — `gifts_passions.description_es` column present and nullable; 17 MyImpact rows backfilled with intact Spanish text; locale validation rejects `'fr'` / `'ZH-cn'`; centralized translations.ts has 50+ entries.

**What the automated suite does NOT cover** — the manual checklist below picks up here.

The tests below assume the API and web are running and that you have at minimum:
- A **member** account
- A **church admin** account (primary admin) with an active subscription
- A **master admin** account
- A `webhook.site` URL ready for inspection (free, no signup) — go to https://webhook.site and copy your unique URL.

---

## Pre-flight: deploy the new render.yaml + set INTERNAL_CRON_SECRET

Before any of the webhook tests will fire end-to-end:

1. In the Render UI, set `INTERNAL_CRON_SECRET` on **both** services:
   - The `gps-api` web service.
   - The new `gps-webhook-retries` cron job (will appear after the next deploy).
   - Use the same value on both. A pre-generated value is in [EXECUTION_PLAN_v2_Addendum.md](EXECUTION_PLAN_v2_Addendum.md) under Phase B.
2. Verify the cron service appeared in the Render dashboard with schedule `* * * * *`.
3. Confirm the cron's `API_BASE_URL` matches your live API URL.

If you want to run things locally instead, set `INTERNAL_CRON_SECRET` in `api/.env` and skip the cron — the retry runner can be invoked manually with curl.

---

## Phase A — In-app notifications

**A1. Bell badge polls every 60 seconds**
- [ ] Log in as a church admin.
- [ ] Open browser DevTools → Network tab → filter for `unread-count`.
- [ ] Wait 60+ seconds. You should see a `GET /notifications/unread-count` request fire approximately once per minute (not 30s — this changed in Phase A).

**A2. New assessment fires the admin notification**
- [ ] In a second browser/incognito window, log in as a member of that admin's church.
- [ ] Submit a GPS or MyImpact assessment.
- [ ] Within 60s, the admin's bell should show a red badge with "1".
- [ ] Click the bell → see "{Member name} completed GPS" / "MyImpact" with a recent timestamp.
- [ ] Click the notification → page navigates somewhere relevant (admin dashboard with the member highlighted).

**A3. Mark-as-read endpoint renamed**
- [ ] In DevTools, click "Mark all as read" in the bell dropdown.
- [ ] Verify the request fires to `PATCH /notifications/mark-all-read` (not `/read-all`).
- [ ] Badge clears to zero.

**A4. Boolean is_read works end-to-end**
- [ ] Pre-existing notifications from before the migration should still display correctly.
- [ ] Reading a single notification should update only that one (not all).

**A5. New event types render with their icons**

Trigger each event and verify the bell shows a sensible icon + correct text:
- [ ] `assessment_completed` (admin) → already covered in A2.
- [ ] `assessment_self_completed` (member) → after a member submits, *they* should also get a "Your results are ready" notification.
- [ ] `member_joined` → register a new user via `/register` with your church's `organization_key` parameter. The admin's bell should show "{Name} joined {Church}".
- [ ] `member_requested` → as an unaffiliated user, navigate to "Find My Church" → request to join. Admin's bell should show "{Name} requested to join".
- [ ] `church_created` → log in as master admin, click "Add Church", create a church with a different master account as admin (or just observe your own bell). All *other* master admins should see "{Church name} was created". (This includes the master admin self-signup flow, but you'd need an unrelated master admin account to actually see the notification.)

---

## Phase B — Webhook configuration UI

**B1. CRM Integration panel renders**
- [ ] As church admin, go to the Settings tab on the admin dashboard.
- [ ] Replace where "Manage Connections" used to be is a "CRM Integration" section with two sub-panels:
  - "Assessment Results Webhook"
  - "New Member Registration Webhook"

**B2. Create + test an assessment webhook**
- [ ] Open https://webhook.site in another tab. Copy the unique URL.
- [ ] In the Assessment Results Webhook section: paste the URL into the field.
- [ ] Tick the "Generate signing secret" checkbox.
- [ ] Click "Create webhook" — toast should say "Webhook created".
- [ ] A yellow banner should appear with the plaintext signing secret. Copy it.
- [ ] After save, the secret display should change to `••••<last4>` (masked).
- [ ] Click "Test connection" — toast should say "Test delivery succeeded (HTTP 200)".
- [ ] Switch to webhook.site tab — verify a request arrived with:
  - JSON body containing `"test": true`
  - Header `X-GPS-Event: assessment_completed`
  - Header `X-GPS-Signature: sha256=...`
  - Verify the signature matches HMAC-SHA256(secret, body) — you can do this in any HMAC validator.

**B3. End-to-end assessment webhook**
- [ ] As a member of that admin's church, submit a GPS assessment.
- [ ] Within ~10 seconds, webhook.site should receive a real payload (no `test: true` flag, real gift/passion data, real user info).
- [ ] Back in the admin's CRM Integration panel, click "Show delivery log".
- [ ] You should see one row with status `success`, HTTP 200, attempts 1.

**B4. End-to-end registration webhook**
- [ ] In the New Member Registration Webhook section, paste a fresh webhook.site URL, click Create.
- [ ] In another browser (logged out), register a new user via `/register?key=<your-org-key>` with that organization key.
- [ ] webhook.site should receive a `user_registered` payload (email, firstName, church id/name).

**B5. SSRF guard blocks bad URLs**
- [ ] Try to save `http://localhost:8080/x` as a webhook URL. Save should fail with a 400 + clear error message about private IPs.
- [ ] Try `http://10.0.0.1/x` — same rejection.
- [ ] Try `file:///etc/passwd` — rejection mentioning scheme.

**B6. Webhook retry on failure**

This needs either time (1 minute for the first retry) or a manual trigger. Two paths:

Option A (real time):
- [ ] Configure a webhook URL that returns 500 (use https://httpbin.org/status/500).
- [ ] As member, submit an assessment. Delivery log shows `failed`, attempts=1, next_retry_at = +60s.
- [ ] Wait ~1 minute. The cron should hit the internal endpoint, redeliver. Refresh log: still failed, attempts=2, next_retry_at = +5 min.
- [ ] Wait ~5 more minutes. attempts=3, status=`dead`, next_retry_at NULL.

Option B (manual trigger):
- [ ] Configure the same 500-returning URL.
- [ ] As member, submit assessment.
- [ ] In a terminal:
  ```
  curl -X POST -H "X-Internal-Secret: $INTERNAL_CRON_SECRET" \
    https://gps-api-4q4m.onrender.com/internal/webhooks/process-retries
  ```
  - First attempt should be still-too-early-to-retry (initial fire just happened); response `{"processed": 0}`.
  - Wait for `next_retry_at` to pass, then re-curl. Should now show `{"processed": 1}` and the delivery row should show attempts=2.

**B7. Cron secret enforcement**
- [ ] `curl` the internal endpoint without the header → 404 (not 401, on purpose).
- [ ] With the wrong secret → also 404.

**B8. Master admin sees webhook config (read-only)**
- [ ] Log in as master admin.
- [ ] On the Churches tab, expand any church that has webhooks configured.
- [ ] You should see a "CRM Integration" section listing both event types with status (configured / not configured), masked URL, and last delivery info.

**B9. Plural API safety: cross-org access blocked**
- [ ] As one church admin (Church A), copy a webhook config ID from the URL bar after editing it.
- [ ] Log out, log in as a different church admin (Church B).
- [ ] In DevTools, try `fetch('/admin/webhooks/<that-id>')` → expect 404 (Org-scoping safety).

---

## Phase C — Event wiring (most overlaps with Phase A/B above)

**C1. Assessment submission still 200 even when webhook URL is broken**
- [ ] Configure a webhook URL pointing at `https://does-not-exist-12345.example.com`.
- [ ] As member, submit an assessment. Submission should complete without error from the user's perspective (page navigates to results).
- [ ] In delivery log, the row shows `failed` with the connection error message.

**C2. Independent registrations don't fire user_registered**
- [ ] As an admin with a configured registration webhook, observe webhook.site.
- [ ] In a fresh browser, register a new user via `/register` *without* an `organization_key` (i.e., independent user).
- [ ] webhook.site should receive **nothing** for this registration.

**C3. Notifications work even when webhook is unconfigured**
- [ ] Delete both webhook configs for your church.
- [ ] As member, submit an assessment.
- [ ] Admin's bell should still get the `assessment_completed` notification (notifications and webhooks are independent).

**C4. `member_joined` fires on link-request approval**
- [ ] As an unaffiliated user, request to join the church (Find My Church flow).
- [ ] As admin, approve the pending request.
- [ ] After approval: admin gets `member_joined` notification + `user_registered` webhook fires (verify webhook.site).

**C5. `church_created` fires on master add-church**
- [ ] You'd need at least 2 master admin accounts to verify this. Master admin Alice clicks Add Church → creates one. Master admin Bob's bell should show "{Church} was created". Master admin Alice's bell should NOT (actor is excluded).

---

## Phase D — Spanish language

**D1. Locale toggle works**
- [ ] As any user, open the dashboard.
- [ ] Click "¿En español?" in the footer. Page reloads in Spanish:
  - Greeting: "Bienvenido a su tablero, {firstName}"
  - Buttons: "Tomar una nueva evaluación GPS", "Tomar una nueva evaluación MiImpacto", "Exportar mis datos"
  - Section headers: "Evaluaciones GPS", "Evaluaciones MiImpacto"
  - Table headers: "Iniciada", "Completadas", "Progreso", "Regalos", "Pasión"
  - Action buttons: "Ver resultados", "Continuar"
  - Hamburger menu: "Cuenta", "Actualizar contraseña", "Cerrar sesión"
- [ ] Footer link now says "In English?".

**D2. Locale persists across sessions**
- [ ] Log out, log back in. Should remain Spanish.

**D3. Locale validation rejects garbage**
- [ ] In DevTools, run:
  ```js
  await fetch('/auth/profile', {
    method:'PUT', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({locale:'fr'})
  })
  ```
  Should return **422 Unprocessable Entity**.

**D4. Spanish GPS questions render**
- [ ] In Spanish mode, start a new GPS assessment.
- [ ] Verify question text is Spanish (e.g., "Busco oportunidades para hablar de asuntos espirituales con personas no creyentes.").
- [ ] Likert scale labels: "Casi Nunca", "Casi Siempre".

**D5. Spanish MyImpact questions render**
- [ ] In Spanish mode, start a new MyImpact assessment.
- [ ] Character section first question: "Soy una persona amorosa. Amo a todas las personas incondicionalmente, como Dios me ama a mí."
- [ ] Calling section first question (after Q9): "Puedo nombrar mis 3 Dones Espirituales principales. ..."

**D6. GPS results page mixed-content**
- [ ] In Spanish mode, view a completed GPS assessment's results.
- [ ] Section headers should be Spanish ("Tus Dones Espirituales", "Pasiones", "Tus Selecciones", "Habilidades Clave").
- [ ] Gift/passion **names** should be Spanish-renderable but currently show their English DB names (e.g., "Wisdom") — there's no `name_es` column. This is expected.
- [ ] Gift/passion **descriptions** are still English — this is a known content gap (`description_es` column exists but isn't populated yet for the 19 gifts + 5 styles). Should *not* break the page.

**D7. English fallback for missing translations**
- [ ] In Spanish mode, navigate to admin or master dashboard. These pages stay English by design (per addendum).
- [ ] No `{key}` placeholders should appear anywhere — that would mean a missing translation key.

---

## Phase E — Included items

**E1. Help button in nav**
- [ ] On any page (logged in or out, member or admin or master), look at the top-right of the navbar.
- [ ] You should see a "Help" link between the GPS/MyImpact logos and the notification bell.
- [ ] On mobile, open the hamburger menu → Help link appears.
- [ ] Click Help → your default email client opens with:
  - To: `info@disciplesmade.com`
  - Subject: `GPS Platform Help Request`
  - Empty body.

**E2. Stripe Customer Portal**
- [ ] As primary admin with an active subscription, navigate to `/admin/billing`.
- [ ] Click "Open billing portal" / "Manage Subscription" (button text varies).
- [ ] Should redirect to a Stripe-hosted page where you can update card, view invoices, cancel.
- [ ] After completing actions, returning to the app should land on the billing dashboard.

**E3. Stripe portal blocks impersonation**
- [ ] As master admin, impersonate the primary admin of some church.
- [ ] Try to open the billing portal. Should return **403 Forbidden** (`require_primary_admin_no_impersonation`).

**E4. Master admin Add Church**
- [ ] As master admin, click "Add Church" on the Churches tab.
- [ ] Fill in: church name, city, state, primary admin email/first/last.
- [ ] Submit. Should:
  - Create the org with a unique slug.
  - Audit log entry written (`master_create_church`).
  - If new user, welcome email sent.
  - `church_created` notification fires for *other* master admins (see C5).

---

## Cross-cutting checks

**X1. No `{firstName}` or `{key}` placeholders visible**
- [ ] After Spanish toggle, no string in the UI should literally contain `{somekey}`. Those would mean the `interpolate()` call missed a value.

**X2. Browser console clean**
- [ ] Open DevTools console on every page after the changes. No unhandled errors related to the new code (NotificationContext, WebhookContext, useTranslation, etc.).

**X3. TypeScript build succeeds**
- [ ] Run `cd web && npm run build`. Should complete with exit 0.

**X4. Backend tests still pass**
- [ ] Run `cd api && pytest tests/`. Existing tests should still pass.

---

## What's intentionally NOT tested here

- **Per-gift `description_es` content** — column exists but no data. Phase D ships infrastructure with English fallback; content backfill is a separate follow-up.
- **Email delivery to real inboxes** — emails fire async via Resend; visual inbox check is on the operator.
- **Render Cron actually firing every minute** — verify in the Render Cron Job logs after deploy. Look for the curl invocation hitting `process-retries`.
- **Webhook signature verification by a real CRM** — webhook.site only shows the headers; integrating with a real ROCK RMS / Planning Center / Zapier is a customer's responsibility.

---

## When something fails

1. Capture the failing test number (e.g., "B6 step 3").
2. Capture the request/response from DevTools Network tab.
3. Capture any backend log lines from Render's logs.
4. Note the alembic version and the affected DB table state (`SELECT * FROM webhook_deliveries WHERE ...`).
