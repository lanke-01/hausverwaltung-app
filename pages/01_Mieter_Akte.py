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

    def footer(self):
        self.set_y(-25)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f"Bank: {self.ld.get('bank', '')} | IBAN: {self.ld.get('iban', '')}", ln=True, align='C')

def create_pdf(landlord_data, mieter_name, wohnung, zeitraum, tage, tabelle, gesamt, voraus, diff):
    pdf = NK_PDF(landlord_data)
    pdf.add_page()
    pdf.set_font('Arial', '', 11)
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 5, mieter_name, ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 5, f"Wohnung: {wohnung}", ln=True)
    pdf.ln(10)
    pdf.write(5, f"Zeitraum: {zeitraum} ({tage} Tage)\n\n")
    
    # Tabelle Header
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(70, 8, 'Kostenart', 1)
    pdf.cell(40, 8, 'Haus Gesamt', 1, 0, 'R')
    pdf.cell(40, 8, 'Ihr Anteil', 1, 1, 'R')
    
    # Tabelle Zeilen
    pdf.set_font('Arial', '', 10)
    for row in tabelle:
        pdf.cell(70, 8, str(row['Kostenart']), 1)
        pdf.cell(40, 8, f"{row['Haus Gesamt']} EUR", 1, 0, 'R')
        pdf.cell(40, 8, f"{row['Ihr Anteil']} EUR", 1, 1, 'R')
    
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(110, 8, "Gesamtkosten Anteil:", 0, 0, 'R')
    pdf.cell(40, 8, f"{gesamt:.2f} EUR", 0, 1, 'R')
    pdf.cell(110, 8, "Vorauszahlungen:", 0, 0, 'R')
    pdf.cell(40, 8, f"{voraus:.2f} EUR", 0, 1, 'R')
    
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    label = "Guthaben:" if diff >= 0 else "Nachforderung:"
    pdf.cell(110, 10, label, 0, 0, 'R')
    pdf.cell(40, 10, f"{abs(diff):.2f} EUR", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP LOGIC ---
st.set_page_config(page_title="Mieter-Akte", layout="wide")
st.title("🔍 Mieter-Akte & Abrechnung")

conn = get_conn()
if conn:
    try:
        cur = conn.cursor()
        
        # 1. Vermieterdaten sicher laden
        cur.execute("SELECT name, street, city, iban, bank_name FROM landlord_settings WHERE id = 1")
        ld_res = cur.fetchone()
        if ld_res:
            l_data = {"name": ld_res[0], "street": ld_res[1], "city": ld_res[2], "iban": ld_res[3], "bank": ld_res[4]}
        else:
            l_data = {"name": "Bitte in Einstellungen ausfüllen", "street": "", "city": "", "iban": "", "bank": ""}
            st.warning("⚠️ Vermieterdaten fehlen! Bitte unter 'Einstellungen' ergänzen.")

        # 2. Mieter-Auswahl
        cur.execute("SELECT id, first_name || ' ' || last_name FROM tenants ORDER BY last_name")
        tenants = cur.fetchall()
        
        if tenants:
            tenant_map = {name: tid for tid, name in tenants}
            search_name = st.selectbox("Mieter auswählen", options=list(tenant_map.keys()))
            t_id = tenant_map[search_name]
            
            # Mieterdetails laden
            cur.execute("""
                SELECT t.first_name, t.last_name, a.unit_name, a.size_sqm, t.occupants, 
                       a.base_rent, a.service_charge_propayment, t.moved_in, t.moved_out
                FROM tenants t 
                JOIN apartments a ON t.apartment_id = a.id 
                WHERE t.id = %s
            """, (t_id,))
            t_data = cur.fetchone()
            
            if t_data:
                t_fn, t_ln, t_apt, t_size, t_occ, t_rent, t_prepay, t_in, t_out = t_data
                
                tab_info, tab_billing = st.tabs(["📋 Stammdaten", "📄 Abrechnung"])
                
                with tab_info:
                    st.subheader(f"Mieter: {t_fn} {t_ln}")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Wohnung:** {t_apt}")
                        st.write(f"**Fläche:** {t_size} m²")
                        st.write(f"**Einzug:** {t_in}")
                    with c2:
                        st.write(f"**Kaltmiete:** {t_rent:.2f} Euro")
                        st.write(f"**NK-Vorauszahlung:** {t_prepay:.2f} Euro")

                with tab_billing:
                    jahr = st.selectbox("Abrechnungsjahr", [2024, 2025, 2026], index=0)
                    # Zeitraum berechnen
                    j_start, j_ende = date(jahr, 1, 1), date(jahr, 12, 31)
                    calc_start = max(j_start, t_in)
                    calc_ende = min(j_ende, t_out) if t_out else j_ende
                    tage = max((calc_ende - calc_start).days + 1, 0)
                    
                    st.info(f"Zeitraum: {calc_start} bis {calc_ende} ({tage} Tage)")
                    
                    # Ausgaben laden
                    df_expenses = pd.read_sql("SELECT expense_type, amount, distribution_key FROM operating_expenses WHERE expense_year = %s", conn, params=(jahr,))
                    
                    if not df_expenses.empty and tage > 0:
                        # Haus-Gesamtwerte für Schlüssel berechnen
                        cur.execute("SELECT SUM(size_sqm) FROM apartments")
                        total_sqm = float(cur.fetchone()[0] or 1.0)
                        
                        billing_rows = []
                        total_share = 0.0
                        for _, row in df_expenses.iterrows():
                            amt, key = float(row['amount']), row['distribution_key']
                            # Einfache Logik für m2 Verteilung
                            share = (amt * (float(t_size) / total_sqm)) * (tage / 365.0)
                            total_share += share
                            billing_rows.append({"Kostenart": row['expense_type'], "Haus Gesamt": f"{amt:.2f}", "Ihr Anteil": f"{share:.2f}"})
                        
                        st.table(pd.DataFrame(billing_rows))
                        
                        voraus_ist = ((float(t_prepay) * 12) / 365) * tage
                        diff = voraus_ist - total_share
                        
                        st.metric("Geleistete Vorauszahlung", f"{voraus_ist:.2f} Euro")
                        st.metric("Ergebnis", f"{diff:.2f} Euro", delta=round(diff, 2))
                        
                        # PDF Button
                        pdf_bytes = create_pdf(l_data, f"{t_fn} {t_ln}", t_apt, f"{calc_start}-{calc_ende}", tage, billing_rows, total_share, voraus_ist, diff)
                        st.download_button("📄 PDF herunterladen", data=pdf_bytes, file_name=f"Abrechnung_{t_ln}.pdf", mime="application/pdf")
                    else:
                        st.warning("Keine Ausgaben für dieses Jahr erfasst.")
        else:
            st.info("Keine Mieter gefunden.")
    except Exception as e:
        st.error(f"Fehler: {e}")
    finally:
        conn.close()