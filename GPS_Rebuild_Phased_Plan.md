# GPS Platform Rebuild: Phased Development Plan

**Project:** GPS Assessment Platform (Disciples Made, Inc.)
**Developer:** Paschal Okonkwo
**Consultant:** ClickDown, LLC (Michael Greenberg)
**Date:** March 23, 2026
**Tooling:** Claude Code / Kimi Code + FastAPI (Python) + React + PostgreSQL + Render

---

## How to Use This Plan

Each phase is designed to produce a **demo-able deliverable**. This means you can show Michael and Brian working software at the end of every phase, collect feedback early, and avoid building the wrong thing for weeks. The phases are ordered by dependency: each one builds on the last, and nothing is wasted if scope changes.

The estimated timelines assume you're using AI coding tools (Claude Code, Kimi Code, or similar) for scaffolding, boilerplate, and pattern implementation, while doing the product thinking, scoring logic, and validation yourself.

---

## Phase 0: Prerequisites (Before You Write Any Code)

**Duration:** 3-5 days
**Payment Milestone:** None (this is pre-work)
**Goal:** Gather everything you need so you don't stall mid-build.

### Current Status (as of March 23, 2026):
- Initial invoice ($1,100) has been paid by Brian (March 17)
- Brian intro'd Doug Niccum (doug@dniccumdesign.com), the original Laravel developer (March 21)
- Brian asked Doug to provide codebase access and database backup; Doug instructed to invoice Brian for time
- Database dump received and schema analyzed: backup-20260322-221322.sql.gz (63MB compressed, 356MB uncompressed, 21 tables, ~31,600 users, ~42,400 assessments, ~4.6M answers, ~27,200 results, ~169 organizations). Full legacy-to-new table mapping completed. See PRD Section 5.3.
- Brian provided GPS question set and scoring rubric as Word doc (all 76 gift questions, 80 influencing style questions, scoring mappings, definitions)
- Brian provided 3 sample assessment result pages (assessment IDs 549, 1911, 26169) as browser-printed PDFs
- Stripe billing confirmed: $10/month or $100/year, no free trial, individuals free, comp tier for partner churches
- Brian confirmed GoDaddy access for DNS changes
- MyImpact Equation: exists as Typeform (gofullyalive.typeform.com/MyImpact), Brian unsure whether to embed or rebuild. Deferred.
- Figma designs in progress; Brian's designer creating phone and tablet versions
- Kickoff meeting planned once Figma files are ready
- Laravel codebase access still pending from Doug

### What is still needed:

1. **Legacy Laravel codebase access**
   - Doug Niccum has been asked to provide this. Awaiting response.
   - Needed to extract the exact PHP scoring logic for validation against our Python port.
   - Not a hard blocker for starting: we have the scoring rubric from Brian's Word doc and the database schema from the dump. The Laravel code is needed for validation, not for building.

2. **Figma design files**
   - Brian's designer is working on these. Desktop first, then phone and tablet.

3. **Clarifications from Brian (can be async)**
   - Is Spanish localization required for the rebuild? (Legacy supports it)
   - What does the "select-package" flow do in the legacy system?
   - Confirm single-church membership as the business rule (legacy data has some multi-church cases)

### What to set up yourself:

- **GitHub repo** initialized as a monorepo with `/api` (FastAPI) and `/web` (React) directories
- **Render account** with three services: a Web Service for FastAPI backend, a Static Site for React frontend, and a PostgreSQL database, all on the same platform
- **Stripe test account** with test API keys
- **Resend account** for transactional email (free tier: 100 emails/day)
- **Python virtual environment** with FastAPI, uvicorn, SQLAlchemy, alembic, pydantic, stripe, resend, passlib[bcrypt], PyJWT, slowapi

### Deliverable:
A running FastAPI backend, React frontend, and PostgreSQL database, all deployed on Render, with a basic project structure. No features yet, but the plumbing works.

---

## Phase 1: Auth + Database Schema + User Registration

**Duration:** 5-7 days
**Payment Milestone:** $1,100 (Initial Deposit) - PAID March 17, 2026
**Goal:** Users can register, log in, and see a skeleton dashboard.

### Why start here:
Everything in the platform depends on knowing *who the user is* and *what role they have*. Authentication is the foundation. Build it first and every subsequent phase just adds features on top of an already-working auth system.

### Tasks:

