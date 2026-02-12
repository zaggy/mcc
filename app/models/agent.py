import uuid
from datetime import datetime

from pydantic import BaseModel


class AgentRead(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    model_config_json: dict
    is_active: bool
    project_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentCreate(BaseModel):
    name: str
    type: str
    model_config_json: dict = {}
    system_prompt: str | None = None
    rules_file_path: str | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    model_config_json: dict | None = None
    system_prompt: str | None = None
    is_active: bool | None = None
