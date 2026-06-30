"""Import all models so that Base.metadata knows about all tables.

This module is used by Alembic's env.py for autogenerate support.
Import this module (not base.py) when you need all models registered.
"""

from app.db.base import Base  # noqa: F401

# Import all models to register them with Base.metadata
from app.models.user import User  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.task_step import TaskStep  # noqa: F401
