import streamlit as st
import pandas as pd
import psycopg2

# --- VERBINDUNGSFUNKTION ---
def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Wohnungsverwaltung", layout="wide")
st.title("🏠 Wohnungsverwaltung")

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung möglich.")
else:
    cur = conn.cursor()

    # --- AUTO-REPAIR & MIGRATION ---
    # Wir stellen sicher, dass die Tabelle existiert und alle Spalten richtig heißen
    try:
        cur.execute("CREATE TABLE IF NOT EXISTS apartments (id SERIAL PRIMARY KEY, unit_name VARCHAR(255))")
        
        # Spalten einzeln prüfen und ggf. hinzufügen oder umbenennen
        # 1. area (Fläche)
        cur.execute("ALTER TABLE apartments ADD COLUMN IF NOT EXISTS area NUMERIC(10,2) DEFAULT 0")
        # 2. base_rent (Kaltmiete)
        cur.execute("ALTER TABLE apartments ADD COLUMN IF NOT EXISTS base_rent NUMERIC(10,2) DEFAULT 0")
        
        # 3. Spezialfall: service_charge_prepayment (NK-Vorschuss)
        # Wir prüfen, ob die Spalte existiert. Wenn nicht, schauen wir nach 'utilities' oder 'service_charge_propayment'
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='apartments'")
        existing_cols = [row[0] for row in cur.fetchall()]
        
        if 'service_charge_prepayment' not in existing_cols:
            if 'utilities' in existing_cols:
                cur.execute("ALTER TABLE apartments RENAME COLUMN utilities TO service_charge_prepayment")
            elif 'service_charge_propayment' in existing_cols:
                cur.execute("ALTER TABLE apartments RENAME COLUMN service_charge_propayment TO service_charge_prepayment")
            else:
                cur.execute("ALTER TABLE apartments ADD COLUMN service_charge_prepayment NUMERIC(10,2) DEFAULT 0")
        
        conn.commit()
    except Exception as e:
        st.error(f"Fehler bei Tabellen-Update: {e}")

    # --- NEUE WOHNUNG ANLEGEN ---
    with st.expander("➕ Neue Wohneinheit anlegen"):
        with st.form("add_apt_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Name der Einheit (z.B. EG Links)")
                flaeche = st.number_input("Fläche (m²)", min_value=0.0, step=0.5)
            with col2:
                miete = st.number_input("Kaltmiete (€)", min_value=0.0, step=10.0)
                nk = st.number_input("NK-Vorauszahlung (€)", min_value=0.0, step=5.0)
            
            if st.form_submit_button("Speichern"):
                if name:
                    cur.execute("""
                        INSERT INTO apartments (unit_name, area, base_rent, service_charge_prepayment)
                        VALUES (%s, %s, %s, %s)
                    """, (name, flaeche, miete, nk))
                    conn.commit()
                    st.success("Wohnung erfolgreich hinzugefügt!")
                    st.rerun()
                else:
                    st.warning("Bitte einen Namen für die Einheit angeben.")

    st.divider()

    # --- ÜBERSICHT ---
    st.subheader("Bestandsliste")
    
    query = """
        SELECT 
            id as "ID", 
            unit_name as "Einheit", 
            area as "m²", 
            base_rent as "Kalt (€)", 
            service_charge_prepayment as "NK-Vorschuss (€)" 
        FROM apartments 
        ORDER BY unit_name ASC
    """
    
    try:
        df = pd.read_sql(query, conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Noch keine Wohnungen angelegt.")
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")

    cur.close()
    conn.close()