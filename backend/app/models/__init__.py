# ORM models attach to app.core.db.Base. Imported here so Base.metadata.create_all()
# (called from app.main's startup) sees every table, even though nothing above imports
# these classes directly.
from app.models.asset import Asset
from app.models.job import Job
from app.models.project import Project

__all__ = ["Asset", "Job", "Project"]
