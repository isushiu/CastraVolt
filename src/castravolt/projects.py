from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from castravolt.account_models import User
from castravolt.auth import csrf, current_user, database, now
from castravolt.project_models import Prediction, Project, Site
from castravolt.locations import resolve_state

router = APIRouter(prefix='/api/v1', tags=['Projects'])
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
SITE_CATEGORIES = ['Strata', 'Shopping Mall', 'Office', 'Showroom', 'Hotel & Resort', 'Others', 'F&B',
    'Petrol Station', 'Recreation Center', 'Hospital', 'Galleria', 'Petrol Station - Highway',
    'Prayer Hall', 'University', 'Convention Center', 'Airport', 'Highway', 'R&R', 'Entertainment',
    'Library', 'Residences', 'Theme Park', 'Services', 'Unknown']


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class ProjectInput(Input):
    name: Name
    description: str = Field(default='', max_length=2000)


class PatchInput(Input):
    @model_validator(mode='after')
    def no_explicit_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError('Fields cannot be null')
        return self


class ProjectPatch(PatchInput):
    name: Name | None = None
    description: str | None = Field(default=None, max_length=2000)


class ProjectResult(ProjectInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class SiteInput(Input):
    name: Name
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    category: str
    address: str = Field(default='', max_length=500)

    @model_validator(mode='after')
    def known_category(self):
        if self.category not in SITE_CATEGORIES: raise ValueError('Choose a supported category')
        return self


class SitePatch(PatchInput):
    name: Name | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    category: str | None = None
    address: str | None = Field(default=None, max_length=500)

    @model_validator(mode='after')
    def site_fields(self):
        if self.category is not None and self.category not in SITE_CATEGORIES: raise ValueError('Choose a supported category')
        return self


class SiteResult(SiteInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    state: str | None
    created_at: datetime
    updated_at: datetime


class PredictionResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    site_id: UUID
    input_snapshot: dict
    raw_estimate: float
    displayed_total: int
    model_version: str
    extraction_rule_version: str
    poi_timestamp: datetime
    adoption_reference_year: int
    adoption_value: int
    rounding_policy: str
    created_at: datetime


def owned_project(db, owner, project_id, lock=False):
    query = select(Project).where(Project.id == project_id, Project.owner_id == owner.id)
    if lock: query = query.with_for_update()
    project = db.scalar(query)
    if project is None: raise HTTPException(404, 'Project not found.')
    return project


def owned_site(db, owner, site_id, lock=False):
    query = select(Site).join(Project).where(Site.id == site_id, Project.owner_id == owner.id)
    site = db.scalar(query)
    if site is None: raise HTTPException(404, 'Site not found.')
    if lock:
        # Parent first, matching project deletion and site creation lock order.
        owned_project(db, owner, site.project_id, lock=True)
        site = db.scalar(select(Site).where(Site.id == site_id).with_for_update().execution_options(populate_existing=True))
        if site is None: raise HTTPException(404, 'Site not found.')
    return site


@router.get('/reference/site-categories', response_model=list[str])
def categories(user: User = Depends(current_user)):
    return SITE_CATEGORIES


@router.get('/projects', response_model=list[ProjectResult])
def projects(user: User = Depends(current_user), db: Session = Depends(database)):
    return db.scalars(select(Project).where(Project.owner_id == user.id).order_by(Project.updated_at.desc(), Project.id)).all()


@router.post('/projects', response_model=ProjectResult, status_code=201, dependencies=[Depends(csrf)])
def create_project(data: ProjectInput, user: User = Depends(current_user), db: Session = Depends(database)):
    project = Project(owner_id=user.id, **data.model_dump(), created_at=now(), updated_at=now())
    db.add(project); db.commit()
    return project


@router.get('/projects/{project_id}', response_model=ProjectResult)
def project(project_id: UUID, user: User = Depends(current_user), db: Session = Depends(database)):
    return owned_project(db, user, project_id)


@router.patch('/projects/{project_id}', response_model=ProjectResult, dependencies=[Depends(csrf)])
def edit_project(project_id: UUID, data: ProjectPatch, user: User = Depends(current_user), db: Session = Depends(database)):
    project = owned_project(db, user, project_id, lock=True)
    for key, value in data.model_dump(exclude_unset=True).items(): setattr(project, key, value)
    project.updated_at = now(); db.commit()
    return project


@router.delete('/projects/{project_id}', status_code=204, dependencies=[Depends(csrf)])
def delete_project(project_id: UUID, user: User = Depends(current_user), db: Session = Depends(database)):
    db.delete(owned_project(db, user, project_id, lock=True)); db.commit()
    return Response(status_code=204)


@router.get('/projects/{project_id}/sites', response_model=list[SiteResult])
def sites(project_id: UUID, user: User = Depends(current_user), db: Session = Depends(database)):
    owned_project(db, user, project_id)
    return db.scalars(select(Site).where(Site.project_id == project_id).order_by(Site.updated_at.desc(), Site.id)).all()


@router.post('/projects/{project_id}/sites', response_model=SiteResult, status_code=201, dependencies=[Depends(csrf)])
def create_site(project_id: UUID, data: SiteInput, user: User = Depends(current_user), db: Session = Depends(database)):
    project = owned_project(db, user, project_id, lock=True)
    site = Site(project_id=project_id, **data.model_dump(), state=resolve_state(data.latitude,data.longitude), created_at=now(), updated_at=now())
    project.updated_at = now()
    db.add(site); db.commit()
    return site


@router.get('/sites/{site_id}', response_model=SiteResult)
def site(site_id: UUID, user: User = Depends(current_user), db: Session = Depends(database)):
    return owned_site(db, user, site_id)


@router.patch('/sites/{site_id}', response_model=SiteResult, dependencies=[Depends(csrf)])
def edit_site(site_id: UUID, data: SitePatch, user: User = Depends(current_user), db: Session = Depends(database)):
    site = owned_site(db, user, site_id, lock=True)
    fields = data.model_dump(exclude_unset=True)
    if 'latitude' in fields or 'longitude' in fields:
        site.state = resolve_state(fields.get('latitude',site.latitude),fields.get('longitude',site.longitude))
    for key, value in fields.items(): setattr(site, key, value)
    site.updated_at = now()
    owned_project(db, user, site.project_id).updated_at = now()
    db.commit()
    return site


@router.delete('/sites/{site_id}', status_code=204, dependencies=[Depends(csrf)])
def delete_site(site_id: UUID, user: User = Depends(current_user), db: Session = Depends(database)):
    site = owned_site(db, user, site_id, lock=True)
    owned_project(db, user, site.project_id).updated_at = now()
    db.delete(site); db.commit()
    return Response(status_code=204)


@router.get('/sites/{site_id}/predictions', response_model=list[PredictionResult])
def history(site_id: UUID, user: User = Depends(current_user), db: Session = Depends(database)):
    owned_site(db, user, site_id)
    return db.scalars(select(Prediction).where(Prediction.site_id == site_id).order_by(Prediction.created_at.desc(), Prediction.id)).all()


@router.get('/predictions/{prediction_id}', response_model=PredictionResult)
def prediction(prediction_id: UUID, user: User = Depends(current_user), db: Session = Depends(database)):
    result = db.scalar(select(Prediction).join(Site).join(Project).where(Prediction.id == prediction_id, Project.owner_id == user.id))
    if result is None: raise HTTPException(404, 'Prediction not found.')
    return result
