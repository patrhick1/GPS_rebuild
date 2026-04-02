"""
Laravel MySQL → FastAPI PostgreSQL Migration Script
====================================================

PREREQUISITES:
1. Have the full production MySQL/MariaDB database running and accessible.
   (The backup-20260322-221322.sql file was used only for structural analysis.)
2. Run db_seed.py first so that roles, types, question_types, gifts_passions,
   and questions are already seeded in PostgreSQL.
3. Set the following environment variables (or edit the defaults below):

   LEGACY_DB_URL   mysql+pymysql://user:pass@host/database_name
   DATABASE_URL    postgresql://user:pass@host/database_name

USAGE:
    cd api
    python -m scripts.migrate_from_laravel

The script is idempotent — safe to run multiple times.
Each phase checks for existing records before inserting.
"""

import os
import re
import sys
import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("migrate")

# ---------------------------------------------------------------------------
# Connection config — override via env vars
# ---------------------------------------------------------------------------
LEGACY_DB_URL = os.getenv(
    "LEGACY_DB_URL",
    "mysql+pymysql://root:password@localhost/gps_production",
)
NEW_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost/gps",
)

# ---------------------------------------------------------------------------
# PHP serialized integer array parser
# Handles the gifts_passions.questions field format:
#   a:4:{i:0;i:9;i:1;i:28;i:2;i:47;i:3;i:66;}  →  [9, 28, 47, 66]
# ---------------------------------------------------------------------------
def parse_php_serialized_ints(value: str) -> list[int]:
    if not value:
        return []
    return [int(x) for x in re.findall(r"i:\d+;i:(\d+);", value)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def safe_dt(value) -> datetime | None:
    """Return a naive datetime or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    return value


# ---------------------------------------------------------------------------
# Main migration
# ---------------------------------------------------------------------------
def run():
    log.info("Connecting to legacy MySQL database …")
    legacy_engine = create_engine(LEGACY_DB_URL)
    LegacySession = sessionmaker(bind=legacy_engine)
    legacy = LegacySession()

    log.info("Connecting to new PostgreSQL database …")
    new_engine = create_engine(NEW_DB_URL)
    NewSession = sessionmaker(bind=new_engine)
    new = NewSession()

    try:
        # ------------------------------------------------------------------ #
        # PHASE 0 — Build lookup maps from already-seeded PostgreSQL data     #
        # ------------------------------------------------------------------ #
        log.info("=== PHASE 0: Building seed lookup maps ===")

        role_map: dict[str, uuid.UUID] = {
            row.name: row.id
            for row in new.execute(text("SELECT id, name FROM roles")).fetchall()
        }
        log.info("  Roles found: %s", list(role_map.keys()))
        required_roles = {"user", "member", "admin", "master"}
        missing = required_roles - set(role_map.keys())
        if missing:
            log.error("Missing roles in PostgreSQL: %s — run db_seed.py first.", missing)
            sys.exit(1)

        # gifts_passions: map short_code → new uuid
        gp_map: dict[str, uuid.UUID] = {
            row.short_code: row.id
            for row in new.execute(
                text("SELECT id, short_code FROM gifts_passions")
            ).fetchall()
        }
        log.info("  Gifts/passions found: %d", len(gp_map))

        # questions: map order (int) → new uuid
        question_order_map: dict[int, uuid.UUID] = {
            row.order: row.id
            for row in new.execute(
                text("SELECT id, \"order\" FROM questions")
            ).fetchall()
        }
        log.info("  Questions found: %d", len(question_order_map))

        # Legacy gifts_passions: old int id → short_code
        legacy_gp_rows = legacy.execute(
            text("SELECT id, short_code FROM gifts_passions")
        ).fetchall()
        legacy_gp_short: dict[int, str] = {row.id: row.short_code for row in legacy_gp_rows}

        # Legacy questions: old int id → order value (stable key)
        legacy_q_rows = legacy.execute(
            text("SELECT id, `order` FROM questions")
        ).fetchall()
        legacy_q_order: dict[int, int] = {row.id: row.order for row in legacy_q_rows}

        def resolve_gp_uuid(old_id: int | None) -> uuid.UUID | None:
            if old_id is None:
                return None
            sc = legacy_gp_short.get(old_id)
            if sc is None:
                return None
            return gp_map.get(sc)

        def resolve_q_uuid(old_id: int | None) -> uuid.UUID | None:
            if old_id is None:
                return None
            order = legacy_q_order.get(old_id)
            if order is None:
                return None
            return question_order_map.get(order)

        # Old role_id → new role name
        OLD_ROLE_MAP = {
            1: "user",      # User
            2: "member",    # Group Leader → member (role dropped)
            3: "admin",     # Organization Administrator
            4: "master",    # Super Administrator
        }

        # ------------------------------------------------------------------ #
        # PHASE 1 — Organizations                                             #
        # ------------------------------------------------------------------ #
        log.info("=== PHASE 1: Migrating organizations ===")

        legacy_orgs = legacy.execute(
            text(
                "SELECT id, name, city, state, country, `key`, stripe_id, "
                "card_brand, card_last_four, trial_ends_at, created_at, updated_at "
                "FROM organizations"
            )
        ).fetchall()
        log.info("  Found %d organizations in legacy DB", len(legacy_orgs))

        org_id_map: dict[int, uuid.UUID] = {}
        orgs_inserted = orgs_skipped = 0

        for row in legacy_orgs:
            existing = new.execute(
                text("SELECT id FROM organizations WHERE key = :key"),
                {"key": row.key},
            ).fetchone()
            if existing:
                org_id_map[row.id] = existing.id
                orgs_skipped += 1
                continue

            new_id = uuid.uuid4()
            org_id_map[row.id] = new_id
            new.execute(
                text(
                    "INSERT INTO organizations "
                    "(id, name, city, state, country, key, stripe_id, "
                    " card_brand, card_last_four, trial_ends_at, status, "
                    " package, is_comped, created_at, updated_at) "
                    "VALUES (:id, :name, :city, :state, :country, :key, :stripe_id, "
                    " :card_brand, :card_last_four, :trial_ends_at, 'active', "
                    " NULL, false, :created_at, :updated_at)"
                ),
                {
                    "id": new_id,
                    "name": row.name,
                    "city": row.city,
                    "state": row.state,
                    "country": row.country,
                    "key": row.key,
                    "stripe_id": row.stripe_id,
                    "card_brand": row.card_brand,
                    "card_last_four": row.card_last_four,
                    "trial_ends_at": safe_dt(row.trial_ends_at),
                    "created_at": safe_dt(row.created_at) or now_utc(),
                    "updated_at": safe_dt(row.updated_at) or now_utc(),
                },
            )
            orgs_inserted += 1

        new.commit()
        log.info(
            "  Organizations: %d inserted, %d skipped (already exist)",
            orgs_inserted, orgs_skipped,
        )

        # ------------------------------------------------------------------ #
        # PHASE 2 — Subscriptions (one per org, yearly at $100)               #
        # ------------------------------------------------------------------ #
        log.info("=== PHASE 2: Creating subscriptions for all organizations ===")

        subs_inserted = subs_skipped = 0
        for old_org_id, new_org_id in org_id_map.items():
            existing = new.execute(
                text("SELECT id FROM subscriptions WHERE organization_id = :oid"),
                {"oid": new_org_id},
            ).fetchone()
            if existing:
                subs_skipped += 1
                continue

            new.execute(
                text(
                    "INSERT INTO subscriptions "
                    "(id, organization_id, status, plan, quantity, unit_amount, "
                    " cancel_at_period_end, created_at, updated_at) "
                    "VALUES (:id, :org_id, 'active', 'yearly', 1, 100.00, "
                    " false, :now, :now)"
                ),
                {"id": uuid.uuid4(), "org_id": new_org_id, "now": now_utc()},
            )
            subs_inserted += 1

        new.commit()
        log.info(
            "  Subscriptions: %d inserted, %d skipped", subs_inserted, subs_skipped
        )

        # ------------------------------------------------------------------ #
        # PHASE 3 — Users                                                     #
        # ------------------------------------------------------------------ #
        log.info("=== PHASE 3: Migrating users ===")

        legacy_users = legacy.execute(
            text(
                "SELECT id, first_name, last_name, email, password, "
                "phone_number, city, state, country, locale, stripe_id, "
                "trial_ends_at, created_at, updated_at "
                "FROM users"
            )
        ).fetchall()
        log.info("  Found %d users in legacy DB", len(legacy_users))

        user_id_map: dict[int, uuid.UUID] = {}
        users_inserted = users_skipped = 0

        for row in legacy_users:
            existing = new.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": row.email},
            ).fetchone()
            if existing:
                user_id_map[row.id] = existing.id
                users_skipped += 1
                continue

            new_id = uuid.uuid4()
            user_id_map[row.id] = new_id
            new.execute(
                text(
                    "INSERT INTO users "
                    "(id, first_name, last_name, email, password_hash, "
                    " phone_number, city, state, country, locale, status, "
                    " stripe_id, trial_ends_at, created_at, updated_at) "
                    "VALUES (:id, :first_name, :last_name, :email, :password_hash, "
                    " :phone_number, :city, :state, :country, :locale, 'active', "
                    " :stripe_id, :trial_ends_at, :created_at, :updated_at)"
                ),
                {
                    "id": new_id,
                    "first_name": row.first_name,
                    "last_name": row.last_name,
                    "email": row.email,
                    # $2y$ (PHP) is accepted natively by Python passlib — no conversion needed
                    "password_hash": row.password,
                    "phone_number": row.phone_number,
                    "city": row.city,
                    "state": row.state,
                    "country": row.country,
                    "locale": row.locale or "en",
                    "stripe_id": row.stripe_id,
                    "trial_ends_at": safe_dt(row.trial_ends_at),
                    "created_at": safe_dt(row.created_at) or now_utc(),
                    "updated_at": safe_dt(row.updated_at) or now_utc(),
                },
            )
            users_inserted += 1

            if (users_inserted + users_skipped) % 5000 == 0:
                new.commit()
                log.info(
                    "    … %d users processed so far", users_inserted + users_skipped
                )

        new.commit()
        log.info(
            "  Users: %d inserted, %d skipped", users_inserted, users_skipped
        )

        # ------------------------------------------------------------------ #
        # PHASE 4 — Memberships                                               #
        # ------------------------------------------------------------------ #
        log.info("=== PHASE 4: Migrating memberships ===")

        legacy_memberships = legacy.execute(
            text(
                "SELECT id, user_id, organization_id, role_id, created_at, updated_at "
                "FROM memberships"
            )
        ).fetchall()
        log.info("  Found %d memberships in legacy DB", len(legacy_memberships))

        # Track the first admin per org so we can set is_primary_admin
        first_admin_per_org: set[uuid.UUID] = set()

        memberships_inserted = memberships_skipped = 0

        for row in legacy_memberships:
            new_user_id = user_id_map.get(row.user_id)
            new_org_id = org_id_map.get(row.organization_id) if row.organization_id else None

            if new_user_id is None:
                log.warning("  Skipping membership %d — user %d not migrated", row.id, row.user_id)
                memberships_skipped += 1
                continue

            new_role_name = OLD_ROLE_MAP.get(row.role_id, "user")
            new_role_id = role_map[new_role_name]

            # Check for duplicate membership
            existing = new.execute(
                text(
                    "SELECT id FROM memberships "
                    "WHERE user_id = :uid AND role_id = :rid "
                    "AND (organization_id = :oid OR (organization_id IS NULL AND :oid IS NULL))"
                ),
                {"uid": new_user_id, "rid": new_role_id, "oid": new_org_id},
            ).fetchone()
            if existing:
                memberships_skipped += 1
                continue

            # First admin in this org gets is_primary_admin=True
            is_primary = False
            if new_role_name == "admin" and new_org_id is not None:
                if new_org_id not in first_admin_per_org:
                    is_primary = True
                    first_admin_per_org.add(new_org_id)

            new.execute(
                text(
                    "INSERT INTO memberships "
                    "(id, user_id, organization_id, role_id, status, "
                    " is_primary_admin, created_at, updated_at) "
                    "VALUES (:id, :uid, :oid, :rid, 'active', "
                    " :primary, :created_at, :updated_at)"
                ),
                {
                    "id": uuid.uuid4(),
                    "uid": new_user_id,
                    "oid": new_org_id,
                    "rid": new_role_id,
                    "primary": is_primary,
                    "created_at": safe_dt(row.created_at) or now_utc(),
                    "updated_at": safe_dt(row.updated_at) or now_utc(),
                },
            )
            memberships_inserted += 1

        new.commit()
        log.info(
            "  Memberships: %d inserted, %d skipped", memberships_inserted, memberships_skipped
        )
        log.info("  Primary admins set for %d organizations", len(first_admin_per_org))

        # ------------------------------------------------------------------ #
        # PHASE 5 — Assessments                                               #
        # ------------------------------------------------------------------ #
        log.info("=== PHASE 5: Migrating assessments ===")

        legacy_assessments = legacy.execute(
            text(
                "SELECT id, user_id, completed_at, created_at, updated_at "
                "FROM assessments"
            )
        ).fetchall()
        log.info("  Found %d assessments in legacy DB", len(legacy_assessments))

        assessment_id_map: dict[int, uuid.UUID] = {}
        assessments_inserted = assessments_skipped = 0

        for row in legacy_assessments:
            new_user_id = user_id_map.get(row.user_id)
            if new_user_id is None:
                assessments_skipped += 1
                continue

            new_id = uuid.uuid4()
            assessment_id_map[row.id] = new_id
            status = "completed" if row.completed_at else "in_progress"

            new.execute(
                text(
                    "INSERT INTO assessments "
                    "(id, user_id, instrument_type, status, completed_at, "
                    " created_at, updated_at) "
                    "VALUES (:id, :uid, 'gps', :status, :completed_at, "
                    " :created_at, :updated_at)"
                ),
                {
                    "id": new_id,
                    "uid": new_user_id,
                    "status": status,
                    "completed_at": safe_dt(row.completed_at),
                    "created_at": safe_dt(row.created_at) or now_utc(),
                    "updated_at": safe_dt(row.updated_at) or now_utc(),
                },
            )
            assessments_inserted += 1

            if (assessments_inserted + assessments_skipped) % 5000 == 0:
                new.commit()
                log.info(
                    "    … %d assessments processed so far",
                    assessments_inserted + assessments_skipped,
                )

        new.commit()
        log.info(
            "  Assessments: %d inserted, %d skipped", assessments_inserted, assessments_skipped
        )

        # ------------------------------------------------------------------ #
        # PHASE 6 — Assessment results                                        #
        # ------------------------------------------------------------------ #
        log.info("=== PHASE 6: Migrating assessment results ===")

        legacy_results = legacy.execute(
            text(
                "SELECT id, assessment_id, user_id, "
                "gift_1_id, spiritual_gift_1_score, "
                "gift_2_id, spiritual_gift_2_score, "
                "gift_3_id, spiritual_gift_3_score, "
                "gift_4_id, spiritual_gift_4_score, "
                "passion_1_id, passion_1_score, "
                "passion_2_id, passion_2_score, "
                "passion_3_id, passion_3_score, "
                "people, cause, abilities, "
                "story_gift_answer, story_ability_answer, story_passion_answer, "
                "story_influencing_answer, story_onechange_answer, "
                "story_closestpeople_answer, story_oneregret_answer, "
                "created_at, updated_at "
                "FROM assessment_results"
            )
        ).fetchall()
        log.info("  Found %d assessment results in legacy DB", len(legacy_results))

        results_inserted = results_skipped = 0

        for row in legacy_results:
            new_assessment_id = assessment_id_map.get(row.assessment_id)
            new_user_id = user_id_map.get(row.user_id) if row.user_id else None

            if new_assessment_id is None:
                results_skipped += 1
                continue

            existing = new.execute(
                text("SELECT id FROM assessment_results WHERE assessment_id = :aid"),
                {"aid": new_assessment_id},
            ).fetchone()
            if existing:
                results_skipped += 1
                continue

            new.execute(
                text(
                    "INSERT INTO assessment_results ("
                    "id, assessment_id, user_id, "
                    "gift_1_id, spiritual_gift_1_score, "
                    "gift_2_id, spiritual_gift_2_score, "
                    "gift_3_id, spiritual_gift_3_score, "
                    "gift_4_id, spiritual_gift_4_score, "
                    "passion_1_id, passion_1_score, "
                    "passion_2_id, passion_2_score, "
                    "passion_3_id, passion_3_score, "
                    "people, cause, abilities, "
                    "story_gift_answer, story_ability_answer, story_passion_answer, "
                    "story_influencing_answer, story_onechange_answer, "
                    "story_closestpeople_answer, story_oneregret_answer, "
                    "created_at, updated_at"
                    ") VALUES ("
                    ":id, :assessment_id, :user_id, "
                    ":gift_1_id, :sg1, "
                    ":gift_2_id, :sg2, "
                    ":gift_3_id, :sg3, "
                    ":gift_4_id, :sg4, "
                    ":passion_1_id, :p1, "
                    ":passion_2_id, :p2, "
                    ":passion_3_id, :p3, "
                    ":people, :cause, :abilities, "
                    ":story_gift, :story_ability, :story_passion, "
                    ":story_influencing, :story_onechange, "
                    ":story_closestpeople, :story_oneregret, "
                    ":created_at, :updated_at"
                    ")"
                ),
                {
                    "id": uuid.uuid4(),
                    "assessment_id": new_assessment_id,
                    "user_id": new_user_id,
                    "gift_1_id": resolve_gp_uuid(row.gift_1_id),
                    "sg1": row.spiritual_gift_1_score,
                    "gift_2_id": resolve_gp_uuid(row.gift_2_id),
                    "sg2": row.spiritual_gift_2_score,
                    "gift_3_id": resolve_gp_uuid(row.gift_3_id),
                    "sg3": row.spiritual_gift_3_score,
                    "gift_4_id": resolve_gp_uuid(row.gift_4_id),
                    "sg4": row.spiritual_gift_4_score,
                    "passion_1_id": resolve_gp_uuid(row.passion_1_id),
                    "p1": row.passion_1_score,
                    "passion_2_id": resolve_gp_uuid(row.passion_2_id),
                    "p2": row.passion_2_score,
                    "passion_3_id": resolve_gp_uuid(row.passion_3_id),
                    "p3": row.passion_3_score,
                    "people": row.people,
                    "cause": row.cause,
                    "abilities": row.abilities,
                    "story_gift": row.story_gift_answer,
                    "story_ability": row.story_ability_answer,
                    "story_passion": row.story_passion_answer,
                    "story_influencing": row.story_influencing_answer,
                    "story_onechange": row.story_onechange_answer,
                    "story_closestpeople": row.story_closestpeople_answer,
                    "story_oneregret": row.story_oneregret_answer,
                    "created_at": safe_dt(row.created_at) or now_utc(),
                    "updated_at": safe_dt(row.updated_at) or now_utc(),
                },
            )
            results_inserted += 1

        new.commit()
        log.info(
            "  Assessment results: %d inserted, %d skipped",
            results_inserted, results_skipped,
        )

        # ------------------------------------------------------------------ #
        # PHASE 7 — Answers  (4.6M rows — batched)                           #
        # ------------------------------------------------------------------ #
        log.info("=== PHASE 7: Migrating answers (batched) ===")

        BATCH_SIZE = 10_000
        offset = 0
        answers_inserted = answers_skipped = 0

        total_answers = legacy.execute(text("SELECT COUNT(*) FROM answers")).scalar()
        log.info("  Found %d answers in legacy DB", total_answers)

        while True:
            batch = legacy.execute(
                text(
                    "SELECT id, assessment_id, question_id, user_id, "
                    "multiple_choice_answer, numeric_value, text_value, "
                    "created_at, updated_at "
                    "FROM answers "
                    "ORDER BY id "
                    "LIMIT :limit OFFSET :offset"
                ),
                {"limit": BATCH_SIZE, "offset": offset},
            ).fetchall()

            if not batch:
                break

            rows_to_insert = []
            for row in batch:
                new_assessment_id = assessment_id_map.get(row.assessment_id)
                new_user_id = user_id_map.get(row.user_id)
                new_question_id = resolve_q_uuid(row.question_id)

                if new_assessment_id is None or new_user_id is None:
                    answers_skipped += 1
                    continue

                rows_to_insert.append({
                    "id": uuid.uuid4(),
                    "assessment_id": new_assessment_id,
                    "question_id": new_question_id,
                    "user_id": new_user_id,
                    "multiple_choice_answer": row.multiple_choice_answer,
                    "numeric_value": row.numeric_value,
                    "text_value": row.text_value,
                    "created_at": safe_dt(row.created_at) or now_utc(),
                    "updated_at": safe_dt(row.updated_at) or now_utc(),
                })

            if rows_to_insert:
                new.execute(
                    text(
                        "INSERT INTO answers "
                        "(id, assessment_id, question_id, user_id, "
                        " multiple_choice_answer, numeric_value, text_value, "
                        " created_at, updated_at) "
                        "VALUES (:id, :assessment_id, :question_id, :user_id, "
                        " :multiple_choice_answer, :numeric_value, :text_value, "
                        " :created_at, :updated_at)"
                    ),
                    rows_to_insert,
                )
                new.commit()
                answers_inserted += len(rows_to_insert)

            offset += BATCH_SIZE
            log.info(
                "    … answers: %d inserted, %d skipped (offset %d / %d)",
                answers_inserted, answers_skipped, offset, total_answers,
            )

        log.info(
            "  Answers: %d inserted, %d skipped", answers_inserted, answers_skipped
        )

        # ------------------------------------------------------------------ #
        # PHASE 8 — Invitations (from organization_admin_registrations)       #
        # ------------------------------------------------------------------ #
        log.info("=== PHASE 8: Migrating invitations ===")

        legacy_invites = legacy.execute(
            text(
                "SELECT id, sign_up_key, email, organization_id, "
                "expired_at, created_at, updated_at "
                "FROM organization_admin_registrations"
            )
        ).fetchall()
        log.info("  Found %d invitations in legacy DB", len(legacy_invites))

        invites_inserted = invites_skipped = 0

        for row in legacy_invites:
            existing = new.execute(
                text("SELECT id FROM invitations WHERE email = :email"),
                {"email": row.email},
            ).fetchone()
            if existing:
                invites_skipped += 1
                continue

            new_org_id = org_id_map.get(row.organization_id) if row.organization_id else None
            expires_at = safe_dt(row.expired_at)
            status = "expired" if (expires_at and expires_at < now_utc()) else "sent"

            new.execute(
                text(
                    "INSERT INTO invitations "
                    "(id, sign_up_key, email, organization_id, created_by, "
                    " status, expires_at, created_at, updated_at) "
                    "VALUES (:id, :key, :email, :org_id, NULL, "
                    " :status, :expires_at, :created_at, :updated_at)"
                ),
                {
                    "id": uuid.uuid4(),
                    "key": row.sign_up_key,
                    "email": row.email,
                    "org_id": new_org_id,
                    "status": status,
                    "expires_at": expires_at,
                    "created_at": safe_dt(row.created_at) or now_utc(),
                    "updated_at": safe_dt(row.updated_at) or now_utc(),
                },
            )
            invites_inserted += 1

        new.commit()
        log.info(
            "  Invitations: %d inserted, %d skipped", invites_inserted, invites_skipped
        )

        # ------------------------------------------------------------------ #
        # Summary                                                             #
        # ------------------------------------------------------------------ #
        log.info("=== MIGRATION COMPLETE ===")
        log.info("  Organizations : %d inserted, %d skipped", orgs_inserted, orgs_skipped)
        log.info("  Subscriptions : %d inserted, %d skipped", subs_inserted, subs_skipped)
        log.info("  Users         : %d inserted, %d skipped", users_inserted, users_skipped)
        log.info("  Memberships   : %d inserted, %d skipped", memberships_inserted, memberships_skipped)
        log.info("  Assessments   : %d inserted, %d skipped", assessments_inserted, assessments_skipped)
        log.info("  Results       : %d inserted, %d skipped", results_inserted, results_skipped)
        log.info("  Answers       : %d inserted, %d skipped", answers_inserted, answers_skipped)
        log.info("  Invitations   : %d inserted, %d skipped", invites_inserted, invites_skipped)

    except Exception:
        new.rollback()
        log.exception("Migration failed — rolled back")
        sys.exit(1)
    finally:
        legacy.close()
        new.close()


if __name__ == "__main__":
    run()
