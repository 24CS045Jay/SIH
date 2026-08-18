from datetime import datetime, timezone
from app.jobs.celery_app import celery_app


@celery_app.task(name="kmrl.jobs.ping")
def ping_job() -> dict[str, str]:
    return {"status": "pong", "completed_at": datetime.now(timezone.utc).isoformat()}
