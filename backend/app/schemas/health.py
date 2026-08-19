from datetime import datetime
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    timestamp: datetime
    database_reachable: bool = False
    migrations_current: bool = False
    demo_users_seeded: bool = False
