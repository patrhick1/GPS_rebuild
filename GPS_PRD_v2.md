# GPS Platform Rebuild: Product Requirements Document

**Client:** Disciples Made, Inc.
**Consultant:** ClickDown, LLC
**Developer:** Paschal Okonkwo
**Version:** 2.0 (Custom Build)
**Date:** March 20, 2026
**Status:** CONFIDENTIAL

---

## 1. Executive Summary

This document defines the product requirements for the complete rebuild of the GPS (Gift, Passion, Story) assessment platform, originally built on Laravel/AWS and currently operated by Disciples Made, Inc. The rebuild replaces both the aging Laravel backend and the Bubble.io migration plan with a custom-built, modern web application.

The GPS platform is a faith-based assessment tool that helps church members discover their spiritual gifts, passions, and personal story. It is deeply integrated into Disciples Made's curriculum, partner training materials, and the Find Your Place program. Any rebuild must maintain full legacy parity while introducing a modernized architecture, a second assessment instrument (MyImpact Equation), Stripe-based subscription billing for church accounts, and improved admin tooling.

### 1.1 Project Objectives

- Port all existing GPS assessment functionality from the legacy Laravel/AWS application to a modern, self-contained web application
- Migrate historical data (users, assessment results, church records) from MySQL to PostgreSQL with full validation
- Introduce MyImpact Equation as a second, parallel assessment instrument
- Implement Stripe subscription billing for church administrator accounts
- Build role-based admin dashboards (Church Admin + Master Admin) with CSV export compatible with Planning Center and ROCK RMS
- Deploy to a managed PaaS provider for operational simplicity

### 1.2 Key Constraints

- Legacy parity is non-negotiable: all existing user flows, scoring logic, and report outputs must be reproduced exactly
- GPS is referenced in published curricula and partner materials; any changes to assessment structure, scoring, or reporting require explicit sign-off from the product owner (Brian D Phipps)
- Assessment instruments are self-hosted (not Typeform): the scoring engine (Python/FastAPI), form rendering (React), and results display (print-friendly HTML) are all built in-house
- Budget is milestone-based per the consulting agreement: $1,100 initial / $2,200 migration / $550 final

---

## 2. Technology Stack

The following stack replaces both the legacy Laravel/AWS infrastructure and the previously proposed Bubble.io approach. The architecture uses a split-stack design: FastAPI (Python) handles all backend logic (scoring engine, API, PDF generation, data processing, Stripe webhooks), while a React frontend handles all user-facing dashboards and forms. This separation plays to Python's strengths for numerical computation and data work, while keeping the frontend modern and responsive.

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend API | FastAPI (Python) | High-performance async Python framework. Ideal for scoring engine math, PDF generation, data processing, and CSV export. Auto-generates OpenAPI/Swagger docs for every endpoint. |
| Frontend | React + Vite (or Next.js) | Modern React SPA for all dashboards and assessment UI. Vite for fast dev builds; Next.js if SSR is needed later. |
| Database | PostgreSQL on Render | Managed Postgres on the same platform as the backend and frontend. One dashboard, one billing, lower latency (same network). Replaces legacy MySQL. |
| Authentication | FastAPI-owned (PyJWT + passlib/bcrypt) | Full auth flow built in Python: registration, login, password reset, invite tokens, JWT issuance/validation. Gives full control over custom flows like church-specific registration links, invite tokens, account merging, and role management. |
| Hosting | Render | Single platform for both FastAPI backend (Web Service) and React frontend (Static Site). Push-to-deploy from GitHub, managed SSL, one dashboard. |
| Billing | Stripe (Python SDK) | Subscription management for church accounts. Monthly/annual plans with payment method management. Webhook handling in FastAPI. |
| Email | Resend (Python SDK) | API-based transactional email for invitations, assessment results, and PDF delivery. Triggered from FastAPI background tasks. |
| Results Output | Print-friendly HTML + CSS | Legacy system uses browser printing, not server-side PDF. Results page styled for clean print output. Server-side PDF generation (ReportLab/WeasyPrint) can be added as a future enhancement. |
| Styling | Tailwind CSS + shadcn/ui | Utility-first CSS with pre-built accessible components. Fast iteration, consistent design system. |

