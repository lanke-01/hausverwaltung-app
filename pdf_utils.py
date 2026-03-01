from fpdf import FPDF
from datetime import datetime

class NK_PDF(FPDF):
    def __init__(self, mieter_name, h_stats, zeitraum, tage, wohnung):
        super().__init__()
        self.mieter_name = mieter_name
        self.h_stats = h_stats
        self.zeitraum = zeitraum
        self.tage = tage
        self.wohnung = wohnung

    def header(self):
        # Absender klein oben (Dynamisch aus h_stats)
        self.set_font("Helvetica", '', 8)
        abs_line = f"{self.h_stats.get('name', 'Vermieter')}, {self.h_stats.get('street', '')}, {self.h_stats.get('city', '')}"
        self.cell(0, 5, abs_line, ln=True)
        self.ln(10)
        
        # Mieter-Adresse
        self.set_font("Helvetica", '', 11)
        self.cell(0, 6, str(self.mieter_name), ln=True)
        # Wir nehmen die Objektadresse aus den Vermieter-Settings für den Mieter
        self.cell(0, 6, self.h_stats.get('street', 'Eintracht Straße 160'), ln=True)
        self.cell(0, 6, self.h_stats.get('city', '42277 Wuppertal'), ln=True)
        self.ln(15)
        
        # Titel und Datum
        self.set_font("Helvetica", 'B', 16)
        self.cell(120, 10, "Nebenkostenabrechnung", 0, 0)
        self.set_font("Helvetica", '', 10)
        self.cell(0, 10, f"Datum: {datetime.now().strftime('%d.%m.%Y')}", 0, 1, 'R')
        self.ln(5)

        # --- HIER STEHT DER MIETZEITRAUM ---
        self.set_font("Helvetica", 'B', 11)
        self.cell(45, 8, "Abrechnungszeitraum:", 0)
        self.set_font("Helvetica", '', 11)
        self.cell(0, 8, f"{self.zeitraum} ({self.tage} Tage)", ln=True)
        
        self.set_font("Helvetica", 'B', 11)
        self.cell(45, 8, "Nutzerheinheit:", 0)
        self.set_font("Helvetica", '', 11)
        self.cell(0, 8, f"{self.wohnung}", ln=True)
        self.ln(10)

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    pdf = NK_PDF(mieter_name, h_stats, zeitraum, tage, wohnung)
    pdf.add_page()

    # Tabelle Kopf
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(75, 10, "Kostenart", 1, 0, 'L', fill=True)
    pdf.cell(35, 10, "Gesamt Haus", 1, 0, 'C', fill=True)
    pdf.cell(45, 10, "Verteilerschlüssel", 1, 0, 'C', fill=True)
    pdf.cell(35, 10, "Ihr Anteil", 1, 1, 'C', fill=True)

    # Tabelleninhalt
    pdf.set_font("Helvetica", '', 10)
    for row in tabelle:
        pdf.cell(75, 8, str(row['Kostenart']), 1)
        pdf.cell(35, 8, f"{row['Gesamtkosten']} EUR", 1, 0, 'R')
        pdf.cell(45, 8, str(row['Schlüssel']), 1, 0, 'C')
        pdf.cell(35, 8, f"{row['Ihr Anteil']} EUR", 1, 1, 'R')

    pdf.ln(10)
    
    # Zusammenfassung
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(155, 10, "Gesamtkostenanteil:", 0)
    pdf.cell(35, 10, f"{gesamt:.2f} EUR", 0, 1, 'R')
    
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(155, 10, "Abzüglich Vorauszahlungen:", 0)
    pdf.cell(35, 10, f"{voraus:.2f} EUR", 0, 1, 'R')
    
    pdf.ln(2)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("Helvetica", 'B', 12)
    label = "Nachzahlender Betrag:" if diff > 0 else "Guthaben / Rückerstattung:"
    pdf.cell(155, 10, label, 0)
    pdf.cell(35, 10, f"{abs(diff):.2f} EUR", 0, 1, 'R')
    
    # Footer
    pdf.set_y(-30)
    pdf.set_font("Helvetica", '', 8)
    pdf.set_text_color(100, 100, 100)
    bank_info = f"IBAN: {h_stats.get('iban', '')} | Bank: {h_stats.get('bank', '')} | Vermieter: {h_stats.get('name', '')}"
    pdf.cell(0, 4, bank_info, ln=True, align='C')

    path = f"/tmp/Abrechnung_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path

def generate_payment_history_pdf(mieter_name, jahr, history_data, h_stats):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(0, 5, f"{h_stats.get('name', '')}, {h_stats.get('street', '')}, {h_stats.get('city', '')}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 6, str(mieter_name), ln=True)
    pdf.cell(0, 6, h_stats.get('street', ''), ln=True)
    pdf.cell(0, 6, h_stats.get('city', ''), ln=True)
    pdf.ln(15)
    
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"Zahlungsverlauf / Kontoauszug {jahr}", ln=True)
    pdf.ln(10)

    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(40, 10, "Monat", 1, 0, 'L', fill=True)
    pdf.cell(40, 10, "Soll", 1, 0, 'C', fill=True)
    pdf.cell(40, 10, "Ist", 1, 0, 'C', fill=True)
    pdf.cell(40, 10, "Saldo", 1, 0, 'C', fill=True)
    pdf.cell(30, 10, "Status", 1, 1, 'C', fill=True)

    pdf.set_font("Helvetica", '', 10)
    for row in history_data:
        pdf.cell(40, 9, str(row['Monat']), 1)
        pdf.cell(40, 9, f"{row['Soll (€)']} EUR", 1, 0, 'R')
        pdf.cell(40, 9, f"{row['Ist (€)']} EUR", 1, 0, 'R')
        pdf.cell(40, 9, f"{row['Saldo (€)']} EUR", 1, 0, 'R')
        st_clean = row['Status'].replace("✅ ", "").replace("❌ ", "").replace("💤 ", "")
        pdf.cell(30, 9, st_clean, 1, 1, 'C')

    path = f"/tmp/Kontoauszug_{mieter_name.replace(' ', '_')}_{jahr}.pdf"
    pdf.output(path)
    return path