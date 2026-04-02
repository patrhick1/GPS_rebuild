# Laravel → PostgreSQL Migration Guide

This guide covers every step required to migrate data from the legacy Laravel/MySQL GPS application into the new FastAPI/PostgreSQL application.

---

## Overview

| Item | Legacy (Laravel) | New (FastAPI) |
|------|-----------------|---------------|
| Database | MySQL / MariaDB | PostgreSQL |
| Primary keys | Auto-increment integers | UUIDs |
| Auth | Session-based | JWT (access + refresh tokens) |
| Passwords | bcrypt `$2y$` | bcrypt `$2y$` carried over (passlib compatible) |
| Subscriptions | User-level, gold/silver/platinum tiers | Org-level, monthly ($10) or yearly ($100) |
| Roles | User, Group Leader, Org Admin, Super Admin | user, member, admin, master |

**Record counts (from reference backup):**

| Table | Rows |
|-------|------|
| users | ~31,600 |
| organizations | ~168 |
| memberships | ~38,300 |
| assessments | ~42,500 |
| assessment_results | ~27,200 |
| answers | ~4,682,000 |
| invitations | ~49 |

---

## Prerequisites

### 1. Production MySQL database access

You need live access to the production MySQL/MariaDB database, not just a backup file.
Have the following ready:

```
Host:     <mysql-host>
Port:     3306
Database: <database-name>
User:     <user>
Password: <password>
```

### 2. PostgreSQL database running

The new PostgreSQL database must be provisioned and accessible.
Confirm you can connect with your `DATABASE_URL`.

### 3. Python environment set up

```bash
cd api
pip install -r requirements.txt
```

This includes `PyMySQL` (MySQL driver) and `psycopg2-binary` (PostgreSQL driver).

### 4. Environment variables

Create or update `api/.env` with both database URLs:

```env
# New PostgreSQL database (already in use)
DATABASE_URL=postgresql://user:password@host:5432/gps_production

# Legacy MySQL database
LEGACY_DB_URL=mysql+pymysql://user:password@host:3306/legacy_database_name
```

---

## Step 1 — Run Alembic migrations (schema)

Ensure the PostgreSQL schema is fully up to date before loading any data.

```bash
cd api
python -m alembic upgrade head
```

Expected output: `Running upgrade ... -> b3c1d2e4f5a6`
This confirms all tables exist including the latest columns (`is_comped`, `is_primary_admin`, MyImpact tables, etc.).

Verify the current head:

```bash
python -m alembic current
# Should show: b3c1d2e4f5a6 (head)
```

---

## Step 1b — Clear test data (production migrations only)

If the PostgreSQL database was previously used for development/testing, it will contain seed test records (`test-church-1`, `user1@test.com`, `master@test.com`, etc.). These are **not deleted by the migration script** — they will remain alongside real migrated data.

Before a production migration, clear them manually:

```sql
-- Wipe all user data (cascades to memberships, assessments, answers, results)
TRUNCATE TABLE answers, assessment_results, assessments, memberships,
               invitations, subscriptions, refresh_tokens,
               audit_log, password_reset_tokens,
               users, organizations RESTART IDENTITY CASCADE;
```

> Skip this step for development/staging runs where test data is acceptable.

---

## Step 2 — Seed reference data

The migration script depends on reference data already being present in PostgreSQL (roles, question types, gifts/passions, questions). Run the seed script:

```bash
cd api
python -m app.db_seed
```

Confirm these tables are populated before continuing:

```sql
SELECT COUNT(*) FROM roles;          -- should be 4 (user, member, admin, master)
SELECT COUNT(*) FROM types;          -- should be 3
SELECT COUNT(*) FROM question_types; -- should be 3+
SELECT COUNT(*) FROM gifts_passions; -- should be 24
SELECT COUNT(*) FROM questions;      -- should be 167+
```

---

## Step 3 — Run the migration script

```bash
cd api
python -m scripts.migrate_from_laravel
```

The script runs 8 phases in order. Each phase is idempotent — records are skipped if they already exist.

### Phase breakdown

| # | Phase | Source table | Target table | Notes |
|---|-------|-------------|-------------|-------|
| 0 | Build lookup maps | PostgreSQL (already seeded) | — | Loads roles, gifts, questions into memory |
| 1 | Organizations | `organizations` | `organizations` | Drops old package tier; sets `status='active'`, `is_comped=false` |
| 2 | Subscriptions | — | `subscriptions` | Creates one yearly/$100 subscription per org; no Stripe IDs yet |
| 3 | Users | `users` | `users` | Carries `$2y$` bcrypt hashes as-is; sets `status='active'` |
| 4 | Memberships | `memberships` | `memberships` | Remaps roles (see table below); sets first admin as `is_primary_admin=true` |
| 5 | Assessments | `assessments` | `assessments` | All set to `instrument_type='gps'`; status inferred from `completed_at` |
| 6 | Assessment results | `assessment_results` | `assessment_results` | Resolves old integer gift/passion IDs to new UUIDs via `short_code` |
| 7 | Answers | `answers` | `answers` | Batched in chunks of 10,000 rows |
| 8 | Invitations | `organization_admin_registrations` | `invitations` | Sets `status='expired'` for past-due records |

