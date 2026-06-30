"""Schemas for Google Classroom data transfer."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ClassroomCourse(BaseModel):
    id: str
    name: str
    section: Optional[str] = None
    description: Optional[str] = None


class ClassroomCourseworkMaterial(BaseModel):
    title: str
    link: str


class ClassroomCoursework(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    alternate_link: Optional[str] = None
    materials: List[ClassroomCourseworkMaterial] = []


class ImportItem(BaseModel):
    coursework_id: str
    course_id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    alternate_link: Optional[str] = None
    materials: List[ClassroomCourseworkMaterial] = []


class ImportClassroomRequest(BaseModel):
    items: List[ImportItem]
