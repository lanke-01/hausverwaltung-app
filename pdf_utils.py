from fpdf import FPDF
from datetime import datetime

class NK_PDF(FPDF):
    def clean_text(self, text):
        """Wandelt Text in das von FPDF benötigte Format um (behebt Euro-Symbol Fehler)."""
        if text is None:
            return ""
        # Ersetzt das Euro-Symbol durch das spezielle Zeichen für CP1252
        text = str(text).replace('€', chr(128))
        # Kodiert zu cp1252, um Sonderzeichen wie ä, ö, ü, ß und € zu unterstützen
        try:
            return text.encode('cp1252', 'replace').decode('latin-1')
        except:
            return str(text)

    def header_shared(self, h_stats, mieter_name, title=""):
        # Absenderzeile oben
        self.set_font("Helvetica", '', 8)
        abs_text = f"Absender - {h_stats.get('name', '')}, {h_stats.get('street', '')}, {h_stats.get('city', '')}"
        self.cell(0, 5, self.clean_text(abs_text), ln=True)
        self.ln(5)
        
        # Mieteradresse
        self.set_font("Helvetica", '', 11)
        self.cell(0, 6, self.clean_text(mieter_name), ln=True)
        self.cell(0, 6, "Eintracht Straße 160", ln=True)
        self.cell(0, 6, "42277 Wuppertal", ln=True)
        self.ln(10)

    def footer_bank(self, h_stats):
        self.set_y(-40)
        self.set_font("Helvetica", '', 8)
        footer1 = f"{h_stats.get('name', '')} | {h_stats.get('street', '')} | {h_stats.get('city', '')}"
        footer2 = f"Bank: {h_stats.get('bank', '')} | IBAN: {h_stats.get('iban', '')}"
        self.cell(0, 4, self.clean_text(footer1), ln=True, align='C')
        self.cell(0, 4, self.clean_text(footer2), ln=True, align='C')

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum_text, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    pdf = NK_PDF()
    pdf.add_page()
    pdf.header_shared(h_stats, mieter_name)
    
    # Zusammenfassung oben links (wie Mustafa Kader)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(65, 8, pdf.clean_text("Ihr Nebenkostenanteil:"), 0)
    pdf.cell(30, 8, f"{gesamt:.2f} {chr(128)}", 0, 1, 'R')
    pdf.cell(65, 8, pdf.clean_text("Ihre Nebenkostenvorauszahlung:"), 0)
    pdf.cell(30, 8, f"{voraus:.2f} {chr(128)}", 0, 1, 'R')
    
    pdf.set_font("Helvetica", 'B', 11)
    label_summe = "Nachzahlung" if diff > 0 else "Guthaben"
    pdf.cell(65, 8, pdf.clean_text(label_summe), 0)
    pdf.cell(30, 8, f"{abs(diff):.2f} {chr(128)}", 0, 1, 'R')
    
    # Titel rechts
    pdf.set_xy(110, 35)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, pdf.clean_text("Nebenkostenabrechnung"), 0, 1, 'R')
    pdf.set_font("Helvetica", '', 10)
    pdf.set_x(110)
    pdf.cell(0, 6, pdf.clean_text(f"für den Zeitraum {zeitraum_text}"), 0, 1, 'R')
    pdf.set_x(110)
    pdf.cell(0, 6, pdf.clean_text(f"Wohnung {wohnung}"), 0, 1, 'R')
    
    pdf.set_xy(10, 75)
    # Box: Allgemeine Angaben
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 8, pdf.clean_text("Allgemeine Angaben"), 0, 1, 'L')
    pdf.set_font("Helvetica", '', 9)
    pdf.cell(50, 6, pdf.clean_text("Nutzungstage"), 1); pdf.cell(50, 6, f"{tage} Tage", 1, 1)
    pdf.cell(50, 6, pdf.clean_text("Wohnfläche"), 1); pdf.cell(50, 6, f"{m_stats.get('area', 0):.2f} m2", 1, 1)
    pdf.ln(5)

    # Kostentabelle
    widths = [45, 30, 25, 35, 30, 25]
    pdf.set_font("Helvetica", 'B', 8)
    headers = ["Kostenart", "Haus Gesamt", "Tage", "Schlüssel", "Anteil Whg", "Ihre Kosten"]
    for i, h in enumerate(headers):
        pdf.cell(widths[i], 10, pdf.clean_text(h), 1, 0, 'C')
    pdf.ln()

    pdf.set_font("Helvetica", '', 8)
    for row in tabelle:
        pdf.cell(widths[0], 8, pdf.clean_text(row['Kostenart']), 1)
        pdf.cell(widths[1], 8, f"{row['Gesamtkosten']} {chr(128)}", 1, 0, 'R')
        pdf.cell(widths[2], 8, f"{tage}", 1, 0, 'C')
        pdf.cell(widths[3], 8, pdf.clean_text(row['Schlüssel']), 1, 0, 'C')
        pdf.cell(widths[4], 8, "anteilig", 1, 0, 'C')
        pdf.cell(widths[5], 8, f"{row['Ihr Anteil']} {chr(128)}", 1, 1, 'R')

    pdf.footer_bank(h_stats)
    path = f"/tmp/Abrechnung_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path

def generate_payment_history_pdf(mieter_name, jahr, history_data, h_stats, zeitraum_text):
    pdf = NK_PDF()
    pdf.add_page()
    pdf.header_shared(h_stats, mieter_name)
    
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, pdf.clean_text(f"Zahlungsverlauf / Kontoauszug {jahr}"), ln=True)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 7, pdf.clean_text(f"Mietverhältnis: {zeitraum_text}"), ln=True)
    pdf.ln(10)
    
    widths = [40, 35, 35, 35, 45]
    pdf.set_font("Helvetica", 'B', 10)
    headers = ["Monat", "Soll", "Ist", "Saldo", "Status"]
    for i, h in enumerate(headers):
        pdf.cell(widths[i], 10, pdf.clean_text(h), 1, 0, 'C')
    pdf.ln()

    pdf.set_font("Helvetica", '', 10)
    for row in history_data:
        pdf.cell(widths[0], 8, pdf.clean_text(row['Monat']), 1)
        pdf.cell(widths[1], 8, f"{row['Soll (€)']} {chr(128)}", 1, 0, 'R')
        pdf.cell(widths[2], 8, f"{row['Ist (€)']} {chr(128)}", 1, 0, 'R')
        pdf.cell(widths[3], 8, f"{row['Saldo (€)']} {chr(128)}", 1, 0, 'R')
        st_clean = row['Status'].replace("✅ ", "").replace("❌ ", "").replace("💤 ", "")
        pdf.cell(widths[4], 8, pdf.clean_text(st_clean), 1, 1, 'C')

    pdf.footer_bank(h_stats)
    path = f"/tmp/Kontoauszug_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path