### Role mapping

| Old role (Laravel) | New role |
|--------------------|----------|
| User | `user` |
| Group Leader | `member` (role dropped; demoted) |
| Organization Administrator | `admin` |
| Super Administrator | `master` |

### Password compatibility

Laravel stores passwords as `$2y$10$...` bcrypt hashes. Python's `passlib` library accepts `$2y$` and `$2b$` variants interchangeably. No password resets are required — users log in normally after migration.

---

## Step 4 — Verify the migration

Run these queries against PostgreSQL to confirm record counts match the legacy database.

```sql
-- Core counts
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM organizations;
SELECT COUNT(*) FROM memberships;
SELECT COUNT(*) FROM assessments;
SELECT COUNT(*) FROM assessment_results;
SELECT COUNT(*) FROM answers;
SELECT COUNT(*) FROM invitations;

-- Every org should have exactly one subscription
SELECT COUNT(*) FROM subscriptions;
-- All should be yearly at $100
SELECT plan, unit_amount, COUNT(*) FROM subscriptions GROUP BY plan, unit_amount;

-- Check role distribution
SELECT r.name, COUNT(m.id)
FROM memberships m
JOIN roles r ON r.id = m.role_id
GROUP BY r.name;

-- No 'group_leader' role should exist
SELECT * FROM roles WHERE name = 'group_leader';  -- should return 0 rows

-- Each org should have at least one primary admin
SELECT o.name, COUNT(m.id) as primary_admins
FROM organizations o
JOIN memberships m ON m.organization_id = o.id
WHERE m.is_primary_admin = true
GROUP BY o.name
ORDER BY primary_admins;

-- Spot-check a known user password login via the API (see Step 5)
```

---

## Step 5 — Smoke test user login

Pick a known user from the legacy system and confirm they can log in with their original password:

```bash
curl -X POST https://your-api-domain/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "known@email.com", "password": "their_original_password"}'
```

Expected: `200 OK` with `access_token` and `refresh_token`.

---

## Step 6 — Link Stripe subscriptions

After migration, all org subscriptions exist in the database with `stripe_customer_id = NULL`.
You will need to manually link each active paying organization to their existing Stripe customer:

1. Log into the [Stripe Dashboard](https://dashboard.stripe.com/customers)
2. For each org, find their Stripe Customer ID (`cus_...`)
3. Update the subscription record:

```sql
UPDATE subscriptions
SET stripe_customer_id     = 'cus_xxxxx',
    stripe_subscription_id = 'sub_xxxxx',
    stripe_price_id        = 'price_xxxxx'
WHERE organization_id = (
    SELECT id FROM organizations WHERE key = 'church-slug'
);
```

Or use the admin UI / master endpoints once fully deployed.

---

## Step 7 — Comp any organizations (if needed)

If certain organizations should bypass Stripe billing entirely (sponsored, partner orgs, etc.), a master admin can comp them via the API:

```
PUT /master/churches/{org_id}/comp
```

This sets `is_comped = true` on the organization and writes to the audit log.
Comped orgs bypass all subscription checks automatically.

---

## Troubleshooting

### "Missing roles in PostgreSQL — run db_seed.py first"
The seed script was not run or did not complete. Re-run `python -m app.db_seed` and check for errors.

### "user X not migrated" warnings in membership phase
The user referenced by a membership row was not migrated (likely a duplicate email or missing record). These memberships are skipped safely.

### Script fails partway through
The script is fully idempotent. Fix the error (connection issue, schema mismatch, etc.) and re-run from the beginning — already-migrated rows will be skipped.

### Answers phase is slow
The answers table has ~4.6 million rows processed in batches of 10,000. This is expected and will take several minutes. Watch the log output for progress.

### Password login fails for migrated users
Confirm `passlib` and `bcrypt` are installed at the correct versions (`passlib==1.7.4`, `bcrypt==4.1.2`). The `$2y$` prefix is handled natively.

---

## Re-running the migration (idempotency)

Every phase checks for existing records before inserting:
- Users are matched by `email`
- Organizations are matched by `key` (slug)
- Memberships are matched by `user_id + role_id + organization_id`
- Assessment results are matched by `assessment_id`
- Invitations are matched by `email`

It is safe to re-run the script at any time. Records already migrated will be skipped and counted in the "skipped" summary.
