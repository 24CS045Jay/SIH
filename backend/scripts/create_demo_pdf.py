from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=14)
pdf.multi_cell(0, 10, "SYNTHETIC DEMO DOCUMENT RETRY\nRolling Stock Engineering review queue\nThis page contains enough selectable text for a high-confidence extraction test.")
pdf.add_page()
pdf.set_font("Arial", size=8)
pdf.cell(0, 10, "")
pdf.output("/tmp/kmrl_phase4_demo2.pdf")
print("/tmp/kmrl_phase4_demo2.pdf")
