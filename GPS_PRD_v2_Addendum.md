# GPS Platform: Enhancement Scope PRD Addendum

**Client:** Disciples Made, Inc.
**Developer:** Paschal Okonkwo
**Version:** 2.1 (Enhancement Scope)
**Date:** April 30, 2026
**Status:** CONFIDENTIAL
**Budget:** $2,700 (separate from original $3,850 base scope)

---

## 1. Overview

This addendum defines four enhancement features agreed upon via email between Paschal Okonkwo and Brian Phipps (April 14-24, 2026). These features are net-new scope beyond the original GPS_PRD_v2.md and are billed separately.

Additionally, two items from the original scope are documented here for implementation clarity: Stripe payment method management and master admin church creation.

---

## 2. Feature 1: In-App Notifications ($500)

### 2.1 User Stories

**US-N1:** As a church admin, I want to see a notification indicator in my dashboard so that I know when something requires my attention without checking email.

**US-N2:** As a church admin, I want to see a list of recent notifications so that I can review what's happened with my church members.

**US-N3:** As a church admin, I want to mark notifications as read so that I can track what I've already reviewed.

**US-N4:** As a master admin, I want to receive notifications for system-wide events so that I can stay informed about platform activity.

### 2.2 Notification Events

| Event | Recipient | Message Template |
|-------|-----------|-----------------|
| Member completes GPS assessment | Church admin(s) of member's church | "{first_name} {last_name} completed their GPS assessment" |
| Member completes MyImpact assessment | Church admin(s) of member's church | "{first_name} {last_name} completed their MyImpact assessment" |
| New member joins church (via link or approved request) | Church admin(s) of that church | "{first_name} {last_name} joined your church" |
| Member requests to link with church | Church admin(s) of that church | "{first_name} {last_name} requested to join your church" |
| New church created | Master admin(s) | "{church_name} was created" |

### 2.3 Data Model

#### notifications (new table)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| recipient_id | UUID (FK) | Yes | References users. The admin receiving the notification. |
| event_type | VARCHAR(50) | Yes | Values: `assessment_completed`, `member_joined`, `member_requested`, `church_created` |
| title | VARCHAR(255) | Yes | Short display text (e.g., "New Assessment Completed") |
| message | TEXT | Yes | Full notification message |
| reference_type | VARCHAR(50) | No | Entity type: `user`, `assessment`, `organization` |
| reference_id | UUID | No | ID of the related entity for deep linking |
| is_read | BOOLEAN | Yes | Default: false |
| created_at | TIMESTAMP | Yes | UTC |

Design notes:
- No `updated_at` needed. Only mutation is `is_read` toggling to true.
- Notifications are user-scoped. Each admin gets their own notification row. If a church has 2 admins, an assessment completion creates 2 notification rows.
- No soft-delete. Old notifications can be hard-deleted by a cleanup job after 90 days if needed (not in scope for now).

### 2.4 API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/notifications` | Authenticated user | Returns notifications for the current user, ordered by `created_at` DESC. Query params: `unread_only` (bool), `limit` (int, default 20), `offset` (int). |
| GET | `/api/notifications/unread-count` | Authenticated user | Returns `{ "count": N }`. Used by the bell badge. |
| PATCH | `/api/notifications/{id}/read` | Authenticated user | Marks a single notification as read. User can only mark their own. |
| PATCH | `/api/notifications/mark-all-read` | Authenticated user | Marks all unread notifications as read for the current user. |

### 2.5 Frontend