**Database (Render PostgreSQL):**
- Create tables matching the legacy-informed schema: `users`, `organizations`, `memberships`, `roles`, `assessments`, `answers`, `assessment_results`, `gifts_passions`, `types`, `questions`, `question_types`, `invitations`, `subscriptions`, `audit_log`
- Data isolation enforced at the FastAPI application layer via membership/organization_id filtering on every query.
- Seed `roles` table with 4 roles (user, member, admin, master)
- Seed `types` table (Spiritual Gift, Influencing Style)
- Seed `question_types` table (likert, multiple_choice, text)
- Seed `gifts_passions` table with all 19 spiritual gifts and 5 influencing styles (names, short_codes, descriptions, question mappings from Brian's Word doc)
- Seed `questions` table with all 76 gift questions, 80 influencing style questions, selection lists, and story prompts (English + Spanish from legacy data)
- Seed with test data (3 organizations, 10 users across roles)

**Auth (FastAPI-owned):**
- Registration endpoint: hash password with bcrypt (passlib), create user record, issue JWT access token + refresh token
- Login endpoint: verify credentials, issue tokens
- Password reset flow: generate reset token, send email via Resend, verify token and update password
- Invite token system: church admin creates invite, system generates unique token, invited user registers via token URL and is auto-affiliated with the church
- JWT access tokens (15-30 min expiry) sent in Authorization header. Refresh tokens (7 day expiry) stored in httpOnly cookie and in database for revocation.
- FastAPI dependencies: `get_current_user`, `require_admin`, `require_master` for route-level auth enforcement
- Rate limiting on auth endpoints via slowapi (5 failed attempts per email per 15 minutes)

**Frontend:**
- Registration page: First Name, Last Name, Email, Password, Phone (optional), Church selector (searchable dropdown) or "Independent"
- Login page
- Password reset page
- Basic dashboard shell (sidebar nav, top bar with user info, empty content area)
- Role-based routing: redirect users to the right dashboard after login
- Store access token in memory, refresh token handled via httpOnly cookie

**AI coding tool leverage:**
This is where Claude Code shines. Scaffold the FastAPI project structure with routers, Pydantic models, and SQLAlchemy schemas. Generate the auth endpoints (registration, login, password reset, token refresh) with bcrypt and PyJWT. Build the React auth pages with form validation. Have the AI tool generate the FastAPI dependency chain (`get_current_user` -> `require_admin` -> `require_master`). Most of this is well-known patterns.

### Deliverable:
A deployed app where users can register (as independent or affiliated with a church), log in, and see their role-appropriate dashboard (empty but functional). Church admins see an admin layout. Master admins see a master layout.

### Demo points:
- Register a new user, log in, see the dashboard
- Register as independent, then as church-affiliated; show the different experiences
- Show that a church admin logging in sees a different layout than a regular user

---

## Phase 2: GPS Assessment Engine (Core Feature)

**Duration:** 7-10 days
**Goal:** Users can take the GPS assessment and see their results.

### Why this phase is critical:
The GPS assessment IS the product. Everything else (dashboards, exports, admin tools) exists to support this. If you nail the assessment flow and scoring engine, the project is 60% done conceptually.

### Tasks:

**Scoring Engine (Backend - FastAPI):**
- Port the GPS scoring algorithm from PHP to Python
  - 76 gift questions: each maps to one of 19 categories (4 questions per gift). Sum the 1-5 ratings per category. Score range: 4-20 per gift. Top 2 scores become the user's identified gifts.
  - 80 influencing style questions: each maps to one of 5 styles. Sum per style. Top score = primary, second = secondary.
  - No normalization or weighting. This is basic arithmetic.
- Write unit tests (pytest) that validate against Brian's sample results
  - Brian's 2/29/2024 assessment: Knowledge=19, Teaching=19, Wisdom=19, Discernment=17. Teacher=88, Apostle=85.

**Assessment Form (Frontend):**
- Multi-step wizard: one question per screen
- Progress indicator ("Question 3 of 25")
- Required field validation with inline error messages
- Mobile-responsive (44px minimum touch targets)
- Deep link support: accept `?member_id=X&church_id=Y` URL params

**Result Storage:**
- On submission: store raw answers (JSONB) and scored results (JSONB) as a new row in `assessments` table
- Never overwrite; retakes create new rows

**Result Display:**
- Result page after submission: gift scores with definitions, influencing styles with definitions, selected abilities/people/causes, and story responses
- Print-friendly CSS so the page looks good when printed from browser (this is how the legacy system works)
- "Return to Dashboard" button

**AI coding tool leverage:**
The React form wizard, progress indicator, and validation are pure frontend patterns; AI tools will produce these quickly. For the scoring engine, paste the legacy PHP code into Claude Code and ask for a Python port with pytest tests. The AI will handle the translation, but *you* need to verify the math against legacy output.

### Deliverable:
A user can log in, take the GPS assessment, submit it, and see their scored results with a graph and text summary. Results are stored in the database.

### Demo points:
- Walk through the full assessment as a user
- Show the result page with scoring graph
- Show that the scores match a legacy PDF report (this is your proof of correctness)

---

## Phase 3: Personal Dashboard + Assessment History

**Duration:** 4-5 days
**Goal:** Users can view all their past assessments and compare results over time.

### Why this order:
Before you build admin dashboards that *view other people's data*, build the personal dashboard that views *your own data*. The component patterns (tables, graphs, filtering, detail views) you build here get reused directly in the admin dashboards.

### Tasks:

**Dashboard:**
- Summary cards: most recent assessment result per instrument, with mini graph, score highlights, and date
- Instrument tabs: GPS tab shows chronological table of all past assessments
- Clickable rows open full detail view (graph + text + raw scores)
- "Retake Assessment" button per instrument

**History & Comparison:**
- Historical timeline table: sortable by date
- Side-by-side comparison view for two assessments (color-highlighted diffs)
- "Growth journey" vertical step sequence under timeline

**Export & Print:**
- "Export CSV" button: exports the logged-in user's own assessment history
- "Print" button: browser print dialog with print-optimized CSS

**Church Linking UI:**
- For independent users: "Join a Church" card with searchable church list and request-to-link flow
- For members: display church affiliation with "Leave Church" option
- "Upgrade to Church Admin" card for eligible users

**AI coding tool leverage:**
Dashboard components, data tables with sorting/filtering, and chart rendering (recharts or Chart.js) are all patterns AI tools handle well. The comparison/diff view is slightly more custom but still well within AI-assisted territory.

### Deliverable:
A user's personal dashboard is fully functional: summary cards, history tables, detail views, comparison tool, export, print, and church linking UI.

---

## Phase 4: Church Admin Dashboard

**Duration:** 7-10 days
**Payment Milestone:** $2,200 (Migration payment)
**Goal:** Church admins can manage their members, view assessment data, and invite new users.

### Why this is the longest phase:
The church admin dashboard has the most features of any single screen: member table with search/sort/filter, invite system with batch email + CSV upload, pending approval queue, role management, member detail panel, and the unique assessment link generator. It's feature-dense.

### Tasks:

**Member Management Table:**
- Columns: First Name, Last Name, Email, Status, Assessment Completion, Last Assessment Date, Instruments Taken, Role
- Search bar (name or email)
- Column sorting and multi-select filters (persistent across refresh)
- Pagination (50 per page) with item count display
- Bulk action checkboxes

**Invite System:**
- Invite modal: manual email entry (batch) + CSV file upload
- Email validation and duplicate detection
- Send invitations via Resend with unique invite tokens
- Status tracking: color-coded (green/yellow/red/grey)
- Resend invite capability

**Church Affiliation Management:**
- Pending member requests queue (approve/decline)
- Unique church assessment link generation (with copy-to-clipboard)
- Make admin / remove admin controls with confirmation dialogs

**Member Detail Panel:**
- Slide-in panel from right side
- Chronological assessment history for selected member
- Single-user CSV export, print, and note-adding

**Results Email (FastAPI backend):**
- On assessment completion, send email via Resend with a link to the user's results page
- Results page already has print-friendly CSS from Phase 2
- If Brian later wants server-generated PDFs, this can be added as an enhancement using ReportLab/WeasyPrint

**AI coding tool leverage:**
Heavy AI usage here. The member table with sorting/filtering/pagination is a well-known pattern. The invite modal, slide-in panel, and confirmation dialogs are all standard UI components. PDF generation is the trickiest part; have the AI tool scaffold the layout, but expect to iterate on styling manually.

### Deliverable:
A church admin can log in, see their member list, invite new members (email or CSV), approve link requests, view any member's assessment history, export data, and generate PDF reports.

---

## Phase 5: Master Admin Dashboard + Audit System

**Duration:** 4-5 days
**Goal:** Master admin has full system visibility and control.

### Why this is relatively fast:
Most of the components already exist from Phases 3 and 4. The master admin dashboard reuses the same table/filter/export patterns but with cross-church scope. The main new work is impersonation and the audit log viewer.

### Tasks:

**System Dashboard:**
- Summary metrics: total churches, users, assessments (30/90/365 day windows)
- Church table: name, admins, active users, assessments per instrument, last activity
- Sort, filter, search on all columns

**Church & User Management:**
- Add/remove church admins via modal with confirmation
- Promote/demote any user across the system
- Resolve affiliation conflicts

**Impersonation:**
- Secure pop-out window showing the platform as the target user
- Mandatory reason field before impersonation starts
- Full logging: admin ID, target user, timestamp, reason

**Audit Log:**
- Immutable log viewer for all sensitive actions
- Filterable by action type, user, date range
- Exportable as CSV

**AI coding tool leverage:**
Mostly reusing existing components with broader data scope. The impersonation feature requires some careful session management logic, but the UI is straightforward.

### Deliverable:
Master admin can view system-wide metrics, manage churches and users, impersonate accounts for troubleshooting, and review the full audit trail.

---

## Phase 6: Stripe Billing Integration

**Duration:** 4-5 days
**Goal:** Church accounts have subscription billing.

### Why this is its own phase:
Billing is important but decoupled from the core assessment functionality. By isolating it, you can launch the platform without billing if needed (useful for testing with real churches) and add it when the pricing structure is finalized.

### Tasks:

**Stripe Integration:**
- Stripe Checkout for new subscriptions (monthly/annual)
- Customer portal for payment method management
- Webhook handler for subscription events (payment succeeded, failed, canceled)
- Grace period logic: if payment fails, show warning banner; after 14 days, restrict to read-only

**Admin Dashboard Billing Section:**
- Current plan display (monthly/annual, next billing date)
- "Manage Payment Method" button (redirects to Stripe portal)
- "Change Plan" option (monthly/annual toggle)
- "Cancel Subscription" with confirmation dialog

**Access Gating:**
- Church admin dashboard features gated behind active subscription
- Appropriate messaging for expired/canceled subscriptions

**AI coding tool leverage:**
Stripe integration is extremely well-documented and AI tools have seen it many times. The webhook handler, checkout flow, and customer portal redirect are all standard patterns. The access gating logic is simple middleware.

### Deliverable:
Church admins can subscribe, manage their payment method, switch plans, and cancel. The system correctly gates features based on subscription status.

---

## Phase 7: Data Migration + MyImpact Equation

**Duration:** 5-7 days
**Goal:** Legacy data is migrated; second assessment instrument is live.

### Why migration is this late:
You want to migrate INTO a system that's fully built and tested. If you migrate data in Phase 1, every schema change in subsequent phases requires re-running and re-validating the migration. By migrating last, you do it once correctly.

### Tasks:

**Data Migration:**
- Legacy MySQL dump already obtained and schema analyzed (21 tables, 356MB uncompressed). Legacy-to-new table mapping completed in PRD Section 5.3.
- Python ETL script reads the dump and inserts into Render PostgreSQL
- Build ID mapping tables: legacy bigint auto-increment IDs -> new UUIDs for all entities
- Migration order (respecting foreign keys): types -> question_types -> roles -> organizations -> users -> questions -> gifts_passions -> memberships -> assessments -> answers (~4.6M rows, largest table) -> assessment_results -> invitations -> subscriptions
- Handle edge cases: users with NULL names or emails, memberships with NULL organization_id, duplicate emails across deleted/active records
- Validate Brian's 3 known assessments (IDs 549, 1911, 26169) against his sample result pages
- Skip Laravel framework tables: failed_jobs, jobs, migrations, operations, sessions
- Document any data quality issues found during migration

**MyImpact Equation (if spec is available):**
- Implement MyImpact scoring engine (same pattern as GPS, different math)
- Add MyImpact questions to the assessment form
- Instrument switcher tab on assessment screen
- MyImpact results display on personal dashboard
- MyImpact data in admin dashboards and CSV exports

**If MyImpact spec is NOT available:**
- Skip it. Flag it as deferred. Don't build what isn't defined.
- The architecture supports adding it later without any rewrite.

### Deliverable:
Legacy data is in the new system. Users can see their historical assessments. If MyImpact is specified, it's live as a second instrument.

---

## Phase 8: Cutover + Polish + Handoff

**Duration:** 3-5 days
**Payment Milestone:** $550 (Final Payment)
**Goal:** Production launch.

### Tasks:

**Final Migration Sync:**
- Run ETL script one final time to capture any new users/assessments since initial migration
- Validate final data set

**DNS Cutover:**
- Point production domain to Render
- Verify SSL certificate
- Test all flows on production domain

**Legacy Decommission:**
- Archive the Laravel server (read-only backup retained 90 days per consulting agreement)
- Confirm no traffic hitting old server

**Documentation:**
- Admin guide: how to use church admin and master admin dashboards
- Technical documentation: environment setup, deployment process, database schema
- Handoff meeting with Michael and Brian

**Polish:**
- Address any feedback from demo sessions
- Performance optimization (lazy loading, image optimization, query optimization)
- Cross-browser testing (Chrome, Safari, Firefox, mobile browsers)
- Accessibility audit (keyboard navigation, screen reader, color contrast)

### Deliverable:
Production system is live, legacy server is archived, documentation is delivered, handoff is complete.

---

## Timeline Summary

| Phase | Name | Duration | Running Total |
|-------|------|----------|---------------|
| 0 | Prerequisites | 3-5 days | Week 1 |
| 1 | Auth + Schema + Registration | 5-7 days | Week 2 |
| 2 | GPS Assessment Engine | 7-10 days | Week 3-4 |
| 3 | Personal Dashboard + History | 4-5 days | Week 5 |
| 4 | Church Admin Dashboard + PDF | 7-10 days | Week 6-7 |
| 5 | Master Admin + Audit | 4-5 days | Week 7-8 |
| 6 | Stripe Billing | 4-5 days | Week 8-9 |
| 7 | Data Migration + MyImpact | 5-7 days | Week 9-10 |
| 8 | Cutover + Handoff | 3-5 days | Week 10-11 |

**Total estimated: 8-11 weeks** (solo developer with AI coding tools)

---

## AI Tooling Strategy: What to Prompt For vs What to Do Yourself

### Let AI tools handle:
- FastAPI project scaffolding: routers, Pydantic models, SQLAlchemy schemas, alembic migrations
- Alembic migration files and SQLAlchemy model definitions
- React form components (registration, assessment wizard, invite modals)
- Dashboard layouts with tables, sorting, filtering, pagination
- Stripe checkout and webhook boilerplate (Python SDK)
- CSV export logic (Python csv module)
- Email templates and Resend integration
- pytest test scaffolding for API endpoints
- FastAPI CRUD route handlers
- Tailwind/shadcn component styling

### Do these yourself:
- Scoring engine validation (verify math against legacy PDFs)
- Data migration validation (compare migrated data against source)
- Product decisions (resolve PRD contradictions with Michael/Brian)
- Security review (RLS policies, auth edge cases, JWT validation middleware)
- PDF report styling (iterative visual matching against legacy reports)
- Stripe webhook edge cases (failed payments, subscription state transitions)
- Final cross-browser and accessibility testing

### Prompting tips for this project:
- When scaffolding, give Claude Code the full Pydantic data models upfront so it generates consistent schemas across all routers
- For the scoring engine: paste the PHP source code and ask for a Python port with pytest tests
- For dashboard components: describe the exact column set, filter behavior, and action buttons; AI tools produce better results with specific UI specs than vague descriptions
- For Stripe: reference Stripe's official Python/FastAPI examples; AI tools will use current patterns instead of deprecated ones
- For the React frontend: feed it the Figma designs (when available) and ask for component-by-component implementation

---

## Risk Register

| Risk | Likelihood | Impact | Status | Mitigation |
|------|-----------|--------|--------|------------|
| ~~Scoring rubric not provided~~ | ~~High~~ | ~~Critical~~ | RESOLVED | Brian provided GPS Word Doc with full question set and scoring mappings. |
| ~~Legacy codebase access~~ | ~~Medium~~ | ~~Critical~~ | PARTIALLY RESOLVED | Doug Niccum intro'd. Database dump received and analyzed (356MB, 21 tables). Laravel source code still pending from Doug, needed for scoring engine validation. |
| ~~Stripe pricing not defined~~ | ~~Medium~~ | ~~Low~~ | RESOLVED | $10/month or $100/year. No trial. Individuals free. Comp tier for partner churches. |
| MyImpact Equation has no spec | High | Medium | OPEN | Defer to post-launch. Architecture supports it. Typeform exists but no scoring rubric. |
| Budget insufficient for full scope | High | High | OPEN | Discuss with Michael before starting. Consider phased billing. |
| Multi-church vs single-church | Medium | Medium | OPEN | Legacy `memberships` table supports multi-church, but business rule says single. Assume single-church, enforce at application layer. |
| Legacy data quality issues | Medium | Medium | OPEN | Legacy has ~31K users, ~4.6M answers. Some users have NULL names/emails. Build validation report during migration. |
| Spanish localization | Medium | Medium | OPEN | Legacy has full Spanish translations in questions table. Confirm with Brian whether required for rebuild. |
| Legacy Stripe billing tied to users, not orgs | Low | Medium | OPEN | Legacy `subscriptions` table references user_id, but `organizations` also has stripe_id. Clarify intended billing model with Brian/Doug. |
