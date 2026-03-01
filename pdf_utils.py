from fpdf import FPDF
from datetime import datetime

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    # PDF-Klasse mit Layout
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
            self.ln(5)

    pdf = NK_PDF()
    pdf.add_page()

    # Zeitraum Info
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(40, 7, "Abrechnungszeitraum:", 0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 7, str(zeitraum), 0, 1)
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(40, 7, "Einheit / Wohnung:", 0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 7, str(wohnung), 0, 1)
    pdf.ln(10)

    # Tabelle Kopf
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(70, 10, "Kostenart", 1, 0, 'L', fill=True)
    pdf.cell(40, 10, "Gesamt Haus", 1, 0, 'C', fill=True)
    pdf.cell(40, 10, "Verteilerschlüssel", 1, 0, 'C', fill=True)
    pdf.cell(40, 10, "Ihr Anteil", 1, 1, 'C', fill=True)

    # Tabelleninhalt
    pdf.set_font("Helvetica", '', 10)
    for row in tabelle:
        pdf.cell(70, 8, str(row['Kostenart']), 1)
        pdf.cell(40, 8, f"{row['Gesamtkosten']} EUR", 1, 0, 'R')
        pdf.cell(40, 8, str(row['Schlüssel']), 1, 0, 'C')
        pdf.cell(40, 8, f"{row['Ihr Anteil']} EUR", 1, 1, 'R')

    pdf.ln(10)
    
    # Zusammenfassung
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(150, 10, "Gesamtkostenanteil:", 0)
    pdf.cell(40, 10, f"{gesamt:.2f} EUR", 0, 1, 'R')
    
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(150, 10, "Abzüglich Vorauszahlungen:", 0)
    pdf.cell(40, 10, f"{voraus:.2f} EUR", 0, 1, 'R')
    
    pdf.ln(2)
    pdf.set_draw_color(0,0,0)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("Helvetica", 'B', 12)
    label = "Nachzahlender Betrag:" if diff > 0 else "Guthaben / Rückerstattung:"
    pdf.cell(150, 10, label, 0)
    pdf.cell(40, 10, f"{abs(diff):.2f} EUR", 0, 1, 'R')
    
    pdf.ln(10)
    pdf.set_font("Helvetica", '', 10)
    fussnoten_text = "Bitte überweisen Sie den Betrag innerhalb von 14 Tagen." if diff > 0 else "Das Guthaben wird mit der nächsten Miete verrechnet oder erstattet."
    pdf.multi_cell(0, 5, fussnoten_text)

    # Footer Bankdaten
    pdf.set_y(-30)
    pdf.set_font("Helvetica", '', 8)
    pdf.set_text_color(100, 100, 100)
    bank_info = f"Vermieter: {h_stats.get('name')} | IBAN: {h_stats.get('iban')} | Bank: {h_stats.get('bank')}"
    pdf.cell(0, 4, bank_info, ln=True, align='C')

    path = f"/tmp/NK_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path

def generate_payment_history_pdf(mieter_name, jahr, history_data, h_stats):
    """Generiert ein PDF mit dem Zahlungsverlauf (Kontoauszug)"""
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(0, 5, f"{h_stats['name']}, {h_stats['street']}, {h_stats['city']}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 6, str(mieter_name), ln=True)
    pdf.cell(0, 6, "Eintracht Straße 160", ln=True)
    pdf.cell(0, 6, "42277 Wuppertal", ln=True)
    pdf.ln(15)
    
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"Zahlungsverlauf / Kontoauszug {jahr}", ln=True)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 10, f"Erstellt am: {datetime.now().strftime('%d.%m.%Y')}", ln=True)
    pdf.ln(5)

    # Tabelle Kopf
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 10)
    h = 9
    pdf.cell(40, h, "Monat", 1, 0, 'L', fill=True)
    pdf.cell(40, h, "Soll (Miete)", 1, 0, 'C', fill=True)
    pdf.cell(40, h, "Ist (Gezahlt)", 1, 0, 'C', fill=True)
    pdf.cell(40, h, "Saldo", 1, 0, 'C', fill=True)
    pdf.cell(30, h, "Status", 1, 1, 'C', fill=True)

    # Tabelleninhalt (Hier war der Einrückungsfehler)
    pdf.set_font("Helvetica", '', 10)
    for row in history_data:
        pdf.cell(40, h, str(row['Monat']), 1)
        pdf.cell(40, h, f"{row['Soll (€)']} EUR", 1, 0, 'R')
        pdf.cell(40, h, f"{row['Ist (€)']} EUR", 1, 0, 'R')
        pdf.cell(40, h, f"{row['Saldo (€)']} EUR", 1, 0, 'R')
        
        # Status Text (Symbole entfernen für PDF-Kompatibilität)
        status_clean = row['Status'].replace("✅ ", "").replace("❌ ", "").replace("💤 ", "")
        pdf.cell(30, h, status_clean, 1, 1, 'C')

    # Footer Bankdaten
    pdf.set_y(-30)
    pdf.set_font("Helvetica", '', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 4, f"IBAN: {h_stats.get('iban', 'N/A')}", ln=True, align='C')

    path = f"/tmp/Zahlungsverlauf_{mieter_name.replace(' ', '_')}_{jahr}.pdf"
    pdf.output(path)
    return path