"""reconcile notifications schema with PRD addendum

Revision ID: c6a7b8d9e0f1
Revises: b5d1f0e2a3c4
Create Date: 2026-04-30 17:00:00.000000

Aligns the partially-built notifications subsystem with the v2.1 addendum spec:
  - is_read: VARCHAR(1) 'Y'/'N' -> BOOLEAN
  - adds reference_type / reference_id for entity deep-linking
    (link column kept; the two are orthogonal: explicit URL vs entity pointer)
  - renames member-self event types (gps_result / myimpact_result ->
    assessment_self_completed) to disambiguate from the admin-facing
    assessment_completed event the addendum lists.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6a7b8d9e0f1'
down_revision: Union[str, None] = 'b5d1f0e2a3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # 1. Add reference_type / reference_id columns for entity deep-linking.
    op.add_column(
        'notifications',
        sa.Column('reference_type', sa.String(50), nullable=True),
    )
    op.add_column(
        'notifications',
        sa.Column('reference_id', sa.UUID(), nullable=True),
    )

    # 2. Convert is_read from VARCHAR(1) Y/N to BOOLEAN.
    # Drop the composite index first since it includes is_read.
    op.drop_index('ix_notifications_user_read_created', table_name='notifications')

    if dialect == 'postgresql':
        # Two-step copy on Postgres: add new col, copy, drop old, rename.
        op.add_column(
            'notifications',
            sa.Column(
                'is_read_bool',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('false'),
            ),
        )
        op.execute("UPDATE notifications SET is_read_bool = (is_read = 'Y')")
        op.drop_column('notifications', 'is_read')
        op.alter_column('notifications', 'is_read_bool', new_column_name='is_read')
    else:
        # SQLite: batch_alter_table handles type swap by table copy.
        with op.batch_alter_table('notifications') as batch_op:
            batch_op.alter_column(
                'is_read',
                existing_type=sa.String(1),
                type_=sa.Boolean(),
                postgresql_using="(is_read = 'Y')",
                existing_nullable=False,
                server_default=sa.text('0'),
            )

    # Recreate the composite index now that is_read is the right type.
    op.create_index(
        'ix_notifications_user_read_created',
        'notifications',
        ['user_id', 'is_read', 'created_at'],
    )

    # 3. Rename member-self assessment notification types.
    # gps_result / myimpact_result are the user's own "your results are ready"
    # notification, which is distinct from the admin-facing assessment_completed
    # the addendum specs. Disambiguate.
    op.execute(
        "UPDATE notifications "
        "SET type = 'assessment_self_completed' "
        "WHERE type IN ('gps_result', 'myimpact_result')"
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Reverse the type rename. We collapse both gps_result/myimpact_result
    # back to gps_result (we can't recover which was which without a marker;
    # the link column points at the right page either way).
    op.execute(
        "UPDATE notifications "
        "SET type = 'gps_result' "
        "WHERE type = 'assessment_self_completed'"
    )

    op.drop_index('ix_notifications_user_read_created', table_name='notifications')

    if dialect == 'postgresql':
        op.add_column(
            'notifications',
            sa.Column(
                'is_read_str',
                sa.String(1),
                nullable=False,
                server_default='N',
            ),
        )
        op.execute(
            "UPDATE notifications SET is_read_str = CASE WHEN is_read THEN 'Y' ELSE 'N' END"
        )
        op.drop_column('notifications', 'is_read')
        op.alter_column('notifications', 'is_read_str', new_column_name='is_read')
    else:
        with op.batch_alter_table('notifications') as batch_op:
            batch_op.alter_column(
                'is_read',
                existing_type=sa.Boolean(),
                type_=sa.String(1),
                existing_nullable=False,
                server_default='N',
            )

    op.create_index(
        'ix_notifications_user_read_created',
        'notifications',
        ['user_id', 'is_read', 'created_at'],
    )

    op.drop_column('notifications', 'reference_id')
    op.drop_column('notifications', 'reference_type')
