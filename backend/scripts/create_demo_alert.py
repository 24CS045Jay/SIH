from __future__ import annotations
import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models import Alert, ActionPriority, DocumentVersion, AlertStatus, RoutingState

async def main():
    async with AsyncSessionLocal() as session:
        version = (await session.execute(select(DocumentVersion).order_by(DocumentVersion.uploaded_at.desc()).limit(1))).scalar_one()
        alert = Alert(source_version_id=version.id, title="Synthetic critical brake inspection alert", priority=ActionPriority.CRITICAL, reason_codes=["Safety-related change", "Regulatory deadline detected"], suggested_department="Rolling Stock Engineering", suggested_action="Review brake inspection frequency and update the maintenance schedule.", source_excerpt="Synthetic maintenance evidence requires a brake inspection frequency update.", status=AlertStatus.DRAFT, routing_state=RoutingState.PENDING)
        session.add(alert); await session.commit(); print(alert.id)

asyncio.run(main())
