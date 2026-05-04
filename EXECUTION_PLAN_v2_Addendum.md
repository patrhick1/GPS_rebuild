# GPS Platform v2.1 Addendum — Execution Plan

**Source spec:** [GPS_PRD_v2_Addendum.md](GPS_PRD_v2_Addendum.md)
**Author:** Paschal Okonkwo
**Date:** 2026-04-30

---

## Phase Status

| Phase | Status | Completed | Notes |
|---|---|---|---|
| A — Notifications reconciliation | ✅ Done | 2026-04-30 | Migration applied to Render via direct psycopg2 (alembic CLI hung). See log. |
| B — Webhook infrastructure | ✅ Done | 2026-05-01 | Tables on Render, plural API only, retry runner via Render Cron. Payload builders + UI + master read-only complete. |
| C — Event wiring | ✅ Done | 2026-05-01 | Assessment completion → webhook. New member events (joined/requested/registered) wired across 3 callsites. Church created → master notifications. Invite-accept flow covered by existing register_user. |
| D — Spanish language | ✅ Done | 2026-05-01 | description_es column on Render, MyImpact 17 questions backfilled, locale Literal validation, centralized translations.ts + useTranslation hook, Wizard/Results/Dashboard refactored, Footer toggle preserved. Open: per-gift description_es content (24 strings). |
| E — Included items | ✅ Done | 2026-05-01 | Stripe portal + Master Add Church verified already-built. Help button (mailto) added to Navbar (desktop + mobile menu). |

Learnings & gotchas accumulate at the bottom of the file under "Implementation Log".

---

## Context

The platform is shipping four billable enhancements ($2,700) on top of the original v2 scope: in-app notifications, CRM webhooks, Zapier registration webhooks, and Spanish language support. Two original-scope items are also documented here for clarity (Stripe portal — already built, master add-church — already built; both verified during exploration).

This plan threads those features into the existing FastAPI + React codebase **without introducing tech debt**. Concretely it (a) reconciles the partially-built notifications subsystem with the addendum's data model rather than letting two shapes coexist, (b) builds a single plural webhook API instead of the addendum's two-step path, (c) consolidates the inline `ES_STRINGS` / `ES_RESULTS` objects in [AssessmentWizard.tsx](web/src/pages/AssessmentWizard.tsx) and [AssessmentResults.tsx](web/src/pages/AssessmentResults.tsx) into a single `translations.ts`, and (d) uses an internal endpoint + Render cron for webhook retries (no new in-process scheduler).

All four user-decision points have been confirmed: PRD-shape migration for notifications, internal endpoint + cron for retries, single-source translations, and plural-only webhook API.

---

## 0. Implementation Order & Dependencies

Follows the addendum's recommended order with one adjustment (notifications reconciliation comes first because it unblocks the new event types webhooks will also emit):

1. **Phase A — Notifications reconciliation** (small migration + endpoint rename). Unblocks PRD-aligned event types used downstream.
2. **Phase B — Webhook infrastructure** (configs + deliveries + delivery engine + retry cron + admin UI). Single plural API supporting both `assessment_completed` and `user_registered`.
3. **Phase C — Event wiring** (assessment completion → webhook + new notification types; church-affiliated registrations → webhook + notifications; church creation → master notification).
4. **Phase D — Spanish language** (centralized translations, locale validation, `description_es` migration, apply to Dashboard/Sidebar). Frontend-heavy, independent of A–C.
5. **Phase E — Included items** (Help button mailto, verify Stripe portal, verify master add-church). Mostly verification.

**Phase D content sources (mostly already in repo — see `/es/` folder and root CSVs):**
- **MyImpact Spanish:** [es/SPANISH - MYIMPACT ASSESSMENT.md](es/SPANISH%20-%20MYIMPACT%20ASSESSMENT.md) — finished spec by Chelsie Carroll (4/22/26). All 9 character + 8 calling questions, prompts, scale labels, result text, and notes are translated. Source for `questions.question_es` backfill on `instrument_type='myimpact'` rows.
- **UI strings:** [es/dashboard.php](es/dashboard.php), [es/forms.php](es/forms.php), [es/auth.php](es/auth.php), [es/toasts.php](es/toasts.php), [es/assessment.php](es/assessment.php) — Laravel translation files from the legacy platform. These cover greetings ("Buenas tardes", "Bienvenido"), navigation ("Tablero", "Idioma"), buttons ("Tomar una nueva evaluación", "guardar", "cancelar"), table headers ("nombre", "última evaluación", "regalos", "pasión"), language toggle ("In English?"), and more. Source for seeding `translations.ts`.
- **GPS questions Spanish:** [gps_questions_spanish.csv](gps_questions_spanish.csv) at repo root (156 rows) — already loaded into the DB via [c4d5e6f7a8b9_populate_gps_spanish_translations.py](api/alembic/versions/c4d5e6f7a8b9_populate_gps_spanish_translations.py). No further work needed for GPS question text.
- **People/causes/abilities lists:** Already translated in [es/assessment.php](es/assessment.php) lines 75-143 (16 people groups, 25 causes, 23 abilities) — these populate the multi-select pages of the GPS wizard.

**Remaining content gap (only one):** Per-gift / per-influencing-style **long descriptions** for `gifts_passions.description_es` (19 spiritual gifts + 5 styles). The `es/assessment.php` only contains short labels ("apostle" → "apóstol", "wisdom" → "sabiduría"); the multi-paragraph definitions shown on the results page have no Spanish source in the repo. Options to resolve, in order of preference:
  1. Extract from the legacy database (Laravel `gifts_passions` table likely has `description_es` populated). Owner: Paschal — pull from legacy DB dump if available, or ask Brian for export.
  2. If no legacy data exists, ask Brian's team to produce the 24 strings.

Phase D infrastructure (translations.ts, hook, locale validation, `description_es` column migration) ships immediately. Description content backfill is a small follow-up data migration once the strings are sourced. English fallback ensures the UI never breaks.

---

## Phase A — Notifications Reconciliation

### A.1 Why
The existing [notification.py](api/app/models/notification.py) drifts from the addendum on four axes (Y/N vs Boolean, missing `reference_type`/`reference_id`, endpoint named `/read-all` vs `/mark-all-read`, 30s vs 60s poll, `gps_result` event type not in spec). Reconciling now is cheap (one migration, four type-name renames) and prevents Feature 1 from being built on a half-aligned foundation.

### A.2 Backend changes

**Migration** — new file in [api/alembic/versions/](api/alembic/versions/), naming convention `{hex}_reconcile_notifications.py`:
- Add column `reference_type VARCHAR(50) NULL`.
- Add column `reference_id UUID NULL`.
- Convert `is_read` from `VARCHAR(1)` to `BOOLEAN`. Two-step in PostgreSQL:
  - `ALTER TABLE notifications ADD COLUMN is_read_bool BOOLEAN NOT NULL DEFAULT false`
  - `UPDATE notifications SET is_read_bool = (is_read = 'Y')`
  - `ALTER TABLE notifications DROP COLUMN is_read`
  - `ALTER TABLE notifications RENAME COLUMN is_read_bool TO is_read`
  - Recreate the existing `(user_id, is_read, created_at)` composite index.
