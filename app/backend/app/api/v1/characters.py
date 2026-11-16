from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional

from app.core.database import get_db
from app.api.v1.auth import get_current_user, create_audit_log
from app.models.user import User
from app.models.project import Project
from app.models.character import Character
from app.models.audit_log import AuditAction
from app.schemas.character import CharacterCreate, CharacterUpdate, CharacterResponse

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


@router.post("/{project_id}/characters", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(
    project_id: str,
    character_data: CharacterCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    # Check character count (max 6 per project as per requirements)
    count_result = await db.execute(
        select(func.count(Character.id)).where(Character.project_id == project_id)
    )
    count = count_result.scalar()
    if count >= 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 6 characters allowed per project"
        )
    
    character = Character(
        project_id=project_id,
        name=character_data.name,
        role=character_data.role,
        order_index=character_data.order_index,
        age=character_data.age,
        gender=character_data.gender,
        ethnicity=character_data.ethnicity,
        height=character_data.height,
        build=character_data.build,
        hair_color=character_data.hair_color,
        hair_style=character_data.hair_style,
        eye_color=character_data.eye_color,
        skin_tone=character_data.skin_tone,
        distinguishing_features=character_data.distinguishing_features,
        personality_traits=str(character_data.personality_traits) if character_data.personality_traits else None,
        background=character_data.background,
        motivations=character_data.motivations,
        fears=character_data.fears,
        quirks=character_data.quirks,
        costume_style=character_data.costume_style,
        signature_items=str(character_data.signature_items) if character_data.signature_items else None,
        color_palette=str(character_data.color_palette) if character_data.color_palette else None,
        reference_images=str(character_data.reference_images) if character_data.reference_images else None,
        consistency_instructions=character_data.consistency_instructions
    )
    db.add(character)
    await db.commit()
    await db.refresh(character)
    
    create_audit_log(
        db, current_user.id, AuditAction.CHARACTER_CREATE,
        resource_type="character", resource_id=character.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        new_values={"name": character.name, "role": character.role, "project_id": project_id}
    )
    await db.commit()
    
    return character


@router.get("/{project_id}/characters", response_model=List[CharacterResponse])
async def list_characters(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Character).where(Character.project_id == project_id).order_by(Character.order_index, Character.created_at)
    )
    characters = result.scalars().all()
    
    create_audit_log(
        db, current_user.id, AuditAction.CHARACTER_READ,
        resource_type="character", resource_id=project_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return characters


@router.get("/{project_id}/characters/{character_id}", response_model=CharacterResponse)
async def get_character(
    project_id: str,
    character_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Character).where(Character.id == character_id, Character.project_id == project_id)
    )
    character = result.scalar_one_or_none()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.CHARACTER_READ,
        resource_type="character", resource_id=character.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return character


@router.patch("/{project_id}/characters/{character_id}", response_model=CharacterResponse)
async def update_character(
    project_id: str,
    character_id: str,
    character_data: CharacterUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Character).where(Character.id == character_id, Character.project_id == project_id)
    )
    character = result.scalar_one_or_none()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    old_values = {
        "name": character.name,
        "role": character.role,
        "order_index": character.order_index,
        "age": character.age,
        "gender": character.gender,
        "ethnicity": character.ethnicity,
        "height": character.height,
        "build": character.build,
        "hair_color": character.hair_color,
        "hair_style": character.hair_style,
        "eye_color": character.eye_color,
        "skin_tone": character.skin_tone,
        "distinguishing_features": character.distinguishing_features,
        "personality_traits": character.personality_traits,
        "background": character.background,
        "motivations": character.motivations,
        "fears": character.fears,
        "quirks": character.quirks,
        "costume_style": character.costume_style,
        "signature_items": character.signature_items,
        "color_palette": character.color_palette,
        "reference_images": character.reference_images,
        "consistency_instructions": character.consistency_instructions
    }
    
    update_data = character_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ["personality_traits", "signature_items", "color_palette", "reference_images"] and value is not None:
            value = str(value)
        setattr(character, field, value)
    
    await db.commit()
    await db.refresh(character)
    
    new_values = {
        "name": character.name,
        "role": character.role,
        "order_index": character.order_index,
        "age": character.age,
        "gender": character.gender,
        "ethnicity": character.ethnicity,
        "height": character.height,
        "build": character.build,
        "hair_color": character.hair_color,
        "hair_style": character.hair_style,
        "eye_color": character.eye_color,
        "skin_tone": character.skin_tone,
        "distinguishing_features": character.distinguishing_features,
        "personality_traits": character.personality_traits,
        "background": character.background,
        "motivations": character.motivations,
        "fears": character.fears,
        "quirks": character.quirks,
        "costume_style": character.costume_style,
        "signature_items": character.signature_items,
        "color_palette": character.color_palette,
        "reference_images": character.reference_images,
        "consistency_instructions": character.consistency_instructions
    }
    
    create_audit_log(
        db, current_user.id, AuditAction.CHARACTER_UPDATE,
        resource_type="character", resource_id=character.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values=old_values,
        new_values=new_values
    )
    await db.commit()
    
    return character


@router.delete("/{project_id}/characters/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    project_id: str,
    character_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_or_404(project_id, current_user.id, db)
    
    result = await db.execute(
        select(Character).where(Character.id == character_id, Character.project_id == project_id)
    )
    character = result.scalar_one_or_none()
    
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )
    
    create_audit_log(
        db, current_user.id, AuditAction.CHARACTER_DELETE,
        resource_type="character", resource_id=character.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        old_values={"name": character.name}
    )
    
    await db.delete(character)
    await db.commit()