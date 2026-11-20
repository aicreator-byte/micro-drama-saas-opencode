from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import json
import uuid
import io

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project
from app.models.series_bible import SeriesBible
from app.models.character import Character
from app.models.location import Location
from app.models.episode import Episode, Scene, Shot
from app.models.prompt import Prompt
from app.models.audit_log import AuditAction
from app.schemas.export import (
    ExportRequest, ExportResponse, ExportFormat, ExportType,
    ProjectExportData, EpisodeExportData, PromptsExportData
)

router = APIRouter()


async def get_project_or_404(project_id: str, user_id: str, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


def serialize_model(model) -> Dict[str, Any]:
    """Convert SQLAlchemy model to dict."""
    if not model:
        return {}
    result = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, bytes):
            value = value.decode('utf-8', errors='ignore')
        result[column.name] = value
    return result


def make_json_serializable(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO format strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    elif hasattr(obj, 'model_dump'):
        return make_json_serializable(obj.model_dump(mode='json'))
    return obj


def _export_title(data: Dict[str, Any]) -> str:
    """Judul naskah dari data export apa pun bentuknya."""
    project = data.get("project") or {}
    episode = data.get("episode") or {}
    if isinstance(project, dict) and project.get("title"):
        return str(project["title"])
    if isinstance(episode, dict) and episode.get("title"):
        return str(episode["title"])
    episodes = data.get("episodes") or []
    if episodes and isinstance(episodes[0], dict) and episodes[0].get("title"):
        return str(episodes[0]["title"])
    return "Untitled"


def _export_scenes(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Kumpulkan scene dari semua bentuk data export (episode/full/scenes)."""
    scenes = data.get("scenes") or []
    if scenes:
        return [s for s in scenes if isinstance(s, dict)]
    # Bentuk project export: episode tidak membawa scene; tidak ada yang bisa dibuat.
    return []


def _scene_time_of_day(scene: Dict[str, Any]) -> str:
    tod = str(scene.get("time_of_day") or "").strip().lower()
    if "night" in tod or "malam" in tod or "evening" in tod:
        return "NIGHT"
    return "DAY"


def _parse_scene_dialogue(scene: Dict[str, Any]) -> List[Dict[str, str]]:
    """Parse kolom dialogue scene (JSON list / string) jadi baris dialog.

    Bentuk yang didukung: [{"character":..,"text":..}],
    [{"character_name":..,"dialogue_text":..,"parenthetical":..}],
    atau string biasa (diperlakukan sebagai satu aksi).
    """
    raw = scene.get("dialogue")
    if not raw:
        return []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str):
        try:
            items = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return [{"action": raw}]
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            return [{"action": str(raw)}]
    else:
        return []
    rows: List[Dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            rows.append({"action": item})
            continue
        if not isinstance(item, dict):
            continue
        char = item.get("character") or item.get("character_name") or ""
        text = item.get("text") or item.get("dialogue_text") or item.get("line") or ""
        if char and text:
            row: Dict[str, str] = {"character": str(char), "text": str(text)}
            if item.get("parenthetical"):
                row["parenthetical"] = str(item["parenthetical"])
            rows.append(row)
        elif text:
            rows.append({"action": str(text)})
        elif item.get("action"):
            rows.append({"action": str(item["action"])})
    return rows


def format_fountain(data: Dict[str, Any]) -> str:
    """Naskah screenplay format Fountain dari episode+scenes+dialogue.

    Bila data kosong tetap hasilkan Title Page minimal.
    """
    title = _export_title(data)
    lines: List[str] = [
        "Title: " + title,
        "Credit: Written by",
        "Draft date: " + datetime.now(timezone.utc).date().isoformat(),
        "",
        "",
    ]
    scenes = _export_scenes(data)
    episodes = data.get("episodes") or []
    if not scenes and episodes:
        # Bentuk full_project tanpa scene: satu slugline per episode.
        for i, ep in enumerate(episodes):
            if not isinstance(ep, dict):
                continue
            ep_title = str(ep.get("title") or f"Episode {ep.get('episode_number', i + 1)}")
            lines.append(f"INT. {ep_title.upper()} - DAY")
            lines.append("")
            if ep.get("summary"):
                lines.append(str(ep["summary"]))
                lines.append("")
            if i < len(episodes) - 1:
                lines.append("CUT TO:")
                lines.append("")
        return "\n".join(lines)

    for i, scene in enumerate(scenes):
        place = str(scene.get("title") or scene.get("description") or "Unknown Location")
        # Slugline Fountain: INT./EXT. + lokasi + waktu
        lines.append(f"INT. {place.strip().upper()} - {_scene_time_of_day(scene)}")
        lines.append("")
        if scene.get("description"):
            lines.append(str(scene["description"]))
            lines.append("")
        if scene.get("action"):
            lines.append(str(scene["action"]))
            lines.append("")
        for row in _parse_scene_dialogue(scene):
            if "character" in row:
                lines.append(row["character"].strip().upper())
                if row.get("parenthetical"):
                    lines.append(f"({row['parenthetical']})")
                lines.append(row["text"])
                lines.append("")
            else:
                lines.append(row["action"])
                lines.append("")
        if i < len(scenes) - 1:
            lines.append("CUT TO:")
            lines.append("")
    return "\n".join(lines)


def format_final_draft(data: Dict[str, Any]) -> str:
    """XML FDX (Final Draft) valid dari data export yang sama."""
    import xml.etree.ElementTree as ET

    title = _export_title(data)
    root = ET.Element("FinalDraft", {
        "DocumentType": "Script",
        "Template": "No",
        "Version": "1",
    })

    title_page = ET.SubElement(root, "TitlePage")
    tp_content = ET.SubElement(title_page, "Content")
    tp_para = ET.SubElement(tp_content, "Paragraph", {"Type": "Title"})
    tp_text = ET.SubElement(tp_para, "Text")
    tp_text.text = title

    content = ET.SubElement(root, "Content")
    scenes = _export_scenes(data)
    episodes = data.get("episodes") or []

    def add_para(ptype: str, text: str) -> None:
        para = ET.SubElement(content, "Paragraph", {"Type": ptype})
        el = ET.SubElement(para, "Text")
        el.text = text

    if not scenes and episodes:
        for ep in episodes:
            if not isinstance(ep, dict):
                continue
            ep_title = str(ep.get("title") or f"Episode {ep.get('episode_number', '')}")
            add_para("Scene Heading", f"INT. {ep_title.upper()} - DAY")
            if ep.get("summary"):
                add_para("Action", str(ep["summary"]))
        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    for scene in scenes:
        place = str(scene.get("title") or scene.get("description") or "Unknown Location")
        add_para("Scene Heading", f"INT. {place.strip().upper()} - {_scene_time_of_day(scene)}")
        if scene.get("description"):
            add_para("Action", str(scene["description"]))
        if scene.get("action"):
            add_para("Action", str(scene["action"]))
        for row in _parse_scene_dialogue(scene):
            if "character" in row:
                add_para("Character", row["character"].strip().upper())
                if row.get("parenthetical"):
                    add_para("Parenthetical", f"({row['parenthetical']})")
                add_para("Dialogue", row["text"])
            else:
                add_para("Action", row["action"])
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def format_export(data: Dict[str, Any], format: ExportFormat) -> tuple[bytes, str]:
    """Format export data according to format. Returns (content_bytes, mime_type)."""
    if format == ExportFormat.JSON:
        content = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
        mime = "application/json"
    elif format == ExportFormat.TXT:
        content = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
        mime = "text/plain"
    elif format == ExportFormat.MARKDOWN:
        # Simple markdown conversion
        md_lines = ["# Export Data", ""]
        def dict_to_md(d, prefix=""):
            for k, v in d.items():
                if isinstance(v, dict):
                    md_lines.append(f"{prefix}## {k}")
                    dict_to_md(v, prefix + "  ")
                elif isinstance(v, list):
                    md_lines.append(f"{prefix}## {k}")
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            md_lines.append(f"{prefix}### Item {i+1}")
                            dict_to_md(item, prefix + "    ")
                        else:
                            md_lines.append(f"{prefix}- {item}")
                else:
                    md_lines.append(f"{prefix}- **{k}**: {v}")
        dict_to_md(data)
        content = "\n".join(md_lines).encode('utf-8')
        mime = "text/markdown"
    elif format == ExportFormat.FOUNTAIN:
        content = format_fountain(data).encode('utf-8')
        mime = "text/x-fountain"
    elif format == ExportFormat.FINAL_DRAFT:
        content = format_final_draft(data).encode('utf-8')
        mime = "application/xml"
    elif format == ExportFormat.CSV:
        # Real CSV (audit F-15/P1-08): previously JSON bytes with a JSON
        # mime type. If the payload holds a top-level list of records
        # (characters/locations/scenes/prompts/shots/episodes), emit one
        # row per record; otherwise emit key,value rows for scalars.
        import csv as _csv
        buf = io.StringIO()
        list_key, rows = None, None
        for key in ("characters", "locations", "scenes", "shots", "prompts", "episodes"):
            value = data.get(key)
            if isinstance(value, list) and value and isinstance(value[0], dict):
                list_key, rows = key, value
                break
        if rows is not None:
            fieldnames: List[str] = []
            for row in rows:
                for k in row:
                    if k not in fieldnames:
                        fieldnames.append(k)
            writer = _csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: _csv_cell(row.get(k)) for k in fieldnames})
        else:
            writer = _csv.writer(buf)
            writer.writerow(["field", "value"])
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False)
                writer.writerow([k, v])
        content = buf.getvalue().encode('utf-8')
        mime = "text/csv"
    else:  # Fallback for any other format: JSON
        content = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
        mime = "application/json"

    return content, mime


def _csv_cell(value: Any) -> str:
    """Flatten one CSV cell value to a plain string."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


@router.post("/{project_id}/export", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
async def create_export(
    project_id: str,
    export_data: ExportRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    export_id = str(uuid.uuid4())
    
    try:
        # Gather data based on export type
        if export_data.export_type == ExportType.PROJECT:
            # Export project with all related data
            sb_result = await db.execute(select(SeriesBible).where(SeriesBible.project_id == project_id))
            series_bible = sb_result.scalar_one_or_none()
            
            char_result = await db.execute(select(Character).where(Character.project_id == project_id))
            characters = char_result.scalars().all()
            
            loc_result = await db.execute(select(Location).where(Location.project_id == project_id))
            locations = loc_result.scalars().all()
            
            ep_result = await db.execute(select(Episode).where(Episode.project_id == project_id))
            episodes = ep_result.scalars().all()
            
            prompt_result = await db.execute(select(Prompt).where(Prompt.project_id == project_id))
            prompts = prompt_result.scalars().all()
            
            data = ProjectExportData(
                project=serialize_model(project),
                series_bible=serialize_model(series_bible) if series_bible else None,
                characters=[serialize_model(c) for c in characters],
                locations=[serialize_model(l) for l in locations],
                episodes=[serialize_model(e) for e in episodes],
                prompts=[serialize_model(p) for p in prompts],
                exported_at=datetime.now(timezone.utc)
            ).model_dump()
            
        elif export_data.export_type == ExportType.EPISODE:
            if not export_data.episode_id:
                raise HTTPException(status_code=400, detail="episode_id required for episode export")
            
            ep_result = await db.execute(
                select(Episode).where(Episode.id == export_data.episode_id, Episode.project_id == project_id)
            )
            episode = ep_result.scalar_one_or_none()
            if not episode:
                raise HTTPException(status_code=404, detail="Episode not found")
            
            scene_result = await db.execute(select(Scene).where(Scene.episode_id == export_data.episode_id))
            scenes = scene_result.scalars().all()
            
            shot_ids = [s.id for s in scenes]
            shots = []
            if shot_ids:
                shot_result = await db.execute(select(Shot).where(Shot.scene_id.in_(shot_ids)))
                shots = shot_result.scalars().all()
            
            prompt_result = await db.execute(
                select(Prompt).where(Prompt.episode_id == export_data.episode_id)
            )
            prompts = prompt_result.scalars().all()
            
            data = EpisodeExportData(
                episode=serialize_model(episode),
                scenes=[serialize_model(s) for s in scenes],
                shots=[serialize_model(sh) for sh in shots],
                prompts=[serialize_model(p) for p in prompts],
                exported_at=datetime.now(timezone.utc)
            ).model_dump()
            
        elif export_data.export_type == ExportType.PROMPTS:
            prompt_result = await db.execute(select(Prompt).where(Prompt.project_id == project_id))
            prompts = prompt_result.scalars().all()
            
            data = PromptsExportData(
                prompts=[serialize_model(p) for p in prompts],
                exported_at=datetime.now(timezone.utc)
            ).model_dump()
            
        elif export_data.export_type == ExportType.SERIES_BIBLE:
            sb_result = await db.execute(select(SeriesBible).where(SeriesBible.project_id == project_id))
            series_bible = sb_result.scalar_one_or_none()
            if not series_bible:
                raise HTTPException(status_code=404, detail="Series Bible not found")
            data = serialize_model(series_bible)
            
        elif export_data.export_type == ExportType.CHARACTERS:
            char_result = await db.execute(select(Character).where(Character.project_id == project_id))
            characters = char_result.scalars().all()
            data = {"characters": [serialize_model(c) for c in characters], "exported_at": datetime.now(timezone.utc).isoformat()}
            
        elif export_data.export_type == ExportType.LOCATIONS:
            loc_result = await db.execute(select(Location).where(Location.project_id == project_id))
            locations = loc_result.scalars().all()
            data = {"locations": [serialize_model(l) for l in locations], "exported_at": datetime.now(timezone.utc).isoformat()}
            
        elif export_data.export_type == ExportType.SCENES:
            ep_result = await db.execute(select(Episode).where(Episode.project_id == project_id))
            episodes = ep_result.scalars().all()
            ep_ids = [e.id for e in episodes]
            scene_result = await db.execute(select(Scene).where(Scene.episode_id.in_(ep_ids)))
            scenes = scene_result.scalars().all()
            data = {"scenes": [serialize_model(s) for s in scenes], "exported_at": datetime.now(timezone.utc).isoformat()}
            
        elif export_data.export_type == ExportType.FULL_PROJECT:
            # Export everything
            sb_result = await db.execute(select(SeriesBible).where(SeriesBible.project_id == project_id))
            series_bible = sb_result.scalar_one_or_none()
            
            char_result = await db.execute(select(Character).where(Character.project_id == project_id))
            characters = char_result.scalars().all()
            
            loc_result = await db.execute(select(Location).where(Location.project_id == project_id))
            locations = loc_result.scalars().all()
            
            ep_result = await db.execute(select(Episode).where(Episode.project_id == project_id))
            episodes = ep_result.scalars().all()
            ep_ids = [e.id for e in episodes]
            
            scene_result = await db.execute(select(Scene).where(Scene.episode_id.in_(ep_ids))) if ep_ids else None
            scenes = scene_result.scalars().all() if scene_result else []
            scene_ids = [s.id for s in scenes]
            
            shot_result = await db.execute(select(Shot).where(Shot.scene_id.in_(scene_ids))) if scene_ids else None
            shots = shot_result.scalars().all() if shot_result else []
            
            prompt_result = await db.execute(select(Prompt).where(Prompt.project_id == project_id))
            prompts = prompt_result.scalars().all()
            
            data = {
                "project": serialize_model(project),
                "series_bible": serialize_model(series_bible) if series_bible else None,
                "characters": [serialize_model(c) for c in characters],
                "locations": [serialize_model(l) for l in locations],
                "episodes": [serialize_model(e) for e in episodes],
                "scenes": [serialize_model(s) for s in scenes],
                "shots": [serialize_model(sh) for sh in shots],
                "prompts": [serialize_model(p) for p in prompts],
                "exported_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unknown export type: {export_data.export_type}")
        
        # Make data JSON serializable (convert datetime objects)
        data = make_json_serializable(data)
        
        # Format the export
        content, mime_type = format_export(data, export_data.format)
        
        # In production, save to file storage (S3, local filesystem, etc.)
        # For now, return as base64 or provide download endpoint
        import base64
        file_url = f"data:{mime_type};base64,{base64.b64encode(content).decode()}"
        
        response = ExportResponse(
            export_id=export_id,
            project_id=project_id,
            export_type=export_data.export_type,
            format=export_data.format,
            status="completed",
            file_url=file_url,
            file_size=len(content),
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )
        
        # Safe audit action lookup
        audit_action_name = f"EXPORT_{export_data.export_type.value.upper()}"
        audit_action = getattr(AuditAction, audit_action_name, AuditAction.EXPORT_PROJECT)
        
        create_audit_log(
            db, current_user.id, audit_action,
            resource_type="export", resource_id=export_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            new_values={"export_type": export_data.export_type.value, "format": export_data.format.value, "size": len(content), "episode_id": export_data.episode_id}
        )
        await db.commit()
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        create_audit_log(
            db, current_user.id, AuditAction.EXPORT_PROJECT,
            resource_type="export", resource_id=export_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            success=False,
            error_message=str(e)
        )
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/{project_id}/export/history", response_model=List[ExportResponse])
async def list_exports(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get export history from audit logs."""
    project = await get_project_or_404(project_id, current_user.id, db)
    
    from app.models.audit_log import AuditLog
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.user_id == current_user.id,
            AuditLog.resource_type == "export",
            AuditLog.action.in_([
                AuditAction.EXPORT_PROJECT,
                AuditAction.EXPORT_EPISODE,
                AuditAction.EXPORT_PROMPTS,
                AuditAction.EXPORT_SERIES_BIBLE,
                AuditAction.EXPORT_CHARACTERS,
                AuditAction.EXPORT_LOCATIONS,
                AuditAction.EXPORT_SCENES,
                AuditAction.EXPORT_FULL_PROJECT,
            ])
        ).order_by(AuditLog.created_at.desc()).limit(50)
    )
    logs = result.scalars().all()
    
    exports = []
    for log in logs:
        new_vals = json.loads(log.new_values) if log.new_values else {}
        exports.append(ExportResponse(
            export_id=log.resource_id,
            project_id=project_id,
            export_type=ExportType(new_vals.get("export_type", "project")),
            format=ExportFormat(new_vals.get("format", "json")),
            status="completed" if log.success else "failed",
            file_size=new_vals.get("size"),
            error_message=log.error_message,
            created_at=log.created_at,
            completed_at=log.created_at if log.success else None
        ))
    
    return exports


@router.get("/{project_id}/export/{export_id}/download")
async def download_export(
    project_id: str,
    export_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download a previously created export (regenerates deterministically
    from the current DB rows, audit F-15 — previously a 307 stub)."""
    from fastapi.responses import Response as FastAPIResponse
    import base64

    project = await get_project_or_404(project_id, current_user.id, db)

    # Check audit log for this export
    from app.models.audit_log import AuditLog
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.resource_id == export_id,
            AuditLog.user_id == current_user.id,
            AuditLog.resource_type == "export"
        )
    )
    log = result.scalar_one_or_none()

    if not log or not log.success:
        raise HTTPException(status_code=404, detail="Export not found or failed")

    # Regenerate the same export from live data and serve the bytes.
    new_vals = json.loads(log.new_values) if log.new_values else {}
    export_type = ExportType(new_vals.get("export_type", "project"))
    format = ExportFormat(new_vals.get("format", "json"))
    export_req = ExportRequest(
        export_type=export_type,
        format=format,
        project_id=project_id,
        episode_id=new_vals.get("episode_id"),
    )
    regenerated = await create_export(project_id, export_req, request, current_user, db)
    file_url = regenerated.file_url or ""
    if ";base64," not in file_url:
        raise HTTPException(status_code=500, detail="Regenerated export has no downloadable content")
    mime_type, b64 = file_url.split(";base64,", 1)
    mime_type = mime_type.replace("data:", "", 1) or "application/octet-stream"
    content = base64.b64decode(b64)
    ext = {"application/json": "json", "text/markdown": "md", "text/plain": "txt", "text/csv": "csv", "text/x-fountain": "fountain", "application/xml": "fdx"}.get(mime_type, "bin")
    filename = f"export-{export_id}.{ext}"
    return FastAPIResponse(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Quick export endpoints for common use cases
@router.get("/{project_id}/export/project")
async def quick_export_project(
    project_id: str,
    format: ExportFormat = Query(ExportFormat.JSON),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Quick export entire project."""
    export_req = ExportRequest(
        export_type=ExportType.FULL_PROJECT,
        format=format,
        project_id=project_id
    )
    return await create_export(project_id, export_req, request, current_user, db)


@router.get("/{project_id}/export/episode/{episode_id}")
async def quick_export_episode(
    project_id: str,
    episode_id: str,
    format: ExportFormat = Query(ExportFormat.JSON),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Quick export single episode."""
    export_req = ExportRequest(
        export_type=ExportType.EPISODE,
        format=format,
        project_id=project_id,
        episode_id=episode_id
    )
    return await create_export(project_id, export_req, request, current_user, db)


@router.get("/{project_id}/export/prompts")
async def quick_export_prompts(
    project_id: str,
    format: ExportFormat = Query(ExportFormat.JSON),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Quick export all prompts."""
    export_req = ExportRequest(
        export_type=ExportType.PROMPTS,
        format=format,
        project_id=project_id
    )
    return await create_export(project_id, export_req, request, current_user, db)