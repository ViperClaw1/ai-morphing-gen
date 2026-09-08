from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models import Asset, Job, Project


def test_project_asset_job_round_trip():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        project = Project(title="My morph")
        db.add(project)
        db.flush()

        asset = Asset(project_id=project.id, filename="a.jpg", order_index=0)
        job = Job(project_id=project.id, queue_name="preview_gpu")
        db.add_all([asset, job])
        db.commit()

        fetched_project = db.get(Project, project.id)
        fetched_asset = db.get(Asset, asset.id)
        fetched_job = db.get(Job, job.id)

    assert fetched_project.status == "draft"
    assert fetched_asset.project_id == project.id
    assert fetched_job.state == "queued"
    assert fetched_job.queue_name == "preview_gpu"
