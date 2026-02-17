from fpdf import FPDF

class NK_PDF(FPDF):
    def __init__(self, landlord_data):
        super().__init__()
        self.ld = landlord_data

    def header(self):
        # Briefkopf des Vermieters
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, f"{self.ld.get('name', '')}", ln=True, align='R')
        self.set_font('Arial', '', 9)
        self.cell(0, 5, f"{self.ld.get('street', '')}", ln=True, align='R')
        self.cell(0, 5, f"{self.ld.get('city', '')}", ln=True, align='R')
        self.ln(10)
        
    def footer(self):
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f"Bankverbindung: {self.ld.get('bank', '')} | IBAN: {self.ld.get('iban', '')}", 0, 0, 'C')

def generate_nebenkosten_pdf(landlord_data, mieter_name, wohnung, zeitraum, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    pdf = NK_PDF(landlord_data)
    pdf.add_page()
    
    # Titel
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Nebenkostenabrechnung', ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 7, f"für den Zeitraum {zeitraum}", ln=True)
    pdf.ln(5)

    # Adressblock Mieter
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, mieter_name, ln=True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, f"Wohnung: {wohnung}", ln=True)
    pdf.ln(10)

    # --- DER BLOCK: ALLGEMEINE ANGABEN (Wie im Beispiel PDF) ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, " Allgemeine Angaben zur Wohnung und zu den Verteilungsschlüsseln", 0, 1, 'L', True)
    pdf.set_font('Arial', '', 9)
    
    col_w = 55
    val_w = 40
    
    # Datenzeilen
    def draw_row(label1, val1, label2, val2):
        pdf.cell(col_w, 6, label1, 0)
        pdf.cell(val_w, 6, str(val1), 0)
        pdf.cell(col_w, 6, label2, 0)
        pdf.cell(val_w, 6, str(val2), 1)

    draw_row("Ihr Nutzungszeitraum:", zeitraum, "Abrechnungszeitraum:", zeitraum)
    draw_row("Ihre Nutzungstage:", tage, "Abrechnungstage:", "365")
    draw_row("Wohnfläche Ihrer Wohnung:", f"{m_stats['area']} m2", "Gesamtwohnfläche Haus:", f"{h_stats['area']} m2")
    draw_row("Personen:", m_stats['pers'], "Anzahl Wohneinheiten:", h_stats['units'])
    
    m_pt = m_stats['pers'] * tage
    h_pt = h_stats['pers'] * 365
    draw_row("Ihre Personentage:", m_pt, "Gesamtpersonentage:", h_pt)
    
    pdf.ln(10)

    # --- KOSTENTABELLE ---
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(55, 8, ' Kostenart', 1, 0, 'L', True)
    pdf.cell(30, 8, 'Haus Ges.', 1, 0, 'C', True)
    pdf.cell(35, 8, 'Schlüssel', 1, 0, 'C', True)
    pdf.cell(35, 8, 'Verhältnis', 1, 0, 'C', True)
    pdf.cell(35, 8, 'Kosten', 1, 1, 'C', True)
    
    pdf.set_font('Arial', '', 9)
    for row in tabelle:
        pdf.cell(55, 8, f" {row['Kostenart']}", 1)
        pdf.cell(30, 8, f"{row['Haus Gesamt']} EUR", 1, 0, 'R')
        pdf.cell(35, 8, row['Verteilung'], 1, 0, 'C')
        pdf.cell(35, 8, row['Anteil'], 1, 0, 'C')
        pdf.cell(35, 8, f"{row['Ihr Anteil']} EUR", 1, 1, 'R')

    # Zusammenfassung
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(155, 8, "Gesamtkosten Anteil:", 0, 0, 'R')
    pdf.cell(35, 8, f"{gesamt:.2f} EUR", 1, 1, 'R')
    pdf.cell(155, 8, "Geleistete Vorauszahlung:", 0, 0, 'R')
    pdf.cell(35, 8, f"{voraus:.2f} EUR", 1, 1, 'R')
    
    pdf.ln(2)
    pdf.set_font('Arial', 'B', 11)
    label = "Guthaben:" if diff >= 0 else "Nachforderung:"
    pdf.cell(155, 10, label, 0, 0, 'R')
    pdf.set_text_color(0, 100, 0) if diff >= 0 else pdf.set_text_color(150, 0, 0)
    pdf.cell(35, 10, f"{abs(diff):.2f} EUR", 1, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1', 'replace')