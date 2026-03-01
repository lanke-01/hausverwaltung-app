from fpdf import FPDF
from datetime import datetime

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    class NK_PDF(FPDF):
        def header(self):
            # Absender klein oben
            self.set_font("Helvetica", '', 8)
            self.cell(0, 5, "Murat Sayilik, Eintrachtstr. 160, 42277 Wuppertal", ln=True)
            self.ln(10)
            
            # Mieter-Adresse
            self.set_font("Helvetica", '', 11)
            self.cell(0, 6, str(mieter_name), ln=True)
            self.cell(0, 6, "Eintracht Straße 160", ln=True)
            self.cell(0, 6, "42277 Wuppertal", ln=True)
            self.ln(15)
            
            # Titel
            self.set_font("Helvetica", 'B', 16)
            self.cell(120, 10, "Nebenkostenabrechnung", 0, 0)
            self.set_font("Helvetica", '', 10)
            self.cell(0, 10, f"Erstellungsdatum: {datetime.now().strftime('%d.%m.%Y')}", 0, 1, 'R')
            
            # --- MIETZEITRAUM IM PDF HEADER ---
            self.ln(5)
            self.set_font("Helvetica", 'B', 11)
            self.cell(45, 8, "Mietzeitraum:", 0)
            self.set_font("Helvetica", '', 11)
            self.cell(0, 8, f"{zeitraum} ({tage} Tage)", ln=True)
            
            self.set_font("Helvetica", 'B', 11)
            self.cell(45, 8, "Objekt:", 0)
            self.set_font("Helvetica", '', 11)
            self.cell(0, 8, f"Wohnung {wohnung} - Eintrachtstr. 160", ln=True)
            self.ln(10)

    pdf = NK_PDF()
    pdf.add_page()
    
    # Tabelle Kopf
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(60, 10, "Kostenart", 1, 0, 'L', fill=True)
    pdf.cell(40, 10, "Gesamt Haus", 1, 0, 'C', fill=True)
    pdf.cell(50, 10, "Verteilerschlüssel", 1, 0, 'C', fill=True)
    pdf.cell(40, 10, "Ihr Anteil", 1, 1, 'C', fill=True)

    # Tabelle Inhalt
    pdf.set_font("Helvetica", '', 10)
    for row in tabelle:
        pdf.cell(60, 8, str(row['Kostenart']), 1)
        pdf.cell(40, 8, f"{row['Gesamtkosten']} EUR", 1, 0, 'R')
        pdf.cell(50, 8, str(row['Schlüssel']), 1, 0, 'C')
        pdf.cell(40, 8, f"{row['Ihr Anteil']} EUR", 1, 1, 'R')

    pdf.ln(10)
    
    # Ergebnis
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(150, 8, "Ihre anteiligen Gesamtkosten:", 0)
    pdf.cell(40, 8, f"{gesamt:.2f} EUR", 0, 1, 'R')
    pdf.cell(150, 8, "Ihre geleisteten Vorauszahlungen:", 0)
    pdf.cell(40, 8, f"{voraus:.2f} EUR", 0, 1, 'R')
    
    pdf.ln(2)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    label = "Nachzahlung:" if diff > 0 else "Guthaben:"
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(150, 10, label, 0)
    pdf.cell(40, 10, f"{abs(diff):.2f} EUR", 0, 1, 'R')

    # Footer
    pdf.set_y(-30)
    pdf.set_font("Helvetica", '', 8)
    bank = f"Bank: {h_stats.get('bank', '')} | IBAN: {h_stats.get('iban', '')} | Inhaber: {h_stats.get('name', '')}"
    pdf.cell(0, 4, bank, ln=True, align='C')

    path = f"/tmp/Abrechnung_Final.pdf"
    pdf.output(path)
    return path