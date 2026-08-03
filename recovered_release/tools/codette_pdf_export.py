"""
Recovered from the Codette archives — see RECOVERY_MANIFEST.md
"""


# PDF Export for Codette Reasoning Outputs

from fpdf import FPDF

class ReasoningPDF:
    def __init__(self, title="Codette Report"):
        self.pdf = FPDF()
        self.pdf.add_page()
        self.pdf.set_font("Arial", size=12)
        self.title = title

    def add_reasoning(self, text_block):
        self.pdf.multi_cell(0, 10, text_block)

    def save(self, filename="Codette_Report.pdf"):
        self.pdf.output(filename)
