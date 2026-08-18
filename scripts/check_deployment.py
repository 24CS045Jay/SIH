from __future__ import annotations

import os
import sys
from urllib.request import Request, urlopen

BASE = os.getenv("KMRL_DEMO_URL", "http://localhost:8080").rstrip("/")
PATHS = ["/", "/health", "/api/v1/health"]

for path in PATHS:
    request = Request(BASE + path, headers={"Accept": "application/json,text/html"})
    with urlopen(request, timeout=10) as response:
        body = response.read().decode(errors="replace")
        assert response.status == 200, (path, response.status)
        print(f"{path}: {response.status} ({len(body)} bytes)")
print(f"deployment health check passed: {BASE}")
