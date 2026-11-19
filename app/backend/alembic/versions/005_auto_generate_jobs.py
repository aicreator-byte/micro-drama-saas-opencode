"""Auto-generate jobs and steps (Fase 1)

Revision ID: 005
Revises: 004
Create Date: 2026-11-19

One job runs the 5 auto-generate steps (series_bible -> characters ->
locations -> episodes -> prompts) for a project; each step tracks its own
status so a failed step can be retried without re-running the rest.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'auto_generate_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('genre', sa.String(length=100), nullable=True),
        sa.Column('total_episodes', sa.Integer(), nullable=False),
        sa.Column('premise', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='autogeneratejobstatus'), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auto_generate_jobs_project_id', 'auto_generate_jobs', ['project_id'], unique=False)
    op.create_index('ix_auto_generate_jobs_project_status', 'auto_generate_jobs', ['project_id', 'status'], unique=False)

    op.create_table(
        'auto_generate_steps',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('step', sa.Enum('series_bible', 'characters', 'locations', 'episodes', 'prompts', name='autogeneratestepname'), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='autogeneratestepstatus'), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['auto_generate_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auto_generate_steps_job_id', 'auto_generate_steps', ['job_id'], unique=False)
    op.create_index('ix_auto_generate_steps_job_order', 'auto_generate_steps', ['job_id', 'step_order'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_auto_generate_steps_job_order', table_name='auto_generate_steps')
    op.drop_index('ix_auto_generate_steps_job_id', table_name='auto_generate_steps')
    op.drop_table('auto_generate_steps')
    op.drop_index('ix_auto_generate_jobs_project_status', table_name='auto_generate_jobs')
    op.drop_index('ix_auto_generate_jobs_project_id', table_name='auto_generate_jobs')
    op.drop_table('auto_generate_jobs')
