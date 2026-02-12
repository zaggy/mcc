import uuid
from datetime import datetime

from pydantic import BaseModel


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    github_repo: str
    is_active: bool
    owner_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    github_repo: str
    github_app_id: str | None = None
    github_installation_id: str | None = None
