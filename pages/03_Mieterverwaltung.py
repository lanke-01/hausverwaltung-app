import streamlit as st
import pandas as pd
from datetime import datetime
from database import get_conn  # Zentraler Import

st.set_page_config(page_title="Mieterverwaltung", layout="wide")

st.title("👤 Mieterverwaltung")

conn = get_conn()

if conn:
    cur = conn.cursor()

    # --- TABELLENÜBERSICHT ---
    st.subheader("Aktuelle Mieterliste")
    df_tenants = pd.read_sql("""
        SELECT t.id, t.first_name as Vorname, t.last_name as Nachname, 
               a.unit_name as Wohnung, t.moved_in as Einzug, t.moved_out as Auszug 
        FROM tenants t 
        LEFT JOIN apartments a ON t.apartment_id = a.id
        ORDER BY t.moved_out IS NOT NULL, t.last_name
    """, conn)
    
    if not df_tenants.empty:
        st.dataframe(df_tenants, use_container_width=True, hide_index=True)
    else:
        st.info("Noch keine Mieter erfasst.")

    st.divider()

    # --- BEREICH 1: NEUER EINZUG ---
    with st.expander("➕ Neuer Mieter / Einzug"):
        # Nur Wohnungen anzeigen, die aktuell frei sind
        cur.execute("""
            SELECT id, unit_name FROM apartments 
            WHERE id NOT IN (SELECT apartment_id FROM tenants WHERE moved_out IS NULL)
        """)
        free_apts = {name: aid for aid, name in cur.fetchall()}
        
        if free_apts:
            with st.form("new_tenant_form"):
                col1, col2 = st.columns(2)
                with col1:
                    fn = st.text_input("Vorname")
                    ln = st.text_input("Nachname")
                    occ = st.number_input("Anzahl Personen", min_value=1, value=1)
                with col2:
                    apt_name = st.selectbox("Wohnung wählen", options=list(free_apts.keys()))
                    in_date = st.date_input("Einzugsdatum", value=datetime.now())
                
                if st.form_submit_button("Einzug speichern"):
                    cur.execute("""
                        INSERT INTO tenants (first_name, last_name, apartment_id, moved_in, occupants) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, (fn, ln, free_apts[apt_name], in_date, occ))
                    conn.commit()
                    st.success(f"Mieter {fn} {ln} wurde erfolgreich angelegt!")
                    st.rerun()
        else:
            st.warning("Momentan sind alle Wohnungen belegt. Erfassen Sie erst einen Auszug.")

    st.divider()

    # --- BEREICH 2: AUSZUG ODER LÖSCHEN ---
    st.subheader("🛠️ Mieter bearbeiten (Auszug/Löschen)")
    cur.execute("SELECT id, first_name || ' ' || last_name FROM tenants WHERE moved_out IS NULL")
    active_tenants = {name: tid for tid, name in cur.fetchall()}

    if active_tenants:
        t_sel = st.selectbox("Aktiven Mieter wählen", options=["-- Bitte wählen --"] + list(active_tenants.keys()))
        
        if t_sel != "-- Bitte wählen --":
            tid = active_tenants[t_sel]
            
            col_out, col_del = st.columns(2)
            with col_out:
                st.write("**Auszug registrieren**")
                out_date = st.date_input("Auszugsdatum")
                if st.button("Auszug jetzt speichern"):
                    cur.execute("UPDATE tenants SET moved_out = %s WHERE id = %s", (out_date, tid))
                    conn.commit()
                    st.success("Auszug wurde gespeichert.")
                    st.rerun()
            
            with col_del:
                st.write("**Fehlbuchung löschen**")
                confirm = st.checkbox("Bestätige: Mieter komplett löschen")
                if st.button("🗑️ Unwiderruflich löschen"):
                    if confirm:
                        cur.execute("DELETE FROM tenants WHERE id = %s", (tid,))
                        conn.commit()
                        st.success("Mieter wurde gelöscht.")
                        st.rerun()
                    else:
                        st.error("Bitte Häkchen zur Bestätigung setzen.")

    conn.close()
else:
    st.error("Datenbankverbindung fehlgeschlagen.")