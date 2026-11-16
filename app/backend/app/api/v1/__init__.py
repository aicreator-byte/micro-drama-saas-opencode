from app.api.v1 import auth, projects, series_bible, characters, locations, episodes, prompts, google_accounts, flow_bridge, audit_logs, story_engine, scene_engine, export, flow_bridge_automation
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(series_bible.router, prefix="/projects", tags=["Series Bible"])
api_router.include_router(characters.router, prefix="/projects", tags=["Characters"])
api_router.include_router(locations.router, prefix="/projects", tags=["Locations"])
api_router.include_router(episodes.router, prefix="/projects", tags=["Episodes & Scenes"])
api_router.include_router(prompts.router, prefix="/projects", tags=["Prompts"])
api_router.include_router(google_accounts.router, prefix="/google-accounts", tags=["Google Accounts"])
api_router.include_router(flow_bridge.router, prefix="/projects", tags=["Flow Bridge"])
api_router.include_router(story_engine.router, prefix="/projects", tags=["Story Engine"])
api_router.include_router(scene_engine.router, prefix="/projects", tags=["Scene Engine"])
api_router.include_router(export.router, prefix="/projects", tags=["Export"])
api_router.include_router(flow_bridge_automation.router, prefix="/projects", tags=["Flow Bridge Automation"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])