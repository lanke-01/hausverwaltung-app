import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_conn
from pdf_utils import generate_nebenkosten_pdf

st.set_page_config(page_title="Mieter-Akte", layout="wide")
st.title("🔍 Mieter-Akte & Abrechnung")

def get_netto_strom_info(cur, jahr):
    """Berechnet Differenz zwischen Hauptstrom und Wallboxen."""
    try:
        cur.execute("""
            SELECT m.id, (MAX(r.reading_value) - MIN(r.reading_value)) 
            FROM meters m JOIN meter_readings r ON m.id = r.meter_id
            WHERE m.meter_type = 'Strom' AND m.is_submeter = FALSE
            AND EXTRACT(YEAR FROM r.reading_date) = %s GROUP BY m.id LIMIT 1
        """, (jahr,))
        main = cur.fetchone()
        if not main or not main[1]: return None
        
        cur.execute("""
            SELECT SUM(sub_val) FROM (
                SELECT (MAX(reading_value) - MIN(reading_value)) as sub_val
                FROM meter_readings r JOIN meters m ON r.meter_id = m.id
                WHERE m.parent_meter_id = %s AND m.is_submeter = TRUE
                AND EXTRACT(YEAR FROM r.reading_date) = %s GROUP BY m.id
            ) s
        """, (main[0], jahr))
        wb = cur.fetchone()[0] or 0
        return {"brutto": float(main[1]), "wallbox": float(wb)}
    except: return None

conn = get_conn()
if conn:
    try:
        cur = conn.cursor()
        # KORREKTUR: apartment_id statt unit_id
        cur.execute("SELECT id, first_name, last_name, apartment_id FROM tenants ORDER BY last_name")
        tenants = cur.fetchall()
        
        if tenants:
            t_opts = {f"{t[1]} {t[2]}": t[0] for t in tenants}
            sel_name = st.sidebar.selectbox("Mieter wählen", list(t_opts.keys()))
            t_id = t_opts[sel_name]
            jahr = st.sidebar.number_input("Jahr", value=datetime.now().year - 1)
            
            tab1, tab2 = st.tabs(["Mieter-Details", "Abrechnung erstellen"])
            
            with tab2:
                cur.execute("""
                    SELECT a.unit_name, a.area, t.occupants, t.move_in, t.move_out, t.monthly_prepayment, t.last_name
                    FROM tenants t JOIN apartments a ON t.apartment_id = a.id WHERE t.id = %s
                """, (t_id,))
                m_data = cur.fetchone()
                
                cur.execute("SELECT total_area, total_occupants, total_units, name, street, city, iban, bank_name FROM landlord_settings WHERE id = 1")
                h_data = cur.fetchone()
                
                if m_data and h_data:
                    st.success(f"Abrechnungsdaten für {sel_name} geladen.")
                    # Hier folgen die Berechnungen wie gehabt...
                else:
                    st.error("Stammdaten unvollständig.")
        else:
            st.info("Keine Mieter in der Datenbank.")
    except Exception as e:
        st.error(f"Fehler bei der Abrechnung: {e}")
    finally:
        cur.close()
        conn.close()
