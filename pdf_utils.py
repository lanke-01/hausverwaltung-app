from fpdf import FPDF
from datetime import datetime

class NK_PDF(FPDF):
    def clean_text(self, text):
        if text is None: return ""
        text = str(text).replace('€', 'EUR').replace('²', '2')
        return text.encode('latin-1', 'replace').decode('latin-1')

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum_text, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    pdf = NK_PDF()
    pdf.add_page()
    
    # Header: Absender
    pdf.set_font("Helvetica", '', 9)
    pdf.cell(0, 5, f"{h_stats.get('name', 'Murat Sayilik')}, {h_stats.get('street', 'Eintrachtstr. 160')}, {h_stats.get('city', '42277 Wuppertal')}", ln=True)
    pdf.ln(10)
    
    # Mieter Adresse
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 6, pdf.clean_text(mieter_name), ln=True)
    pdf.cell(0, 6, "Eintracht Straße 160", ln=True)
    pdf.cell(0, 6, "42277 Wuppertal", ln=True)
    pdf.ln(10)
    
    # Titel Bereich
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, "Nebenkostenabrechnung", ln=True)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 6, f"für den Abrechnungszeitraum {zeitraum_text}", ln=True)
    pdf.cell(0, 6, f"Wohnung: {wohnung}", ln=True)
    pdf.cell(0, 6, "Eintracht Straße 160, 42277 Wuppertal", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 8, "Allgemeine Angaben zur Wohnung und zu den Verteilungsschlüsseln", ln=True)
    pdf.set_font("Helvetica", '', 9)
    pdf.cell(0, 6, f"Erstellungsdatum: {datetime.now().strftime('%d.%m.%Y')}", ln=True)
    
    # Tabelle: Allgemeine Angaben (Exakt wie Beispiel)
    col = 48
    pdf.cell(col, 7, "Ihr Nutzungszeitraum:", 1); pdf.cell(col, 7, f"{tage/30.4:.1f} Monate", 1)
    pdf.cell(col, 7, "Abrechnungszeitraum:", 1); pdf.cell(col, 7, zeitraum_text, 1, 1)
    pdf.cell(col, 7, "Ihre Nutzungstage:", 1); pdf.cell(col, 7, f"{tage} Tage", 1)
    pdf.cell(col, 7, "Abrechnungstage:", 1); pdf.cell(col, 7, "365 Tage", 1, 1)
    pdf.cell(col, 7, "Wohnung:", 1); pdf.cell(col, 7, f"{m_stats.get('area', 0):.2f} m2", 1)
    pdf.cell(col, 7, "Gesamtwohnfläche:", 1); pdf.cell(col, 7, f"{h_stats.get('total_area', 0):.2f} m2", 1, 1)
    pdf.cell(col, 7, "Personen:", 1); pdf.cell(col, 7, f"{m_stats.get('occupants', 1)}", 1)
    pdf.cell(col, 7, "Gesamtzahl Personen:", 1); pdf.cell(col, 7, f"{h_stats.get('total_occupants', 1)}", 1, 1)
    pdf.ln(8)

    # Haupttabelle Kosten
    pdf.set_font("Helvetica", 'B', 8)
    widths = [45, 30, 25, 40, 25, 30]
    headers = ["Kostenart", "Gesamtkosten Haus", "Anteil Tage", "Verteilungsschlüssel", "Anteil Whg.", "Ihre Kosten"]
    for i, h in enumerate(headers):
        pdf.cell(widths[i], 8, h, 1, 0, 'C')
    pdf.ln()

    pdf.set_font("Helvetica", '', 8)
    for row in tabelle:
        pdf.cell(widths[0], 7, pdf.clean_text(row['Kostenart']), 1)
        pdf.cell(widths[1], 7, f"{row['Gesamtkosten']} EUR", 1, 0, 'R')
        pdf.cell(widths[2], 7, f"{tage} Tage", 1, 0, 'C')
        pdf.cell(widths[3], 7, pdf.clean_text(row['Schlüssel']), 1, 0, 'C')
        pdf.cell(widths[4], 7, "Anteilig", 1, 0, 'C')
        pdf.cell(widths[5], 7, f"{row['Ihr Anteil']} EUR", 1, 1, 'R')

    # Saldo
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(165, 8, "Summe Ihrer anteiligen Kosten:", 0, 0, 'R')
    pdf.cell(30, 8, f"{gesamt:.2f} EUR", 0, 1, 'R')
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(165, 8, "Abzüglich geleistete Vorauszahlungen:", 0, 0, 'R')
    pdf.cell(30, 8, f"{voraus:.2f} EUR", 0, 1, 'R')
    pdf.set_font("Helvetica", 'B', 11)
    label = "Nachzahlung:" if diff > 0 else "Guthaben:"
    pdf.cell(165, 10, label, 0, 0, 'R')
    pdf.cell(30, 10, f"{abs(diff):.2f} EUR", 0, 1, 'R')

    path = f"/tmp/NK_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path

def generate_payment_history_pdf(mieter_name, jahr, history_data, h_stats, zeitraum_text):
    pdf = NK_PDF()
    pdf.add_page()
    
    # Header wie oben
    pdf.set_font("Helvetica", '', 9)
    pdf.cell(0, 5, f"{h_stats.get('name', '')}, {h_stats.get('street', '')}, {h_stats.get('city', '')}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, pdf.clean_text(f"Zahlungsverlauf / Kontoauszug {jahr}"), ln=True)
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, pdf.clean_text(f"Mieter: {mieter_name}"), ln=True)
    pdf.cell(0, 8, f"Mietverhältnis: {zeitraum_text}", ln=True)
    pdf.ln(10)

    # Tabelle Zahlungsverlauf
    widths = [40, 35, 35, 35, 45]
    pdf.set_font("Helvetica", 'B', 10)
    headers = ["Monat", "Soll", "Ist", "Saldo", "Status"]
    for i, h in enumerate(headers):
        pdf.cell(widths[i], 10, h, 1, 0, 'C')
    pdf.ln()

    pdf.set_font("Helvetica", '', 10)
    for row in history_data:
        pdf.cell(widths[0], 8, pdf.clean_text(row['Monat']), 1)
        pdf.cell(widths[1], 8, f"{row['Soll (€)']} EUR", 1, 0, 'R')
        pdf.cell(widths[2], 8, f"{row['Ist (€)']} EUR", 1, 0, 'R')
        pdf.cell(widths[3], 8, f"{row['Saldo (€)']} EUR", 1, 0, 'R')
        pdf.cell(widths[4], 8, pdf.clean_text(row['Status']), 1, 1, 'C')
        st_clean = row['Status'].replace("✅ ", "").replace("❌ ", "").replace("💤 ", "")
        
    path = f"/tmp/Kontoauszug_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path