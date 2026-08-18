from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.rag import allowed

scope = {"roles": ["department_user"], "department_id": "engineering", "sensitivity": "internal"}
assert allowed(scope, {"role": "department_user", "department_id": "engineering"})
assert not allowed(scope, {"role": "department_user", "department_id": "finance"})
assert allowed(scope, {"role": "reviewer", "department_id": "finance"})
print("RAG pre-retrieval access filtering passed")
