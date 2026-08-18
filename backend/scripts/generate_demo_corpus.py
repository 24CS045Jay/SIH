from __future__ import annotations
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage

ROOT = Path(__file__).resolve().parent / "demo_corpus"
ROOT.mkdir(parents=True, exist_ok=True)
WATERMARK = "SYNTHETIC DEMO DATA — NOT CONFIDENTIAL KMRL DATA"
RUN_MARKER = date.today().isoformat()
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=9, leading=12, textColor=colors.HexColor("#223247")))
styles.add(ParagraphStyle(name="HeadingBlue", parent=styles["Heading2"], fontSize=14, leading=18, textColor=colors.HexColor("#123b5d"), spaceBefore=7, spaceAfter=5))

DOCS = {
"Safety Circular S-101": {"department":"Safety/Compliance", "date":"18 August 2026", "subject":"Platform evacuation signage and emergency brake isolation review", "rows":[["Control", "Requirement", "Owner"],["S-101.1", "Review emergency brake isolation signage by 25 August 2026", "Safety/Compliance"],["S-101.2", "Brief station supervisors before the next drill", "Operations"],["S-101.3", "Record corrective evidence in the safety register", "Maintenance/Quality"]], "paras":["This fictional circular directs Safety/Compliance and Maintenance/Quality teams to review emergency brake isolation signage after a simulated platform event.", "Required action: complete the review by 25 August 2026 and brief station supervisors before the 30 August 2026 drill.", "Signal detail: the change is safety-related and should be routed to Safety/Compliance with support from Rolling Stock Engineering.", "Distractor: the staff cafeteria menu will change on 21 August 2026; this detail has no operational bearing."], "scan":"Scanned acknowledgement: supervisor initials S-101 / low-contrast copy / verify the date against the approved circular."},
"Maintenance Manual V2": {"department":"Rolling Stock Engineering", "date":"01 July 2026", "subject":"Brake inspection baseline", "rows":[["Section", "Baseline control", "Evidence"],["4.2", "Inspect fleet brakes every 30 days", "Inspection sheet"],["4.3", "Use the standard brake checklist", "Signed checklist"],["4.4", "Submit records within 30 days", "Maintenance register"]], "paras":["Brake inspection frequency: inspect every 30 days for fleet units.", "Maintenance checklist: use the standard brake checklist and sign the inspection sheet.", "Deadline: submit inspection records within 30 days of the maintenance circular.", "Distractor: the training room projector is scheduled for calibration on 12 July 2026."], "scan":"Scanned legacy note: archive box 14 / low-quality photocopy / confirm the inspection record number manually."},
"Maintenance Manual V3": {"department":"Rolling Stock Engineering", "date":"18 August 2026", "subject":"Brake inspection baseline", "rows":[["Section", "Baseline control", "Evidence"],["4.2", "Inspect fleet brakes every 30 days", "Inspection sheet"],["4.3", "Use the standard brake checklist", "Signed checklist"],["4.4", "Submit records within 30 days", "Maintenance register"]], "paras":["Brake inspection frequency: inspect every 14 days for fleet units.", "Maintenance checklist: use the revised brake checklist, including caliper photos, and sign the inspection sheet.", "Deadline: submit inspection records within 10 days of the maintenance circular.", "Distractor: the training room projector is scheduled for calibration on 12 July 2026."], "scan":"Scanned revised note: archive box 14 / low-quality photocopy / confirm the inspection record number manually."},
"Purchase Order Correspondence P-44": {"department":"Procurement/Finance", "date":"12 August 2026", "subject":"Vendor delivery clarification for platform door sensors", "rows":[["Reference", "Value", "Owner"],["P-44", "PO-2026-044", "Procurement/Finance"],["Vendor", "Metro Signal Components Pvt. Ltd.", "Procurement"],["Amount", "INR 845,000; tax invoice due 22 August 2026", "Finance"]], "paras":["Vendor entity: Metro Signal Components Pvt. Ltd. confirms delivery of platform door sensor assemblies against purchase order PO-2026-044.", "Required action: Procurement/Finance must reconcile the tax invoice by 22 August 2026 and Maintenance Planning must confirm receipt.", "Location: Stores Building B, Kalamassery depot; affected asset IDs are PDS-14 and PDS-15.", "Distractor: a stationery request for blue folders is included in the correspondence but is unrelated to the purchase order."], "scan":"Scanned vendor signature: M.S.C. Pvt Ltd / faint stamp / verify the invoice reference against the source."},
"Incident Report I-09": {"department":"Maintenance/Quality", "date":"09 August 2026", "subject":"Simulated door obstruction incident", "rows":[["Field", "Recorded value", "Evidence"],["Incident", "I-09", "Control-room log"],["Asset", "Platform door PDS-14", "Inspection note"],["Action due", "20 August 2026", "Corrective-action register"]], "paras":["Incident I-09 records a simulated platform door obstruction involving asset PDS-14 at Kaloor station on 09 August 2026.", "Required action: Maintenance/Quality must inspect the door sensor, document the root cause, and close the corrective-action record by 20 August 2026.", "Witness and location: the control-room operator reported the event at 09:40 near platform 2.", "Distractor: the weather log states light rain; it is retained for context but is not a causal finding."], "scan":"Scanned operator note: PDS-14 / 09:40 / low-contrast handwriting / review against the control-room log."},
"HR Training Notice H-12": {"department":"HR/Training", "date":"05 August 2026", "subject":"Mandatory human-factors refresher", "rows":[["Audience", "Course", "Due date"],["Station supervisors", "Human-factors refresher H-12", "31 August 2026"],["New reviewers", "Evidence-handling module", "05 September 2026"],["Evidence", "Attendance export", "HR/Training"]], "paras":["HR/Training Notice H-12 requires station supervisors and new document reviewers to complete a human-factors refresher.", "Required action: department managers must nominate attendees by 24 August 2026; course completion is due by 31 August 2026.", "Routing: HR/Training owns the attendance export and Department Users confirm local attendance.", "Distractor: the annual sports-day registration closes on 28 August 2026 and is unrelated to the training obligation."], "scan":"Scanned attendance slip: H-12 / nominee initials / low-quality photocopy / confirm the employee ID manually."},
"Environmental Compliance Note E-07": {"department":"Safety/Compliance", "date":"14 August 2026", "subject":"Waste-oil manifest retention", "rows":[["Control", "Requirement", "Deadline"],["E-07.1", "Retain waste-oil manifests", "30 September 2026"],["E-07.2", "Upload monthly evidence", "Within 7 days"],["E-07.3", "Review depot storage labels", "25 August 2026"]], "paras":["Environmental Compliance Note E-07 requires Maintenance/Quality and Safety/Compliance teams to retain waste-oil manifests for the depot audit.", "Required action: upload monthly evidence within 7 days and complete the storage-label review by 25 August 2026.", "Regulatory signal: the manifest retention record must be available to the compliance reviewer on 30 September 2026.", "Distractor: the landscaping contractor will trim the depot hedge on 22 August 2026; this is not an environmental control."], "scan":"Scanned manifest excerpt: drum code W-07 / faded ink / low-confidence region requiring manual verification."},
}

