"""Add AppSettings table, Google OAuth fields, Dialogue and EpisodeRevision models

Revision ID: 002
Revises: 001_initial
Create Date: 2026-11-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create app_settings table
    op.create_table(
        'app_settings',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('ai_providers', sa.JSON().with_variant(sqlite.JSON, 'sqlite'), nullable=True),
        sa.Column('google_oauth_client_id_encrypted', sa.Text(), nullable=True),
        sa.Column('google_oauth_client_secret_encrypted', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Add password_encrypted to google_accounts
    op.add_column('google_accounts', sa.Column('password_encrypted', sa.Text(), nullable=True))

    # Create dialogue table
    op.create_table(
        'dialogues',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scene_id', sa.String(36), sa.ForeignKey('scenes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('character_id', sa.String(36), sa.ForeignKey('characters.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('character_name', sa.String(255), nullable=False),
        sa.Column('dialogue_text', sa.Text(), nullable=False),
        sa.Column('parenthetical', sa.Text(), nullable=True),
        sa.Column('action', sa.Text(), nullable=True),
        sa.Column('beat_number', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # NOTE: ix_dialogues_scene_id is auto-created by index=True on the
    # scene_id column above; creating it again fails on a fresh DB.
    op.create_index('ix_dialogues_scene_line', 'dialogues', ['scene_id', 'line_number'], unique=True)

    # Create episode_revisions table
    op.create_table(
        'episode_revisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('episode_id', sa.String(36), sa.ForeignKey('episodes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('scene_breakdown', sa.JSON().with_variant(sqlite.JSON, 'sqlite'), nullable=True),
        sa.Column('full_text', sa.Text(), nullable=True),
        sa.Column('change_notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # NOTE: ix_episode_revisions_episode_id is auto-created by index=True
    # on the episode_id column above; creating it again fails on a fresh DB.
    op.create_index('ix_episode_revisions_episode_revision', 'episode_revisions', ['episode_id', 'revision_number'], unique=True)


def downgrade() -> None:
    op.drop_table('episode_revisions')
    op.drop_table('dialogues')
    op.drop_column('google_accounts', 'password_encrypted')
    op.drop_table('app_settings')