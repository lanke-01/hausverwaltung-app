from fpdf import FPDF

class NK_PDF(FPDF):
    def __init__(self, landlord_data):
        super().__init__()
        self.ld = landlord_data

    def header(self):
        # Briefkopf oben rechts
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, f"{self.ld.get('name', '')}", ln=True, align='R')
        self.set_font('Arial', '', 9)
        self.cell(0, 5, f"{self.ld.get('street', '')}", ln=True, align='R')
        self.cell(0, 5, f"{self.ld.get('city', '')}", ln=True, align='R')
        self.ln(10)
        
    def footer(self):
        # Bankdaten am unteren Rand
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

    # Mieter-Daten
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 6, mieter_name, ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 6, f"Wohnung: {wohnung}", ln=True)
    pdf.ln(10)

    # --- INFODATEN-BLOCK (FIX FÜR ABSCHNITTENEN TEXT) ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 8, " Allgemeine Angaben zur Wohnung und zu den Verteilungsschlüsseln", 0, 1, 'L', True)
    pdf.ln(2)

    # Zwei-Spalten-Layout (95mm + 95mm = 190mm)
    col = 95
    pdf.set_font('Arial', 'B', 9)
    
    # Zeile 1: Zeiträume
    pdf.cell(col, 5, "Ihr Nutzungszeitraum:", 0, 0)
    pdf.cell(col, 5, "Abrechnungszeitraum:", 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(col, 5, zeitraum, 0, 0)
    pdf.cell(col, 5, zeitraum, 0, 1)
    pdf.ln(2)

    # Zeile 2: Tage
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(col, 5, "Ihre Nutzungstage:", 0, 0)
    pdf.cell(col, 5, "Abrechnungstage:", 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(col, 5, str(tage), 0, 0)
    pdf.cell(col, 5, "365", 0, 1)
    pdf.ln(2)

    # Zeile 3: Fläche
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(col, 5, "Wohnfläche Ihrer Wohnung:", 0, 0)
    pdf.cell(col, 5, "Gesamtwohnfläche Haus:", 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(col, 5, f"{m_stats['area']} m²", 0, 0)
    pdf.cell(col, 5, f"{h_stats['area']} m²", 0, 1)
    
    pdf.ln(8)

    # --- KOSTENTABELLE ---
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

    # Zusammenfassung & Farbliches Ergebnis
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(160, 8, "Gesamtkosten Anteil:", 0, 0, 'R')
    pdf.cell(30, 8, f"{gesamt:.2f} EUR", 1, 1, 'R')
    pdf.cell(160, 8, "Geleistete Vorauszahlung:", 0, 0, 'R')
    pdf.cell(30, 8, f"{voraus:.2f} EUR", 1, 1, 'R')
    
    pdf.ln(2)
    label = "Guthaben:" if diff >= 0 else "Nachforderung:"
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(160, 10, label, 0, 0, 'R')
    
    if diff >= 0:
        pdf.set_text_color(0, 120, 0) # Grün für Guthaben
    else:
        pdf.set_text_color(200, 0, 0) # Rot für Nachzahlung
        
    pdf.cell(30, 10, f"{abs(diff):.2f} EUR", 1, 1, 'R')
    pdf.set_text_color(0, 0, 0) # Zurück auf Schwarz

    # --- DYNAMISCHER ZAHLUNGSHINWEIS ---
    pdf.ln(10)
    if diff < 0:
        pdf.set_font('Arial', 'B', 10)
        pdf.multi_cell(0, 6, "Bitte überweisen Sie den Betrag der Nachforderung innerhalb von 14 Tagen auf das unten angegebene Konto.", 0, 'L')
    elif diff > 0:
        pdf.set_font('Arial', 'I', 10)
        pdf.multi_cell(0, 6, "Das Guthaben wird mit Ihrer nächsten Mietzahlung verrechnet.", 0, 'L')

    return pdf.output(dest='S').encode('latin-1', 'replace')