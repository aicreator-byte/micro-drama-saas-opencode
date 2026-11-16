export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
  last_login: string | null;
}

export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export enum ProjectStatus {
  DRAFT = 'draft',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  ARCHIVED = 'archived',
}

export interface Project {
  id: string;
  owner_id: string;
  title: string;
  description: string | null;
  genre: string | null;
  themes: string[] | null;
  status: ProjectStatus;
  total_episodes: number;
  google_account_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  title: string;
  description?: string;
  genre?: string;
  themes?: string[];
  total_episodes?: number;
}

export interface ProjectUpdate {
  title?: string;
  description?: string;
  genre?: string;
  themes?: string[];
  status?: ProjectStatus;
  total_episodes?: number;
  google_account_id?: string | null;
}

export interface SeriesBible {
  id: string;
  project_id: string;
  premise: string | null;
  main_plot: string | null;
  subplots: string[] | null;
  character_relationships: string | null;
  world_settings: string | null;
  tone_and_visual_style: string | null;
  ending_direction: string | null;
  episode_structure: string | null;
  created_at: string;
  updated_at: string;
}

export interface SeriesBibleCreate {
  premise?: string;
  main_plot?: string;
  subplots?: string[];
  character_relationships?: string;
  world_settings?: string;
  tone_and_visual_style?: string;
  ending_direction?: string;
  episode_structure?: string;
}

export interface SeriesBibleUpdate extends SeriesBibleCreate {}

export interface Character {
  id: string;
  project_id: string;
  name: string;
  role: string | null;
  order_index: number;
  age: string | null;
  gender: string | null;
  ethnicity: string | null;
  height: string | null;
  build: string | null;
  hair_color: string | null;
  hair_style: string | null;
  eye_color: string | null;
  skin_tone: string | null;
  distinguishing_features: string | null;
  personality_traits: string[] | null;
  background: string | null;
  motivations: string | null;
  fears: string | null;
  quirks: string | null;
  costume_style: string | null;
  signature_items: string[] | null;
  color_palette: string[] | null;
  reference_images: string[] | null;
  consistency_instructions: string | null;
  created_at: string;
  updated_at: string;
}

export interface CharacterCreate {
  name: string;
  role?: string;
  order_index?: number;
  age?: string;
  gender?: string;
  ethnicity?: string;
  height?: string;
  build?: string;
  hair_color?: string;
  hair_style?: string;
  eye_color?: string;
  skin_tone?: string;
  distinguishing_features?: string;
  personality_traits?: string[];
  background?: string;
  motivations?: string;
  fears?: string;
  quirks?: string;
  costume_style?: string;
  signature_items?: string[];
  color_palette?: string[];
  reference_images?: string[];
  consistency_instructions?: string;
}

export interface CharacterUpdate extends Partial<CharacterCreate> {}

export interface Location {
  id: string;
  project_id: string;
  name: string;
  type: string | null;
  order_index: number;
  description: string | null;
  environment_details: Record<string, any> | null;
  reference_images: string[] | null;
  visual_style_notes: string | null;
  lighting: Record<string, any> | null;
  atmosphere: string | null;
  time_of_day: string | null;
  weather: string | null;
  consistency_instructions: string | null;
  created_at: string;
  updated_at: string;
}

export interface LocationCreate {
  name: string;
  type?: string;
  order_index?: number;
  description?: string;
  environment_details?: Record<string, any>;
  reference_images?: string[];
  visual_style_notes?: string;
  lighting?: Record<string, any>;
  atmosphere?: string;
  time_of_day?: string;
  weather?: string;
  consistency_instructions?: string;
}

export interface LocationUpdate extends Partial<LocationCreate> {}

export enum EpisodeStatus {
  PLANNED = 'planned',
  OUTLINED = 'outlined',
  SCENES_WRITTEN = 'scenes_written',
  PROMPTS_READY = 'prompts_ready',
  IN_PRODUCTION = 'in_production',
  POST_PRODUCTION = 'post_production',
  COMPLETED = 'completed',
}

export enum SceneStatus {
  PLANNED = 'planned',
  WRITTEN = 'written',
  PROMPTS_READY = 'prompts_ready',
  GENERATING = 'generating',
  GENERATED = 'generated',
  APPROVED = 'approved',
  NEEDS_REVISION = 'needs_revision',
}

export enum ShotStatus {
  PLANNED = 'planned',
  PROMPT_READY = 'prompt_ready',
  GENERATING = 'generating',
  GENERATED = 'generated',
  APPROVED = 'approved',
  NEEDS_REVISION = 'needs_revision',
}

