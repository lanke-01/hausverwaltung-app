import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Wohnungen verwalten", layout="wide")

def get_conn():
    conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
    conn.set_client_encoding('UTF8')
    return conn

st.title("🏠 Wohnungs-Verwaltung")

conn = get_conn()
cur = conn.cursor()

# --- BEREICH 1: BEARBEITEN & LÖSCHEN ---
st.subheader("📝 Wohnung bearbeiten oder löschen")
# Wir laden die ID mit in die Auswahl, um bei Duplikaten die richtige zu treffen
cur.execute("SELECT id, unit_name FROM apartments ORDER BY unit_name, id")
apts = cur.fetchall()
apt_options = {f"{name} (ID: {aid})": aid for aid, name in apts}

if apt_options:
    selected_label = st.selectbox("Wohnung auswählen", options=["-- Bitte wählen --"] + list(apt_options.keys()))
    
    if selected_label != "-- Bitte wählen --":
        aid = apt_options[selected_label]
        
        # Aktuelle Daten laden
        cur.execute("SELECT unit_name, size_sqm, base_rent, service_charge_propayment FROM apartments WHERE id = %s", (aid,))
        current_data = cur.fetchone()
        
        with st.form("edit_delete_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Bezeichnung", value=current_data[0])
                new_size = st.number_input("Fläche (m²)", value=float(current_data[1]), step=0.1)
            with col2:
                new_rent = st.number_input("Kaltmiete (€)", value=float(current_data[2]), step=1.0)
                new_prepay = st.number_input("NK-Vorauszahlung (€)", value=float(current_data[3]), step=1.0)
            
            # Zwei Buttons nebeneinander
            btn_save, btn_delete = st.columns([1, 1])
            
            with btn_save:
                if st.form_submit_button("💾 Änderungen speichern"):
                    cur.execute("""
                        UPDATE apartments 
                        SET unit_name = %s, size_sqm = %s, base_rent = %s, service_charge_propayment = %s 
                        WHERE id = %s
                    """, (new_name, new_size, new_rent, new_prepay, aid))
                    conn.commit()
                    st.success(f"Wohnung {aid} aktualisiert!")
                    st.rerun()
            
            with btn_delete:
                # Da Löschen gefährlich ist, nutzen wir eine Checkbox zur Bestätigung
                confirm = st.checkbox("Sicher löschen?")
                if st.form_submit_button("🗑️ Datensatz löschen"):
                    if confirm:
                        try:
                            cur.execute("DELETE FROM apartments WHERE id = %s", (aid,))
                            conn.commit()
                            st.success(f"Wohnung ID {aid} gelöscht!")
                            st.rerun()
                        except Exception as e:
                            st.error("Löschen nicht möglich: Wohnung ist wahrscheinlich noch einem Mieter zugeordnet!")
                    else:
                        st.warning("Bitte erst das Häkchen bei 'Sicher löschen' setzen.")

st.divider()

# --- BEREICH 2: NEU ANLEGEN ---
with st.expander("➕ Neue Wohneinheit hinzufügen"):
    with st.form("apt_form_new"):
        c1, c2 = st.columns(2)
        with c1:
            n_name = st.text_input("Bezeichnung")
            n_size = st.number_input("Fläche (m²)", min_value=0.0, step=0.1)
        with c2:
            n_rent = st.number_input("Kaltmiete (€)", min_value=0.0, step=1.0)
            n_prepay = st.number_input("NK-Vorauszahlung (€)", min_value=0.0, step=1.0)
            
        if st.form_submit_button("Anlegen"):
            cur.execute("""
                INSERT INTO apartments (unit_name, size_sqm, base_rent, service_charge_propayment) 
                VALUES (%s, %s, %s, %s)
            """, (n_name, n_size, n_rent, n_prepay))
            conn.commit()
            st.rerun()

st.divider()

# --- BEREICH 3: TABELLE ---
st.subheader("Aktueller Bestand")
df_apts = pd.read_sql("SELECT id, unit_name as Einheit, size_sqm as m2, base_rent as Kalt, service_charge_propayment as NK_Vorschuss FROM apartments ORDER BY unit_name, id", conn)
st.dataframe(df_apts, width="stretch")

conn.close()