- **Bell icon** in the top navigation bar (visible to admin and master admin roles only).
- **Unread badge** showing count of unread notifications. Displays number if 1-99, "99+" if more.
- **Dropdown panel** on bell click: scrollable list of notifications, newest first. Each item shows icon (based on event type), message text, and relative timestamp ("2 hours ago"). Unread items have a visual indicator (dot or background color).
- **"Mark all as read"** link at the top of the dropdown.
- **Click behavior:** Clicking a notification marks it as read and navigates to the relevant page (e.g., clicking an assessment notification navigates to that member's detail panel).
- **Polling:** Frontend polls `/api/notifications/unread-count` every 60 seconds. No websockets needed at this scale.

### 2.6 Backend Logic

Notification creation happens as a side effect of existing operations. Insert notification rows in the same request handler (not a background task -- the volume is low enough that synchronous insertion is fine):

- **Assessment completion handler:** On successful assessment submission, query the user's church membership, find all admins of that church, create one notification per admin.
- **Church join handler:** On membership creation (via link registration, request approval, or admin invite acceptance), create notification for all church admins.
- **Church link request handler:** On link request creation, create notification for all church admins.
- **Church creation handler:** On new organization creation, create notification for all master admins.

### 2.7 Out of Scope

- Email notifications for these events (email notifications for assessment completion already exist separately)
- Notification preferences/settings (admin cannot turn off specific notification types)
- Push notifications (mobile/browser)
- Notification grouping or batching

---

## 3. Feature 2: Webhook Integration / CRM Auto-Push ($800)

### 3.1 User Stories

**US-W1:** As a church admin, I want to configure a webhook URL so that assessment results are automatically sent to my church's CRM (ROCK RMS, Planning Center, etc.) when a member completes an assessment.

**US-W2:** As a church admin, I want to test my webhook connection so that I can verify my CRM is receiving data correctly before relying on it.

**US-W3:** As a church admin, I want to see the delivery status of recent webhooks so that I can troubleshoot if my CRM stops receiving data.

**US-W4:** As a master admin, I want to see which churches have webhooks configured so that I can support troubleshooting.

### 3.2 Data Model

#### webhook_configs (new table)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| organization_id | UUID (FK) | Yes | References organizations. One config per church. UNIQUE constraint. |
| webhook_url | VARCHAR(2048) | Yes | The destination URL |
| is_active | BOOLEAN | Yes | Default: true. Admin can disable without deleting. |
| secret | VARCHAR(255) | No | Optional shared secret for payload signing (HMAC-SHA256). Generated by the system if requested. |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

#### webhook_deliveries (new table)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| webhook_config_id | UUID (FK) | Yes | References webhook_configs |
| event_type | VARCHAR(50) | Yes | `assessment_completed` (extensible for future events) |
| payload | JSONB | Yes | The full JSON payload that was sent |
| status | VARCHAR(20) | Yes | Values: `pending`, `success`, `failed` |
| http_status_code | SMALLINT | No | Response status code from the destination |
| error_message | TEXT | No | Error details if delivery failed |
| attempts | SMALLINT | Yes | Default: 0. Incremented on each attempt. |
| next_retry_at | TIMESTAMP | No | When to retry next (NULL if success or max attempts reached) |
| created_at | TIMESTAMP | Yes | UTC |

Design notes:
- One webhook config per church. If a church needs multiple destinations, they use a middleware like Zapier to fan out.
- Delivery log retained for 30 days, then eligible for cleanup (not in scope for now).
- Max 3 retry attempts with exponential backoff: 1 min, 5 min, 30 min.

### 3.3 Webhook Payload

Matches the legacy OpenAPI spec provided by Doug Niccum. The payload structure is:

```json
{
  "user": {
    "id": 18122,
    "firstName": "Doug",
    "lastName": "Niccum",
    "email": "doug@example.com"
  },
  "assessment": {
    "instrument": "gps",
    "gifts": [
      { "id": 19, "name": "Wisdom", "abbreviation": "W", "description": "...", "points": 20 }
    ],
    "topGifts": [
      { "id": 19, "name": "Wisdom", "abbreviation": "W", "description": "...", "points": 20 }
    ],
    "passions": [
      { "id": 23, "name": "Shepherd", "abbreviation": "S", "description": "...", "points": 77 }
    ],
    "topPassion": [
      { "id": 23, "name": "Shepherd", "abbreviation": "S", "description": "...", "points": 77 }
    ],
    "abilities": ["Project management", "Web Development"],
    "people": ["Infants/Babies", "Singles"],
    "causes": ["At-Risk Children", "Race"],
    "stories": [
      { "question": "...", "questionEs": "...", "answer": "..." }
    ]
  }
}
```

Notes:
- The `instrument` field is added (not in legacy) to distinguish GPS from MyImpact payloads.
- For MyImpact assessments, the payload structure will follow MyImpact's scoring output (Character, Calling, Impact scores). Define exact shape when MyImpact webhook is implemented.
- User IDs: The legacy payload uses integer IDs. The new system uses UUIDs. Include both `id` (UUID) and `legacyId` (integer, if available from migration) for backward compatibility during transition.

### 3.4 API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/admin/webhook` | Church admin | Returns the webhook config for the current admin's church. |
| POST | `/api/admin/webhook` | Church admin | Creates or updates the webhook config. Body: `{ "webhook_url": "...", "is_active": true }` |
| DELETE | `/api/admin/webhook` | Church admin | Removes the webhook config. |
| POST | `/api/admin/webhook/test` | Church admin | Sends a test payload to the configured URL. Returns success/failure. |
| GET | `/api/admin/webhook/deliveries` | Church admin | Returns recent delivery log (last 30 days). Query params: `status`, `limit`, `offset`. |
| GET | `/api/master/churches/{id}/webhook` | Master admin | View webhook config for any church. Read-only. |

### 3.5 Frontend

- **Location:** Church Profile & Settings page, under a section called "CRM Integration" (replaces the current "Manage Connections" stub button).
- **Configuration form:** URL input field, active/inactive toggle, "Save" button, "Test Connection" button, "Remove" button with confirmation.
- **Test Connection:** Fires a test payload and shows success (green checkmark + HTTP status) or failure (red X + error message) inline.
- **Delivery log:** Collapsible section below the config form. Table showing recent deliveries: date, event type, status (color-coded: green/red), HTTP status code. Failed deliveries show error message on row expand.
- **Master admin view:** Read-only webhook status visible in the church detail panel on the Master dashboard. Shows whether webhook is configured, URL (masked), and last delivery status.

### 3.6 Backend Logic

- **Trigger:** On assessment completion (after scoring and result storage), check if the user's church has an active webhook config. If yes, build the payload and attempt delivery.
- **Delivery:** HTTP POST to the configured URL with `Content-Type: application/json`. Timeout: 10 seconds. If the destination returns 2xx, mark as `success`. Otherwise, mark as `failed` and schedule retry.
- **Retry logic:** Max 3 attempts. Backoff: 1 minute, 5 minutes, 30 minutes. Retries run via a lightweight background task (FastAPI BackgroundTasks or a simple cron-like check on a `/api/internal/process-retries` endpoint called periodically).
- **Payload signing (optional):** If `secret` is set on the webhook config, include an `X-GPS-Signature` header with HMAC-SHA256(secret, payload_body). This lets the receiving system verify the payload is authentic.
- **Test payload:** Same structure as a real payload but with clearly fake data (e.g., firstName: "Test", lastName: "User") and an additional `"test": true` flag in the root object.

### 3.7 Out of Scope

- Multiple webhook URLs per church
- Event selection (admin cannot choose which events trigger webhooks -- all assessment completions fire)
- Webhook management from master admin (master can view but not create/edit)
- MyImpact-specific webhook payload format (use a generic structure until MyImpact webhook shape is defined)

---

## 4. Feature 3: Zapier Integration ($500)

### 4.1 User Stories

**US-Z1:** As a church admin, I want new user registrations to be sent to Zapier so that new members are automatically added to our email nurture campaigns in Kit.

**US-Z2:** As a church admin, I want to configure my Zapier webhook URL separately from my CRM webhook so that registration events and assessment events go to different destinations.

### 4.2 Data Model

Reuses the `webhook_configs` table with an additional field:

#### Modification to webhook_configs

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| event_type | VARCHAR(50) | Yes | Default: `assessment_completed`. Values: `assessment_completed`, `user_registered`. Allows separate configs per event type. |

This changes the UNIQUE constraint from `(organization_id)` to `(organization_id, event_type)`, allowing one webhook per event type per church.

Reuses the `webhook_deliveries` table as-is.

### 4.3 Zapier Payload (User Registration)

```json
{
  "event": "user_registered",
  "user": {
    "id": "uuid-here",
    "firstName": "Jane",
    "lastName": "Smith",
    "email": "jane@example.com",
    "phone": "555-1234"
  },
  "church": {
    "id": "uuid-here",
    "name": "Grace Community Church"
  },
  "registeredAt": "2026-04-30T14:30:00Z"
}
```

### 4.4 API Endpoints

Extends the existing webhook endpoints:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/admin/webhooks` | Church admin | Returns all webhook configs for the current admin's church (both assessment and registration). |
| POST | `/api/admin/webhooks` | Church admin | Creates a webhook config. Body: `{ "webhook_url": "...", "event_type": "user_registered", "is_active": true }` |
| PUT | `/api/admin/webhooks/{id}` | Church admin | Updates a specific webhook config. |
| DELETE | `/api/admin/webhooks/{id}` | Church admin | Removes a specific webhook config. |
| POST | `/api/admin/webhooks/{id}/test` | Church admin | Sends a test payload for the specified webhook. |
| GET | `/api/admin/webhooks/{id}/deliveries` | Church admin | Returns delivery log for a specific webhook. |

Note: These endpoints replace the singular `/api/admin/webhook` endpoints from Feature 2. The combined design supports both assessment webhooks and registration webhooks through a single, consistent API.

### 4.5 Frontend

- **Location:** Same "CRM Integration" section on Church Profile & Settings.
- **Layout:** Two sections within the CRM Integration panel:
  - "Assessment Results Webhook" (for CRM/ROCK integration)
  - "New Member Registration Webhook" (for Zapier/Kit integration)
- Each section has its own URL field, active toggle, test button, and delivery log.
- Labels use plain language: "When a member completes an assessment, send results to:" and "When a new member registers, send their info to:"

### 4.6 Backend Logic

- **Trigger:** On user registration (after account creation and church affiliation), check if the user's church has an active webhook config with `event_type = 'user_registered'`. If yes, build the payload and deliver.
- **Delivery:** Same HTTP POST pattern, timeout, retry logic, and optional signing as the assessment webhook.
- **Edge case:** If the user registers as independent (no church), no webhook fires. Webhooks only fire for church-affiliated registrations.

### 4.7 Out of Scope

- Zapier OAuth integration (admin pastes the URL manually, same as legacy)
- Webhook for events other than registration (e.g., church join, assessment started)
- Any Zapier-specific UI branding or Zap template

---

## 5. Feature 4: Spanish Language Support ($900)

### 5.1 User Stories

**US-S1:** As a Spanish-speaking user, I want to switch the platform to Spanish so that I can take assessments and navigate the dashboard in my language.

**US-S2:** As a user, I want my language preference to persist across sessions so that I don't have to switch every time I log in.

**US-S3:** As a church admin, I want my Spanish-speaking members to see the platform in Spanish so that language is not a barrier to taking assessments.

### 5.2 Scope Definition

Spanish language support matches the legacy system's hybrid approach. Based on Brian's screenshots of the current Laravel platform, the following elements are translated:

**Translated:**
- Assessment questions and answer labels (GPS + MyImpact)
- Assessment results page (gift/passion names, descriptions, story questions)
- Dashboard greeting ("Bienvenido a su tablero" / "Buenas tardes")
- Navigation sidebar labels (Evaluaciones, Usuarios, Recursos, Registros y Estadisticas)
- Table headers (Nombre, Ultima Evaluacion, Regalos, Pasion)
- Primary action buttons (Tomar Una Nueva Evaluacion, Ver Resultados, Continuar)
- Language toggle link ("En espanol?" / "In English?")

**Not translated (stays English):**
- Admin-only pages (master dashboard, billing, webhook settings)
- Error messages and validation text
- Email templates
- System-generated text (file names, CSV headers)

### 5.3 Translation Data Sources

| Content | Source | Provider |
|---------|--------|----------|
| GPS assessment questions | Already in database (`question_es` fields) | Legacy data |
| GPS gift/passion descriptions | Already in database (gifts_passions table may need `description_es` field) | Legacy data |
| MyImpact assessment questions | Brian's team pulls from Typeform | Client provides |
| UI strings (sidebar, buttons, headers, greetings) | Brian's team pulls from legacy screenshots or Doug provides | Client provides |

**Prerequisite:** Brian's team must provide MyImpact Spanish translations and a list of UI string translations before development begins.

### 5.4 Data Model Changes

#### Modification to users table

The `locale` field already exists on the users table (VARCHAR(10), default 'en'). No schema change needed.

#### Modification to gifts_passions table

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| description_es | TEXT | No | Spanish description. Displayed on results page when user locale is 'es'. |

**Confirmed:** This field does NOT exist. The `GiftsPassion` model only has `description` (English). The 19 gifts and 5 influencing styles all lack Spanish descriptions. Requires an Alembic migration to add the column, plus seeding the Spanish descriptions (Brian's team to provide, or extract from legacy database if available).

#### MyImpact questions

**Confirmed:** MyImpact questions share the same `questions` table as GPS, differentiated by `instrument_type` column (`'gps'` or `'myimpact'`). The `question_es` field already exists on this table. Brian's team will provide MyImpact Spanish translations from Typeform to populate these fields.

#### Locale validation fix

**Confirmed:** The `PUT /auth/profile` endpoint accepts any string for `locale` (up to 10 chars). Add validation to constrain accepted values to `en` and `es` only. Update the `UserUpdate` Pydantic schema to use `Literal['en', 'es']` or a validator.

### 5.5 Implementation Approach

**No i18n library.** The translation scope is small enough (roughly 30-50 UI strings) that a simple key-value approach is sufficient. Avoid the overhead of react-i18next for this scale.

**Frontend approach:**
- Create a `translations.ts` file with a flat key-value map:
  ```
  const translations = {
    en: {
      "dashboard.greeting": "Welcome to your dashboard",
      "dashboard.takeAssessment": "Take a New Assessment",
      "nav.assessments": "Assessments",
      ...
    },
    es: {
      "dashboard.greeting": "Bienvenido a su tablero",
      "dashboard.takeAssessment": "Tomar una Nueva Evaluacion",
      "nav.assessments": "Evaluaciones",
      ...
    }
  }
  ```
- Create a `useTranslation()` hook that reads the current user's locale from auth context and returns a `t()` function.
- Replace hardcoded strings in translated components with `t('key')` calls.

**Backend approach:**
- Assessment question endpoints already return both `question` and `question_es`. Frontend selects the correct field based on locale.
- Gift/passion description endpoints return both `description` and `description_es`.
- No backend translation logic needed. The backend serves both languages; the frontend picks which to display.

### 5.6 API Changes

No new endpoint needed. The existing `PUT /auth/profile` endpoint already accepts `locale` in the `UserUpdate` schema. The only change is adding validation to constrain `locale` to `['en', 'es']` via a Pydantic `Literal` or validator.

The assessment question endpoints already return `question_es`, `passion_type_es`, `default_text_es`, and `summary_es` fields. The frontend selects which field to display based on the user's locale.

### 5.7 Frontend Changes

- **Language toggle:** An "En espanol?" / "In English?" link in the same position as the legacy system (bottom of sidebar or footer area). Clicking it calls the locale endpoint, updates local state, and re-renders translated components.
- **Affected pages:**
  - Member dashboard (greeting, assessment table headers, buttons)
  - Assessment wizard (question text, navigation buttons, progress labels)
  - Assessment results page (gift/passion names, descriptions, story questions)
  - Navigation sidebar (section labels)
- **Unaffected pages:**
  - Admin dashboard (English only)
  - Master dashboard (English only)
  - Billing/subscription pages (English only)
  - Login/registration (English only -- legacy also keeps these in English)

### 5.8 Out of Scope

- Full i18n framework
- Admin or master dashboard translation
- Email template translation
- Right-to-left (RTL) language support
- Additional languages beyond Spanish
- Translation of assessment result PDFs or CSV exports
- Auto-detecting browser language (user must manually toggle)

---

## 6. Included Items (No Extra Cost)

### 6.1 Help Button

A visible "Help" button in the platform navigation that opens a pre-addressed email: `mailto:info@disciplesmade.com?subject=GPS%20Platform%20Help%20Request`.

- Visible to all user roles
- Positioned in the top navigation bar or sidebar footer
- No backend component, purely a mailto link

### 6.2 Stripe Payment Method Management

Part of the original $3,850 scope (PRD Section 4.3).

**Implementation:** When an admin clicks "Manage Payment" or "Update Payment Method", the system generates a Stripe Customer Portal session via the Stripe API (`stripe.billing_portal.sessions.create()`) and redirects the admin to that hosted page. Stripe handles card updates, billing history, and invoice display. On completion, Stripe redirects back to the admin dashboard.

No custom payment form needed. Stripe's hosted portal covers: update card, view invoices, view payment history.

### 6.3 Master Admin: Create Church

Part of the original scope (UC-14 in Use Cases doc: "Master admin can add new church records").

**Implementation:**
- "Add Church" button on the Master Admin churches page
- Modal form: Church Name (required), City (required), State, Country
- On submit: creates organization record, generates unique `key` slug for the church assessment link
- Optionally assign an existing user as admin during creation
- No Stripe subscription created (comp church until admin subscribes themselves)
- Logged in audit_log

---

## 7. Implementation Order

Recommended build sequence to minimize rework:

1. **Webhook infrastructure** (Feature 2 + Feature 3 together) -- Build the webhook_configs and webhook_deliveries tables, delivery engine, and retry logic once. Then wire up both event triggers (assessment completion and user registration). Build the CRM Integration UI on the admin settings page.

2. **In-App Notifications** (Feature 1) -- Notifications table, API endpoints, bell component. The notification triggers partially overlap with webhook triggers (both fire on assessment completion), so building them second lets you reuse the event detection pattern.

3. **Spanish Language** (Feature 4) -- Blocked until Brian's team provides MyImpact translations and UI strings. Build the translation infrastructure, hook, and toggle. Apply to affected pages. This is mostly frontend work and independent of the other features.

4. **Included items** (Help button, Stripe portal, Master create church) -- These can be done at any point. Small, independent tasks.

---

## 8. Acceptance Criteria Summary

| Feature | Done When |
|---------|-----------|
| In-App Notifications | Bell icon shows unread count. Clicking opens dropdown with notifications. Notifications fire on assessment completion, member join, and link request. Mark-as-read works. |
| Webhook / CRM | Admin can configure a webhook URL. Assessment completion sends payload matching Doug's OpenAPI spec. Test connection works. Delivery log shows success/failure. Retry on failure. |
| Zapier | Admin can configure a separate registration webhook. New church-affiliated registrations fire a payload to the URL. Delivery log works. |
| Spanish | User can toggle to Spanish. GPS questions, results, dashboard, and sidebar display in Spanish. Preference persists across sessions. MyImpact questions display in Spanish (contingent on Brian providing translations). |
| Help Button | Visible button opens mailto to info@disciplesmade.com. |
| Stripe Portal | Admin clicks "Manage Payment" and is redirected to Stripe Customer Portal. Can update card and view invoices. |
| Master Create Church | Master admin can create a new church from the dashboard. Church gets a unique assessment link. |