export interface Episode {
  id: string;
  project_id: string;
  episode_number: number;
  title: string | null;
  summary: string | null;
  status: EpisodeStatus;
  estimated_cost: number;
  actual_cost: number;
  production_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface EpisodeCreate {
  episode_number: number;
  title?: string;
  summary?: string;
}

export interface EpisodeUpdate {
  title?: string;
  summary?: string;
  status?: EpisodeStatus;
  estimated_cost?: number;
  actual_cost?: number;
  production_notes?: string;
}

export interface Scene {
  id: string;
  episode_id: string;
  scene_number: number;
  title: string | null;
  description: string | null;
  location_id: string | null;
  time_of_day: string | null;
  duration_estimate: number | null;
  status: SceneStatus;
  action: string | null;
  dialogue: string | null;
  characters_present: string[] | null;
  production_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SceneCreate {
  scene_number: number;
  title?: string;
  description?: string;
  location_id?: string;
  time_of_day?: string;
  duration_estimate?: number;
  action?: string;
  dialogue?: string;
  characters_present?: string[];
}

export interface SceneUpdate extends Partial<SceneCreate> {
  status?: SceneStatus;
  production_notes?: string;
}

export interface Shot {
  id: string;
  scene_id: string;
  shot_number: number;
  shot_type: string | null;
  camera_angle: string | null;
  camera_movement: string | null;
  duration: number | null;
  description: string | null;
  characters_in_shot: string[] | null;
  status: ShotStatus;
  image_prompt: string | null;
  video_prompt: string | null;
  generated_image_url: string | null;
  generated_video_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface ShotCreate {
  shot_number: number;
  shot_type?: string;
  camera_angle?: string;
  camera_movement?: string;
  duration?: number;
  description?: string;
  characters_in_shot?: string[];
}

export interface ShotUpdate extends Partial<ShotCreate> {
  status?: ShotStatus;
  image_prompt?: string;
  video_prompt?: string;
  generated_image_url?: string;
  generated_video_url?: string;
}

export enum PromptType {
  CHARACTER_IMAGE = 'character_image',
  LOCATION_IMAGE = 'location_image',
  SCENE_IMAGE = 'scene_image',
  VIDEO_GENERATION = 'video_generation',
  CAMERA_MOVEMENT = 'camera_movement',
  CHARACTER_ACTION = 'character_action',
  DIALOGUE_AUDIO = 'dialogue_audio',
  SOUND_EFFECT = 'sound_effect',
  MUSIC = 'music',
}

export enum PromptStatus {
  DRAFT = 'draft',
  FINALIZED = 'finalized',
  USED = 'used',
  ARCHIVED = 'archived',
}

export interface Prompt {
  id: string;
  project_id: string;
  episode_id: string | null;
  scene_id: string | null;
  shot_id: string | null;
  character_id: string | null;
  location_id: string | null;
  prompt_type: PromptType;
  title: string | null;
  prompt_text: string;
  negative_prompt: string | null;
  parameters: Record<string, any> | null;
  status: PromptStatus;
  version: number;
  parent_prompt_id: string | null;
  times_used: number;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface PromptCreate {
  prompt_type: PromptType;
  title?: string;
  prompt_text: string;
  negative_prompt?: string;
  parameters?: Record<string, any>;
  episode_id?: string;
  scene_id?: string;
  shot_id?: string;
  character_id?: string;
  location_id?: string;
}

export interface PromptUpdate {
  title?: string;
  prompt_text?: string;
  negative_prompt?: string;
  parameters?: Record<string, any>;
  status?: PromptStatus;
  version?: number;
}

export enum GoogleAccountStatus {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  EXPIRED = 'expired',
  ERROR = 'error',
}

export interface GoogleAccount {
  id: string;
  user_id: string;
  email: string;
  display_name: string | null;
  profile_picture: string | null;
  google_user_id: string | null;
  status: GoogleAccountStatus;
  last_verified_at: string | null;
  error_message: string | null;
  projects_assigned: number;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
  connected_at: string | null;
  disconnected_at: string | null;
}

export interface GoogleAccountConnect {
  email: string;
  session_data: string;
  expires_at?: string;
}

export enum FlowBridgeTaskStatus {
  PENDING = 'pending',
  PREPARING = 'preparing',
  READY_FOR_GENERATION = 'ready_for_generation',
  GENERATING = 'generating',
  WAITING_FOR_IMPORT = 'waiting_for_import',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export enum FlowBridgeAssetType {
  REFERENCE_IMAGE = 'reference_image',
  CHARACTER_IMAGE = 'character_image',
  LOCATION_IMAGE = 'location_image',
  STORYBOARD = 'storyboard',
  VIDEO_CLIP = 'video_clip',
  AUDIO_CLIP = 'audio_clip',
  SUBTITLE_FILE = 'subtitle_file',
  OTHER = 'other',
}

export interface FlowBridgeTask {
  id: string;
  project_id: string;
  episode_id: string | null;
  scene_id: string | null;
  shot_id: string | null;
  google_account_id: string | null;
  title: string;
  description: string | null;
  task_type: string | null;
  status: FlowBridgeTaskStatus;
  input_prompts: Record<string, any> | null;
  input_references: string[] | null;
  input_parameters: Record<string, any> | null;
  output_assets: string[] | null;
  generation_log: Record<string, any> | null;
  error_message: string | null;
  automation_data: Record<string, any> | null;
  manual_steps_completed: string[] | null;
  priority: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface FlowBridgeTaskCreate {
  title: string;
  description?: string;
  task_type?: string;
  input_prompts?: Record<string, any>;
  input_references?: string[];
  input_parameters?: Record<string, any>;
  priority?: number;
  episode_id?: string;
  scene_id?: string;
  shot_id?: string;
  google_account_id?: string;
}

export interface FlowBridgeTaskUpdate extends Partial<FlowBridgeTaskCreate> {
  status?: FlowBridgeTaskStatus;
  output_assets?: string[];
  generation_log?: Record<string, any>;
  error_message?: string;
  automation_data?: Record<string, any>;
  manual_steps_completed?: string[];
}

export interface FlowBridgeAsset {
  id: string;
  task_id: string;
  project_id: string;
  asset_type: FlowBridgeAssetType;
  title: string | null;
  description: string | null;
  file_path: string | null;
  file_url: string | null;
  file_size: number | null;
  mime_type: string | null;
  checksum: string | null;
  source: string | null;
  source_metadata: Record<string, any> | null;
  episode_id: string | null;
  scene_id: string | null;
  shot_id: string | null;
  character_id: string | null;
  location_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface FlowBridgeAssetCreate {
  asset_type: FlowBridgeAssetType;
  title?: string;
  description?: string;
  file_path?: string;
  file_url?: string;
  file_size?: number;
  mime_type?: string;
  checksum?: string;
  source?: string;
  source_metadata?: Record<string, any>;
  episode_id?: string;
  scene_id?: string;
  shot_id?: string;
  character_id?: string;
  location_id?: string;
}

export enum AuditAction {
  LOGIN = 'login',
  LOGOUT = 'logout',
  REGISTER = 'register',
  PASSWORD_CHANGE = 'password_change',
  PROJECT_CREATE = 'project_create',
  PROJECT_READ = 'project_read',
  PROJECT_UPDATE = 'project_update',
  PROJECT_DELETE = 'project_delete',
  SERIES_BIBLE_CREATE = 'series_bible_create',
  SERIES_BIBLE_READ = 'series_bible_read',
  SERIES_BIBLE_UPDATE = 'series_bible_update',
  SERIES_BIBLE_DELETE = 'series_bible_delete',
  CHARACTER_CREATE = 'character_create',
  CHARACTER_READ = 'character_read',
  CHARACTER_UPDATE = 'character_update',
  CHARACTER_DELETE = 'character_delete',
  LOCATION_CREATE = 'location_create',
  LOCATION_READ = 'location_read',
  LOCATION_UPDATE = 'location_update',
  LOCATION_DELETE = 'location_delete',
  EPISODE_CREATE = 'episode_create',
  EPISODE_READ = 'episode_read',
  EPISODE_UPDATE = 'episode_update',
  EPISODE_DELETE = 'episode_delete',
  SCENE_CREATE = 'scene_create',
  SCENE_READ = 'scene_read',
  SCENE_UPDATE = 'scene_update',
  SCENE_DELETE = 'scene_delete',
  SHOT_CREATE = 'shot_create',
  SHOT_READ = 'shot_read',
  SHOT_UPDATE = 'shot_update',
  SHOT_DELETE = 'shot_delete',
  PROMPT_CREATE = 'prompt_create',
  PROMPT_READ = 'prompt_read',
  PROMPT_UPDATE = 'prompt_update',
  PROMPT_DELETE = 'prompt_delete',
  PROMPT_EXPORT = 'prompt_export',
  GOOGLE_ACCOUNT_CONNECT = 'google_account_connect',
  GOOGLE_ACCOUNT_DISCONNECT = 'google_account_disconnect',
  GOOGLE_ACCOUNT_UPDATE = 'google_account_update',
  GOOGLE_ACCOUNT_VERIFY = 'google_account_verify',
  FLOW_TASK_CREATE = 'flow_task_create',
  FLOW_TASK_UPDATE = 'flow_task_update',
  FLOW_TASK_EXECUTE = 'flow_task_execute',
  FLOW_ASSET_UPLOAD = 'flow_asset_upload',
  FLOW_ASSET_DOWNLOAD = 'flow_asset_download',
  EXPORT_PROJECT = 'export_project',
  EXPORT_EPISODE = 'export_episode',
  EXPORT_PROMPTS = 'export_prompts',
}

export interface AuditLog {
  id: string;
  user_id: string;
  action: AuditAction;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  request_id: string | null;
  old_values: Record<string, any> | null;
  new_values: Record<string, any> | null;
  success: boolean;
  error_message: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export enum ExportFormat {
  JSON = 'json',
  TXT = 'txt',
  CSV = 'csv',
  PDF = 'pdf',
  MARKDOWN = 'markdown',
}

export enum ExportType {
  PROJECT = 'project',
  EPISODE = 'episode',
  PROMPTS = 'prompts',
  SERIES_BIBLE = 'series_bible',
  CHARACTERS = 'characters',
  LOCATIONS = 'locations',
  SCENES = 'scenes',
  FULL_PROJECT = 'full_project',
}

export interface ExportRequest {
  export_type: ExportType;
  format?: ExportFormat;
  project_id?: string;
  episode_id?: string;
  include_related?: boolean;
}

export interface ExportResponse {
  export_id: string;
  project_id: string;
  export_type: ExportType;
  format: ExportFormat;
  status: string;
  file_url: string | null;
  file_size: number | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}