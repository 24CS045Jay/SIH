from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.intelligence import analyze_pages

text = "CIRCULAR No. KMRL/RS/2026/043 Date: 18/08/2026. Safety inspection deadline is 18/09/2026. Rolling Stock Engineering must inspect asset TS-17 at Aluva Depot."
result = analyze_pages([(1, text)])
assert result.classification.document_type.value == "circular"
assert len(result.entities) >= 3
assert result.deadline.explicit_date == "18/09/2026", result.deadline
assert result.priority.reason_codes
assert result.summary.key_facts
print("strict intelligence schema and deadline selection passed")
