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

st.set_page_config(page_title="Mieterverwaltung", layout="wide")
st.title("👥 Mieterverwaltung")

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung möglich.")
else:
    # --- ÜBERSICHTSTABELLE ---
    st.subheader("Aktuelle Mieterliste")
    
    # Korrigierte Spaltennamen: 
    # move_in statt moved_in, move_out statt moved_out
    # base_rent statt rent, monthly_prepayment statt utilities (basierend auf deinem init_db)
    query = """
        SELECT 
            t.id, 
            t.first_name as Vorname, 
            t.last_name as Nachname, 
            a.unit_name as Wohnung, 
            t.move_in as Einzug 
        FROM tenants t
        LEFT JOIN apartments a ON t.apartment_id = a.id
        WHERE t.move_out IS NULL
        ORDER BY t.last_name
    """
    
    try:
        df_tenants = pd.read_sql(query, conn)
        if not df_tenants.empty:
            st.dataframe(df_tenants, use_container_width=True, hide_index=True)
        else:
            st.info("Momentan sind keine aktiven Mieter registriert.")
    except Exception as e:
        st.error(f"Fehler beim Laden der Mieterliste: {e}")

    st.divider()

    # --- NEUEN MIETER ANLEGEN ---
    st.subheader("➕ Neuen Mieter hinzufügen")
    
    with st.form("add_tenant_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            f_name = st.text_input("Vorname")
            l_name = st.text_input("Nachname")
            # Wohnungen für Selectbox laden
            cur = conn.cursor()
            cur.execute("SELECT id, unit_name FROM apartments ORDER BY unit_name")
            apartments = cur.fetchall()
            apt_options = {a[1]: a[0] for a in apartments}
            sel_apt = st.selectbox("Wohnung zuweisen", list(apt_options.keys()) if apt_options else ["Keine Wohnungen vorhanden"])
        
        with col2:
            m_in = st.date_input("Einzugsdatum")
            # Falls deine Tabelle diese Spalten hat (monthly_prepayment ist Standard in deinem Setup)
            prepayment = st.number_input("Nebenkosten-Vorauszahlung (€)", min_value=0.0, step=5.0)

        if st.form_submit_button("Mieter speichern"):
            if not f_name or not l_name or not apt_options:
                st.warning("Bitte alle Pflichtfelder ausfüllen.")
            else:
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO tenants (first_name, last_name, apartment_id, move_in, monthly_prepayment)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (f_name, l_name, apt_options[sel_apt], m_in, prepayment))
                    conn.commit()
                    st.success(f"✅ Mieter {f_name} {l_name} wurde erfolgreich angelegt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")

    conn.close()