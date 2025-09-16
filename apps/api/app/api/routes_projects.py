from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from glocal_shared_schemas import Project as ProjectSchema
from glocal_shared_schemas import ProjectCreate, ProjectSummary
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps.auth import get_current_user
from app.models.entities import AppUser, Project

router = APIRouter()


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    db: AsyncSession = Depends(get_db), user: AppUser = Depends(get_current_user)
) -> list[ProjectSummary]:
    result = await db.execute(
        select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return [
        ProjectSummary(id=project.id, name=project.name, created_at=project.created_at)
        for project in projects
    ]


@router.post("", response_model=ProjectSummary, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: AppUser = Depends(get_current_user),
) -> ProjectSummary:
    new_project = Project(id=str(uuid.uuid4()), owner_id=user.id, name=payload.name)
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return ProjectSummary(
        id=new_project.id,
        name=new_project.name,
        created_at=new_project.created_at,
    )


@router.get("/{project_id}", response_model=ProjectSchema)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: AppUser = Depends(get_current_user),
) -> ProjectSchema:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == user.id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectSchema(
        id=project.id,
        owner_id=project.owner_id,
        name=project.name,
        created_at=project.created_at,
    )
