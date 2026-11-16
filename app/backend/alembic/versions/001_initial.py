"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2026-11-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('is_superuser', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('last_login', sa.DateTime, nullable=True),
    )

    # Projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('genre', sa.String(100), nullable=True),
        sa.Column('themes', sa.Text, nullable=True),
        sa.Column('status', sa.Enum('draft', 'in_progress', 'completed', 'archived', name='projectstatus'), default='draft', nullable=False),
        sa.Column('total_episodes', sa.Integer, default=20, nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('google_account_id', sa.String(36), sa.ForeignKey('google_accounts.id', ondelete='SET NULL'), nullable=True),
    )

    # Series Bibles table
    op.create_table(
        'series_bibles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('premise', sa.Text, nullable=True),
        sa.Column('main_plot', sa.Text, nullable=True),
        sa.Column('subplots', sa.Text, nullable=True),
        sa.Column('character_relationships', sa.Text, nullable=True),
        sa.Column('world_settings', sa.Text, nullable=True),
        sa.Column('tone_and_visual_style', sa.Text, nullable=True),
        sa.Column('ending_direction', sa.Text, nullable=True),
        sa.Column('episode_structure', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Characters table
    op.create_table(
        'characters',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(100), nullable=True),
        sa.Column('order_index', sa.Integer, default=0, nullable=False),
        sa.Column('age', sa.String(50), nullable=True),
        sa.Column('gender', sa.String(50), nullable=True),
        sa.Column('ethnicity', sa.String(100), nullable=True),
        sa.Column('height', sa.String(50), nullable=True),
        sa.Column('build', sa.String(50), nullable=True),
        sa.Column('hair_color', sa.String(50), nullable=True),
        sa.Column('hair_style', sa.String(100), nullable=True),
        sa.Column('eye_color', sa.String(50), nullable=True),
        sa.Column('skin_tone', sa.String(50), nullable=True),
        sa.Column('distinguishing_features', sa.Text, nullable=True),
        sa.Column('personality_traits', sa.Text, nullable=True),
        sa.Column('background', sa.Text, nullable=True),
        sa.Column('motivations', sa.Text, nullable=True),
        sa.Column('fears', sa.Text, nullable=True),
        sa.Column('quirks', sa.Text, nullable=True),
        sa.Column('costume_style', sa.Text, nullable=True),
        sa.Column('signature_items', sa.Text, nullable=True),
        sa.Column('color_palette', sa.Text, nullable=True),
        sa.Column('reference_images', sa.Text, nullable=True),
        sa.Column('consistency_instructions', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Locations table
    op.create_table(
        'locations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(100), nullable=True),
        sa.Column('order_index', sa.Integer, default=0, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('environment_details', sa.Text, nullable=True),
        sa.Column('reference_images', sa.Text, nullable=True),
        sa.Column('visual_style_notes', sa.Text, nullable=True),
        sa.Column('lighting', sa.Text, nullable=True),
        sa.Column('atmosphere', sa.Text, nullable=True),
        sa.Column('time_of_day', sa.String(50), nullable=True),
        sa.Column('weather', sa.String(100), nullable=True),
        sa.Column('consistency_instructions', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Episodes table
    op.create_table(
        'episodes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('episode_number', sa.Integer, nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('status', sa.Enum('planned', 'outlined', 'scenes_written', 'prompts_ready', 'in_production', 'post_production', 'completed', name='episodestatus'), default='planned', nullable=False),
        sa.Column('estimated_cost', sa.Integer, default=0, nullable=False),
        sa.Column('actual_cost', sa.Integer, default=0, nullable=False),
        sa.Column('production_notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )

    # Scenes table
    op.create_table(
        'scenes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('episode_id', sa.String(36), sa.ForeignKey('episodes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('scene_number', sa.Integer, nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('location_id', sa.String(36), sa.ForeignKey('locations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('time_of_day', sa.String(50), nullable=True),
        sa.Column('duration_estimate', sa.Integer, nullable=True),
        sa.Column('status', sa.Enum('planned', 'written', 'prompts_ready', 'generating', 'generated', 'approved', 'needs_revision', name='scenestatus'), default='planned', nullable=False),
        sa.Column('action', sa.Text, nullable=True),
        sa.Column('dialogue', sa.Text, nullable=True),
        sa.Column('characters_present', sa.Text, nullable=True),
        sa.Column('production_notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Shots table
    op.create_table(
        'shots',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('scene_id', sa.String(36), sa.ForeignKey('scenes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('shot_number', sa.Integer, nullable=False),
        sa.Column('shot_type', sa.String(50), nullable=True),
        sa.Column('camera_angle', sa.String(50), nullable=True),
        sa.Column('camera_movement', sa.String(100), nullable=True),
        sa.Column('duration', sa.Integer, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('characters_in_shot', sa.Text, nullable=True),
        sa.Column('status', sa.Enum('planned', 'prompt_ready', 'generating', 'generated', 'approved', 'needs_revision', name='shotstatus'), default='planned', nullable=False),
        sa.Column('image_prompt', sa.Text, nullable=True),
        sa.Column('video_prompt', sa.Text, nullable=True),
        sa.Column('generated_image_url', sa.String(500), nullable=True),
        sa.Column('generated_video_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Prompts table
    op.create_table(
        'prompts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('episode_id', sa.String(36), sa.ForeignKey('episodes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('scene_id', sa.String(36), sa.ForeignKey('scenes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('shot_id', sa.String(36), sa.ForeignKey('shots.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('character_id', sa.String(36), sa.ForeignKey('characters.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('location_id', sa.String(36), sa.ForeignKey('locations.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('prompt_type', sa.Enum('character_image', 'location_image', 'scene_image', 'video_generation', 'camera_movement', 'character_action', 'dialogue_audio', 'sound_effect', 'music', name='prompttype'), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('prompt_text', sa.Text, nullable=False),
        sa.Column('negative_prompt', sa.Text, nullable=True),
        sa.Column('parameters', sa.Text, nullable=True),
        sa.Column('status', sa.Enum('draft', 'finalized', 'used', 'archived', name='promptstatus'), default='draft', nullable=False),
        sa.Column('version', sa.Integer, default=1, nullable=False),
        sa.Column('parent_prompt_id', sa.String(36), sa.ForeignKey('prompts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('times_used', sa.Integer, default=0, nullable=False),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('generation_time', sa.Integer, nullable=True),
        sa.Column('generated_asset_path', sa.String(500), nullable=True),
        sa.Column('generation_status', sa.String(50), default='draft', nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    # Google Accounts table
    op.create_table(
        'google_accounts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('profile_picture', sa.String(500), nullable=True),
        sa.Column('google_user_id', sa.String(100), nullable=True, unique=True),
        sa.Column('encrypted_session_data', sa.Text, nullable=True),
        sa.Column('session_expires_at', sa.DateTime, nullable=True),
        sa.Column('status', sa.Enum('connected', 'disconnected', 'expired', 'error', name='googleaccountstatus'), default='disconnected', nullable=False),
        sa.Column('last_verified_at', sa.DateTime, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('projects_assigned', sa.Integer, default=0, nullable=False),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('connected_at', sa.DateTime, nullable=True),
        sa.Column('disconnected_at', sa.DateTime, nullable=True),
    )

    # Flow Bridge Tasks table
    op.create_table(
        'flow_bridge_tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('episode_id', sa.String(36), sa.ForeignKey('episodes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('scene_id', sa.String(36), sa.ForeignKey('scenes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('shot_id', sa.String(36), sa.ForeignKey('shots.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('google_account_id', sa.String(36), sa.ForeignKey('google_accounts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('task_type', sa.String(100), nullable=True),
        sa.Column('status', sa.Enum('pending', 'preparing', 'ready_for_generation', 'generating', 'waiting_for_import', 'completed', 'failed', name='flowbridgetaskstatus'), default='pending', nullable=False),
        sa.Column('input_prompts', sa.Text, nullable=True),
        sa.Column('input_references', sa.Text, nullable=True),
        sa.Column('input_parameters', sa.Text, nullable=True),
        sa.Column('output_assets', sa.Text, nullable=True),
        sa.Column('generation_log', sa.Text, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('automation_data', sa.Text, nullable=True),
        sa.Column('manual_steps_completed', sa.Text, nullable=True),
        sa.Column('priority', sa.Integer, default=0, nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )

    # Flow Bridge Assets table
    op.create_table(
        'flow_bridge_assets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('flow_bridge_tasks.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('asset_type', sa.Enum('reference_image', 'character_image', 'location_image', 'storyboard', 'video_clip', 'audio_clip', 'subtitle_file', 'other', name='flowbridgeassettype'), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_url', sa.String(500), nullable=True),
        sa.Column('file_size', sa.Integer, nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('source_metadata', sa.Text, nullable=True),
        sa.Column('episode_id', sa.String(36), sa.ForeignKey('episodes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('scene_id', sa.String(36), sa.ForeignKey('scenes.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('shot_id', sa.String(36), sa.ForeignKey('shots.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('character_id', sa.String(36), sa.ForeignKey('characters.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('location_id', sa.String(36), sa.ForeignKey('locations.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('action', sa.Enum(
            'login', 'logout', 'register', 'password_change',
            'project_create', 'project_read', 'project_update', 'project_delete',
            'series_bible_create', 'series_bible_update',
            'character_create', 'character_update', 'character_delete',
            'location_create', 'location_update', 'location_delete',
            'episode_create', 'episode_update', 'episode_delete',
            'scene_create', 'scene_update', 'scene_delete',
            'shot_create', 'shot_update', 'shot_delete',
            'prompt_create', 'prompt_update', 'prompt_delete', 'prompt_generate',
            'google_account_connect', 'google_account_disconnect', 'google_account_update',
            'flow_task_create', 'flow_task_update', 'flow_asset_import',
            'export_project', 'export_episode',
            name='auditaction'
        ), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(36), nullable=True, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('old_values', sa.Text, nullable=True),
        sa.Column('new_values', sa.Text, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_id', sa.String(36), nullable=True),
        sa.Column('success', sa.Integer, default=1, nullable=False),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('flow_bridge_assets')
    op.drop_table('flow_bridge_tasks')
    op.drop_table('google_accounts')
    op.drop_table('prompts')
    op.drop_table('shots')
    op.drop_table('scenes')
    op.drop_table('episodes')
    op.drop_table('locations')
    op.drop_table('characters')
    op.drop_table('series_bibles')
    op.drop_table('projects')
    op.drop_table('users')