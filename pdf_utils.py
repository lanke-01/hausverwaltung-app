from fpdf import FPDF
from datetime import datetime

class MyPDF(FPDF):
    def header_shared(self, title, h_stats, mieter_name):
        # Absenderzeile
        self.set_font("Helvetica", '', 8)
        abs_text = f"{h_stats.get('name', 'Vermieter')}, {h_stats.get('street', '')}, {h_stats.get('city', '')}"
        self.cell(0, 5, abs_text, ln=True)
        self.ln(10)
        
        # Mieteradresse
        self.set_font("Helvetica", '', 11)
        self.cell(0, 6, str(mieter_name), ln=True)
        self.cell(0, 6, h_stats.get('street', 'Eintrachtstr. 160'), ln=True)
        self.cell(0, 6, h_stats.get('city', '42277 Wuppertal'), ln=True)
        self.ln(15)
        
        # Titel
        self.set_font("Helvetica", 'B', 16)
        self.cell(0, 10, title, ln=True)
        self.set_font("Helvetica", '', 10)
        self.cell(0, 5, f"Datum: {datetime.now().strftime('%d.%m.%Y')}", ln=True, align='R')
        self.ln(5)

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    pdf = MyPDF()
    pdf.add_page()
    pdf.header_shared("Nebenkostenabrechnung", h_stats, mieter_name)
    
    # Mietinfos
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(40, 7, "Zeitraum:", 0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 7, f"{zeitraum} ({tage} Tage)", ln=True)
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(40, 7, "Wohnung:", 0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 7, str(wohnung), ln=True)
    pdf.ln(8)

    # Tabelle - Breiten optimiert, damit nichts abgeschnitten wird
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Helvetica", 'B', 9)
    # Gesamtbreite ca. 190mm
    pdf.cell(65, 10, " Kostenart", 1, 0, 'L', fill=True)
    pdf.cell(35, 10, "Gesamt Haus", 1, 0, 'C', fill=True)
    pdf.cell(50, 10, "Verteilerschlüssel", 1, 0, 'C', fill=True)
    pdf.cell(40, 10, "Ihr Anteil", 1, 1, 'C', fill=True)

    pdf.set_font("Helvetica", '', 9)
    for row in tabelle:
        # Multi_cell wäre für Umbrüche gut, hier nutzen wir angepasste Breiten
        pdf.cell(65, 8, f" {row['Kostenart']}", 1)
        pdf.cell(35, 8, f"{row['Gesamtkosten']} EUR", 1, 0, 'R')
        pdf.cell(50, 8, f"{row['Schlüssel']}", 1, 0, 'C')
        pdf.cell(40, 8, f"{row['Ihr Anteil']} EUR", 1, 1, 'R')

    pdf.ln(10)
    
    # Zusammenfassung
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(150, 8, "Gesamtkostenanteil:", 0)
    pdf.cell(40, 8, f"{gesamt:.2f} EUR", 0, 1, 'R')
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(150, 8, "Vorauszahlungen:", 0)
    pdf.cell(40, 8, f"{voraus:.2f} EUR", 0, 1, 'R')
    
    pdf.line(10, pdf.get_y()+2, 200, pdf.get_y()+2)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'B', 12)
    label = "Nachzahlung:" if diff > 0 else "Guthaben:"
    pdf.cell(150, 10, label, 0)
    pdf.cell(40, 10, f"{abs(diff):.2f} EUR", 0, 1, 'R')

    path = f"/tmp/Abrechnung_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path

def generate_payment_history_pdf(mieter_name, jahr, history_data, h_stats):
    pdf = MyPDF()
    pdf.add_page()
    pdf.header_shared(f"Zahlungsverlauf {jahr}", h_stats, mieter_name)
    
    # Tabelle für Zahlungen
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(40, 10, " Monat", 1, 0, 'L', fill=True)
    pdf.cell(40, 10, "Soll", 1, 0, 'C', fill=True)
    pdf.cell(40, 10, "Ist", 1, 0, 'C', fill=True)
    pdf.cell(35, 10, "Saldo", 1, 0, 'C', fill=True)
    pdf.cell(35, 10, "Status", 1, 1, 'C', fill=True)

    pdf.set_font("Helvetica", '', 10)
    for row in history_data:
        pdf.cell(40, 8, f" {row['Monat']}", 1)
        pdf.cell(40, 8, f"{row['Soll (€)']}", 1, 0, 'R')
        pdf.cell(40, 8, f"{row['Ist (€)']}", 1, 0, 'R')
        pdf.cell(40, 8, f"{row['Saldo (€)']}", 1, 0, 'R')
        status_text = row['Status'].replace("✅ ", "").replace("❌ ", "").replace("💤 ", "")
        pdf.cell(30, 8, status_text, 1, 1, 'C')

    path = f"/tmp/Zahlungsverlauf_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path