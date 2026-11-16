"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('owner_id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('genre', sa.String(100), nullable=True),
        sa.Column('themes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='draft'),
        sa.Column('total_episodes', sa.Integer(), nullable=False, default=20),
        sa.Column('google_account_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['google_account_id'], ['google_accounts.id'], ondelete='SET NULL')
    )
    op.create_index('ix_projects_owner_id', 'projects', ['owner_id'])
    op.create_index('ix_projects_google_account_id', 'projects', ['google_account_id'])
    
    # Create series_bibles table
    op.create_table(
        'series_bibles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('premise', sa.Text(), nullable=True),
        sa.Column('main_plot', sa.Text(), nullable=True),
        sa.Column('subplots', sa.Text(), nullable=True),
        sa.Column('character_relationships', sa.Text(), nullable=True),
        sa.Column('world_settings', sa.Text(), nullable=True),
        sa.Column('tone_and_visual_style', sa.Text(), nullable=True),
        sa.Column('ending_direction', sa.Text(), nullable=True),
        sa.Column('episode_structure', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('project_id')
    )
    op.create_index('ix_series_bibles_project_id', 'series_bibles', ['project_id'])
    
    # Create characters table
    op.create_table(
        'characters',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(100), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, default=0),
        sa.Column('age', sa.String(50), nullable=True),
        sa.Column('gender', sa.String(50), nullable=True),
        sa.Column('ethnicity', sa.String(100), nullable=True),
        sa.Column('height', sa.String(50), nullable=True),
        sa.Column('build', sa.String(50), nullable=True),
        sa.Column('hair_color', sa.String(50), nullable=True),
        sa.Column('hair_style', sa.String(100), nullable=True),
        sa.Column('eye_color', sa.String(50), nullable=True),
        sa.Column('skin_tone', sa.String(50), nullable=True),
        sa.Column('distinguishing_features', sa.Text(), nullable=True),
        sa.Column('personality_traits', sa.Text(), nullable=True),
        sa.Column('background', sa.Text(), nullable=True),
        sa.Column('motivations', sa.Text(), nullable=True),
        sa.Column('fears', sa.Text(), nullable=True),
        sa.Column('quirks', sa.Text(), nullable=True),
        sa.Column('costume_style', sa.Text(), nullable=True),
        sa.Column('signature_items', sa.Text(), nullable=True),
        sa.Column('color_palette', sa.Text(), nullable=True),
        sa.Column('reference_images', sa.Text(), nullable=True),
        sa.Column('consistency_instructions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE')
    )
    op.create_index('ix_characters_project_id', 'characters', ['project_id'])
    
    # Create locations table
    op.create_table(
        'locations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(100), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, default=0),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('environment_details', sa.Text(), nullable=True),
        sa.Column('reference_images', sa.Text(), nullable=True),
        sa.Column('visual_style_notes', sa.Text(), nullable=True),
        sa.Column('lighting', sa.Text(), nullable=True),
        sa.Column('atmosphere', sa.Text(), nullable=True),
        sa.Column('time_of_day', sa.String(50), nullable=True),
        sa.Column('weather', sa.String(100), nullable=True),
        sa.Column('consistency_instructions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE')
    )
    op.create_index('ix_locations_project_id', 'locations', ['project_id'])
    
    # Create episodes table
    op.create_table(
        'episodes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('episode_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='planned'),
        sa.Column('estimated_cost', sa.Integer(), nullable=False, default=0),
        sa.Column('actual_cost', sa.Integer(), nullable=False, default=0),
        sa.Column('production_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE')
    )
    op.create_index('ix_episodes_project_id', 'episodes', ['project_id'])
    op.create_index('ix_episodes_episode_number', 'episodes', ['project_id', 'episode_number'], unique=True)
    
    # Create scenes table
    op.create_table(
        'scenes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('episode_id', sa.String(36), nullable=False),
        sa.Column('scene_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location_id', sa.String(36), nullable=True),
        sa.Column('time_of_day', sa.String(50), nullable=True),
        sa.Column('duration_estimate', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='planned'),
        sa.Column('action', sa.Text(), nullable=True),
        sa.Column('dialogue', sa.Text(), nullable=True),
        sa.Column('characters_present', sa.Text(), nullable=True),
        sa.Column('production_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='SET NULL')
    )
    op.create_index('ix_scenes_episode_id', 'scenes', ['episode_id'])
    op.create_index('ix_scenes_scene_number', 'scenes', ['episode_id', 'scene_number'], unique=True)
    op.create_index('ix_scenes_location_id', 'scenes', ['location_id'])
    
    # Create shots table
    op.create_table(
        'shots',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scene_id', sa.String(36), nullable=False),
        sa.Column('shot_number', sa.Integer(), nullable=False),
        sa.Column('shot_type', sa.String(50), nullable=True),
        sa.Column('camera_angle', sa.String(50), nullable=True),
        sa.Column('camera_movement', sa.String(100), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('characters_in_shot', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='planned'),
        sa.Column('image_prompt', sa.Text(), nullable=True),
        sa.Column('video_prompt', sa.Text(), nullable=True),
        sa.Column('generated_image_url', sa.String(500), nullable=True),
        sa.Column('generated_video_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='CASCADE')
    )
    op.create_index('ix_shots_scene_id', 'shots', ['scene_id'])
    op.create_index('ix_shots_shot_number', 'shots', ['scene_id', 'shot_number'], unique=True)
    
    # Create prompts table
    op.create_table(
        'prompts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('episode_id', sa.String(36), nullable=True),
        sa.Column('scene_id', sa.String(36), nullable=True),
        sa.Column('shot_id', sa.String(36), nullable=True),
        sa.Column('character_id', sa.String(36), nullable=True),
        sa.Column('location_id', sa.String(36), nullable=True),
        sa.Column('prompt_type', sa.String(30), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('negative_prompt', sa.Text(), nullable=True),
        sa.Column('parameters', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='draft'),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('parent_prompt_id', sa.String(36), nullable=True),
        sa.Column('times_used', sa.Integer(), nullable=False, default=0),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['shot_id'], ['shots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_prompt_id'], ['prompts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_prompts_project_id', 'prompts', ['project_id'])
    op.create_index('ix_prompts_episode_id', 'prompts', ['episode_id'])
    op.create_index('ix_prompts_scene_id', 'prompts', ['scene_id'])
    op.create_index('ix_prompts_shot_id', 'prompts', ['shot_id'])
    op.create_index('ix_prompts_character_id', 'prompts', ['character_id'])
    op.create_index('ix_prompts_location_id', 'prompts', ['location_id'])
    op.create_index('ix_prompts_prompt_type', 'prompts', ['prompt_type'])
    
    # Create google_accounts table
    op.create_table(
        'google_accounts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('profile_picture', sa.String(500), nullable=True),
        sa.Column('google_user_id', sa.String(100), nullable=True),
        sa.Column('encrypted_session_data', sa.Text(), nullable=True),
        sa.Column('session_expires_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='disconnected'),
        sa.Column('last_verified_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('projects_assigned', sa.Integer(), nullable=False, default=0),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('connected_at', sa.DateTime(), nullable=True),
        sa.Column('disconnected_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('google_user_id')
    )
    op.create_index('ix_google_accounts_user_id', 'google_accounts', ['user_id'])
    op.create_index('ix_google_accounts_email', 'google_accounts', ['user_id', 'email'], unique=True)
    
    # Create flow_bridge_tasks table
    op.create_table(
        'flow_bridge_tasks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('episode_id', sa.String(36), nullable=True),
        sa.Column('scene_id', sa.String(36), nullable=True),
        sa.Column('shot_id', sa.String(36), nullable=True),
        sa.Column('google_account_id', sa.String(36), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', sa.String(100), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, default='pending'),
        sa.Column('input_prompts', sa.Text(), nullable=True),
        sa.Column('input_references', sa.Text(), nullable=True),
        sa.Column('input_parameters', sa.Text(), nullable=True),
        sa.Column('output_assets', sa.Text(), nullable=True),
        sa.Column('generation_log', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('automation_data', sa.Text(), nullable=True),
        sa.Column('manual_steps_completed', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['shot_id'], ['shots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['google_account_id'], ['google_accounts.id'], ondelete='SET NULL')
    )
    op.create_index('ix_flow_bridge_tasks_project_id', 'flow_bridge_tasks', ['project_id'])
    op.create_index('ix_flow_bridge_tasks_episode_id', 'flow_bridge_tasks', ['episode_id'])
    op.create_index('ix_flow_bridge_tasks_status', 'flow_bridge_tasks', ['status'])
    
    # Create flow_bridge_assets table
    op.create_table(
        'flow_bridge_assets',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('task_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('asset_type', sa.String(30), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_url', sa.String(500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('source_metadata', sa.Text(), nullable=True),
        sa.Column('episode_id', sa.String(36), nullable=True),
        sa.Column('scene_id', sa.String(36), nullable=True),
        sa.Column('shot_id', sa.String(36), nullable=True),
        sa.Column('character_id', sa.String(36), nullable=True),
        sa.Column('location_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['task_id'], ['flow_bridge_tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['shot_id'], ['shots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='SET NULL')
    )
    op.create_index('ix_flow_bridge_assets_task_id', 'flow_bridge_assets', ['task_id'])
    op.create_index('ix_flow_bridge_assets_project_id', 'flow_bridge_assets', ['project_id'])
    op.create_index('ix_flow_bridge_assets_asset_type', 'flow_bridge_assets', ['asset_type'])
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(36), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_id', sa.String(36), nullable=True),
        sa.Column('old_values', sa.Text(), nullable=True),
        sa.Column('new_values', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_user_action', 'audit_logs', ['user_id', 'action'])


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