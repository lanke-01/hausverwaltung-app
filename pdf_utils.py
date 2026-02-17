from fpdf import FPDF

class NK_PDF(FPDF):
    def __init__(self, landlord_data):
        super().__init__()
        self.ld = landlord_data

    def header(self):
        # Briefkopf rechtsbündig
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

    # Mieter-Info
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 5, mieter_name, ln=True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 5, f"Wohnung: {wohnung}", ln=True)
    pdf.ln(10)

    # --- INFODATEN (HIER WURDEN DIE BREITEN KORRIGIERT: 50+45+50+45 = 190mm) ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 8, " Allgemeine Angaben zur Wohnung und zu den Verteilungsschlüsseln", 0, 1, 'L', True)
    pdf.set_font('Arial', '', 9)
    
    c1, v1, c2, v2 = 60, 35, 60, 35
    
    def row(l1, v1_val, l2, v2_val):
        pdf.cell(c1, 6, l1, 0)
        pdf.cell(v1, 6, str(v1_val), 0)
        pdf.cell(c2, 6, l2, 0)
        pdf.cell(v2, 6, str(v2_val), 1)

    row("Ihr Nutzungszeit:", zeitraum, "Abrechnungszeit:", zeitraum)
    row("Ihre Nutzungstage:", tage, "Abrechnungstage:", "365")
    row("Fläche Ihrer Wohnung:", f"{m_stats['area']} m2", "Gesamtfläche Haus:", f"{h_stats['area']} m2")
    row("Personen (Ihr Haushalt):", m_stats['pers'], "Wohneinheiten Haus:", h_stats['units'])
    
    m_pt = m_stats['pers'] * tage
    h_pt = h_stats['pers'] * 365
    row("Ihre Personentage:", m_pt, "Gesamt-Personentage:", h_pt)
    
    pdf.ln(20)

    # --- KOSTENTABELLE (OPTIMIERTE BREITEN: 55+30+35+40+30 = 190mm) ---
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(55, 8, ' Kostenart', 1, 0, 'L', True)
    pdf.cell(30, 8, 'Haus Ges.', 1, 0, 'C', True)
    pdf.cell(35, 8, 'Schlüssel', 1, 0, 'C', True)
    pdf.cell(40, 8, 'Verhältnis', 1, 0, 'C', True)
    pdf.cell(30, 8, 'Ihr Anteil', 1, 1, 'C', True)
    
    pdf.set_font('Arial', '', 9)
    for r in tabelle:
        pdf.cell(55, 7, f" {r['Kostenart'][:28]}", 1)
        pdf.cell(30, 7, f"{r['Haus Gesamt']} EUR", 1, 0, 'R')
        pdf.cell(35, 7, r['Verteilung'], 1, 0, 'C')
        pdf.cell(40, 7, r['Anteil'], 1, 0, 'C')
        pdf.cell(30, 7, f"{r['Ihr Anteil']} EUR", 1, 1, 'R')

    # Zusammenfassung
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(160, 8, "Gesamtkosten Anteil:", 0, 0, 'R')
    pdf.cell(30, 8, f"{gesamt:.2f} EUR", 1, 1, 'R')
    pdf.cell(160, 8, "Geleistete Vorauszahlung:", 0, 0, 'R')
    pdf.cell(30, 8, f"{voraus:.2f} EUR", 1, 1, 'R')
    
    pdf.ln(2)
    label = "Guthaben:" if diff >= 0 else "Nachforderung:"
    pdf.cell(160, 10, label, 0, 0, 'R')
    pdf.cell(30, 10, f"{abs(diff):.2f} EUR", 1, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1', 'replace')