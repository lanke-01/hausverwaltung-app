from fpdf import FPDF
from datetime import datetime

class NK_PDF(FPDF):
    def header_shared(self, h_stats, mieter_name):
        # Absenderzeile oben
        self.set_font("Helvetica", '', 8)
        abs_text = f"Absender - {h_stats.get('name', 'Murat')}, {h_stats.get('street', 'Eintrachtstr. 160')}, {h_stats.get('city', '42277 Wuppertal')}"
        self.cell(0, 5, abs_text, ln=True)
        self.ln(5)
        
        # Mieteradresse
        self.set_font("Helvetica", '', 11)
        self.cell(0, 6, str(mieter_name), ln=True)
        self.cell(0, 6, "Eintracht Straße 160", ln=True)
        self.cell(0, 6, "42277 Wuppertal", ln=True)
        self.ln(10)

    def footer_bank(self, h_stats):
        self.set_y(-40)
        self.set_font("Helvetica", '', 8)
        self.cell(0, 4, f"{h_stats.get('name', 'Murat Sayilik')} | {h_stats.get('street', 'Eintrachtstr. 160')} | {h_stats.get('city', '42277 Wuppertal')}", ln=True, align='C')
        self.cell(0, 4, f"Bank: {h_stats.get('bank', 'Stadtsparkasse Wuppertal')} | IBAN: {h_stats.get('iban', 'DE42 ...')}", ln=True, align='C')

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum_text, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    pdf = NK_PDF()
    pdf.add_page()
    pdf.header_shared(h_stats, mieter_name)
    
    # Zusammenfassung oben links
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(60, 8, "Ihr Nebenkostenanteil:", 0)
    pdf.cell(30, 8, f"{gesamt:.2f} €", 0, 1, 'R')
    pdf.cell(60, 8, "Ihre Nebenkostenvorauszahlung:", 0)
    pdf.cell(30, 8, f"{voraus:.2f} €", 0, 1, 'R')
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(60, 8, "Zu zahlender Betrag", 0)
    pdf.cell(30, 8, f"{diff:.2f} €", 0, 1, 'R')
    self_y = pdf.get_y()
    
    # Titel rechts daneben
    pdf.set_xy(110, 35)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "Nebenkostenabrechnung", 0, 1, 'R')
    pdf.set_font("Helvetica", '', 10)
    pdf.set_x(110)
    pdf.cell(0, 6, f"für den Abrechnungszeitraum {zeitraum_text}", 0, 1, 'R')
    pdf.set_x(110)
    pdf.cell(0, 6, f"Wohnung {wohnung}", 0, 1, 'R')
    pdf.set_x(110)
    pdf.cell(0, 6, "Eintracht Straße 160, 42277 Wuppertal", 0, 1, 'R')
    
    pdf.set_xy(10, self_y + 10)
    
    # BOX 1: Allgemeine Angaben
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 8, "Allgemeine Angaben zur Wohnung und zu den Verteilungsschlüsseln", 0, 1, 'L')
    pdf.set_font("Helvetica", '', 9)
    
    col1, col2 = 45, 50
    pdf.cell(col1, 6, "Ihr Nutzungszeitraum", 1); pdf.cell(col2, 6, f"{tage//30} Monate", 1)
    pdf.cell(col1, 6, "Abrechnungszeitraum", 1); pdf.cell(col2, 6, zeitraum_text, 1, 1)
    
    pdf.cell(col1, 6, "Ihr Nutzungstage", 1); pdf.cell(col2, 6, f"{tage} tage", 1)
    pdf.cell(col1, 6, "Abrechnungstage", 1); pdf.cell(col2, 6, "366 tage", 1, 1)
    
    pdf.cell(col1, 6, "Wohnung", 1); pdf.cell(col2, 6, f"{m_stats.get('area', 0):.2f} m²", 1)
    pdf.cell(col1, 6, "Gesamtwohnfläche", 1); pdf.cell(col2, 6, f"{h_stats.get('total_area', 0):.2f} m²", 1, 1)
    pdf.ln(5)

    # BOX 2: Kostentabelle
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 8, "Gesamtkosten und Verteilung", 0, 1, 'L')
    pdf.set_font("Helvetica", 'B', 8)
    
    # Header wie im Beispiel
    widths = [45, 30, 25, 35, 30, 25]
    pdf.cell(widths[0], 10, "Kostenart", 1, 0, 'C')
    pdf.cell(widths[1], 10, "Gesamtkosten Haus", 1, 0, 'C')
    pdf.cell(widths[2], 10, "Anteil Tage", 1, 0, 'C')
    pdf.cell(widths[3], 10, "Verteilungsschlüssel", 1, 0, 'C')
    pdf.cell(widths[4], 10, "Anteil Wohnung", 1, 0, 'C')
    pdf.cell(widths[5], 10, "Ihre Kosten", 1, 1, 'C')

    pdf.set_font("Helvetica", '', 8)
    for row in tabelle:
        pdf.cell(widths[0], 8, f" {row['Kostenart']}", 1)
        pdf.cell(widths[1], 8, f"{row['Gesamtkosten']} €", 1, 0, 'R')
        pdf.cell(widths[2], 8, f"{tage} tage", 1, 0, 'C')
        pdf.cell(widths[3], 8, row['Schlüssel'], 1, 0, 'C')
        pdf.cell(widths[4], 8, "anteilig", 1, 0, 'C')
        pdf.cell(widths[5], 8, f"{row['Ihr Anteil']} €", 1, 1, 'R')
    
    pdf.set_font("Helvetica", 'B', 8)
    pdf.cell(sum(widths[:-1]), 8, "Gesamtsumme", 1, 0, 'R')
    pdf.cell(widths[5], 8, f"{gesamt:.2f} €", 1, 1, 'R')

    pdf.footer_bank(h_stats)
    
    path = f"/tmp/Nebenkosten_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path

# generate_payment_history_pdf bleibt wie es war, da es bereits gut aussieht
def generate_payment_history_pdf(mieter_name, jahr, history_data, h_stats, zeitraum_text):
    pdf = NK_PDF()
    pdf.add_page()
    pdf.header_shared(h_stats, mieter_name)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, f"Zahlungsverlauf / Kontoauszug {jahr}", ln=True)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 7, f"Mietverhältnis: {zeitraum_text}", ln=True)
    pdf.ln(5)
    
    widths = [40, 40, 40, 35, 35]
    pdf.set_font("Helvetica", 'B', 10)
    for i, h in enumerate(["Monat", "Soll", "Ist", "Saldo", "Status"]):
        pdf.cell(widths[i], 10, h, 1, 0, 'C')
    pdf.ln()

    pdf.set_font("Helvetica", '', 10)
    for row in history_data:
        pdf.cell(widths[0], 8, row['Monat'], 1)
        pdf.cell(widths[1], 8, row['Soll (€)'], 1, 0, 'R')
        pdf.cell(widths[2], 8, row['Ist (€)'], 1, 0, 'R')
        pdf.cell(widths[3], 8, row['Saldo (€)'], 1, 0, 'R')
        st_clean = row['Status'].replace("✅ ", "").replace("❌ ", "").replace("💤 ", "")
        pdf.cell(widths[4], 8, st_clean, 1, 1, 'C')

    pdf.footer_bank(h_stats)
    path = f"/tmp/Kontoauszug_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path