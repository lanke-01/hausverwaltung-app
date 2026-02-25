from fpdf import FPDF
import os
from datetime import datetime

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    class NK_PDF(FPDF):
        def header(self):
            # Absender klein
            self.set_font("Helvetica", '', 8)
            self.cell(0, 5, f"{h_stats.get('name', '')}, {h_stats.get('street', '')}, {h_stats.get('city', '')}", ln=True)
            self.ln(10)
            
            # Empfänger
            self.set_font("Helvetica", '', 11)
            self.cell(0, 6, str(mieter_name), ln=True)
            self.cell(0, 6, "Eintracht Straße 160", ln=True)
            self.cell(0, 6, "42277 Wuppertal", ln=True)
            self.ln(15)

    pdf = NK_PDF()
    pdf.add_page()
    
    # Titel
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "Nebenkostenabrechnung", ln=True)
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(0, 8, f"Zeitraum: {zeitraum} ({tage} Tage)", ln=True)
    pdf.cell(0, 8, f"Objekt: {wohnung}", ln=True)
    pdf.ln(10)

    # Tabelle Kopf
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(50, 10, "Kostenart", 1, 0, 'L', True)
    pdf.cell(40, 10, "Haus Gesamt", 1, 0, 'C', True)
    pdf.cell(50, 10, "Verteilung", 1, 0, 'C', True)
    pdf.cell(40, 10, "Ihr Anteil", 1, 1, 'C', True)

    # Tabelle Inhalt
    pdf.set_font("Helvetica", '', 9)
    for row in tabelle:
        # Hier nutzen wir .get(), um Abstürze zu vermeiden, falls ein Key fehlt
        k_art = str(row.get('Kostenart', '-')).replace("€", "EUR")
        # WICHTIG: Hier muss 'Gesamtkosten' stehen, passend zur Akte.py
        g_haus = str(row.get('Gesamtkosten', '0.00')).replace("€", "EUR")
        schluessel = str(row.get('Schlüssel', '-')).replace("€", "EUR")
        anteil = str(row.get('Ihr Anteil', '0.00')).replace("€", "EUR")
        
        pdf.cell(50, 10, k_art, 1)
        pdf.cell(40, 10, g_haus, 1, 0, 'R')
        pdf.cell(50, 10, schluessel, 1, 0, 'C')
        pdf.cell(40, 10, anteil, 1, 1, 'R')

    pdf.ln(10)
    
    # Finanzen
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(100, 8, "Ihre Kostenanteil gesamt:", 0)
    pdf.cell(40, 8, f"{gesamt:.2f} EUR", 0, 1, 'R')
    pdf.cell(100, 8, "Ihre Vorauszahlungen:", 0)
    pdf.cell(40, 8, f"{voraus:.2f} EUR", 0, 1, 'R')
    
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    
    label = "Nachzahlung:" if diff > 0 else "Guthaben:"
    pdf.cell(100, 10, label, 0)
    pdf.cell(40, 10, f"{abs(diff):.2f} EUR", 0, 1, 'R')

    # Footer
    pdf.set_y(-30)
    pdf.set_font("Helvetica", '', 8)
    footer_text = f"Bank: {h_stats.get('bank', '')} | IBAN: {h_stats.get('iban', '')}"
    pdf.cell(0, 5, footer_text, 0, 1, 'C')

    path = f"/tmp/Abrechnung_{mieter_name.replace(' ', '_')}.pdf"
    pdf.output(path)
    return path