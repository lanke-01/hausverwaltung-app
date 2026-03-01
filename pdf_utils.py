from fpdf import FPDF
from datetime import datetime

            # Im Header oder direkt nach dem Erstellen der Seite:
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(45, 7, "Abrechnungszeitraum:", 0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 7, str(zeitraum), 0, 1) # Hier wird nun z.B. "01.01.2024 - 15.08.2024" gedruckt

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    class NK_PDF(FPDF):
        def header(self):
            # 1. Absenderzeile ganz oben (klein)
            self.set_font("Helvetica", '', 8)
            absender = f"{h_stats.get('name', '')}, {h_stats.get('street', '')}, {h_stats.get('city', '')}"
            self.cell(0, 5, absender, ln=True)
            self.ln(10)
            
            # 2. Empfängeradresse (Mieter + Hausadresse aus Datenbank)
            self.set_font("Helvetica", '', 11)
            self.cell(0, 6, str(mieter_name), ln=True)
            # Hier nutzen wir die Adresse des Objekts aus den Einstellungen
            self.cell(0, 6, h_stats.get('street', 'Eintracht Straße 160'), ln=True)
            self.cell(0, 6, h_stats.get('city', '42277 Wuppertal'), ln=True)
            self.ln(15)
            
            # 3. Titel und Datum
            self.set_font("Helvetica", 'B', 16)
            self.cell(120, 10, "Nebenkostenabrechnung", 0, 0)
            self.set_font("Helvetica", '', 10)
            self.cell(0, 10, f"Erstellungsdatum: {datetime.now().strftime('%d.%m.%Y')}", 0, 1, 'R')
            self.ln(5)

    pdf = NK_PDF()
    pdf.add_page()

    # Zeitraum & Wohnung Info
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(45, 7, "Abrechnungszeitraum:", 0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 7, str(zeitraum), 0, 1)
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(45, 7, "Einheit / Wohnung:", 0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 7, str(wohnung), 0, 1)
    pdf.ln(10)

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
    
    # Berechnungsblock
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
    label = "Nachzahlung:" if diff > 0 else "Guthaben:"
    pdf.cell(155, 10, label, 0)
    pdf.cell(35, 10, f"{abs(diff):.2f} EUR", 0, 1, 'R')
    
    pdf.ln(10)
    pdf.set_font("Helvetica", '', 10)
    text = "Bitte überweisen Sie den Betrag auf das unten angegebene Konto." if diff > 0 else "Das Guthaben wird mit der nächsten Miete verrechnet."
    pdf.multi_cell(0, 5, text)

    # Footer mit Bankdaten
    pdf.set_y(-30)
    pdf.set_font("Helvetica", '', 8)
    pdf.set_text_color(100, 100, 100)
    bank = f"Bank: {h_stats.get('bank', '')} | IBAN: {h_stats.get('iban', '')} | Vermieter: {h_stats.get('name', '')}"
    pdf.cell(0, 4, bank, ln=True, align='C')

    path = f"/tmp/Abrechnung_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path

def generate_payment_history_pdf(mieter_name, jahr, history_data, h_stats):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Helvetica", '', 8)
    absender = f"{h_stats.get('name', '')}, {h_stats.get('street', '')}, {h_stats.get('city', '')}"
    pdf.cell(0, 5, absender, ln=True)
    pdf.ln(10)
    
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 6, str(mieter_name), ln=True)
    pdf.cell(0, 6, h_stats.get('street', ''), ln=True)
    pdf.cell(0, 6, h_stats.get('city', ''), ln=True)
    pdf.ln(15)
    
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, f"Zahlungsverlauf / Kontoauszug {jahr}", ln=True)
    pdf.ln(10)

    # Tabellenkopf
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
        status_clean = row['Status'].replace("✅ ", "").replace("❌ ", "").replace("💤 ", "")
        pdf.cell(30, 9, status_clean, 1, 1, 'C')

    path = f"/tmp/Kontoauszug_{mieter_name.replace(' ', '_')}_{jahr}.pdf"
    pdf.output(path)
    return path