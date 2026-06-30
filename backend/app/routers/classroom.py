"""Router for Google Classroom integration."""

from datetime import datetime, timezone, time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task, TaskType, TaskStatus, AIPlanStatus
from app.schemas.classroom import (
    ClassroomCourse,
    ClassroomCoursework,
    ClassroomCourseworkMaterial,
    ImportClassroomRequest,
)
from app.services.google_service import get_classroom_service

router = APIRouter(prefix="/classroom", tags=["classroom"])


@router.get("/courses", response_model=List[ClassroomCourse])
def list_classroom_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List active Google Classroom courses for the authenticated user."""
    if not current_user.google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account is not connected. Please connect Google first.",
        )

    try:
        service = get_classroom_service(current_user, db)
        results = service.courses().list(courseStates="ACTIVE").execute()
        courses = results.get("courses", [])
        
        response_courses = []
        for course in courses:
            response_courses.append(
                ClassroomCourse(
                    id=course.get("id"),
                    name=course.get("name"),
                    section=course.get("section"),
                    description=course.get("descriptionHeading") or course.get("description"),
                )
            )
        return response_courses

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Classroom API error: {str(e)}",
        )


@router.get("/courses/{course_id}/coursework", response_model=List[ClassroomCoursework])
def list_coursework_items(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List coursework assignments for a given Classroom course."""
    if not current_user.google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account is not connected. Please connect Google first.",
        )

    try:
        service = get_classroom_service(current_user, db)
        results = service.courses().courseWork().list(courseId=course_id).execute()
        coursework_list = results.get("courseWork", [])

        response_items = []
        for item in coursework_list:
            # Parse due date & due time
            due_dt = None
            g_due_date = item.get("dueDate")
            if g_due_date:
                year = g_due_date.get("year")
                month = g_due_date.get("month")
                day = g_due_date.get("day")
                
                g_due_time = item.get("dueTime") or {}
                hour = g_due_time.get("hours", 23)
                minute = g_due_time.get("minutes", 59)
                
                # Assemble timezone-aware datetime in UTC
                due_dt = datetime(
                    year, month, day, hour, minute, tzinfo=timezone.utc
                )

            # Parse materials/attachments
            materials = []
            g_materials = item.get("materials", [])
            for m in g_materials:
                title = "Attachment"
                link = None
                if "driveFile" in m:
                    title = m["driveFile"]["driveFile"].get("title", "Google Drive File")
                    link = m["driveFile"]["driveFile"].get("alternateLink")
                elif "youtubeVideo" in m:
                    title = m["youtubeVideo"].get("title", "YouTube Video")
                    link = m["youtubeVideo"].get("alternateLink")
                elif "link" in m:
                    title = m["link"].get("title", "Web Link")
                    link = m["link"].get("url")
                elif "form" in m:
                    title = m["form"].get("title", "Google Form")
                    link = m["form"].get("formUrl")
                
                if link:
                    materials.append(ClassroomCourseworkMaterial(title=title, link=link))

            response_items.append(
                ClassroomCoursework(
                    id=item.get("id"),
                    title=item.get("title"),
                    description=item.get("description"),
                    due_date=due_dt,
                    alternate_link=item.get("alternateLink"),
                    materials=materials,
                )
            )

        return response_items

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Classroom API error: {str(e)}",
        )


@router.post("/import", status_code=status.HTTP_201_CREATED)
def import_classroom_assignments(
    data: ImportClassroomRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import selected coursework assignments as Tasks."""
    imported_tasks = []
    
    for item in data.items:
        # Build raw description by compiling instruction text and attachment links
        desc_parts = []
        if item.description:
            desc_parts.append(item.description)
            
        if item.materials:
            desc_parts.append("\n**Attachments & Resources:**")
            for m in item.materials:
                desc_parts.append(f"- [{m.title}]({m.link})")
                
        if item.alternate_link:
            desc_parts.append(f"\n[View assignment in Google Classroom]({item.alternate_link})")
            
        compiled_desc = "\n".join(desc_parts) if desc_parts else None

        task = Task(
            user_id=current_user.id,
            title=item.title,
            raw_description=compiled_desc,
            task_type=TaskType.assignment,
            due_date=item.due_date,
            status=TaskStatus.not_started,
            ai_plan_status=AIPlanStatus.not_generated,
        )
        db.add(task)
        imported_tasks.append(task)
        
    db.commit()
    return {"message": f"Successfully imported {len(imported_tasks)} tasks."}
