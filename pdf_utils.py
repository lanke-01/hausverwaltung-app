from fpdf import FPDF
from datetime import datetime
import re

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
            
            # Titel und Datum
            self.set_font("Helvetica", 'B', 16)
            self.cell(120, 10, "Nebenkostenabrechnung", 0, 0)
            self.set_font("Helvetica", '', 10)
            self.cell(0, 10, f"Erstellungsdatum: {datetime.now().strftime('%d.%m.%Y')}", 0, 1, 'R')
            
            # Mietzeitraum fett hervorheben
            self.ln(5)
            self.set_font("Helvetica", 'B', 11)
            self.cell(45, 8, "Mietzeitraum:", 0)
            self.set_font("Helvetica", '', 11)
            self.cell(0, 8, f"{zeitraum} ({tage} Tage)", ln=True)
            
            self.set_font("Helvetica", 'B', 11)
            self.cell(45, 8, "Wohnung:", 0)
            self.set_font("Helvetica", '', 11)
            self.cell(0, 8, f"{wohnung} - Eintracht Straße 160, 42277 Wuppertal", ln=True)
            self.ln(10)

    pdf = NK_PDF()
    pdf.add_page()
    
    # --- BOX 1: ALLGEMEINE ANGABEN ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 8, "Allgemeine Angaben zur Wohnung und zu den Verteilungsschlüsseln", 0, 1, 'L', fill=True)
    pdf.set_font("Helvetica", '', 9)
    
    col_w = 47
    pdf.cell(col_w, 7, "Ihre Nutzungstage:", 0)
    pdf.cell(col_w, 7, f"{tage} Tage", 0)
    pdf.cell(col_w, 7, "m2 Wohnung:", 0)
    pdf.cell(col_w, 7, f"{m_stats['area']:.2f} m2", 0, 1)
    
    pdf.cell(col_w, 7, "Personen:", 0)
    pdf.cell(col_w, 7, f"{m_stats['occupants']}", 0)
    pdf.cell(col_w, 7, "Gesamtwohnfläche:", 0)
    pdf.cell(col_w, 7, f"{h_stats['total_area']:.2f} m2", 0, 1)
    pdf.ln(5)

    # --- BOX 2: KOSTENTABELLE ---
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 8, "Gesamtkosten und Verteilung", 0, 1, 'L', fill=True)
    
    pdf.set_font("Helvetica", 'B', 8)
    h = 8
    pdf.cell(50, h, "Kostenart", 1)
    pdf.cell(35, h, "Gesamtkosten Haus", 1)
    pdf.cell(35, h, "Verteilerschlüssel", 1)
    pdf.cell(35, h, "Tage Faktor", 1)
    pdf.cell(35, h, "Ihr Anteil", 1, 1)

    pdf.set_font("Helvetica", '', 8)
    for row in tabelle:
        pdf.cell(50, h, str(row['Kostenart']), 1)
        pdf.cell(35, h, f"{row['Gesamtkosten']} EUR", 1)
        pdf.cell(35, h, str(row['Schlüssel']), 1)
        pdf.cell(35, h, f"{tage} Tage", 1)
        pdf.cell(35, h, f"{row['Ihr Anteil']} EUR", 1, 1)

    pdf.ln(5)

    # --- BOX 3: ABRECHNUNGSERGEBNIS ---
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(100, 8, "Ihr Nebenkostenanteil:", 0)
    pdf.cell(40, 8, f"{gesamt:.2f} EUR", 0, 1, 'R')
    
    pdf.cell(100, 8, "Ihre Nebenkostenvorauszahlung:", 0)
    pdf.cell(40, 8, f"{voraus:.2f} EUR", 0, 1, 'R')
    
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    
    label = "Zu zahlender Betrag:" if diff > 0 else "Guthaben / Rückerstattung:"
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(100, 12, label, 0)
    pdf.cell(40, 12, f"{abs(diff):.2f} EUR", 0, 1, 'R')
    
    # Bankdaten Footer
    pdf.set_y(-30)
    pdf.set_font("Helvetica", '', 8)
    bank_info = f"Bank: {h_stats.get('bank', '')} | IBAN: {h_stats.get('iban', '')} | Inhaber: {h_stats.get('name', '')}"
    pdf.cell(0, 4, bank_info, ln=True, align='C')

    zeit_suffix = re.sub(r'[^0-9]', '', zeitraum) 
    path = f"/tmp/Abrechnung_{mieter_name.replace(' ', '_')}_{zeit_suffix}.pdf"
    pdf.output(path)
    return path