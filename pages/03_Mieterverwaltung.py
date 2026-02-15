import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Mieterverwaltung", layout="wide")

def get_conn():
    conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
    conn.set_client_encoding('UTF8')
    return conn

st.title("👤 Mieterverwaltung")

conn = get_conn()
cur = conn.cursor()

# --- TABELLENÜBERSICHT ---
st.subheader("Aktuelle Mieterliste")
df_tenants = pd.read_sql("""
    SELECT t.id, t.first_name, t.last_name, a.unit_name, t.moved_in, t.moved_out 
    FROM tenants t 
    LEFT JOIN apartments a ON t.apartment_id = a.id
    ORDER BY t.moved_out IS NOT NULL, t.last_name
""", conn)
if not df_tenants.empty:
    st.dataframe(df_tenants, width="stretch")
else:
    st.info("Noch keine Mieter erfasst.")

st.divider()

# --- BEREICH 1: NEUER EINZUG ---
with st.expander("➕ Neuer Mieter / Einzug"):
    # Nur Wohnungen anzeigen, die NICHT belegt sind
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
            with col2:
                apt = st.selectbox("Wohnung", options=list(free_apts.keys()))
                in_date = st.date_input("Einzugsdatum", value=datetime.now())
            
            occ = st.number_input("Personenanzahl", min_value=1, value=1)
            
            if st.form_submit_button("Einzug speichern"):
                cur.execute("""
                    INSERT INTO tenants (first_name, last_name, apartment_id, moved_in, occupants) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (fn, ln, free_apts[apt], in_date, occ))
                conn.commit()
                st.success(f"Mieter {fn} {ln} eingezogen!")
                st.rerun()
    else:
        st.warning("Keine freien Wohnungen verfügbar. Lege erst eine Wohnung an oder buche einen Auszug.")

st.divider()

# --- BEREICH 2: MIETER BEARBEITEN / LÖSCHEN ---
st.subheader("🛠️ Mieter korrigieren oder löschen")
cur.execute("SELECT id, first_name || ' ' || last_name || ' (' || id || ')' FROM tenants")
t_list = {name: tid for tid, name in cur.fetchall()}

if t_list:
    t_sel = st.selectbox("Mieter wählen", options=["-- Bitte wählen --"] + list(t_list.keys()))
    
    if t_sel != "-- Bitte wählen --":
        tid = t_list[t_sel]
        
        col_edit, col_del = st.columns(2)
        
        with col_edit:
            st.write("**Auszug registrieren**")
            out_date = st.date_input("Auszugsdatum")
            if st.button("Auszug speichern"):
                cur.execute("UPDATE tenants SET moved_out = %s WHERE id = %s", (out_date, tid))
                conn.commit()
                st.success("Auszug vermerkt.")
                st.rerun()
        
        with col_del:
            st.write("**Datenfehler löschen**")
            st.warning("Vorsicht: Löscht auch alle verknüpften Zahlungen!")
            confirm = st.checkbox("Sicher löschen? (ID: " + str(tid) + ")")
            if st.button("🗑️ Mieter komplett löschen"):
                if confirm:
                    # Zuerst Zahlungen löschen (wegen Foreign Key)
                    cur.execute("DELETE FROM payments WHERE tenant_id = %s", (tid,))
                    # Dann Mieter löschen
                    cur.execute("DELETE FROM tenants WHERE id = %s", (tid,))
                    conn.commit()
                    st.success("Mieter und Zahlungen gelöscht!")
                    st.rerun()
                else:
                    st.error("Bitte Häkchen zur Bestätigung setzen.")

conn.close()