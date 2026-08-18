from pathlib import Path

Path("/tmp/kmrl_synthetic_maintenance_manual.txt").write_text("""SYNTHETIC MAINTENANCE MANUAL MM-2026-09
\nBrake inspection frequency change\n\nEffective 01/09/2026, brake inspections for trainset TS-17 and all Series-2 trainsets change from every 30 days to every 14 days. The affected stakeholders are Rolling Stock Engineering and Maintenance Planning. Maintenance Planning must update the preventive-maintenance schedule, and Rolling Stock Engineering must record the inspection result after each cycle. Safety/Compliance must verify the first completed cycle.\n""")
print("/tmp/kmrl_synthetic_maintenance_manual.txt")
