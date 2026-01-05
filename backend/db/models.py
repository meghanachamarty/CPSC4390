"""minimized database models (no content field, no canvas_file_id).
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

class User(BaseModel):
    """user model"""
    id: Optional[UUID] = None
    auth_user_id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    canvas_api_token: Optional[str] = None  # encrypted canvas api token
    created_at: Optional[datetime] = None

class CanvasInstitution(BaseModel):
    """canvas institution model"""
    id: Optional[UUID] = None
    name: str
    canvas_domain: str
    canvas_base_url: str
    created_at: Optional[datetime] = None

class Course(BaseModel):
    """course model"""
    id: Optional[UUID] = None
    user_id: UUID
    institution_id: Optional[UUID] = None
    canvas_course_id: Optional[str] = None
    course_code: str
    course_name: str
    semester: Optional[str] = None
    is_active: bool = True
    last_synced_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

class CourseFile(BaseModel):
    """minimized course file model (no content, no canvas_file_id)"""
    id: Optional[UUID] = None
    course_id: UUID
    filename: str
    file_type: Optional[str] = None
    file_url: str  # required - url to file in storage
    storage_path: str  # required - path in storage bucket
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None
