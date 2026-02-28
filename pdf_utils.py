from fpdf import FPDF
from datetime import datetime

def generate_nebenkosten_pdf(mieter_name, wohnung, zeitraum, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    # PDF-Klasse mit Mustafa-Kader-Layout
    class NK_PDF(FPDF):
        def header(self):
            # Absender klein oben (wie im Muster)
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
            
            self.set_font("Helvetica", '', 11)
            self.cell(0, 8, f"für den Abrechnungszeitraum {zeitraum}", ln=True)
            self.cell(0, 8, f"Wohnung: {wohnung}", ln=True)
            self.cell(0, 8, "Eintracht Straße 160, 42277 Wuppertal", ln=True)
            self.ln(5)

    pdf = NK_PDF()
    pdf.add_page()
    
    # --- BOX 1: ALLGEMEINE ANGABEN (nach Muster) ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 8, "Allgemeine Angaben zur Wohnung und zu den Verteilungsschlüsseln", 0, 1, 'L', fill=True)
    pdf.set_font("Helvetica", '', 9)
    
    # Berechnungen für die Infobox
    tage_jahr = 366 if "2024" in zeitraum else 365
    col_w = 47
    
    # Zeile 1
    pdf.cell(col_w, 7, "Ihr Nutzungszeitraum:", 0)
    pdf.cell(col_w, 7, f"{round(tage/30.4, 1)} Monate", 0)
    pdf.cell(col_w, 7, "Abrechnungszeitraum:", 0)
    pdf.cell(col_w, 7, zeitraum, 0, 1)
    
    # Zeile 2
    pdf.cell(col_w, 7, "Ihre Nutzungstage:", 0)
    pdf.cell(col_w, 7, f"{tage} Tage", 0)
    pdf.cell(col_w, 7, "Abrechnungstage:", 0)
    pdf.cell(col_w, 7, f"{tage_jahr} Tage", 0, 1)
    
    # Zeile 3
    pdf.cell(col_w, 7, "Wohnung:", 0)
    pdf.cell(col_w, 7, f"{m_stats['area']:.2f} m2", 0)
    pdf.cell(col_w, 7, "Gesamtwohnfläche:", 0)
    pdf.cell(col_w, 7, f"{h_stats['total_area']:.2f} m2", 0, 1)

    # Zeile 4
    pdf.cell(col_w, 7, "Personen:", 0)
    pdf.cell(col_w, 7, f"{m_stats['occupants']}", 0)
    pdf.cell(col_w, 7, "Gesamtzahl Personen:", 0)
    pdf.cell(col_w, 7, f"{h_stats['total_occupants']}", 0, 1)
    
    pdf.ln(10)

    # --- BOX 2: KOSTENTABELLE ---
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 8, "Gesamtkosten und Verteilung", 0, 1, 'L', fill=True)
    
    # Tabellenkopf (exakt wie im PDF-Muster)
    pdf.set_font("Helvetica", 'B', 8)
    h = 8
    pdf.cell(45, h, "Kostenart", 1)
    pdf.cell(30, h, "Gesamtkosten Haus", 1)
    pdf.cell(25, h, "Anteil Tage", 1)
    pdf.cell(35, h, "Verteilungsschlüssel", 1)
    pdf.cell(25, h, "Anteil Whg.", 1)
    pdf.cell(30, h, "Ihre Kosten", 1, 1)

    # Tabelleninhalt
    pdf.set_font("Helvetica", '', 8)
    for row in tabelle:
        # Reinigung der Werte für PDF (EUR statt €)
        k_art = str(row['Kostenart'])[:25]
        g_haus = str(row['Gesamtkosten']).replace("€", "")
        schluessel = str(row['Schlüssel'])
        anteil_ihr = str(row['Ihr Anteil']).replace("€", "")
        
        pdf.cell(45, h, k_art, 1)
        pdf.cell(30, h, f"{g_haus} EUR", 1)
        pdf.cell(25, h, f"{tage} Tage", 1)
        pdf.cell(35, h, schluessel, 1)
        pdf.cell(25, h, "Anteilig", 1)
        pdf.cell(30, h, f"{anteil_ihr} EUR", 1, 1)

    # Gesamtsumme Zeile
    pdf.set_font("Helvetica", 'B', 9)
    pdf.cell(160, h, "Gesamt", 1, 0, 'R')
    pdf.cell(30, h, f"{gesamt:.2f} EUR", 1, 1)

    pdf.ln(10)

    # --- BOX 3: ABRECHNUNGSERGEBNIS (Zusammenfassung) ---
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(100, 8, "Ihr Nebenkostenanteil:", 0)
    pdf.cell(40, 8, f"{gesamt:.2f} EUR", 0, 1, 'R')
    
    pdf.cell(100, 8, "Ihre Nebenkostenvorauszahlung:", 0)
    pdf.cell(40, 8, f"{voraus:.2f} EUR", 0, 1, 'R')
    
    pdf.set_draw_color(0,0,0)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    
    label = "Zu zahlender Betrag:" if diff > 0 else "Guthaben / Rückerstattung:"
    pdf.cell(100, 10, label, 0)
    pdf.cell(40, 10, f"{abs(diff):.2f} EUR", 0, 1, 'R')
    
    label = "Bitte Überweisen Sie innerhalb von 14 Tagen auf das unten angegebenes Konto" if diff > 0 else "Ihr Guthaben / Rückerstattung wird Ihnen Überwiesen"
    pdf.cell(100, 10, label, 0)
  
    
    

  # --- Footer / Bankdaten (DYNAMISCH AUS DATENBANK) ---
    pdf.set_y(-40)
    pdf.set_font("Helvetica", '', 8)
    pdf.set_text_color(100, 100, 100)
    
    # Zeile 1: Name und Adresse des Vermieters
    absender_info = f"{h_stats.get('name', '')}, {h_stats.get('street', '')}, {h_stats.get('city', '')}"
    pdf.cell(0, 4, absender_info, ln=True, align='C')
    
    # Zeile 2: Bankdaten
    bank_info = f"Bank: {h_stats.get('bank', '')} | IBAN: {h_stats.get('iban', '')}"
    pdf.cell(0, 4, bank_info, ln=True, align='C')
    
    # Zeile 3: Kontaktdaten (Falls du diese auch in die DB aufnimmst, sonst als Platzhalter)
    # Wenn du Tel/Email nicht in der DB hast, lassen wir es fest oder ziehen es aus h_stats falls vorhanden
    pdf.cell(0, 4, "Tel: +49 1751713681 | E-Mail: murat@sayilik.de", ln=True, align='C')

    path = f"/tmp/Abrechnung_{mieter_name.replace(' ', '_')}zeitraum.pdf"
    pdf.output(path)
    return path