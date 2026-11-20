"""Round-2 tables: subscriptions, LLM usage events, assets, video jobs.

Revision ID: 006
Revises: 005
Create Date: 2026-11-20

Mirrors the SQLAlchemy models added in the round-2 future-development
work (billing, analytics, asset management, video pipeline). Runtime
startup uses init_db() / create_all, so this migration only matters for
databases managed by Alembic — it keeps `alembic upgrade head` able to
reproduce the same schema from scratch.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True),
        sa.Column('plan', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'], unique=False)
    op.create_index('ix_subscriptions_stripe_customer_id', 'subscriptions', ['stripe_customer_id'], unique=False)
    op.create_index('ix_subscriptions_stripe_subscription_id', 'subscriptions', ['stripe_subscription_id'], unique=False)

    op.create_table(
        'llm_usage_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('job_id', sa.String(length=36), nullable=True),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('model', sa.String(length=255), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('completion_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['auto_generate_jobs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_llm_usage_events_user_id', 'llm_usage_events', ['user_id'], unique=False)
    op.create_index('ix_llm_usage_events_project_id', 'llm_usage_events', ['project_id'], unique=False)
    op.create_index('ix_llm_usage_events_job_id', 'llm_usage_events', ['job_id'], unique=False)

    op.create_table(
        'assets',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('backend', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_assets_project_id', 'assets', ['project_id'], unique=False)
    op.create_index('ix_assets_key', 'assets', ['key'], unique=False)

    op.create_table(
        'video_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('episode_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('input_files', sa.Text(), nullable=True),
        sa.Column('output_path', sa.String(length=500), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_video_jobs_project_id', 'video_jobs', ['project_id'], unique=False)
    op.create_index('ix_video_jobs_episode_id', 'video_jobs', ['episode_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_video_jobs_episode_id', table_name='video_jobs')
    op.drop_index('ix_video_jobs_project_id', table_name='video_jobs')
    op.drop_table('video_jobs')
    op.drop_index('ix_assets_key', table_name='assets')
    op.drop_index('ix_assets_project_id', table_name='assets')
    op.drop_table('assets')
    op.drop_index('ix_llm_usage_events_job_id', table_name='llm_usage_events')
    op.drop_index('ix_llm_usage_events_project_id', table_name='llm_usage_events')
    op.drop_index('ix_llm_usage_events_user_id', table_name='llm_usage_events')
    op.drop_table('llm_usage_events')
    op.drop_index('ix_subscriptions_stripe_subscription_id', table_name='subscriptions')
    op.drop_index('ix_subscriptions_stripe_customer_id', table_name='subscriptions')
    op.drop_index('ix_subscriptions_user_id', table_name='subscriptions')
    op.drop_table('subscriptions')
