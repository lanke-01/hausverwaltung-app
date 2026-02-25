import streamlit as st
import pandas as pd
from datetime import datetime, date
import psycopg2
from pdf_utils import generate_nebenkosten_pdf

def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Mieter-Akte", layout="wide")
st.title("🔍 Mieter-Akte & Abrechnung")

DEUTSCHE_SCHLUESSEL = {
    "area": "m² Wohnfläche",
    "persons": "Anzahl Personen",
    "unit": "Wohneinheiten (1/6)",
    "direct": "Direktzuordnung"
}

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung.")
else:
    cur = conn.cursor()
    try:
        # Mieterliste laden
        cur.execute("SELECT id, first_name, last_name FROM tenants ORDER BY last_name")
        tenants = cur.fetchall()
        
        if tenants:
            t_opts = {f"{t[1]} {t[2]}": t[0] for t in tenants}
            sel_name = st.sidebar.selectbox("Mieter wählen", list(t_opts.keys()))
            t_id = t_opts[sel_name]
            jahr = st.sidebar.number_input("Abrechnungsjahr", value=2024)
            
            # 1. Daten abrufen
            cur.execute("""
                SELECT a.unit_name, a.area, t.occupants, t.move_in, t.move_out, t.monthly_prepayment, t.first_name, t.last_name 
                FROM tenants t JOIN apartments a ON t.apartment_id = a.id WHERE t.id = %s
            """, (t_id,))
            m_data = cur.fetchone()
            
            cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants FROM landlord_settings WHERE id = 1")
            h_data = cur.fetchone()

            cur.execute("SELECT expense_type, amount, distribution_key FROM operating_expenses WHERE expense_year = %s", (jahr,))
            expenses = cur.fetchall()

            if m_data and h_data and expenses:
                # --- FEHLERQUELLE 1: ZEITRAUM ---
                abr_start = date(jahr, 1, 1)
                abr_ende = date(jahr, 12, 31)
                
                # Mietzeitraum innerhalb des Abrechnungsjahres eingrenze
                m_start = max(m_data[3], abr_start)
                m_ende = min(m_data[4] or abr_ende, abr_ende)
                
                mieter_tage = (m_ende - m_start).days + 1
                tage_jahr = (abr_ende - abr_start).days + 1
                
                # Wenn der Mieter gar nicht in dem Jahr gewohnt hat
                if mieter_tage <= 0:
                    st.warning("Dieser Mieter hat im gewählten Jahr nicht im Objekt gewohnt.")
                else:
                    zeit_faktor = mieter_tage / tage_jahr

                    st.info(f"Berechnung für {mieter_tage} von {tage_jahr} Tagen.")

                    # --- FEHLERQUELLE 2: KOSTENANTEILE ---
                    rows = []
                    summe_mieter = 0.0
                    
                    for exp in expenses:
                        name, gesamt_h, key = exp
                        gesamt_h = float(gesamt_h)
                        
                        if key == "area":
                            # (Gesamtbetrag / Gesamtfläche Haus) * Mieterfläche * Anteil Tage
                            anteil = (gesamt_h / float(h_data[5])) * float(m_data[1]) * zeit_faktor
                        elif key == "persons":
                            # Personentage: (Gesamtbetrag / (Gesamtpersonen * Tage_Jahr)) * (Mieterpersonen * Mieter_Tage)
                            h_pers_tage = float(h_data[6]) * tage_jahr
                            m_pers_tage = float(m_data[2] or 1) * mieter_tage
                            anteil = (gesamt_h / h_pers_tage) * m_pers_tage
                        elif key == "unit":
                            # Pro Wohneinheit (1/6) * Anteil Tage
                            anteil = (gesamt_h / 6.0) * zeit_faktor
                        else:
                            anteil = gesamt_h * zeit_faktor
                        
                        summe_mieter += anteil
                        rows.append({
                            "Kostenart": name,
                            "Gesamtkosten Haus": f"{gesamt_h:.2f} €",
                            "Schlüssel": DEUTSCHE_SCHLUESSEL.get(key, key),
                            "Ihr Anteil": f"{anteil:.2f} €"
                        })

                    st.table(pd.DataFrame(rows))

                    # --- FEHLERQUELLE 3: VORAUSZAHLUNG ---
                    # Vorauszahlung exakt auf Tage gerechnet
                    voraus_anteilig = (float(m_data[5]) * 12) * zeit_faktor
                    saldo = summe_mieter - voraus_anteilig

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Summe Kosten", f"{summe_mieter:.2f} €")
                    c2.metric("Vorauszahlung", f"{voraus_anteilig:.2f} €")
                    c3.metric("Saldo", f"{saldo:.2f} €", delta_color="inverse")

                    # PDF Button bleibt gleich...