---

## 3. User Roles & Permissions

### 3.1 Role Definitions

**Independent User:** A registered individual who is not affiliated with any church. Can take assessments and view their own results. Their data is private and not visible to any church administrator.

**Church Member:** A user affiliated with a single church (via admin invite, unique church link, or approved request-to-link). All assessment history becomes visible to the affiliated church's admin. Unlinking makes data private again.

**Church Admin:** Manages users, church profile, assessment access, and exports for their specific church. Can invite members, promote/demote roles, and view all affiliated member data.

**Master Admin:** Full cross-church visibility and control. Manages all churches, users, survey instruments, and system settings. Can impersonate any account for troubleshooting.

### 3.2 Permissions Matrix

| Action | Independent User | Church Member | Church Admin | Master Admin |
|--------|-----------------|---------------|-------------|-------------|
| Take/retake assessments | Yes | Yes | Yes | Yes |
| View own results/history | Yes | Yes | Yes | Yes |
| View member results | No | No | Own church | All |
| Invite new users | No | No | Yes | Yes |
| Export results (CSV) | Self only | Self only | Own church | All churches |
| Manage churches | No | No | No | Yes |
| Promote/demote members | No | No | Own church | All |
| Impersonate users | No | No | No | Yes |
| Manage billing | No | No | Yes | Yes |
| View audit logs | No | No | No | Yes |

### 3.3 Key User Workflows

**Admin Upgrade Flow:** Any registered individual user may upgrade to Church Administrator. The system creates a new church record, assigns the user as primary admin, activates the admin dashboard, and initiates Stripe subscription billing.

**Church Request-to-Link:** An independent user searches for an existing church and submits a connection request. The church admin reviews and approves/declines. Until approved, the user remains independent and their data stays private.

**Unique Church Assessment Link:** Each church generates a unique assessment URL from their admin dashboard. New users registering through this link are automatically affiliated with that church.

---

## 4. Functional Requirements

### 4.1 Assessment Engine

The assessment engine is the core of the platform. It must support multiple instruments (GPS and MyImpact Equation initially) with the ability to add new instruments without architectural changes.

- Multi-step form interface: one question per screen with visual progress indicator (e.g., "Question 3 of 25")
- Instrument switcher as persistent horizontal tab at top of assessment screen
- All fields required with inline validation and clear error messaging
- Scoring engine: translate legacy PHP scoring algorithms to Python (FastAPI backend). The GPS scoring is straightforward addition: 76 questions mapped to 19 gift categories (4 questions each), rated 1-5, summed per category. Top 2 scores become the user's identified gifts. Influencing Style scoring follows the same pattern: 80 questions mapped to 5 styles, summed per style, top 2 identified as primary and secondary.
- Deep linking: accept URL parameters (Member ID, Church ID) from external platforms (Mighty Networks) to auto-tag users
- On completion: display results page with scores, definitions, and selections. Page must have print-friendly CSS for browser printing. Email a link to the results page to the user.
- Retakes always create a new assessment record; historical results are never overwritten
- Draft/resume capability: users can save progress and return to complete later
- Mobile-optimized with minimum 44px touch targets

### 4.2 Personal Dashboard

- Summary panel: most recent assessment result per instrument displayed as a card with visual (bar/line/radar graph), key score highlights, and date
- Tabbed instrument navigation: each tab shows chronological history table of all past assessments for that instrument, sortable by date, with clickable rows for full detail
- Side-by-side comparison view for GPS vs MyImpact results across time, with color-highlighted diff format
- Export and print buttons in top-right corner for CSV and print-optimized output
- Admin upgrade card and church linking UI prominently displayed for independent users
- All elements load within 3 seconds; responsive from 320px mobile width
- All graphs include textual value/interpretation below the visual
- "Growth journey" shown as a step-by-step vertical sequence under each assessment timeline

### 4.3 Church Admin Dashboard

