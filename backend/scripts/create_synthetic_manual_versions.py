from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
now = time.time()
(ROOT / "maintenance_manual_v2.txt").write_text(f"""Maintenance Manual — Brake Inspection Frequency

Phase 8 verification batch: {now}

Brake inspection frequency: inspect every 30 days for fleet units.

Maintenance checklist: use the standard brake checklist and sign the inspection sheet.

Deadline: submit inspection records within 30 days of the maintenance circular.
""")
(ROOT / "maintenance_manual_v3.txt").write_text(f"""Maintenance Manual — Brake Inspection Frequency

Phase 8 verification batch: {now}

Brake inspection frequency: inspect every 14 days for fleet units.

Maintenance checklist: use the revised brake checklist, including caliper photos, and sign the inspection sheet.

Deadline: submit inspection records within 10 days of the maintenance circular.
""")
print("created maintenance_manual_v2.txt and maintenance_manual_v3.txt")
