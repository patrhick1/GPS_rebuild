"""
One-shot cascade-delete of a user by email.
Dry-run by default. Pass --yes to commit.

    python scripts/delete_user_cascade.py paschal@3rdbrain.co
    python scripts/delete_user_cascade.py paschal@3rdbrain.co --yes
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from app.core.database import SessionLocal


TABLES = [
    ("notifications",              "user_id"),
    ("audit_log",                  "user_id"),
    ("email_verification_tokens",  "user_id"),
    ("password_reset_tokens",      "user_id"),
    ("invitations",                "created_by"),
    ("myimpact_results",           "user_id"),
    ("assessment_results",         "user_id"),
    ("answers",                    "user_id"),
    ("assessments",                "user_id"),
    ("refresh_tokens",             "user_id"),
    ("memberships",                "user_id"),
]


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: delete_user_cascade.py <email> [--yes]")
        return 2

    email = sys.argv[1].strip().lower()
    commit = "--yes" in sys.argv[2:]

    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT id, email FROM users WHERE LOWER(email) = :e"),
            {"e": email},
        ).first()
        if not row:
            print(f"[abort] no user found with email {email}")
            return 1

        uid, found_email = row
        print(f"[target] user_id={uid}  email={found_email}")
        print(f"[mode]   {'COMMIT' if commit else 'DRY-RUN (no --yes)'}")
        print()

        for table, col in TABLES:
            n = db.execute(
                text(f"DELETE FROM {table} WHERE {col} = :uid"),
                {"uid": uid},
            ).rowcount
            print(f"  {table:<28} {col:<12} -> {n} rows")

        n = db.execute(
            text("DELETE FROM users WHERE id = :uid"),
            {"uid": uid},
        ).rowcount
        print(f"  {'users':<28} {'id':<12} -> {n} rows")

        if commit:
            db.commit()
            print("\n[done] committed.")
        else:
            db.rollback()
            print("\n[done] rolled back. re-run with --yes to commit.")
        return 0
    except Exception as e:
        db.rollback()
        print(f"[error] {e}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
