"""Perbaikan audit ronde 2 (20 Nov 2026).

Revision ID: 007
Revises: 006
Create Date: 2026-11-20

- P1-2: tabel `checkout_sessions` — pemetaan sesi checkout Stripe ke
  user/plan lokal, supaya webhook `checkout.session.completed` bisa
  mengaitkan event asli yang metadata-nya kosong.
- P2-4: kolom `subtitle_key`, `audio_key`, `resolution` di `video_jobs` —
  tanpa ini job yang terpotong restart tidak bisa di-resume (parameter
  perakitan hilang, hanya input_files yang tersimpan).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'checkout_sessions',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('plan', sa.String(length=50), nullable=False),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_checkout_sessions_user_id', 'checkout_sessions', ['user_id'], unique=False)
    op.create_index('ix_checkout_sessions_stripe_customer_id', 'checkout_sessions', ['stripe_customer_id'], unique=False)

    op.add_column('video_jobs', sa.Column('subtitle_key', sa.String(length=500), nullable=True))
    op.add_column('video_jobs', sa.Column('audio_key', sa.String(length=500), nullable=True))
    op.add_column('video_jobs', sa.Column('resolution', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('video_jobs', 'resolution')
    op.drop_column('video_jobs', 'audio_key')
    op.drop_column('video_jobs', 'subtitle_key')
    op.drop_index('ix_checkout_sessions_stripe_customer_id', table_name='checkout_sessions')
    op.drop_index('ix_checkout_sessions_user_id', table_name='checkout_sessions')
    op.drop_table('checkout_sessions')
