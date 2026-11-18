"""Add fallback_history to flow_bridge_tasks

Revision ID: 004
Revises: 003
Create Date: 2026-11-17

Google account fallback (Flow Bridge): record which account was used and
why the task moved to the next one, as a JSON list on the task.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('flow_bridge_tasks', sa.Column('fallback_history', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('flow_bridge_tasks', 'fallback_history')
