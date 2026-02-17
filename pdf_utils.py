# --- INFODATEN: KORRIGIERTES LAYOUT ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    # Nutzt die volle Breite von 190mm (DIN A4 minus Ränder)
    pdf.cell(190, 8, " Allgemeine Angaben zur Wohnung und zu den Verteilungsschlüsseln", 0, 1, 'L', True)
    pdf.ln(2) # Kleiner Abstand nach der Überschrift

    pdf.set_font('Arial', '', 9)
    
    # Definition der Spaltenbreiten für ein sauberes Raster
    # Spalte 1 (Mieter-Info) | Spalte 2 (Haus-Gesamtinfo)
    col_width = 95 
    
    # Zeile 1: Zeiträume
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(col_width, 5, "Ihr Nutzungszeitraum:", 0, 0)
    pdf.cell(col_width, 5, "Abrechnungszeitraum:", 0, 1)
    
    pdf.set_font('Arial', '', 9)
    pdf.cell(col_width, 5, zeitraum, 0, 0)
    pdf.cell(col_width, 5, zeitraum, 0, 1)
    pdf.ln(2)

    # Zeile 2: Tage
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(col_width, 5, "Ihre Nutzungstage:", 0, 0)
    pdf.cell(col_width, 5, "Abrechnungstage:", 0, 1)
    
    pdf.set_font('Arial', '', 9)
    pdf.cell(col_width, 5, str(tage), 0, 0)
    pdf.cell(col_width, 5, "365", 0, 1)
    pdf.ln(2)

    # Zeile 3: Fläche
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(col_width, 5, "Wohnfläche Ihrer Wohnung:", 0, 0)
    pdf.cell(col_width, 5, "Gesamtwohnfläche Haus:", 0, 1)
    
    pdf.set_font('Arial', '', 9)
    pdf.cell(col_width, 5, f"{m_stats['area']} m2", 0, 0)
    pdf.cell(col_width, 5, f"{h_stats['area']} m2", 0, 1)
    pdf.ln(2)

    # Zeile 4: Personen & Einheiten
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(col_width, 5, "Personen (Ihr Haushalt):", 0, 0)
    pdf.cell(col_width, 5, "Anzahl Wohneinheiten Haus:", 0, 1)
    
    pdf.set_font('Arial', '', 9)
    pdf.cell(col_width, 5, str(m_stats['pers']), 0, 0)
    pdf.cell(col_width, 5, str(h_stats['units']), 0, 1)
    pdf.ln(5) # Größerer Abstand vor der Tabelle