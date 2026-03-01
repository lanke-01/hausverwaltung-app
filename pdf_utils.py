from fpdf import FPDF
from datetime import datetime

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    class NK_PDF(FPDF):
        def header(self):
            # 1. Absenderzeile ganz oben (klein)
            self.set_font("Helvetica", '', 8)
            abs_info = f"{h_stats.get('name', '')}, {h_stats.get('street', '')}, {h_stats.get('city', '')}"
            self.cell(0, 5, abs_info, ln=True)
            self.ln(10)
            
            # 2. Empfängeradresse
            self.set_font("Helvetica", '', 11)
            self.cell(0, 6, str(mieter_name), ln=True)
            self.cell(0, 6, h_stats.get('street', 'Eintracht Straße 160'), ln=True)
            self.cell(0, 6, h_stats.get('city', '42277 Wuppertal'), ln=True)
            self.ln(15)
            
            # 3. Titel
            self.set_font("Helvetica", 'B', 16)
            self.cell(120, 10, "Nebenkostenabrechnung", 0, 0)
            self.set_font("Helvetica", '', 10)
            self.cell(0, 10, f"Datum: {datetime.now().strftime('%d.%m.%Y')}", 0, 1, 'R')
            self.ln(5)

    pdf = NK_PDF()
    pdf.add_page()

    # --- HIER SIND DIE ÄNDERUNGEN FÜR DEN ZEITRAUM ---
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(45, 7, "Abrechnungszeitraum:", 0)
    pdf.set_font("Helvetica", '', 10)
    # Zeigt jetzt z.B. "01.01.2024 - 31.12.2024 (366 Tage)"
    pdf.cell(0, 7, f"{zeitraum} ({tage} Tage)", 0, 1)
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(45, 7, "Einheit / Wohnung:", 0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 7, str(wohnung), 0, 1)
    pdf.ln(10)

    # ... (Rest der Tabellen-Logik bleibt gleich) ...
    # Tabelle Kopf
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(75, 10, "Kostenart", 1, 0, 'L', fill=True)
    pdf.cell(35, 10, "Gesamt Haus", 1, 0, 'C', fill=True)
    pdf.cell(45, 10, "Verteilerschlüssel", 1, 0, 'C', fill=True)
    pdf.cell(35, 10, "Ihr Anteil", 1, 1, 'C', fill=True)

    pdf.set_font("Helvetica", '', 10)
    for row in tabelle:
        pdf.cell(75, 8, str(row['Kostenart']), 1)
        pdf.cell(35, 8, f"{row['Gesamtkosten']} EUR", 1, 0, 'R')
        pdf.cell(45, 8, str(row['Schlüssel']), 1, 0, 'C')
        pdf.cell(35, 8, f"{row['Ihr Anteil']} EUR", 1, 1, 'R')

    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(155, 10, "Gesamtkostenanteil:", 0)
    pdf.cell(35, 10, f"{gesamt:.2f} EUR", 0, 1, 'R')
    pdf.cell(155, 10, "Abzüglich Vorauszahlungen:", 0)
    pdf.cell(35, 10, f"{voraus:.2f} EUR", 0, 1, 'R')
    
    pdf.ln(2)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("Helvetica", 'B', 12)
    label = "Nachzahlung:" if diff > 0 else "Guthaben:"
    pdf.cell(155, 10, label, 0)
    pdf.cell(35, 10, f"{abs(diff):.2f} EUR", 0, 1, 'R')

    pdf.set_y(-30)
    pdf.set_font("Helvetica", '', 8)
    pdf.set_text_color(100, 100, 100)
    bank = f"Bank: {h_stats.get('bank', '')} | IBAN: {h_stats.get('iban', '')} | Vermieter: {h_stats.get('name', '')}"
    pdf.cell(0, 4, bank, ln=True, align='C')

    path = f"/tmp/NK_Abrechnung_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path