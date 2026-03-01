from fpdf import FPDF
from datetime import datetime

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    class NK_PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", '', 8)
            self.cell(0, 5, f"{h_stats.get('name')}, {h_stats.get('street')}, {h_stats.get('city')}", ln=True)
            self.ln(10)
            self.set_font("Helvetica", '', 11)
            self.cell(0, 6, str(mieter_name), ln=True)
            self.cell(0, 6, h_stats.get('street'), ln=True)
            self.cell(0, 6, h_stats.get('city'), ln=True)
            self.ln(15)
            self.set_font("Helvetica", 'B', 16)
            self.cell(120, 10, "Nebenkostenabrechnung", 0, 0)
            self.set_font("Helvetica", '', 10)
            self.cell(0, 10, f"Datum: {datetime.now().strftime('%d.%m.%Y')}", 0, 1, 'R')
            self.ln(5)
            self.set_font("Helvetica", 'B', 11)
            self.cell(45, 8, "Mietzeitraum:", 0)
            self.set_font("Helvetica", '', 11)
            self.cell(0, 8, f"{zeitraum} ({tage} Tage)", ln=True)
            self.ln(10)

    pdf = NK_PDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(70, 10, "Kostenart", 1, 0, 'L')
    pdf.cell(40, 10, "Haus Gesamt", 1, 0, 'C')
    pdf.cell(40, 10, "Anteil Mieter", 1, 1, 'C')
    pdf.set_font("Helvetica", '', 10)
    for row in tabelle:
        pdf.cell(70, 8, row['Kostenart'], 1)
        pdf.cell(40, 8, f"{row['Gesamtkosten']} EUR", 1, 0, 'R')
        pdf.cell(40, 8, f"{row['Ihr Anteil']} EUR", 1, 1, 'R')
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(110, 10, "Gesamtkostenanteil:", 0)
    pdf.cell(40, 10, f"{gesamt:.2f} EUR", 0, 1, 'R')
    pdf.cell(110, 10, "Vorauszahlungen:", 0)
    pdf.cell(40, 10, f"{voraus:.2f} EUR", 0, 1, 'R')
    pdf.ln(2)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.cell(110, 10, "Saldo:", 0)
    pdf.cell(40, 10, f"{diff:.2f} EUR", 0, 1, 'R')
    path = f"/tmp/Abrechnung_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path

def generate_payment_history_pdf(mieter_name, jahr, history_data, h_stats):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(0, 5, f"{h_stats.get('name')}, {h_stats.get('street')}, {h_stats.get('city')}", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"Zahlungsverlauf {jahr} - {mieter_name}", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(40, 10, "Monat", 1)
    pdf.cell(40, 10, "Soll", 1)
    pdf.cell(40, 10, "Ist", 1)
    pdf.cell(40, 10, "Saldo", 1, 1)
    pdf.set_font("Helvetica", '', 10)
    for row in history_data:
        pdf.cell(40, 8, row['Monat'], 1)
        pdf.cell(40, 8, row['Soll (€)'], 1)
        pdf.cell(40, 8, row['Ist (€)'], 1)
        pdf.cell(40, 8, row['Saldo (€)'], 1, 1)
    path = f"/tmp/Kontoauszug_{mieter_name.replace(' ', '_')}_{jahr}.pdf"
    pdf.output(path)
    return path