- Church context banner with name/logo and "Switch Church" dropdown if admin manages multiple churches
- Preferred survey instrument setting: admin can assign a default assessment instrument for their church, highlighted (but not required) on member dashboards
- Member table with columns: First Name, Last Name, Email, Status (Active/Pending/Locked/Deleted), Assessment Completion per instrument, Last Assessment Date, Instruments Taken, Role
- Sticky table headers remain visible during scroll
- Search, sort, and filter on all columns; filters persist across session refreshes
- Pagination at 50 results per page with item count display ("Showing 1-50 of 213 results")
- Invite modal: batch email field + CSV upload; color-coded status (green=Accepted, yellow=Sent, red=Failed, grey=Deleted)
- Pending member requests queue with approve/decline actions
- Unique church assessment link generation and management
- Make admin / remove admin controls with confirmation dialogs; irreversible actions (e.g., removing last admin) use "type to confirm" pattern
- Subscription and billing section: Stripe integration for monthly/annual plans, payment method management, cancellation
- Member detail slide-in panel: chronological assessment history, single-user CSV export, print, and note-adding
- Resync/reload button for on-demand data refresh without browser reload
- All admin actions show clear success/failure feedback; no silent fails

### 4.4 Master Admin Dashboard

- System-wide summary metrics: total churches, users, assessments in last 30/90/365 days
- Church table: Church Name, Primary/Secondary Admin (clickable email), Active Users, Active Assessments per Instrument, Completed/Incomplete counts, Instrument Mix, Last Activity
- Sticky table headers; pagination with item count display
- Add/remove church admins via modal with explicit confirmation; irreversible actions use "type to confirm" pattern
- User impersonation in secure pop-out window with mandatory logging (time/user/reason)
- Export controls: dropdown for single/bulk by church, date range, instrument, with filter context summary
- Activity log for all sensitive actions (add/remove admin, export, impersonate), visible and exportable
- Resync/reload button for on-demand data refresh

### 4.5 CSV Export System

All exports are manual, user-initiated. No scheduled or automated exports at MVP.

- Export selection: all users, filtered group, individual users, or date range
- UTF-8 encoding, ASCII comma delimiter, CRLF line endings
- Field mapping compatible with Planning Center and ROCK RMS import schemas
- Required fields: First Name, Last Name, Email, Church Name, Assessment Instrument, Assessment Date (ISO), Score Categories (per instrument rubric), Raw Answers (JSON string), Status
- Admin can preview sample CSV row before download
- Confirmation modal before download with file name convention: [ChurchName]_[Instrument]_[YYYYMMDD].csv
- If export fails: explicit red error modal with troubleshooting steps

---

## 5. Data Model

The data model below is informed by the legacy MySQL schema (21 tables, ~31,600 users, ~42,400 assessments, ~169 organizations). The new schema preserves the legacy patterns that work (junction table for memberships, data-driven question/gift definitions, separate answers and results tables) while modernizing for PostgreSQL and adding fields required by the new PRD features.

### 5.1 Core Entities

#### users

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated. Legacy uses auto-increment bigint; migration maps old IDs to UUIDs. |
| first_name | VARCHAR(255) | No | Nullable in legacy (some invited users have no name yet) |
| last_name | VARCHAR(255) | No | Same as above |
| email | VARCHAR(255) | Yes | Unique, validated, lowercase |
| password_hash | TEXT | Yes* | *Not required for invite-only users until first login |
| phone_number | VARCHAR(255) | No | |
| city | VARCHAR(255) | No | Legacy stores location on user |
| state | VARCHAR(255) | No | |
| country | VARCHAR(255) | No | |
| locale | VARCHAR(10) | Yes | Default 'en'. Legacy supports 'es' (Spanish). |
| status | VARCHAR(20) | Yes | Values: active, invited, locked, deleted (soft-delete only) |
| stripe_id | VARCHAR(255) | No | Legacy stores Stripe customer ID on user (for individual billing) |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