- Rename existing notification rows where `type = 'gps_result'` or `type = 'myimpact_result'` to `assessment_completed` (data backfill in the migration's `upgrade()`).
- Rename `assessment_admin_notification` (whatever the current admin-facing type is — verify exact value during impl) to `assessment_completed`. Both user and admin notifications can share `assessment_completed`; recipient distinguishes them.

**Model** — [api/app/models/notification.py](api/app/models/notification.py):
- Change `is_read = Column(String(1), default='N')` → `is_read = Column(Boolean, nullable=False, default=False)`.
- Add `reference_type = Column(String(50), nullable=True)` and `reference_id = Column(UUID(as_uuid=True), nullable=True)`.
- **Keep** the existing `link` column — it's a finished deep-link string and orthogonal to `reference_type`/`reference_id` (entity pointer vs explicit URL). Both have value: `link` lets the backend dictate the route; `reference_type`/`reference_id` lets the frontend choose route shape per role.

**Service** — [api/app/services/notification_service.py](api/app/services/notification_service.py):
- Update `create_notification()` signature to accept `reference_type` and `reference_id` (both optional). Existing callers pass nothing → backwards compatible.
- Update `get_notifications()` to filter `is_read == False` (was `is_read == 'N'`).
- Update `mark_read()` and `mark_all_read()` to set `is_read = True` (was `'Y'`).

**Router** — [api/app/routers/notifications.py](api/app/routers/notifications.py):
- Rename `PATCH /notifications/read-all` → `PATCH /notifications/mark-all-read`.
- Confirm `GET /notifications` already supports `unread_only`, `limit`, `offset` query params; if `unread_only` is missing, add it.
- Confirm `GET /notifications/unread-count` already exists.

**Schemas** — [api/app/schemas/notification.py](api/app/schemas/notification.py):
- Update `NotificationResponse` to `is_read: bool` and add optional `reference_type: Optional[str]`, `reference_id: Optional[UUID]`.

### A.3 New event types
Add (or rename to) the addendum's four event types:
- `assessment_completed` — fired to admins on member's GPS or MyImpact completion.
- `member_joined` — fired to admins when a user joins their church (link registration, request approval, invite acceptance).
- `member_requested` — fired to admins when a user submits a link request to their church.
- `church_created` — fired to all master admins when a new organization is created.

The current "user gets a copy of their own assessment result" notification (currently `gps_result` / `myimpact_result`) is **out of the addendum's notification list**. Decision: keep firing it (existing functionality, member-facing), but rename the type to `assessment_self_completed` to disambiguate from the admin-facing `assessment_completed`. Migration handles the rename.

### A.4 Frontend changes
- [web/src/context/NotificationContext.tsx](web/src/context/NotificationContext.tsx) — change `POLL_INTERVAL = 30000` to `60000`. Update API calls: `/notifications/read-all` → `/notifications/mark-all-read`.
- [web/src/components/NotificationBell.tsx](web/src/components/NotificationBell.tsx) — update `is_read` checks from `=== 'Y'` / `=== 'N'` to `=== true` / `=== false` (or just truthy/falsy). Add icon mapping for the four addendum event types (assessment, member-join, member-request, church-created).
- Click behavior: prefer `notification.link` if present; otherwise compute route from `reference_type` + `reference_id`. Future-proof for notifications created without explicit links.

### A.5 Files touched
- `api/alembic/versions/{new_hex}_reconcile_notifications.py` (new)
- `api/app/models/notification.py` (modify)
- `api/app/services/notification_service.py` (modify)
- `api/app/routers/notifications.py` (modify)
- `api/app/schemas/notification.py` (modify)
- `api/app/routers/assessments.py` (rename type strings on existing `notification_service.create_notification` calls)
- `web/src/context/NotificationContext.tsx` (modify)
- `web/src/components/NotificationBell.tsx` (modify)

---

## Phase B — Webhook Infrastructure

### B.1 Why
The platform has zero generic-webhook scaffolding ([webhook_event.py](api/app/models/webhook_event.py) is Stripe-idempotency only). Building the full delivery engine once — with retry, signing, and a delivery log — supports both Feature 2 (assessment webhooks) and Feature 3 (Zapier registration webhooks) through one plural API. The "Manage Connections" stub on [AdminDashboard.tsx](web/src/pages/AdminDashboard.tsx) becomes the entry point.

### B.2 Data model

**New table `webhook_configs`** — [api/app/models/webhook_config.py](api/app/models/webhook_config.py):

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | `default=uuid.uuid4` |
| `organization_id` | UUID FK → organizations.id | NOT NULL |
| `event_type` | VARCHAR(50) | Values: `assessment_completed`, `user_registered` |
| `webhook_url` | VARCHAR(2048) | NOT NULL |
| `is_active` | BOOLEAN | NOT NULL, default `true` |
| `secret` | VARCHAR(255) | nullable; if set, signs payloads via HMAC-SHA256 |
| `created_at` | TIMESTAMP | UTC, default `datetime.utcnow` |
| `updated_at` | TIMESTAMP | UTC, default + `onupdate=datetime.utcnow` |

Constraints:
- `UNIQUE (organization_id, event_type)` — one webhook per (church, event) pair.
- Index on `(organization_id, is_active)` for fast lookup at fire-time.

**New table `webhook_deliveries`** — [api/app/models/webhook_delivery.py](api/app/models/webhook_delivery.py):

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `webhook_config_id` | UUID FK → webhook_configs.id | ON DELETE CASCADE |
| `event_type` | VARCHAR(50) | Denormalized for query convenience |
| `payload` | JSONB | Full body that was sent |
| `status` | VARCHAR(20) | `pending`, `success`, `failed`, `dead` (after max attempts) |
| `http_status_code` | SMALLINT | nullable |
| `error_message` | TEXT | nullable |
| `attempts` | SMALLINT | NOT NULL, default 0 |
| `next_retry_at` | TIMESTAMP | nullable; NULL when status is `success` or `dead` |
| `created_at` | TIMESTAMP | UTC |

Status semantics: `pending` (just enqueued, never tried), `success` (2xx received), `failed` (last attempt non-2xx but more retries remain), `dead` (3 attempts exhausted). The retry runner only picks up `failed` rows with `next_retry_at <= now`.

Index on `(status, next_retry_at)` for the retry runner's scan.

**Migration** — `api/alembic/versions/{hex}_add_webhook_configs_and_deliveries.py`. Single migration creates both tables.

### B.3 Delivery engine

**New service** — [api/app/services/webhook_service.py](api/app/services/webhook_service.py):

```
class WebhookService:
    def __init__(self, db: Session): ...

    def get_configs_for_org(self, organization_id: UUID) -> list[WebhookConfig]
    def get_config(self, config_id: UUID) -> WebhookConfig | None
    def upsert_config(self, organization_id: UUID, event_type: str, url: str, is_active: bool, generate_secret: bool) -> WebhookConfig
    def delete_config(self, config_id: UUID) -> None

    # Core dispatch
    def fire(self, organization_id: UUID, event_type: str, payload: dict) -> WebhookDelivery | None
        # Looks up active config for (org, event_type). If none, returns None (no-op).
        # Creates webhook_delivery row with status=pending.
        # Calls _deliver(); updates row status accordingly.
        # Always commits (failure path included) so the log row exists.

    def _deliver(self, delivery: WebhookDelivery, config: WebhookConfig) -> None
        # POST to config.webhook_url with httpx. Timeout 10s.
        # Headers: Content-Type: application/json, X-GPS-Event: <event_type>,
        #   X-GPS-Delivery-Id: <delivery.id>, optional X-GPS-Signature: <hmac>.
        # 2xx → status=success, http_status_code set, next_retry_at=NULL.
        # Non-2xx or network error → status=failed, attempts+=1, schedule retry.
        # If attempts == 3 after increment → status=dead, next_retry_at=NULL.

    def schedule_retry(self, delivery: WebhookDelivery) -> None
        # Backoff: attempt 1 fail → +60s, attempt 2 fail → +300s, attempt 3 fail → dead.

    def process_pending_retries(self, batch_size: int = 50) -> int
        # Called by the cron endpoint. SELECT FOR UPDATE SKIP LOCKED rows where
        # status='failed' AND next_retry_at <= now AND attempts < 3.
        # For each: load config, call _deliver(). Returns count processed.

    def test_delivery(self, config_id: UUID) -> dict
        # Builds a test payload (real shape but with firstName="Test", lastName="User",
        # plus root-level "test": true). Synchronously POSTs it. Returns
        # {"ok": bool, "status_code": int|null, "error": str|null}.
        # Does NOT write to webhook_deliveries (test pings shouldn't pollute the log).
```

**Why `httpx` over `requests`:** matches existing async patterns in the codebase and supports both sync and async modes. The service runs sync inside FastAPI request handlers using `httpx.Client(timeout=10.0)`.

**Signing** — when `config.secret` is set: `signature = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()`. Header: `X-GPS-Signature: sha256=<hex>`. Receivers verify by computing the same HMAC over the raw request body.

**Secret generation** — when caller passes `generate_secret=True`, service generates `secrets.token_urlsafe(32)` and returns it once (in the create/update response only). After that, `GET /webhooks/{id}` returns the secret masked (`••••...last4`) — admins can rotate by saving with `generate_secret=True` again.

### B.4 Payload builders

Two pure functions in [api/app/services/webhook_payloads.py](api/app/services/webhook_payloads.py):

```
def build_assessment_payload(assessment, result, user, organization) -> dict
def build_user_registered_payload(user, organization, registered_at) -> dict
```

The assessment payload matches Doug's OpenAPI spec verbatim (see addendum §3.3). For UUID compatibility, include `id` (UUID) and `legacyId` (integer, nullable; populated only if a migration mapping exists in the user record). MyImpact payload: same envelope, with `instrument: "myimpact"` and an `myImpactScores` block (`{character, calling, impact}`); finalize exact MyImpact field shape during Phase C wiring (PRD allows generic-now, refine-later).

The user-registration payload matches addendum §4.3.

### B.5 API endpoints

All under [api/app/routers/webhooks.py](api/app/routers/webhooks.py) (new), prefix `/api/admin/webhooks`, all guarded by `require_admin` from [dependencies/auth.py](api/app/dependencies/auth.py):

| Method | Path | Description |
|---|---|---|
| GET | `/api/admin/webhooks` | List all webhook configs for the current admin's org |
| POST | `/api/admin/webhooks` | Create a new config (one per event_type per org). Body: `{webhook_url, event_type, is_active, generate_secret?}`. Returns config + secret if generated. |
| GET | `/api/admin/webhooks/{id}` | Get one config (secret masked) |
| PUT | `/api/admin/webhooks/{id}` | Update url / is_active / regenerate secret |
| DELETE | `/api/admin/webhooks/{id}` | Delete |
| POST | `/api/admin/webhooks/{id}/test` | Synchronously fire a test payload, return `{ok, status_code, error}` |
| GET | `/api/admin/webhooks/{id}/deliveries` | Paginated delivery log. Query: `status`, `limit`, `offset`. Last 30d. |

Master admin read-only:
| GET | `/api/master/organizations/{id}/webhooks` | List webhook configs for any org. Read-only. |

Internal retry endpoint:
| POST | `/api/internal/webhooks/process-retries` | Triggered by Render cron. Auth: `X-Internal-Secret` header equal to `settings.INTERNAL_CRON_SECRET`. Returns `{processed: N}`. |

**Org-scoping safety:** every endpoint that takes `{id}` resolves the config and verifies `config.organization_id == current_admin_org_id` before any operation. Master endpoints bypass this with explicit `require_master`.

### B.6 Retry runner — Render cron job

Add a Render Cron Job (configured in `render.yaml` if it exists, or in Render dashboard if not) that runs every 1 minute:

```
curl -X POST -H "X-Internal-Secret: $INTERNAL_CRON_SECRET" \
  https://api.disciplesmade.com/api/internal/webhooks/process-retries
```

The endpoint:
1. Validates the secret header (constant-time compare).
2. Calls `WebhookService.process_pending_retries(batch_size=50)`.
3. Returns count.

Concurrency is handled by `SELECT FOR UPDATE SKIP LOCKED` on PostgreSQL — multiple cron firings or worker instances can't double-deliver the same row. SQLite (dev) doesn't support this but dev never runs the cron, so it's fine.

### B.7 Frontend

**New context** — [web/src/context/WebhookContext.tsx](web/src/context/WebhookContext.tsx). Mirrors the existing `AdminContext` pattern: `webhooks`, `loadWebhooks()`, `createWebhook()`, `updateWebhook()`, `deleteWebhook()`, `testWebhook(id)`, `fetchDeliveries(id)`. Provider wraps the admin section in [App.tsx](web/src/App.tsx).

**New component** — [web/src/components/CrmIntegrationPanel.tsx](web/src/components/CrmIntegrationPanel.tsx). Renders two collapsible sub-panels inside the AdminDashboard settings tab:
1. **"Assessment Results Webhook"** — bound to `event_type=assessment_completed`. URL field, active toggle, "Generate signing secret" checkbox, Save / Test / Remove buttons. Below: collapsible "Recent deliveries" table (date, event, status pill green/red, HTTP status). Failed rows expand to show `error_message`.
2. **"New Member Registration Webhook"** — same UI, bound to `event_type=user_registered`.

**Replace stub** — the "Manage Connections" stub button at [AdminDashboard.tsx](web/src/pages/AdminDashboard.tsx) is replaced by this panel inline in the settings tab.

**Test feedback** — uses the already-installed `sonner` toast library: `toast.success("Test delivery succeeded (HTTP 200)")` / `toast.error("Test failed: connection refused")`.

**Master view** — small read-only section in the church detail expand on [MasterDashboard.tsx](web/src/pages/MasterDashboard.tsx): "Assessment webhook: configured ✓ (last delivery: success, 2h ago)" / "Registration webhook: not configured". URL is masked (`https://hooks.zapier.com/.../••••XYZ`).

### B.8 Files touched
- `api/alembic/versions/{hex}_add_webhook_configs_and_deliveries.py` (new)
- `api/app/models/webhook_config.py` (new)
- `api/app/models/webhook_delivery.py` (new)
- `api/app/schemas/webhook.py` (new — request/response shapes)
- `api/app/services/webhook_service.py` (new)
- `api/app/services/webhook_payloads.py` (new)
- `api/app/routers/webhooks.py` (new)
- `api/app/routers/master.py` (add the read-only webhook endpoint)
- `api/app/main.py` (register the new router)
- `api/app/core/config.py` (add `INTERNAL_CRON_SECRET` setting)
- `render.yaml` or Render dashboard (add cron job)
- `web/src/context/WebhookContext.tsx` (new)
- `web/src/components/CrmIntegrationPanel.tsx` (new)
- `web/src/components/WebhookDeliveryTable.tsx` (new)
- `web/src/pages/AdminDashboard.tsx` (replace stub, mount panel)
- `web/src/pages/MasterDashboard.tsx` (read-only display in church expand)
- `web/src/App.tsx` (wrap admin routes in `<WebhookProvider>`)

---

## Phase C — Event Wiring

This phase plugs the new event types into the existing handlers. All side effects are wrapped in `try/except` and logged but **not allowed to fail the parent request** (matches existing pattern at [assessments.py:383-405](api/app/routers/assessments.py#L383-L405)).

### C.1 Assessment completion

**Location:** [api/app/routers/assessments.py:383-405](api/app/routers/assessments.py#L383) (GPS) and the parallel block ~line 355 (MyImpact).

**Add** — after the existing `notification_service.create_notification(...)` for the user, add:

```python
# Admin notifications — one per admin of the user's church
try:
    org = _get_user_org(db, current_user)  # existing helper
    if org:
        admins = _get_org_admins(db, org.id)  # existing query in _notify_org_admins
        for admin in admins:
            notification_service.create_notification(
                db,
                recipient_id=admin.id,
                type="assessment_completed",
                title="New Assessment Completed",
                message=f"{current_user.first_name} {current_user.last_name} completed their {'GPS' if instrument == 'gps' else 'MyImpact'} assessment",
                link=f"/admin?member={current_user.id}&assessment={assessment.id}",
                reference_type="assessment",
                reference_id=assessment.id,
            )
except Exception:
    logger.exception("Failed to create admin assessment notifications")

# Webhook delivery
try:
    if org:
        payload = build_assessment_payload(assessment, result, current_user, org)
        WebhookService(db).fire(org.id, "assessment_completed", payload)
except Exception:
    logger.exception("Failed to fire assessment_completed webhook")
```

**Note:** the existing `_notify_org_admins()` helper already sends emails to admins; reuse its admin-discovery query but extract the admin list into a small `_get_org_admins()` helper to avoid duplicating the SQL.

### C.2 New member joined

Three call sites, all create a `Membership` row that affiliates a user with an organization. After each successful commit:

1. **Self-registration with `organization_key`** — [api/app/services/auth_service.py:97](api/app/services/auth_service.py) `register_user()`. After commit, fire `member_joined` notification to admins + `user_registered` webhook.

2. **Pending request approval** — [api/app/routers/admin.py:881](api/app/routers/admin.py) `approve_pending()`. After commit, fire `member_joined` notification to admins + `user_registered` webhook.

3. **Invite acceptance** — find the accept-invite endpoint (likely `POST /auth/accept-invite` or similar; verify exact path in impl). After membership is committed, fire same two events.

Helper to add — [api/app/services/membership_events.py](api/app/services/membership_events.py) (new, small):
```python
def fire_member_joined_events(db, user, organization, registered_at):
    """Side effects to run after a user becomes affiliated with a church."""
    # 1. member_joined notification to all admins
    # 2. user_registered webhook
```
Each of the three call sites invokes this single helper inside a try/except. Avoids three near-identical inline blocks.

### C.3 Member requested join

**Location:** the church link request endpoint. From the integration map: pending memberships are created with `status="pending"` somewhere in [api/app/routers/admin.py](api/app/routers/admin.py) or [api/app/services/auth_service.py](api/app/services/auth_service.py). Verify exact location at impl-time (search for `status = "pending"` and `Membership(`).

After the pending row is committed, fire `member_requested` notification to all church admins. **No webhook fires** here — the spec only emits `user_registered` after approval, not request.

### C.4 Church created

Two call sites:

1. **Master-initiated** — [api/app/routers/master.py:306-410](api/app/routers/master.py#L306) `create_church()`. After the existing `db.commit()` (line ~384), fire `church_created` notification to all master admins (excluding the actor). The existing audit log already covers the action; this just adds the in-app surface.

2. **Self-signup as church admin** — [api/app/services/auth_service.py:166](api/app/services/auth_service.py) `register_church_admin()`. After commit, fire `church_created` notification to all master admins.

Helper — small inline query: `db.query(User).join(Membership).join(Role).filter(Role.name == 'master', User.id != actor_id).all()`, then loop and create one notification per master.

### C.5 Files touched
- `api/app/routers/assessments.py` (add admin notifications + webhook fire)
- `api/app/services/auth_service.py` (add events on register_user with org, register_church_admin)
- `api/app/routers/admin.py` (add events on approve_pending, on pending creation, accept_invite)
- `api/app/routers/master.py` (add church_created notification)
- `api/app/services/membership_events.py` (new helper)

---

## Phase D — Spanish Language Support

### D.1 Why
Question/result-level Spanish exists in the schema and is partially rendered. The gap is **UI chrome** (dashboard greeting, sidebar, table headers, primary buttons) plus a missing `description_es` on `gifts_passion`. The current inline `ES_STRINGS` in [AssessmentWizard.tsx](web/src/pages/AssessmentWizard.tsx) and `ES_RESULTS` in [AssessmentResults.tsx](web/src/pages/AssessmentResults.tsx) are tech debt — two separate string tables, neither reusable. Phase D consolidates them into one source of truth before adding the new translations.

### D.2 Backend changes

**Migration 1 — `description_es` on gifts_passion** — `api/alembic/versions/{hex}_add_gifts_passion_description_es.py`:
- `ALTER TABLE gifts_passions ADD COLUMN description_es TEXT NULL`.
- Migration ships the column unpopulated. Follow-up data migration (`{hex}_populate_gifts_passion_description_es.py`) lands once the 24 strings are sourced (see "Remaining content gap" in §0). Frontend falls back to English `description` when `description_es` is NULL — no UI breakage in the interim.

**Model update** — [api/app/models/gifts_passion.py](api/app/models/gifts_passion.py): add `description_es = Column(Text, nullable=True)`.

**Schema update** — [api/app/schemas/assessment.py](api/app/schemas/assessment.py): the gift/passion response shape includes both `description` and `description_es`. Frontend selects per locale.

**Locale validation** — [api/app/schemas/user.py:48](api/app/schemas/user.py#L48):
```python
from typing import Literal
class UserUpdate(BaseModel):
    ...
    locale: Optional[Literal['en', 'es']] = None
```
This rejects garbage at the API boundary. Existing rows with non-{en,es} locale (shouldn't be any, but defensively) — add a one-line cleanup in the same migration: `UPDATE users SET locale='en' WHERE locale NOT IN ('en','es')`.

**Migration 2 — MyImpact Spanish question text** — `api/alembic/versions/{hex}_populate_myimpact_spanish.py`:
- The `questions.question_es` field already exists on the shared `questions` table (filtered by `instrument_type='myimpact'`).
- **Source:** [es/SPANISH - MYIMPACT ASSESSMENT.md](es/SPANISH%20-%20MYIMPACT%20ASSESSMENT.md) — already in repo. Map document IDs (C1–C9, CL1–CL8) to `questions` rows by matching English text or by sequence within `instrument_type='myimpact'` ordered by `order`. The migration uses an explicit dict mapping (e.g., `{"C1": "Soy una persona amorosa.", ...}`) — no Typeform fetch needed.
- Also populate the section prompts ("Comencemos preguntando acerca de su Carácter (Fruto del Espíritu)…", etc.) into whichever table holds intro text (verify at impl-time — likely `questions` rows with a `section` field, or a separate `instrument_section` table).

### D.3 Frontend — translation infrastructure

**Translation seed source.** Don't hand-translate the UI strings — port them from the legacy Laravel files in `/es/`. A one-shot script ([scripts/build_translations_from_legacy.py](scripts/build_translations_from_legacy.py), run once, output checked in) parses [es/dashboard.php](es/dashboard.php), [es/forms.php](es/forms.php), [es/auth.php](es/auth.php), [es/toasts.php](es/toasts.php), and the relevant subset of [es/assessment.php](es/assessment.php) into a single namespaced JSON, then the developer maps each entry into the new `translations.ts` keys. Concretely:
- `dashboard.php` → `dashboard.*`, `nav.*`, `webhook.*` (the "webhook-management", "destination-url", etc. strings — though admin-only pages stay English per addendum, these may seed future use).
- `forms.php` → `forms.*` (church-name, city, state, save, submit, cancel, last-assessment, gifts/passion table headers).
- `auth.php` → `auth.*` (used only on already-Spanish auth pages if/when added; addendum keeps auth English).
- `toasts.php` → `toasts.*` (greetings: good-morning, good-afternoon, good-evening; success messages).
- `assessment.php` → `assessment.*`, `results.*`, `people.*`, `causes.*`, `abilities.*` (the multi-select option labels are the bulk).

**New file** — [web/src/i18n/translations.ts](web/src/i18n/translations.ts):

```typescript
type Locale = 'en' | 'es';
type TranslationKey = string; // dot-namespaced

const translations: Record<Locale, Record<TranslationKey, string>> = {
  en: {
    'dashboard.greeting': 'Welcome to your dashboard',
    'dashboard.takeGps': 'Take a New GPS Assessment',
    'dashboard.takeMyImpact': 'Take a New MyImpact Assessment',
    'dashboard.viewResults': 'View Results',
    'dashboard.continue': 'Continue',
    'dashboard.exportData': 'Export My Data',
    'dashboard.tableHeaders.started': 'Started',
    'dashboard.tableHeaders.completed': 'Completed',
    'dashboard.tableHeaders.gifts': 'Gifts',
    'dashboard.tableHeaders.passion': 'Passion',
    'nav.gpsAssessments': 'GPS Assessments',
    'nav.myimpactAssessments': 'MyImpact Assessments',
    'nav.account': 'Account',
    'nav.updatePassword': 'Update Password',
    'nav.logout': 'Logout',
    'assessment.next': 'Next',
    'assessment.previous': 'Previous',
    'assessment.submit': 'Submit',
    'assessment.progress': 'Progress',
    'results.spiritualGifts': 'Your Spiritual Gifts',
    'results.passions': 'Passions',
    'results.selections': 'Your Selections',
    'results.story': 'Story',
    'results.downloadPdf': 'Download PDF',
    'results.print': 'Print',
    'language.toggle.toEs': '¿En español?',
    'language.toggle.toEn': 'In English?',
    // ... full key set, ~50 entries
  },
  es: {
    'dashboard.greeting': 'Bienvenido a su tablero',
    'dashboard.takeGps': 'Tomar una Nueva Evaluación GPS',
    // ... mirrored
  },
};

export default translations;
export type { Locale, TranslationKey };
```

**New hook** — [web/src/hooks/useTranslation.ts](web/src/hooks/useTranslation.ts):

```typescript
import { useAuth } from '../context/AuthContext';
import translations, { Locale, TranslationKey } from '../i18n/translations';

export function useTranslation() {
  const { locale } = useAuth();
  const lang: Locale = locale === 'es' ? 'es' : 'en';

  const t = (key: TranslationKey, fallback?: string): string => {
    return translations[lang][key] ?? translations.en[key] ?? fallback ?? key;
  };

  return { t, locale: lang };
}
```

Why this minimal hook over `react-i18next`: <100 strings, no plurals, no formatting needs. Adding a library would be ~30KB of bundle for nothing. The hook fits in 15 lines; missing-key fallback to English keeps half-translated states usable.

### D.4 Frontend — apply translations

**Refactor inline objects:**
- [web/src/pages/AssessmentWizard.tsx](web/src/pages/AssessmentWizard.tsx) — delete `ES_STRINGS` constant; replace `{isEs ? ES_STRINGS.next : "Next"}` with `t('assessment.next')`.
- [web/src/pages/AssessmentResults.tsx](web/src/pages/AssessmentResults.tsx) — delete `ES_RESULTS` constant; replace lookups with `t('results.*')`.

**New translations:**
- [web/src/pages/Dashboard.tsx](web/src/pages/Dashboard.tsx) — replace hardcoded greeting, table headers, button labels with `t()` calls.
- The hamburger menu inside Dashboard.tsx (lines 188-242) — wrap each menu label in `t('nav.*')`.
- [web/src/components/Footer.tsx](web/src/components/Footer.tsx) — toggle text already locale-aware; verify it uses `t('language.toggle.toEs')` / `toEn` for consistency.

**Display Spanish gift/passion descriptions** — in the results component, switch from `gift.description` to `locale === 'es' && gift.description_es ? gift.description_es : gift.description`. Same fallback pattern already used for `question_es`.

### D.5 Files touched
- `api/alembic/versions/{hex}_add_gifts_passion_description_es.py` (new)
- `api/alembic/versions/{hex}_populate_myimpact_spanish.py` (new, blocked on Brian's content)
- `api/app/models/gifts_passion.py` (add column)
- `api/app/schemas/assessment.py` (return description_es)
- `api/app/schemas/user.py` (Literal validation)
- `web/src/i18n/translations.ts` (new)
- `web/src/hooks/useTranslation.ts` (new)
- `web/src/pages/AssessmentWizard.tsx` (delete ES_STRINGS, use hook)
- `web/src/pages/AssessmentResults.tsx` (delete ES_RESULTS, use hook, render description_es)
- `web/src/pages/Dashboard.tsx` (apply translations)
- `web/src/components/Footer.tsx` (use hook)

---

## Phase E — Included Items

### E.1 Help button
- New component — [web/src/components/HelpLink.tsx](web/src/components/HelpLink.tsx): single anchor with `href="mailto:info@disciplesmade.com?subject=GPS%20Platform%20Help%20Request"`. Styled to match existing nav link patterns.
- Mount in [web/src/components/Navbar.tsx](web/src/components/Navbar.tsx) (visible to all roles, including unauthenticated). Mobile placement in the hamburger menu.
- No backend.

### E.2 Stripe Customer Portal
**Already built** at [api/app/routers/billing.py:543-571](api/app/routers/billing.py#L543) (`POST /billing/portal`) and [api/app/services/stripe_service.py](api/app/services/stripe_service.py) `create_billing_portal_session()`. Verification only:
- Confirm a "Manage Payment" / "Update Payment Method" button on [web/src/pages/AdminBilling.tsx](web/src/pages/AdminBilling.tsx) calls the endpoint and redirects.
- If button is missing, add it (one button + one click handler).

### E.3 Master admin: create church
**Already built** at [api/app/routers/master.py:306-410](api/app/routers/master.py#L306) (`POST /master/churches`). Verification:
- Confirm the "Add Church" button on [web/src/pages/MasterDashboard.tsx](web/src/pages/MasterDashboard.tsx) opens the modal and posts to the endpoint.
- Confirm audit log fires (already does, lines 370-382).
- The Phase C `church_created` notification piggy-backs on this flow without additional work here.

---

## File Inventory (Net New / Modified)

### Backend new
- 5 Alembic migrations (notifications reconcile, webhook tables, gifts_passions.description_es, MyImpact Spanish backfill, gifts_passions description_es backfill — the last is small and follows once content is sourced)
- `app/models/webhook_config.py`, `app/models/webhook_delivery.py`
- `app/schemas/webhook.py`
- `app/services/webhook_service.py`, `app/services/webhook_payloads.py`, `app/services/membership_events.py`
- `app/routers/webhooks.py`

### Backend modified
- `app/models/notification.py`, `app/models/gifts_passion.py`
- `app/schemas/notification.py`, `app/schemas/user.py`, `app/schemas/assessment.py`
- `app/services/notification_service.py`, `app/services/auth_service.py`
- `app/routers/notifications.py`, `app/routers/assessments.py`, `app/routers/admin.py`, `app/routers/master.py`
- `app/main.py`, `app/core/config.py`
- `render.yaml` (or Render dashboard cron entry)

### Frontend new
- `src/context/WebhookContext.tsx`
- `src/components/CrmIntegrationPanel.tsx`, `src/components/WebhookDeliveryTable.tsx`, `src/components/HelpLink.tsx`
- `src/i18n/translations.ts`
- `src/hooks/useTranslation.ts`

### Frontend modified
- `src/App.tsx`
- `src/context/NotificationContext.tsx`
- `src/components/NotificationBell.tsx`, `src/components/Navbar.tsx`, `src/components/Footer.tsx`
- `src/pages/AdminDashboard.tsx`, `src/pages/MasterDashboard.tsx`, `src/pages/Dashboard.tsx`, `src/pages/AssessmentWizard.tsx`, `src/pages/AssessmentResults.tsx`, `src/pages/AdminBilling.tsx` (verify only)

---

## Verification & Test Plan

### Migrations
- Run `alembic upgrade head` against a copy of staging DB. Verify:
  - All four notifications drift columns/types match (`is_read` Boolean, `reference_type` exists, `reference_id` exists, indexes preserved).
  - `webhook_configs` and `webhook_deliveries` tables exist with FKs and indexes.
  - `gifts_passions.description_es` column exists.
- `alembic downgrade -1` round-trip on each migration to confirm reversibility.

### Backend unit tests (extend [api/tests/](api/tests/))
- `tests/test_notifications.py` — exercise the 4 endpoints, the new event types, and the `is_read` Boolean read/write path.
- `tests/test_webhook_service.py` — mock `httpx.Client.post`. Verify: success path writes status=success; failure schedules retry with correct backoff; third failure marks dead; signing header present iff secret set.
- `tests/test_webhook_endpoints.py` — full round-trip: admin creates config → fires test → reads delivery log. Org-scoping: admin A cannot read admin B's config (403).
- `tests/test_assessment_completion_events.py` — submit assessment, assert: admin notification row created, webhook_deliveries row created, parent submission still 200 even when webhook URL returns 500.
- `tests/test_locale_validation.py` — `PUT /auth/profile` with `locale="fr"` returns 422; `locale="es"` returns 200.

### Manual / E2E
1. **Notifications:** as admin, complete an assessment as a member → bell badge increments within 60s → drop down shows "{member} completed their GPS assessment" with deep link → click marks read → click "Mark all as read" zeros the count.
2. **Webhook (assessment):** in admin settings, configure webhook to `https://webhook.site/{uuid}`, save → click Test → webhook.site shows test payload with `"test": true` → submit a real assessment as member → real payload appears at webhook.site within ~10s → delivery log shows status=success, HTTP 200.
3. **Webhook (registration):** configure registration webhook → register a new user with this church's `organization_key` → user_registered payload arrives at the configured URL.
4. **Webhook retry:** point webhook at a URL that returns 500 → submit assessment → delivery log shows status=failed, attempts=1, next_retry_at=+60s → wait, observe retry → after 3 failures, status=dead. Verify cron is hitting `/internal/webhooks/process-retries` (Render logs).
5. **Spanish:** toggle locale via Footer link → Dashboard greeting changes to "Bienvenido a su tablero" → table headers Spanish → Assessment Wizard renders `question_es` → Results page renders `description_es` (once seeded). Reload page → still Spanish (persisted via `PUT /auth/profile`). Try `PUT /auth/profile` with `locale="zh"` via curl → 422.
6. **Help button:** click in nav → opens email client with pre-filled to/subject.
7. **Stripe portal:** as primary admin, click "Manage Payment" → redirects to Stripe → can update card → returns to dashboard.
8. **Master add church:** as master admin, click "Add Church" → fill modal → submit → church appears in list, audit log shows entry, master admins receive `church_created` notification.

### Security checks
- Webhook URL field validates `https://` only (or `http://localhost` in dev). Reject `file://`, `gopher://`, internal IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, 127.0.0.0/8) to prevent SSRF — apply in `WebhookService.upsert_config()`.
- Internal cron endpoint uses constant-time secret comparison (`hmac.compare_digest`).
- Test endpoint runs with the same SSRF guard (don't let admins probe internal IPs by configuring + testing).
- HMAC signing uses raw bytes of the JSON body, not re-serialized.

---

## Out of Scope (Per Addendum + This Plan)

- Email notifications for the new in-app notification events (existing assessment-result emails stay as-is).
- Notification preferences UI.
- Push notifications.
- Multiple webhook URLs per church per event type.
- Webhook events beyond `assessment_completed` and `user_registered`.
- Master admin webhook editing (read-only only).
- Full i18n framework, RTL support, additional languages, browser-language auto-detect.
- Translation of admin dashboards, emails, PDFs, CSV exports.
- Zapier OAuth (manual URL paste, same as legacy).
- 90-day notification cleanup job, 30-day delivery log cleanup job (deferred).

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Notification migration on prod data | Two-step column add/copy/drop. Test on staging copy first. Migration is reversible (downgrade reverses the column dance). |
| Webhook delivery blocking assessment submission | All `WebhookService.fire()` calls are wrapped in try/except in the request handler — same pattern as existing email sends at [assessments.py:386-393](api/app/routers/assessments.py#L386). Delivery uses 10s timeout. |
| Cron double-firing same retry | `SELECT FOR UPDATE SKIP LOCKED` on PostgreSQL. Atomic. |
| SSRF via webhook URL | Reject internal/loopback IPs and non-http schemes in `upsert_config` and `test_delivery`. |
| Per-gift `description_es` content not in repo | Phase D ships the column + frontend fallback. English fallback shows on results page until the 24 strings are sourced from legacy DB or Brian. No blocker for shipping the rest. |
| Translation key drift between English and Spanish | TypeScript will fail to compile if a Spanish key is missing (the `translations` object is typed `Record<Locale, Record<TranslationKey, string>>`). Adding a key forces both languages to be supplied. |
| HMAC secret leak via API response | Secret returned **once** at creation/regeneration; subsequent reads return masked value. Mirrors how Stripe / GitHub handle webhook secrets. |

---

## Implementation Log

This section is appended-to as each phase is built. Captures gotchas, deviations from the plan, and anything future-me would want to know.

### Phase A — Notifications Reconciliation
*Status: done — 2026-04-30*

**What shipped**
- New migration `c6a7b8d9e0f1_reconcile_notifications.py` (down_revision `b5d1f0e2a3c4`).
  - `is_read` migrated from `VARCHAR(1)` Y/N → `BOOLEAN` (two-step copy on Postgres).
  - Added `reference_type VARCHAR(50)` and `reference_id UUID` (kept `link` — they're orthogonal).
  - Renamed existing `gps_result` / `myimpact_result` rows → `assessment_self_completed` to disambiguate from the admin-facing `assessment_completed` event.
- Updated [Notification model](api/app/models/notification.py), [notification_service](api/app/services/notification_service.py), [router](api/app/routers/notifications.py) (`/read-all` → `/mark-all-read`), and [schemas](api/app/schemas/notification.py) (`is_read: bool`, optional `reference_type`/`reference_id`).
- Updated assessment-completion notification calls in [assessments.py](api/app/routers/assessments.py) at lines ~84 (admin), ~358 (MyImpact self), ~398 (GPS self) — all now pass `reference_type="assessment"` and `reference_id=assessment.id`.
- Frontend: [NotificationContext](web/src/context/NotificationContext.tsx) poll 30s → 60s, `is_read: string` → `is_read: boolean`, endpoint renamed. [NotificationBell](web/src/components/NotificationBell.tsx) now uses `!n.is_read`, has icons for `assessment_self_completed`, `member_joined`, `member_requested`, `church_created`, and falls back from `link` to `routeFromReference(reference_type, reference_id)`.

**Migration applied to Render Postgres**
- Render head moved from `a1b2c3d4e5f6` → `c6a7b8d9e0f1` (skipping the previously-undeployed `b5d1f0e2a3c4_add_webhook_events` along the way).
- Schema verified: `is_read boolean NOT NULL`, `reference_type varchar`, `reference_id uuid`, type-rename took effect on existing rows.

**Gotchas / learnings**

1. **Alembic CLI hangs in this dev environment.** `python -m alembic current` and `python -m alembic upgrade head` both hung indefinitely (zero output, even with `-u`). A bare `import alembic` from the venv hung too — but `import psycopg2` and direct DB queries worked fine. Suspected interaction between Windows + Claude Code's Bash background-task wrapper + alembic; never fully diagnosed. **Workaround:** [scripts/apply_migrations_direct.py](api/scripts/apply_migrations_direct.py) — a one-off psycopg2 script that runs the migration SQL directly and updates `alembic_version` manually. Idempotent (checks current rev). For future migrations, try alembic CLI first; fall back to the direct script (and add a new step for the new revision) if it hangs again.

2. **PowerShell's `Tee-Object` writes UTF-16 with BOM.** The first attempt to capture stdout via `| Tee-Object -FilePath ...` produced files that `cat` rendered as `��s t a r t u p` (bytes `fffe 7300 7400...`) — readable but confusing, and `grep` patterns won't match cleanly. Stick to bash `>` redirect or pipe through `Out-File -Encoding utf8` if PowerShell is needed.

3. **The Render DB was two migrations behind.** Local repo head was `c6a7b8d9e0f1`, but Render was at `a1b2c3d4e5f6` — the previously-committed `b5d1f0e2a3c4_add_webhook_events` (Stripe idempotency table) had never been deployed. The direct-apply script handled both in sequence.

4. **`gps_result` / `myimpact_result` collapse to one type.** PRD specs `assessment_completed` for the admin-facing event. The pre-existing per-instrument `gps_result` / `myimpact_result` types were the *user-facing* "your results are ready" notifications. Renamed both to a single `assessment_self_completed` rather than keeping the per-instrument distinction — the `link` field already encodes which page to navigate to, so the type granularity was redundant. Downgrade collapses both back to `gps_result` since we have no marker to recover the original split.

5. **Existing `_notify_org_admins()` already creates the admin-facing `assessment_completed` notification.** I assumed Phase C would need to add this; it doesn't. Phase C will only need to wire **webhook delivery** at that callsite (the notification side is already there). Updated my mental model — re-check Phase C plan when starting it.

6. **`membership_approved` and `membership_declined` types are not in the addendum's event list** but already exist and are useful. Decision: keep them. The addendum's event list is *additive*, not exclusive.

### Phase B — Webhook Infrastructure
*Status: done — 2026-05-01*

**What shipped**

Backend:
- Two new models: [WebhookConfig](api/app/models/webhook_config.py) (one row per (org, event_type), unique constraint enforced) and [WebhookDelivery](api/app/models/webhook_delivery.py) (append-only attempt log).
- Migration `d7e8f9a0b1c2_add_webhook_configs_and_deliveries.py` applied to Render.
- [WebhookService](api/app/services/webhook_service.py): config CRUD, sync delivery with HMAC-SHA256 signing, exponential backoff (60s → 300s → dead at 3 attempts), `process_pending_retries()` using `SELECT FOR UPDATE SKIP LOCKED` so concurrent cron firings can't double-deliver. SSRF guard (`assert_url_safe`) resolves the URL to IPs and rejects loopback / private / link-local / metadata-service ranges, called both at config save AND at every delivery attempt (DNS may have changed). 10s timeout via httpx.
- [webhook_payloads.py](api/app/services/webhook_payloads.py): pure functions `build_assessment_payload` (matches Doug's legacy OpenAPI shape verbatim, with `instrument: "gps"`), `build_user_registered_payload` (Zapier shape), `build_test_assessment_payload` (real shape, fake data, root-level `"test": true`).
- [webhooks.py router](api/app/routers/webhooks.py) — three sub-routers:
  - `/admin/webhooks` — full CRUD + `/test` + `/deliveries` (last 30 days, paginated). Org-scoping enforced via `_ensure_admin_owns()` which 404s on cross-org access (no existence leak).
  - `/master/organizations/{id}/webhooks` — read-only master view. URLs masked, secrets never exposed (only `has_secret: bool`).
  - `/internal/webhooks/process-retries` — cron-driven retry processor. Auth via `X-Internal-Secret` header; constant-time compare via `hmac.compare_digest`. Returns 404 (not 401) on bad secret to keep the endpoint invisible to scanners.
- [config.py](api/app/core/config.py): added `INTERNAL_CRON_SECRET: Optional[str] = None`.
- [main.py](api/app/main.py): mounted all three sub-routers.
- [requirements.txt](api/requirements.txt): pinned `httpx==0.28.1` (was a transitive dep, now explicit).
- [render.yaml](render.yaml): added a `type: cron` service (`gps-webhook-retries`) that runs every minute, hits the internal endpoint with the shared secret. Both API and cron need `INTERNAL_CRON_SECRET` set in the Render UI.

Frontend:
- [WebhookContext](web/src/context/WebhookContext.tsx) — typed `WebhookConfig` / `WebhookDelivery` / `WebhookEventType`, hook with `loadWebhooks`, `createWebhook`, `updateWebhook`, `deleteWebhook`, `testWebhook`, `fetchDeliveries`. Mounted around `/admin` route in [App.tsx](web/src/App.tsx).
- [CrmIntegrationPanel](web/src/components/CrmIntegrationPanel.tsx) — two collapsible sections (Assessment Results, New Member Registration), URL field + active toggle + "generate signing secret" + Save / Test / Remove buttons. Plaintext secret shown once with prominent banner (mirrors Stripe / GitHub secret-handling pattern). Toast feedback via the already-installed `sonner`.
- [WebhookDeliveryTable](web/src/components/WebhookDeliveryTable.tsx) — collapsible 30-day delivery log; failed/dead rows expand to show `error_message`.
- Replaced the "Manage Connections" stub at [AdminDashboard.tsx:1330](web/src/pages/AdminDashboard.tsx#L1330) with `<CrmIntegrationPanel readOnly={isReadOnly} />`.
- [MasterWebhookSummary](web/src/components/MasterWebhookSummary.tsx) — read-only inline summary mounted in the expanded church row of [MasterDashboard](web/src/pages/MasterDashboard.tsx). Always renders both event-type slots (configured / not configured) so missing webhooks are visually obvious.

**Migration applied to Render**
- Head moved `c6a7b8d9e0f1` → `d7e8f9a0b1c2`.
- Verified: `webhook_configs` (8 cols + `uq_webhook_configs_org_event` + `ix_webhook_configs_org_active`), `webhook_deliveries` (10 cols + `ix_webhook_deliveries_status_next_retry` + `ix_webhook_deliveries_config_created`).

**TypeScript clean** — `npx tsc --noEmit` returns exit 0 across the web project after all changes.

**Setup required before this ships (operator action):**
1. Set `INTERNAL_CRON_SECRET` env var on **both** services in Render UI (the API and the new cron job). Generated value for this branch: `VQaEtvBTTa9lz6CS8r2bWHX0SB28RbeWk-ohSaOnqO8` — replace if you'd rather rotate. The cron job's `curl` and the API's auth check must use the same value.
2. Confirm the cron-job's `API_BASE_URL` env var matches the API service URL (currently `https://gps-api-4q4m.onrender.com` per the existing `VITE_API_URL` value).
3. After Render picks up the new `render.yaml`, the cron job will be created automatically.

**Gotchas / learnings**

1. **Migration runner needed a `>=` skip check, not `==`.** [scripts/apply_migrations_direct.py](api/scripts/apply_migrations_direct.py) had `if head == to_rev: skip` from Phase A. When I added the Phase B step on top, `run_step("a1b2c3d4e5f6", "b5d1f0e2a3c4", ...)` raised `Expected head a1b2c3d4e5f6, found c6a7b8d9e0f1` because we were already past it. Fixed with an explicit `REV_ORDER` list and `head_idx >= target_idx` check. Add new revs to `REV_ORDER` before each phase migration.

2. **`MyImpactResult.user` relationship requires `User.myimpact_results` back-populates.** Verified [user.py:36](api/app/models/user.py#L36) already has `myimpact_results = relationship("MyImpactResult", back_populates="user")`. The webhook payload builder can call `myimpact_result.get_character_breakdown()` etc. directly.

3. **The 404-on-bad-secret pattern for the internal endpoint** is intentional. Returning 401 reveals the endpoint exists; 404 doesn't. The same approach is recommended for any "secret URL" endpoint.

4. **`SELECT FOR UPDATE SKIP LOCKED` is Postgres-only.** SQLite (used in dev sometimes) silently ignores `FOR UPDATE`, so the dev story for retries is "they happen, just without the no-double-delivery guarantee." The cron job is never wired to dev anyway, so this is fine — just don't try to test the retry runner against SQLite.

5. **httpx was a transitive dep.** It's installed via FastAPI's TestClient, so the import worked without changes. But pinning it explicitly in [requirements.txt](api/requirements.txt) prevents a future FastAPI upgrade from accidentally dropping it. Lock to `0.28.1` to match what's already on disk.

6. **Test connection deliberately doesn't write to `webhook_deliveries`.** Test pings would otherwise pollute the production delivery log every time an admin checks their config. Documented in `WebhookService.test_delivery()`.

7. **The plaintext signing secret returns once and only once.** Mirrors the Stripe / GitHub model. After creation, GETs return `secret_masked` (`••••<last4>`). Admins rotate by ticking "Regenerate signing secret" on save. The frontend banner explicitly tells them to copy it now.

8. **Render `type: cron` services do not get autoscale.** They run a single curl command on schedule. Our cron is just `curl -fsS -X POST -H "X-Internal-Secret: ..." "$API_BASE_URL/internal/webhooks/process-retries"` — nothing fancy needed. The Postgres `SKIP LOCKED` guard means even if Render fires it twice (or we add more workers later), no row gets double-delivered.

9. **The `_get_active_membership` ordering bug from `dependencies/auth.py`.** Already fixed in main, but worth noting when org-scoping admin endpoints: master admins who once had a different church membership had non-deterministic pass/fail behavior depending on insertion order. The new code uses a direct query in `_has_master_membership`. The webhook router uses `get_admin_organization` from [admin.py:54](api/app/routers/admin.py#L54), which does its own dedicated query — safe.

### Phase C — Event Wiring
*Status: done — 2026-05-01*

**What shipped**

New helper [api/app/services/membership_events.py](api/app/services/membership_events.py) — three pure functions, all wrapped by callers in try/except so a notification or webhook hiccup never fails the parent request:
- `fire_member_joined_events(db, user, organization, registered_at)` — `member_joined` notification to every admin of the church + `user_registered` webhook (no-op if no config).
- `fire_member_requested_event(db, user, organization)` — `member_requested` notification to admins. Deliberately no webhook here; addendum spec only fires `user_registered` after approval.
- `fire_church_created_event(db, organization, actor_user_id)` — `church_created` notification to all master admins (excluding the actor).

Assessment completion ([assessments.py](api/app/routers/assessments.py)):
- New helper `_fire_assessment_webhook(db, current_user, assessment, result)` — pre-fetches all referenced GiftsPassion rows in a single `IN (...)` query, builds story-question pairs from `_STORY_PROMPTS` (a static map of field-name → English prompt), calls `WebhookService.fire(org_id, "assessment_completed", payload)`. Called after both GPS and MyImpact scoring branches commit.
- The pre-existing `_notify_org_admins()` already fires the admin `assessment_completed` notification — confirmed during Phase A. Phase C only added the webhook-delivery side.

Membership lifecycle wiring (4 callsites total):

1. **Self-registration with `organization_key`** — [auth_service.py:97](api/app/services/auth_service.py#L97). `register_user()` now tracks `joined_org` and calls `fire_member_joined_events` after the membership commit when the user joins an existing church.

2. **Admin approval of pending request** — [admin.py:889](api/app/routers/admin.py#L889). `approve_pending()` calls `fire_member_joined_events` after updating `membership.status = "active"` and committing. The existing `membership_approved` user-facing notification stays as-is.

3. **Pending request creation** — [dashboard.py:635](api/app/routers/dashboard.py#L635). `request_church_link()` calls `fire_member_requested_event` after creating the pending membership row. This is the new in-app notification path; admins see "John Smith requested to join" in their bell.

4. **Invite-accept flow** — *N/A in current codebase*. The repo has an `InvitationAccept` schema but no router endpoint that uses it. Invited users go through `/register` with `organization_key` from the invite link, which already routes through `register_user()` (callsite #1). When/if a dedicated accept-invite endpoint ships, just call `fire_member_joined_events` after the membership commit.

Church creation wiring (3 callsites):
- **Master admin creates church** — [master.py:391](api/app/routers/master.py) `create_church()` after the audit-log commit.
- **Self-signup as new church admin** — [auth_service.py:181](api/app/services/auth_service.py) `register_church_admin()` after the org+membership commit.
- **Upgrade existing user to admin (creates new org)** — [auth_service.py:301](api/app/services/auth_service.py) `upgrade_to_church_admin()` after the new-org commit. (Originally not in the plan — caught while reading the auth_service code; the helper is the same.)

**Smoke test**
- All imports clean. `from app.main import app` succeeds with the full new event graph loaded.
- `build_user_registered_payload(...)` returns the addendum-spec'd shape — `event`, `user`, `church`, `registeredAt` keys; `user.firstName` / `church.key` populated correctly.

**Gotchas / learnings**

1. **The User model's phone column is `phone_number`, not `phone`.** [webhook_payloads.py](api/app/services/webhook_payloads.py)'s `build_user_registered_payload` originally read `getattr(user, "phone", None)` and would have always returned None. Fixed to read `phone_number` first, fall back to `phone` (the addendum's `Zapier Payload` example uses the `phone` key, which is what the receiving system sees — only the source attribute differs). Not a bug we'd have caught without exercising the flow; worth a real end-to-end test before shipping.

2. **No accept-invite endpoint exists in the rebuild.** [schemas/invitation.py:48](api/app/schemas/invitation.py#L48) defines `InvitationAccept` but no router consumes it. Invited users register via `/register?key=<sign_up_key>` which becomes `organization_key` in `register_user()` — same path as a direct member self-registration. The Invitation row's `status` doesn't get marked `accepted` automatically; that's pre-existing behavior unrelated to this work, but worth flagging for the maintainer (out of Phase C scope).

3. **`upgrade_to_church_admin` is a third church-creation path** that wasn't in the original plan. The plan listed two (master-admin and self-signup); reading the code surfaced the third (existing user creating their own church). All three now fire `fire_church_created_event`. Catch: the original plan implied the helper would be small but the actual fan-out is 3 callsites — easy to miss one. The helper-driven approach was right; the alternative (inline notification creation in each branch) would have been three near-identical 12-line blocks.

4. **Story prompts are hardcoded in [_STORY_PROMPTS](api/app/routers/assessments.py).** The legacy GPS Laravel app didn't expose these as structured data; the rebuild stores the answers in named columns (`story_gift_answer`, `story_passion_answer`, etc.) but never the prompts. I added a small static map mapping field-name → English prompt for the webhook payload. Generic wording — Brian may have exact prompt text the integrators expect; if so, update the dict. No Spanish (`questionEs: None`) for now — Phase D will handle Spanish for assessment-question text but story prompts are out of that scope unless we extend.

5. **`approve_pending` has TWO notifications now: one to user (`membership_approved`, pre-existing), one to admins via `member_joined`.** Both are useful — the user gets "Welcome to X" in their bell, the admins get "John Smith joined". They don't conflict. The webhook only fires once.

6. **Independent users (no `organization_key`) still get registered, but no event fires.** Confirmed in `register_user()` — `joined_org` stays None, helper isn't called. PRD §4.6 says "If the user registers as independent (no church), no webhook fires." Confirmed correct behavior.

7. **`fire_church_created_event` excludes the actor.** Master admin Alice creating a church doesn't need a notification telling herself she just did it. Implemented by passing `actor_user_id=current_user.id` and filtering with `User.id != actor_user_id` in the master query. For self-signup (`register_church_admin`), the actor is the new admin themselves who isn't a master, so the filter is a no-op — but passing the ID anyway is defensive against role changes.

### Phase D — Spanish Language Support
*Status: done — 2026-05-01*

**What shipped**

Backend:
- Migration `e8f9a0b1c2d3_add_gifts_passion_description_es.py` — `gifts_passions.description_es` column, nullable. Frontend falls back to English `description` when null.
- Migration `f9a0b1c2d3e4_populate_myimpact_spanish.py` — backfills `questions.question_es` for all 17 MyImpact questions (9 Character + 8 Calling). Source is [es/SPANISH - MYIMPACT ASSESSMENT.md](es/SPANISH%20-%20MYIMPACT%20ASSESSMENT.md) (Chelsie Carroll, 2026-04-22). Idempotent — `WHERE question_es IS NULL` so re-running doesn't clobber edits.
- Both migrations applied to Render via [scripts/apply_migrations_direct.py](api/scripts/apply_migrations_direct.py); head moved `d7e8f9a0b1c2` → `f9a0b1c2d3e4`. Verified: column present, 17 rows updated.
- [schemas/user.py](api/app/schemas/user.py) — exported `Locale = Literal['en', 'es']`. `UserBase.locale` and `UserUpdate.locale` both use it; `PUT /auth/profile` now returns 422 on `locale='fr'` (verified).
- [schemas/assessment.py](api/app/schemas/assessment.py) — added `description_es` to `GiftPassionResult`, all 7 slots in `AssessmentResultWithDetails`.
- [services/scoring_service.py](api/app/services/scoring_service.py) — `GiftPassionResult` dataclass now carries `description_es`; `_calculate_gifts` and `_calculate_passions` populate it from `GiftsPassion.description_es`.
- [routers/assessments.py](api/app/routers/assessments.py) — `/grade` endpoint dicts and `build_result_with_details` both surface `description_es`.

Frontend:
- New [web/src/i18n/translations.ts](web/src/i18n/translations.ts) — flat English-key → Spanish-value map, ~80 entries seeded from existing inline ES_STRINGS / ES_RESULTS plus the legacy [es/dashboard.php](es/dashboard.php), [es/forms.php](es/forms.php), [es/toasts.php](es/toasts.php) files. The English entries object is intentionally empty: English passes through as the source-of-truth.
- New [web/src/hooks/useTranslation.ts](web/src/hooks/useTranslation.ts) — 30-line hook returning `{ t, locale, isEs }`. Supports `{name}` placeholder interpolation via the second arg.
- Refactored [AssessmentWizard.tsx](web/src/pages/AssessmentWizard.tsx): deleted inline `ES_STRINGS`, swapped `useMemo`/`isEs` plumbing for `useTranslation()`. Inner `LikertPage`/`TextPage` components no longer take an `isEs` prop — they call `useTranslation()` directly.
- Refactored [AssessmentResults.tsx](web/src/pages/AssessmentResults.tsx): deleted inline `ES_RESULTS`. Gift/passion descriptions now use `(isEs && gift.description_es) || gift.description` — Spanish if available, English fallback otherwise. `GiftResult` interface in both this file *and* [AssessmentContext.tsx](web/src/context/AssessmentContext.tsx) extended with `description_es`.
- [Dashboard.tsx](web/src/pages/Dashboard.tsx) — applied `t()` to greeting (with `{firstName}` interpolation), description, three CTA buttons, hamburger menu items, GPS section header + table headers + empty state, MyImpact section header + table headers, "incomplete" labels, View Results / Continue buttons, link prompts (church-link CTA, upgrade prompt). The `<span className="text-brand-teal">{orgName}</span>` highlight inside the pending-request message is preserved by splitting the template on `{orgName}` and rendering the inner span between the two halves.
- [Footer.tsx](web/src/components/Footer.tsx) — switched from `useAuth().locale` to `useTranslation().isEs`. Toggle text stays inline ("In English?" / "¿En español?") because each version is meant to read in the *opposite* current language so users always see the alternative.

**TypeScript clean** — `npx tsc --noEmit` returns exit 0 across all four refactor steps.

**Smoke tests run**
- Backend: `UserUpdate(locale='fr')` raises Pydantic ValidationError; `UserUpdate(locale='es')` passes. ✅
- DB verification: Render `alembic_version = f9a0b1c2d3e4`, `gifts_passions.description_es` exists, `SELECT COUNT(*) FROM questions WHERE instrument_type='myimpact' AND question_es IS NOT NULL` → 17. ✅

**Gotchas / learnings**

1. **Two `GiftResult` interfaces in the frontend.** Adding `description_es` to [AssessmentResults.tsx](web/src/pages/AssessmentResults.tsx) wasn't enough — `results = contextResults || localResults`, so TypeScript narrowed to the union of both interfaces, which made `description_es` "missing" via [AssessmentContext.tsx:26](web/src/context/AssessmentContext.tsx#L26). Caught by `tsc --noEmit`. Fix: add the field to **both** interfaces. Lesson: when a type lives in two places (local + shared context), tsc errors will point at the call-site, not the definition that's missing the field — check both.

2. **English source-of-truth pattern.** `translations.en` is an empty object: when locale='en', the hook just returns the input string as-is. This avoids duplicating English in two places (the call-site already has it as the key) and prevents drift between "the key" and "the English text". Tradeoff: there's no English-only typo check via the i18n table. Fine at this scale.

3. **The pending-request message has inline JSX styling on the org name.** The naive translate-the-whole-string approach loses the `<span className="text-brand-teal">` highlight on the org name. Solved by splitting the translation on `{orgName}` and rendering the inner JSX between halves. Documented inline. If more such cases appear we'd want a richer `<Trans>` component (react-i18next pattern), but for one occurrence the inline IIFE is fine.

4. **MyImpact Spanish content was already in repo.** The PRD addendum framed MyImpact translations as a Brian-team-blocked deliverable, but [es/SPANISH - MYIMPACT ASSESSMENT.md](es/SPANISH%20-%20MYIMPACT%20ASSESSMENT.md) (Chelsie Carroll, 2026-04-22) had it in full. Phase 1 exploration would have missed this without the user's nudge ("check the es folder"). Lesson: read the repo's untracked files before assuming external deliverables are needed.

5. **Per-gift `description_es` content is the only remaining content gap.** Migration `e8f9a0b1c2d3` ships the column. Frontend falls back to English when null. The 24 long-form gift/style descriptions need to come from either the legacy Laravel DB dump or Brian's team. Out of Phase D scope; track separately. Until then, Spanish users will see Spanish UI/questions but English gift descriptions on the results page — gracefully degraded, not broken.

6. **`/loop` story prompts are not translated.** Story-question prompts in the GPS wizard come from the Question table's `default_text` field — but that field has both `default_text` (en) and `default_text_es` (es) columns, populated for some rows from the GPS Spanish CSV migration `c4d5e6f7a8b9`. Already handled in the wizard's `TextPage` indirectly via `question.question_es` rendering. Did not need new wiring.

7. **`Locale` is a single source of truth.** Defined once in [schemas/user.py](api/app/schemas/user.py) (backend) and once in [translations.ts](web/src/i18n/translations.ts) (frontend). Adding a new language requires touching both — guarded by Pydantic on the backend (422 if a frontend bug pushes 'fr') and by the missing-key fallback to English on the frontend (rendering won't break, just won't translate).

8. **Spanish text encoding looks weird in CLI output but is correct in DB.** The Render verification print showed `'Soy una persona pac�fica'` instead of `'pacífica'` — that's just terminal codepage rendering. The actual UTF-8 bytes in Postgres are intact (length matches, accents will render correctly in any UTF-8 client including the React app).

### Phase E — Included Items
*Status: done — 2026-05-01*

**Verifications (no code changes needed)**

- **Stripe Customer Portal** is fully wired:
  - Backend: [stripe_service.create_billing_portal_session](api/app/services/stripe_service.py) (line 186) calls `stripe.billing_portal.Session.create()`.
  - Endpoint: `POST /billing/portal` at [billing.py:543](api/app/routers/billing.py#L543) — guarded by `require_primary_admin_no_impersonation`. Returns `{url: ...}`.
  - Frontend hook: [BillingContext.openBillingPortal](web/src/context/BillingContext.tsx) — POSTs the endpoint, redirects to the returned URL.
  - Frontend trigger: [BillingDashboard.handleOpenPortal](web/src/pages/BillingDashboard.tsx) (line 333) wraps the hook with error toast. The "Manage Payment Method" button on AdminDashboard navigates to `/admin/billing` where this trigger lives.

- **Master admin Add Church** is fully wired:
  - Backend: [master.create_church](api/app/routers/master.py) at line 306, schema [CreateChurchRequest](api/app/schemas/master.py#L56). Audit-logged. Creates org + primary admin + invites new admin via password-reset email if needed. Now also fires `church_created` notification (Phase C wiring).
  - Frontend hook: [MasterContext.createChurch](web/src/context/MasterContext.tsx#L195) — POSTs `/master/churches`.
  - UI: "Add Church" button at [MasterDashboard.tsx:590](web/src/pages/MasterDashboard.tsx#L590) opens a modal; submission calls `createChurch(payload)` at line 186.

**What shipped (Help button)**

- New [HelpLink.tsx](web/src/components/HelpLink.tsx) component — single anchor with `href="mailto:info@disciplesmade.com?subject=GPS%20Platform%20Help%20Request"`. Accepts an optional `className` so the same component renders both as an inline link in the desktop nav and as a stacked menu item in the mobile drawer.
- Mounted in [Navbar.tsx](web/src/components/Navbar.tsx): desktop right cluster (between MyImpact logo and notification bell) and mobile menu (after the logos). Visible to all roles, including unauthenticated users — the addendum says "all user roles" and the mailto works without an auth check.

**TypeScript clean** — `npx tsc --noEmit` exit 0.

**Gotchas / learnings**

1. **The "Manage Payment Method" button doesn't open Stripe directly.** It navigates to `/admin/billing`, where a separate "Manage Subscription" / "Open Portal" button calls the actual portal endpoint. This is fine — the addendum doesn't specify a one-click flow, and the BillingDashboard's intermediate page surfaces invoices / payments / subscription status alongside the portal link, which is more useful than going straight to Stripe.

2. **Help button is unauthenticated-friendly.** Pure mailto with no API call. Works on the login/register pages too — useful when the user's blocker is "I can't log in". Visible-everywhere is the right call.

3. **`HelpLink` accepts a `className` override** rather than a `variant` prop. The two render contexts (inline desktop link vs. stacked mobile menu item) only differ in font-size and padding — a className override is more honest than codifying two variants in the component itself. If a third variant shows up, refactor.

4. **No need to translate the Help button.** The addendum says admin-only / system text stays English; "Help" is part of the chrome that surfaces on every page including admin pages, and the mailto subject line is a routing key for the receiving inbox so it must stay in English. Skipped from translations.ts intentionally.
