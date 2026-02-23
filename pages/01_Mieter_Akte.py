import streamlit as st
import pandas as pd
from datetime import datetime, date
import psycopg2
from pdf_utils import generate_nebenkosten_pdf

# --- DIREKTE VERBINDUNGSFUNKTION --
def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Mieter-Akte", layout="wide")
st.title("🔍 Mieter-Akte & Abrechnung")

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung.")
else:
    cur = conn.cursor()
    try:
        # Mieter laden (WICHTIG: apartment_id statt unit_id)
        cur.execute("SELECT id, first_name, last_name, apartment_id FROM tenants ORDER BY last_name")
        tenants = cur.fetchall()
        
        if tenants:
            # Mieter-Auswahl in der Seitenleiste
            t_opts = {f"{t[1]} {t[2]}": t[0] for t in tenants}
            sel_name = st.sidebar.selectbox("Mieter wählen", list(t_opts.keys()))
            t_id = t_opts[sel_name]
            jahr = st.sidebar.number_input("Abrechnungsjahr", value=datetime.now().year - 1)
            
            tab1, tab2 = st.tabs(["📋 Mieter-Details", "📄 Abrechnung erstellen"])
            
            with tab1:
                st.subheader(f"Daten von {sel_name}")
                cur.execute("SELECT * FROM tenants WHERE id = %s", (t_id,))
                t_data = cur.fetchone()
                st.write(t_data) # Kurz-Übersicht

            with tab2:
                # JOIN mit apartments über apartment_id
                cur.execute("""
                    SELECT a.unit_name, a.size_sqm, t.occupants, t.move_in, t.move_out, t.monthly_prepayment, t.last_name
                    FROM tenants t 
                    JOIN apartments a ON t.apartment_id = a.id 
                    WHERE t.id = %s
                """, (t_id,))
                m_data = cur.fetchone()
                
                # Haus-Stammdaten aus den Einstellungen
                cur.execute("SELECT total_area, total_occupants, name, street, city, iban, bank_name FROM landlord_settings WHERE id = 1")
                h_data = cur.fetchone()
                
                if m_data and h_data:
                    st.success(f"Daten für {jahr} bereit.")
                    
                    # Hier die Werte für die Berechnung zuordnen
                    m_area = float(m_data[1] or 0)
                    h_area = float(h_data[0] or 0)
                    
                    col1, col2 = st.columns(2)
                    col1.metric("Wohnfläche Mieter", f"{m_area} m²")
                    col2.metric("Gesamtfläche Haus", f"{h_area} m²")
                    
                    if h_area == 0:
                        st.warning("⚠️ Die Gesamtfläche des Hauses ist in den Einstellungen noch 0. Die Berechnung wird nicht korrekt sein.")
                else:
                    st.error("⚠️ Stammdaten unvollständig (Wohnung oder Haus-Einstellungen fehlen).")
        else:
            st.info("Keine Mieter in der Datenbank gefunden.")
            
    except Exception as e:
        st.error(f"Fehler im System: {e}")
    finally:
        cur.close()
        conn.close()