def watermark(canvas, doc):
    canvas.saveState(); canvas.setFont("Helvetica-Bold", 7); canvas.setFillColor(colors.HexColor("#8b97a6")); canvas.drawCentredString(A4[0] / 2, 10 * mm, WATERMARK); canvas.drawRightString(A4[0] - 12 * mm, 10 * mm, f"Page {doc.page}"); canvas.restoreState()

def make_scan(path: Path, title: str, text: str):
    image = Image.new("RGB", (1200, 800), "#dfdfd9"); draw = ImageDraw.Draw(image)
    try: font = ImageFont.truetype("DejaVuSans.ttf", 30); small = ImageFont.truetype("DejaVuSans.ttf", 22)
    except OSError: font = small = ImageFont.load_default()
    draw.text((70, 55), title, fill="#3b3b35", font=font)
    y = 170
    for line in [text[:72], text[72:144], "LOW-CONFIDENCE OCR REGION — VERIFY AGAINST SOURCE"]:
        draw.text((70, y), line, fill="#77776e" if "LOW" in line else "#4e4e49", font=small); y += 90
    draw.text((70, 650), WATERMARK, fill="#8a8a82", font=small)
    image.save(path, quality=35)

def make_pdf(name: str, data: dict):
    pdf = ROOT / f"{name}.pdf"; scan = ROOT / f"{name}_scan.jpg"; make_scan(scan, name, data["scan"])
    doc = SimpleDocTemplate(str(pdf), pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=15*mm, bottomMargin=18*mm)
    story = [Paragraph("KMRL DOCUMENT INTELLIGENCE PORTAL", styles["Heading1"]), Paragraph(name, styles["HeadingBlue"]), Paragraph(f"Fictional controlled copy · Issued {data['date']} · Department: {data['department']}", styles["BodySmall"]), Spacer(1, 7), Paragraph(f"Subject: {data['subject']}", styles["BodySmall"]), Spacer(1, 7)]
    for paragraph in data["paras"]: story += [Paragraph(paragraph, styles["BodySmall"]), Spacer(1, 5)]
    table = Table(data["rows"], colWidths=[36*mm, 86*mm, 45*mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#123b5d")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#aab4be")), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8), ("VALIGN", (0,0), (-1,-1), "TOP"), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f2f6f8")])]))
    story += [Spacer(1, 8), table, PageBreak(), Paragraph(f"{name} — scanned supporting page", styles["HeadingBlue"]), Spacer(1, 10), RLImage(str(scan), width=178*mm, height=119*mm), Spacer(1, 8), Paragraph("This scanned page is intentionally low quality for OCR-review demonstration. The amber low-confidence state must remain visible in the portal.", styles["BodySmall"])]
    doc.build(story, onFirstPage=watermark, onLaterPages=watermark)
    scan.unlink(missing_ok=True)

if __name__ == "__main__":
    for name, data in DOCS.items(): make_pdf(name, data)
    print(f"generated {len(DOCS)} watermarked PDFs in {ROOT}")
