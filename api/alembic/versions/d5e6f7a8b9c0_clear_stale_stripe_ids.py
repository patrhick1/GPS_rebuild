"""clear stale stripe ids after api key switch

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-04-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clear stale Stripe IDs from subscriptions
    op.execute(
        "UPDATE subscriptions SET "
        "stripe_customer_id = NULL, "
        "stripe_subscription_id = NULL, "
        "stripe_price_id = NULL, "
        "status = 'incomplete'"
    )

    # Clear stale Stripe IDs from organizations
    op.execute(
        "UPDATE organizations SET "
        "stripe_id = NULL, "
        "card_brand = NULL, "
        "card_last_four = NULL"
    )

    # Clear stale Stripe IDs from users
    op.execute("UPDATE users SET stripe_id = NULL")


def downgrade() -> None:
    # Data migration — cannot be reversed
    pass
