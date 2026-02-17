import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_conn
from fpdf import FPDF
import io

# --- PDF GENERATOR ---
class NK_PDF(FPDF):
    def __init__(self, landlord_data):
        super().__init__()
        self.ld = landlord_data

    def header(self):
        self.set_font('Arial', 'I', 8)
        header_text = f"{self.ld.get('name', '')} - {self.ld.get('street', '')} - {self.ld.get('city', '')}"
        self.cell(0, 5, header_text, ln=True)
        self.ln(5)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Nebenkostenabrechnung', ln=True)

def create_pdf(landlord_data, mieter_name, wohnung, zeitraum, tage, tabelle, gesamt, voraus, diff, m_stats, h_stats):
    pdf = NK_PDF(landlord_data)
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    
    # Info-Block
    pdf.cell(0, 5, f"Mieter: {mieter_name}", ln=True)
    pdf.cell(0, 5, f"Wohnung: {wohnung}", ln=True)
    pdf.cell(0, 5, f"Zeitraum: {zeitraum} ({tage} Tage)", ln=True)
    pdf.ln(5)
    
    # Tabelle
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(50, 8, 'Kostenart', 1)
    pdf.cell(30, 8, 'Haus Ges.', 1, 0, 'R')
    pdf.cell(40, 8, 'Schlüssel', 1, 0, 'C')
    pdf.cell(30, 8, 'Anteil', 1, 0, 'R')
    pdf.cell(30, 8, 'Kosten', 1, 1, 'R')
    
    pdf.set_font('Arial', '', 8)
    for row in tabelle:
        pdf.cell(50, 8, str(row['Kostenart']), 1)
        pdf.cell(30, 8, row['Haus Gesamt'], 1, 0, 'R')
        pdf.cell(40, 8, row['Verteilung'], 1, 0, 'C')
        pdf.cell(30, 8, row['Anteil'], 1, 0, 'R')
        pdf.cell(30, 8, f"{row['Ihr Anteil']} EUR", 1, 1, 'R')

    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(150, 8, "Gesamtkosten:", 0, 0, 'R')
    pdf.cell(30, 8, f"{gesamt:.2f} EUR", 0, 1, 'R')
    pdf.cell(150, 8, "Vorauszahlung:", 0, 0, 'R')
    pdf.cell(30, 8, f"{voraus:.2f} EUR", 0, 1, 'R')
    pdf.cell(150, 10, "Ergebnis:", 0, 0, 'R')
    pdf.cell(30, 10, f"{diff:.2f} EUR", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- BERECHNUNGSLOGIK (WIE PDF) ---
def get_share(art, betrag, m_area, h_area, m_pers, h_pers, h_units, tage):
    # Zuordnung der Schlüssel
    area_keys = ["Grundsteuer", "Sach- und Haftpflichtversicherung", "Schornsteinfeger"]
    person_keys = ["Kaltwasser", "Entwässerung", "Straßenreinigung und Müll", "Allgemeinstrom", "Beleuchtung"]
    unit_keys = ["Gartenpflege", "Hausmeister", "Sonstiges"]

    zf = tage / 365.0
    
    if any(k in art for k in area_keys):
        schl = "m2"
        anteil_str = f"{m_area}/{h_area}"
        kosten = (betrag / h_area) * m_area * zf
    elif any(k in art for k in person_keys):
        schl = "Pers.-Tage"
        m_pt = m_pers * tage
        h_pt = h_pers * 365
        anteil_str = f"{m_pt}/{h_pt}"
        kosten = (betrag / h_pt) * m_pt
    elif any(k in art for k in unit_keys):
        schl = "Einheit"
        anteil_str = f"1/{h_units}"
        kosten = (betrag / h_units) * zf
    else:
        schl = "m2 (Std)"
        anteil_str = f"{m_area}/{h_area}"
        kosten = (betrag / h_area) * m_area * zf
        
    return round(kosten, 2), schl, anteil_str

# --- MAIN APP ---
conn = get_conn()
if conn:
    cur = conn.cursor()
    
    # 1. Haus-Daten laden
    cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants, total_units FROM landlord_settings WHERE id = 1")
    h_data = cur.fetchone()
    if h_data:
        ld = {"name": h_data[0], "street": h_data[1], "city": h_data[2], "iban": h_data[3], "bank": h_data[4]}
        h_stats = {"area": float(h_data[5] or 1), "pers": int(h_data[6] or 1), "units": int(h_data[7] or 1)}
    
    # 2. Mieter Auswahl
    cur.execute("SELECT id, first_name || ' ' || last_name FROM tenants WHERE moved_out IS NULL")
    t_list = {name: tid for tid, name in cur.fetchall()}
    
    sel_name = st.selectbox("Mieter wählen", options=["--"] + list(t_list.keys()))
    
    if sel_name != "--":
        tid = t_list[sel_name]
        cur.execute("SELECT apartment_id, area, occupants, moved_in, utilities FROM tenants WHERE id = %s", (tid,))
        t_res = cur.fetchone()
        m_stats = {"apt": t_res[0], "area": float(t_res[1] or 0), "pers": int(t_res[2] or 0), "in": t_res[3], "pre": float(t_res[4] or 0)}
        
        jahr = st.selectbox("Jahr", [2024, 2025, 2026], index=2)
        tage = 365 # Vereinfacht für das ganze Jahr
        
        # Ausgaben laden
        df_exp = pd.read_sql("SELECT expense_type, amount FROM operating_expenses WHERE expense_year = %s", conn, params=(jahr,))
        
        if not df_exp.empty:
            rows = []
            total = 0.0
            for _, r in df_exp.iterrows():
                amt = float(r['amount'])
                kosten, schl, ant_s = get_share(r['expense_type'], amt, m_stats['area'], h_stats['area'], m_stats['pers'], h_stats['pers'], h_stats['units'], tage)
                total += kosten
                rows.append({"Kostenart": r['expense_type'], "Haus Gesamt": f"{amt:.2f}", "Verteilung": schl, "Anteil": ant_s, "Ihr Anteil": f"{kosten:.2f}"})
            
            st.table(pd.DataFrame(rows))
            voraus = m_stats['pre'] * 12
            diff = voraus - total
            
            st.metric("Ergebnis", f"{diff:.2f} EUR", delta=round(diff, 2))
            
            # PDF Erstellung
            if st.button("📄 PDF generieren"):
                pdf_b = create_pdf(ld, sel_name, "Whg", f"01.01.{jahr}-31.12.{jahr}", tage, rows, total, voraus, diff, m_stats, h_stats)
                st.download_button("Download PDF", pdf_b, f"Abrechnung_{sel_name}.pdf")

    cur.close()
    conn.close()