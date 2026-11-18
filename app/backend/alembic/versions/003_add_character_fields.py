"""Add voice_pattern, physical_traits, skills columns to characters

Revision ID: 003
Revises: 002
Create Date: 2026-11-17

Fixes audit finding F-03: Scene Engine dialogue/action prompts read
Character.voice_pattern / physical_traits / skills, which did not exist
on the model, so generation always crashed when a project had characters.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('characters', sa.Column('voice_pattern', sa.Text(), nullable=True))
    op.add_column('characters', sa.Column('physical_traits', sa.Text(), nullable=True))
    op.add_column('characters', sa.Column('skills', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('characters', 'skills')
    op.drop_column('characters', 'physical_traits')
    op.drop_column('characters', 'voice_pattern')
