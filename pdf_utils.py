from fpdf import FPDF
from datetime import datetime

class NK_PDF(FPDF):
    def __init__(self, mieter_name, wohnung, zeitraum_text, tage, h_stats, m_stats):
        super().__init__()
        self.mieter_name = mieter_name
        self.wohnung = wohnung
        self.zeitraum_text = zeitraum_text
        self.tage = tage
        self.h_stats = h_stats
        self.m_stats = m_stats

    def header(self):
        # Absenderzeile oben links
        self.set_font("Helvetica", '', 9)
        abs_text = f"{self.h_stats.get('name', 'Murat Sayilik')}, {self.h_stats.get('street', 'Eintrachtstr. 160')}, {self.h_stats.get('city', '42277 Wuppertal')}"
        self.cell(0, 5, abs_text, ln=True)
        self.ln(10)
        
        # Mieteradresse
        self.set_font("Helvetica", '', 11)
        self.cell(0, 6, self.mieter_name, ln=True)
        self.cell(0, 6, "Eintracht Straße 160", ln=True)
        self.cell(0, 6, "42277 Wuppertal", ln=True)
        self.ln(10)
        
        # Titel und Zeitraum
        self.set_font("Helvetica", 'B', 14)
        self.cell(0, 8, "Nebenkostenabrechnung", ln=True)
        self.set_font("Helvetica", '', 11)
        self.cell(0, 6, f"für den Abrechnungszeitraum {self.zeitraum_text}", ln=True)
        self.cell(0, 6, f"Wohnung: {self.wohnung}", ln=True)
        self.cell(0, 6, "Eintracht Straße 160, 42277 Wuppertal", ln=True)
        self.ln(5)
        
        self.set_font("Helvetica", 'B', 11)
        self.cell(0, 8, "Allgemeine Angaben zur Wohnung und zu den Verteilungsschlüsseln", ln=True)
        self.set_font("Helvetica", '', 9)
        self.cell(0, 6, f"Erstellungsdatum: {datetime.now().strftime('%d.%m.%Y')}", ln=True)
        self.ln(2)

    def footer(self):
        # Footer mit Bankdaten (wie im Beispiel)
        self.set_y(-30)
        self.set_font("Helvetica", '', 8)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)
        f_text = f"{self.h_stats.get('name', '')} | {self.h_stats.get('street', '')} | {self.h_stats.get('city', '')} | Bank: {self.h_stats.get('bank', '')} | IBAN: {self.h_stats.get('iban', '')}"
        self.cell(0, 10, f_text, 0, 0, 'C')

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum_text, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    pdf = NK_PDF(mieter_name, wohnung, zeitraum_text, tage, h_stats, m_stats)
    pdf.add_page()
    
    # 1. Tabelle: Allgemeine Angaben
    pdf.set_font("Helvetica", '', 9)
    col_w = 45
    # Zeile 1
    pdf.cell(col_w, 7, "Ihr Nutzungszeitraum:", 1); pdf.cell(col_w, 7, f"{tage/30:.1f} Monate", 1)
    pdf.cell(col_w, 7, "Abrechnungszeitraum:", 1); pdf.cell(col_w, 7, zeitraum_text, 1, 1)
    # Zeile 2
    pdf.cell(col_w, 7, "Ihre Nutzungstage:", 1); pdf.cell(col_w, 7, f"{tage} Tage", 1)
    pdf.cell(col_w, 7, "Abrechnungstage:", 1); pdf.cell(col_w, 7, "365 Tage", 1, 1)
    # Zeile 3
    pdf.cell(col_w, 7, "Wohnung:", 1); pdf.cell(col_w, 7, f"{m_stats.get('area', 0):.2f} m2", 1)
    pdf.cell(col_w, 7, "Gesamtwohnfläche:", 1); pdf.cell(col_w, 7, f"{h_stats.get('total_area', 0):.2f} m2", 1, 1)
    # Zeile 4
    pdf.cell(col_w, 7, "Personen:", 1); pdf.cell(col_w, 7, f"{m_stats.get('occupants', 1)}", 1)
    pdf.cell(col_w, 7, "Gesamtzahl Personen:", 1); pdf.cell(col_w, 7, f"{h_stats.get('total_occupants', 1)}", 1, 1)
    
    pdf.ln(8)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 8, "Gesamtkosten und Verteilung", ln=True)
    
    # 2. Kostentabelle
    pdf.set_font("Helvetica", 'B', 8)
    widths = [45, 35, 25, 40, 25, 25]
    headers = ["Kostenart", "Gesamtkosten Haus", "Anteil Tage", "Verteilungsschlüssel", "Anteil Whg.", "Ihre Kosten"]
    for i, h in enumerate(headers):
        pdf.cell(widths[i], 8, h, 1, 0, 'C')
    pdf.ln()

    pdf.set_font("Helvetica", '', 8)
    for row in tabelle:
        pdf.cell(widths[0], 7, f" {row['Kostenart']}", 1)
        pdf.cell(widths[1], 7, f"{row['Gesamtkosten']} EUR", 1, 0, 'R')
        pdf.cell(widths[2], 7, f"{tage} Tage", 1, 0, 'C')
        pdf.cell(widths[3], 7, row['Schlüssel'], 1, 0, 'C')
        pdf.cell(widths[4], 7, "Anteilig", 1, 0, 'C')
        pdf.cell(widths[5], 7, f"{row['Ihr Anteil']} EUR", 1, 1, 'R')

    # Zusammenfassung am Ende der Tabelle
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(145, 8, "Summe Ihrer anteiligen Kosten:", 0, 0, 'R')
    pdf.cell(50, 8, f"{gesamt:.2f} EUR", 0, 1, 'R')
    
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(145, 8, "Abzüglich geleistete Vorauszahlungen:", 0, 0, 'R')
    pdf.cell(50, 8, f"{voraus:.2f} EUR", 0, 1, 'R')
    
    pdf.line(130, pdf.get_y(), 200, pdf.get_y())
    
    pdf.set_font("Helvetica", 'B', 11)
    label = "Nachzahlung:" if diff > 0 else "Guthaben:"
    pdf.cell(145, 10, label, 0, 0, 'R')
    pdf.cell(50, 10, f"{abs(diff):.2f} EUR", 0, 1, 'R')

    path = f"/tmp/NK_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path

# Die Funktion für den Kontoauszug bleibt separat, damit sie den Tab 1 bedient
def generate_payment_history_pdf(mieter_name, jahr, history_data, h_stats, zeitraum_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, f"Kontoauszug {jahr} - {mieter_name}", ln=True)
    pdf.ln(10)
    # ... (Rest der Kontoauszug-Logik)
    path = f"/tmp/Kontoauszug_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path