#### organizations (churches)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| name | VARCHAR(255) | Yes | |
| city | VARCHAR(255) | Yes | Legacy requires city |
| state | VARCHAR(255) | No | |
| country | VARCHAR(255) | No | |
| key | VARCHAR(255) | Yes | Unique slug for church-specific registration URL (e.g., `/register/{key}`) |
| package | VARCHAR(255) | No | Legacy has this for tiered access. Maps to subscription tier in new system. |
| stripe_id | VARCHAR(255) | No | Stripe customer ID for organization-level billing |
| card_brand | VARCHAR(255) | No | Last known card brand |
| card_last_four | VARCHAR(4) | No | Last 4 digits of payment card |
| trial_ends_at | TIMESTAMP | No | |
| preferred_instrument | VARCHAR(50) | No | Admin-assigned default assessment instrument for this church. Highlighted on member dashboards. |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

#### memberships (user-to-organization link with role)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| user_id | UUID (FK) | Yes | References users |
| organization_id | UUID (FK) | No | References organizations. NULL if independent. |
| role_id | UUID (FK) | Yes | References roles |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

This junction table replaces the earlier design of a single `church_id` on the user table. The legacy system uses this pattern and it cleanly separates "which church" from "what role." A user can have one active membership (per Brian's single-church business rule), but the table structure supports the edge cases found in legacy data where some users have multiple memberships.

#### roles

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| name | VARCHAR(255) | Yes | Legacy has 4 roles (likely: user, member, admin, master) |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

#### assessments

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| user_id | UUID (FK) | Yes | References users |
| completed_at | TIMESTAMP | No | NULL if in progress |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

Assessment is the container record. One per attempt. Individual answers and scored results are stored separately.

#### answers (individual question responses)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| assessment_id | UUID (FK) | Yes | References assessments. CASCADE on delete. |
| question_id | UUID (FK) | No | References questions |
| user_id | UUID (FK) | Yes | References users |
| multiple_choice_answer | VARCHAR(255) | No | For selection-type questions (people, causes, abilities) |
| numeric_value | SMALLINT | No | For 1-5 Likert scale ratings |
| text_value | TEXT | No | For Story free-text responses |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

Each row is one user's answer to one question. ~170 rows per completed assessment.

#### assessment_results (scored output)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| assessment_id | UUID (FK) | Yes | References assessments. CASCADE on delete. |
| user_id | UUID (FK) | No | References users |
| gift_1_id | UUID (FK) | Yes | Top spiritual gift. References gifts_passions. |
| spiritual_gift_1_score | SMALLINT | No | Score for top gift (range 4-20) |
| gift_2_id | UUID (FK) | Yes | Second spiritual gift |
| spiritual_gift_2_score | SMALLINT | No | |
| gift_3_id | UUID (FK) | No | Third gift (if tied scores) |
| spiritual_gift_3_score | SMALLINT | No | |
| gift_4_id | UUID (FK) | No | Fourth gift (if tied scores) |
| spiritual_gift_4_score | SMALLINT | No | |
| passion_1_id | UUID (FK) | Yes | Primary influencing style. References gifts_passions. |
| passion_1_score | SMALLINT | No | |
| passion_2_id | UUID (FK) | No | Secondary influencing style |
| passion_2_score | SMALLINT | No | |
| passion_3_id | UUID (FK) | No | Third influencing style (if tied) |
| passion_3_score | SMALLINT | No | |
| people | TEXT | No | Selected people groups (stored as text) |
| cause | TEXT | No | Selected causes (stored as text) |
| abilities | TEXT | No | Selected key abilities (stored as text) |
| story_gift_answer | TEXT | No | Story reflection on spiritual gifts |
| story_ability_answer | TEXT | No | Story reflection on abilities |
| story_passion_answer | TEXT | No | Story reflection on passions |
| story_influencing_answer | TEXT | No | Story reflection on influencing styles |
| story_onechange_answer | TEXT | No | "If God could use your story..." |
| story_closestpeople_answer | TEXT | No | "What would people say you're passionate about?" |
| story_oneregret_answer | TEXT | No | "One regret you want to avoid?" |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

This matches the legacy structure. Gift and passion IDs reference the `gifts_passions` lookup table for names and definitions.

#### gifts_passions (scoring category definitions)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| name | VARCHAR(100) | Yes | e.g., "Administration", "Apostle", "Teacher" |
| short_code | VARCHAR(5) | Yes | e.g., "AD", "AP", "TE". Unique. |
| description | TEXT | Yes | Full definition displayed in results |
| questions | TEXT | Yes | Comma-separated question IDs that map to this gift/passion |
| type_id | UUID (FK) | Yes | References types (Spiritual Gift vs Influencing Style) |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

This is the scoring engine's lookup table. The `questions` field tells the system which questions to sum for each gift/passion category.

#### types

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| name | VARCHAR(100) | Yes | e.g., "Spiritual Gift", "Influencing Style" |
| description | TEXT | Yes | |
| order | SMALLINT | Yes | Display order |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

#### questions

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| question | TEXT | Yes | English question text |
| question_es | TEXT | No | Spanish translation |
| order | INTEGER | Yes | Display sequence |
| passion_type | VARCHAR(255) | No | Sub-categorization for passion questions |
| passion_type_es | VARCHAR(255) | No | Spanish translation of passion_type |
| default | TEXT | No | Default/placeholder text |
| default_es | TEXT | No | Spanish default |
| summary | TEXT | No | Summary text |
| summary_es | TEXT | No | Spanish summary |
| type_id | UUID (FK) | Yes | References types |
| question_type_id | UUID (FK) | Yes | References question_types |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

Spanish translations are stored inline on each question row, matching the legacy pattern.

#### question_types

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| type | VARCHAR(100) | Yes | e.g., "likert", "multiple_choice", "text", etc. |

#### invitations (admin invite tokens)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| sign_up_key | VARCHAR(255) | No | Unique invite token |
| email | VARCHAR(100) | Yes | Invited email address |
| organization_id | UUID (FK) | No | Church they're being invited to |
| expired_at | TIMESTAMP | No | Token expiry |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

Based on legacy `organization_admin_registrations` table.

#### subscriptions (Stripe)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| user_id | UUID (FK) | Yes | References users. Legacy ties billing to the admin user, not the org. |
| name | VARCHAR(255) | Yes | Subscription name/plan |
| stripe_id | VARCHAR(255) | Yes | Stripe subscription ID |
| stripe_status | VARCHAR(255) | Yes | Stripe subscription status |
| stripe_plan | VARCHAR(255) | No | Plan identifier |
| quantity | INTEGER | No | |
| trial_ends_at | TIMESTAMP | No | |
| ends_at | TIMESTAMP | No | Cancellation effective date |
| created_at | TIMESTAMP | Yes | UTC |
| updated_at | TIMESTAMP | Yes | UTC |

#### audit_log (new table, not in legacy)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID (PK) | Yes | System-generated |
| user_id | UUID (FK) | Yes | Who performed the action |
| action | VARCHAR(100) | Yes | e.g., "role_change", "export", "impersonate", "lock_account" |
| target_type | VARCHAR(50) | No | e.g., "user", "organization", "assessment" |
| target_id | UUID | No | ID of the affected record |
| details | JSONB | No | Additional context |
| created_at | TIMESTAMP | Yes | UTC. Append-only, no updates or deletes. |

### 5.2 Data Integrity Rules

- All assessment records are immutable once submitted. No overwrites, no deletions. Soft-delete via status field only.
- If an assessment instrument is updated, store as a new version. Prior results are never recalculated.
- User merge/de-duplication: if a user registers with an email that matches an existing deleted or invited record, merge into a single account preserving all historical data. Log every merge in audit_log.
- All timestamps stored in UTC. No timezone conversion in the database layer.
- All admin actions logged in the audit_log table (append-only).
- The scoring engine reads question-to-gift mappings from the `gifts_passions.questions` field, not from hardcoded logic. This makes the instrument data-driven and extensible.

### 5.3 Legacy Schema Mapping

For migration reference, here is how legacy MySQL tables map to the new schema:

| Legacy Table | New Table | Notes |
|-------------|-----------|-------|
| users | users | Add locale field, map auto-increment IDs to UUIDs |
| organizations | organizations | Rename concept to "churches" in UI only; table keeps legacy name for migration simplicity |
| memberships | memberships | Direct port with UUID conversion |
| roles | roles | Direct port |
| assessments | assessments | Direct port |
| answers | answers | Direct port; ~4.6M rows |
| assessment_results | assessment_results | Direct port; gift/passion IDs map to gifts_passions |
| gifts_passions | gifts_passions | Direct port; scoring definitions |
| types | types | Direct port |
| questions | questions | Direct port; includes Spanish translations |
| question_types | question_types | Direct port |
| organization_admin_registrations | invitations | Rename; same structure |
| subscriptions | subscriptions | Direct port (Laravel Cashier format) |
| subscription_items | subscription_items | Direct port if needed |
| password_reset_tokens | password_reset_tokens | Direct port |
| webhooks | webhooks | Port if webhook integrations are needed |
| failed_jobs, jobs, migrations, operations, sessions | Not migrated | Laravel framework tables |

---

## 6. Data Migration Plan

The migration moves all historical data from the legacy MySQL database to the new PostgreSQL instance. Legacy database contains ~31,600 users, ~42,400 assessments, ~4.6M individual answers, ~27,200 scored results, and ~169 organizations. This is a one-time operation with a final sync at cutover.

1. **Export:** Full MySQL dump from Doug Niccum (backup-20260322-221322.sql.gz, 63MB compressed / 356MB uncompressed). Already obtained.
2. **ID Mapping:** Legacy uses auto-increment bigint IDs. New system uses UUIDs. Build a mapping table (legacy_id -> new_uuid) for each entity to preserve all foreign key relationships during migration.
3. **ETL Script:** Python script that reads the MySQL dump and inserts into PostgreSQL. Core table migration order (respecting foreign keys): types -> question_types -> roles -> organizations -> users -> questions -> gifts_passions -> memberships -> assessments -> answers -> assessment_results -> invitations -> subscriptions.
4. **Validation:** For a representative sample of users (including Brian's 3 known assessments: IDs 549, 1911, 26169), verify that scored results in the new database match the legacy PDF reports.
5. **Final Sync:** Immediately before DNS cutover, run the migration script one final time to capture any users/assessments created since the initial migration.
6. **DNS Switch:** Point assessments.giftpassionstory.com to Render via GoDaddy DNS.
7. **Archive:** Decommission the legacy Laravel/AWS server. Retain a read-only backup for 90 days.

---

## 7. Development Phases

| Phase | Name | Deliverables | Payment Milestone |
|-------|------|-------------|-------------------|
| 1 | Analysis & Setup | Code review of legacy scoring logic; repo initialization; database provisioning; environment setup | $1,100 (Initial Deposit) |
| 2 | Data Migration | ETL script; MySQL-to-PostgreSQL migration; validation against legacy PDF reports | Included in Phase 1 |
| 3 | Backend Build | API endpoints; GPS scoring engine; MyImpact scoring engine; PDF generation service; email integration | $2,200 (Migration) |
| 4 | Frontend Build | Assessment UI; personal dashboard; church admin dashboard; master admin dashboard; Stripe billing integration | Included in Phase 3 |
| 5 | Cutover & Handoff | Final data sync; DNS switch; legacy server decommission; documentation and training | $550 (Final Payment) |

---

## 8. Non-Functional Requirements

- **Performance:** All dashboards and paginated results must load in under 2 seconds for up to 1,000 rows. Assessment forms must load in under 3 seconds. Use skeleton loaders (not spinners) for loading states on all data-heavy screens.
- **Responsiveness:** All screens must be fully functional at 320px mobile width through desktop. Touch targets minimum 44px.
- **Audit:** All sensitive admin actions logged with who/when/what in an immutable audit table. Impersonation sessions logged with time, target user, and reason.
- **Data Privacy:** Church admins can only see data for their affiliated members. Unlinking a member immediately revokes admin access to that user's data. Master admin has cross-church access.
- **Accessibility:** WCAG 2.1 AA compliance for all public-facing screens. Keyboard navigation, screen reader support, sufficient color contrast.

## 8.1 Security

### Authentication
- Auth is fully owned by FastAPI (not delegated to any third-party auth provider).
- Passwords hashed with bcrypt via passlib (cost factor 12).
- JWTs issued by FastAPI on login. Short-lived access tokens (15-30 minutes) plus longer-lived refresh tokens (7 days).
- Refresh tokens stored in the database so they can be revoked (on password change, account lock, or logout).
- Access tokens sent via Authorization header. Refresh tokens stored in httpOnly, Secure, SameSite=Lax cookies (not accessible to JavaScript, preventing XSS token theft).
- FastAPI dependency injection enforces auth on every protected route: `get_current_user` validates the JWT and loads the user; `require_admin` and `require_master` add role checks on top.

### Rate Limiting
- Auth endpoints (login, registration, password reset) rate-limited to prevent brute force. 5 failed attempts per email per 15 minutes, then temporary lockout.
- Implemented via slowapi or custom middleware in FastAPI.

### Data Isolation
- No multi-tenancy. Single shared database, shared schema. Church isolation enforced at the application layer via `church_id` filtering on every query.
- Every FastAPI endpoint that returns user or assessment data filters by `church_id` matching the requesting user's church. This is enforced in the backend regardless of what the frontend sends.
- Master admin endpoints bypass church filtering but are gated behind `require_master` dependency.

### Input Validation
- All request bodies validated via Pydantic schemas before route code executes. Email fields validated as emails, strings have max lengths, enums only accept defined values.
- SQLAlchemy ORM used for all database queries (parameterized queries, no raw SQL string concatenation). Prevents SQL injection.

### Transport Security
- HTTPS enforced on all endpoints. Render provides automatic SSL certificates.
- CORS configured to only accept requests from the frontend's domain (no wildcard origins).

### Stripe Security
- All incoming Stripe webhooks verified against the webhook signing secret before processing. Unverified webhooks are rejected.

### Secret Management
- All secrets (database URL, JWT signing key, Stripe keys, Resend API key) stored as environment variables on Render. Never committed to code or version control.
- `.env` file used for local development only, included in `.gitignore`.

### Soft Deletes
- Users and assessments are never hard-deleted. Status field set to "deleted" but row preserved for data integrity and audit trails.

---

## 9. Open Questions & Risks

### Resolved:
- ~~Scoring rubrics needed~~ — Brian provided the full GPS Word Doc with all 76 gift questions, 80 influencing style questions, scoring mappings, and definitions. Scoring is straightforward addition (sum of 1-5 ratings per category), not weighted normalization.
- ~~Legacy codebase access~~ — Brian connected developer Doug Niccum (doug@dniccumdesign.com) who built and maintains the Laravel platform. Code and database access requested.
- ~~Stripe billing structure~~ — $10/month or $100/year for church admin accounts. No free trial. Individual assessment is free. Some churches get comp access (billed through other Disciples Made services).
- ~~Legacy PDF reports~~ — Brian provided 3 sample results. These are browser-rendered HTML pages, not server-generated PDFs. The results page needs print-friendly styling.
- ~~GoDaddy access~~ — Brian confirmed he has access for DNS changes at cutover.

### Still Open:
1. The original PRD references multi-church membership (many-to-many) but business rules enforce single-church. This document assumes single-church. Product owner should confirm.
2. MyImpact Equation exists as a Typeform at gofullyalive.typeform.com/MyImpact. Brian is unsure whether to embed Typeform or rebuild natively. Decision needed, but can be deferred past MVP.
3. Spanish localization exists in the current system (results display in Spanish for Spanish-speaking users). Confirm whether this is required for the rebuild or can be deferred.
4. The "select-package" flow on the legacy site suggests existing tiered access. Confirm with Doug what this does and whether it maps to the new Stripe billing model.
5. The $3,500 base project fee is tight relative to the full scope. Developer should confirm scope-to-budget alignment with Michael before starting.

### Deferred to Post-MVP:
- **48-hour revert button for admin actions.** The original Bubble PRD specified that admin actions should be revertible within 48 hours via a button in the audit log. This adds significant complexity (each action type needs custom undo logic). The audit log provides full visibility; manual correction by master admin covers the same need. Revisit if Brian specifically requests it.
