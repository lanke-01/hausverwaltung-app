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
    cur = conn.cursor()
    
    # Sicherstellen, dass die Spalte 'occupants' existiert
    cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS occupants INTEGER DEFAULT 1")
    conn.commit()

    # --- ÜBERSICHTSTABELLE ---
    st.subheader("Aktuelle Mieterliste")
    
    # Abfrage inklusive Personenanzahl (occupants)
    query = """
        SELECT 
            t.id as ID, 
            t.first_name as Vorname, 
            t.last_name as Nachname, 
            a.unit_name as Wohnung, 
            t.occupants as Personen,
            t.move_in as Einzug,
            t.monthly_prepayment as "NK-Vorschuss (€)"
        FROM tenants t
        LEFT JOIN apartments a ON t.apartment_id = a.id
        WHERE t.move_out IS NULL
        ORDER BY t.last_name
    """
    
    try:
        df_tenants = pd.read_sql(query, conn)
        if not df_tenants.empty:
            st.dataframe(df_tenants, use_container_width=True, hide_index=True)
            
            # --- BEARBEITUNGS-MODUS ---
            st.divider()
            with st.expander("✏️ Bestehenden Mieter bearbeiten"):
                # Mieter für Auswahl laden
                tenant_list = {f"{r['Vorname']} {r['Nachname']} (ID: {r['ID']})": r['ID'] for _, r in df_tenants.iterrows()}
                selected_tenant_label = st.selectbox("Mieter zum Bearbeiten wählen", list(tenant_list.keys()))
                t_id_to_edit = tenant_list[selected_tenant_label]

                # Aktuelle Daten laden
                cur.execute("SELECT first_name, last_name, occupants, monthly_prepayment, apartment_id FROM tenants WHERE id = %s", (t_id_to_edit,))
                current_val = cur.fetchone()

                with st.form("edit_tenant_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_f_name = st.text_input("Vorname", value=current_val[0])
                        new_l_name = st.text_input("Nachname", value=current_val[1])
                        new_occupants = st.number_input("Personenanzahl", min_value=1, value=int(current_val[2] or 1))
                    with col2:
                        new_prepayment = st.number_input("NK-Vorauszahlung (€)", min_value=0.0, value=float(current_val[3] or 0.0), step=5.0)
                        
                        # Wohnungen laden
                        cur.execute("SELECT id, unit_name FROM apartments ORDER BY unit_name")
                        apts = cur.fetchall()
                        apt_opts = {a[1]: a[0] for a in apts}
                        # Finde Index der aktuellen Wohnung
                        current_apt_name = next((name for name, i in apt_opts.items() if i == current_val[4]), list(apt_opts.keys())[0] if apt_opts else "N/A")
                        new_apt = st.selectbox("Wohnung ändern", list(apt_opts.keys()), index=list(apt_opts.keys()).index(current_apt_name) if current_apt_name in apt_opts else 0)

                    if st.form_submit_button("💾 Änderungen speichern"):
                        cur.execute("""
                            UPDATE tenants 
                            SET first_name=%s, last_name=%s, occupants=%s, monthly_prepayment=%s, apartment_id=%s
                            WHERE id=%s
                        """, (new_f_name, new_l_name, new_occupants, new_prepayment, apt_opts[new_apt], t_id_to_edit))
                        conn.commit()
                        st.success("✅ Mieterdaten wurden aktualisiert!")
                        st.rerun()
        else:
            st.info("Momentan sind keine aktiven Mieter registriert.")
    except Exception as e:
        st.error(f"Fehler: {e}")

    st.divider()

    # --- NEUEN MIETER ANLEGEN ---
    st.subheader("➕ Neuen Mieter hinzufügen")
    
    with st.form("add_tenant_form"):
        col1, col2 = st.columns(2)
        with col1:
            f_name = st.text_input("Vorname")
            l_name = st.text_input("Nachname")
            cur.execute("SELECT id, unit_name FROM apartments ORDER BY unit_name")
            apartments = cur.fetchall()
            apt_options = {a[1]: a[0] for a in apartments}
            sel_apt = st.selectbox("Wohnung zuweisen", list(apt_options.keys()) if apt_options else ["Keine Wohnungen vorhanden"])
        
        with col2:
            m_in = st.date_input("Einzugsdatum")
            prepayment = st.number_input("Nebenkosten-Vorauszahlung (€)", min_value=0.0, step=5.0)
            occupants = st.number_input("Anzahl Personen", min_value=1, step=1, value=1)

        if st.form_submit_button("Mieter speichern"):
            if not f_name or not l_name or not apt_options:
                st.warning("Bitte alle Pflichtfelder ausfüllen.")
            else:
                try:
                    cur.execute("""
                        INSERT INTO tenants (first_name, last_name, apartment_id, move_in, monthly_prepayment, occupants)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (f_name, l_name, apt_options[sel_apt], m_in, prepayment, occupants))
                    conn.commit()
                    st.success(f"✅ Mieter {f_name} {l_name} wurde erfolgreich angelegt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")

    cur.close()
    conn.close()