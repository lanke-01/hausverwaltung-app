import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime  # <-- Dieser Import hat gefehlt!

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
    
    # Sicherstellen, dass die Spalten existieren
    cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS occupants INTEGER DEFAULT 1")
    cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS move_in DATE")
    cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS move_out DATE")
    conn.commit()

    # --- ÜBERSICHTSTABELLE ---
    st.subheader("Aktuelle Mieterliste")
    
    query = """
        SELECT 
            t.id AS id, 
            t.first_name AS vorname, 
            t.last_name AS nachname, 
            a.unit_name AS wohnung, 
            t.occupants AS personen,
            t.move_in AS einzug,
            t.monthly_prepayment AS vorschuss,
            t.move_out AS auszug
        FROM tenants t
        LEFT JOIN apartments a ON t.apartment_id = a.id
        ORDER BY t.last_name
    """
    
    try:
        cur.execute(query)
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        df_tenants = pd.DataFrame(rows, columns=colnames)

        if not df_tenants.empty:
            st.dataframe(df_tenants, use_container_width=True)

            # --- BEARBEITUNGS-BEREICH ---
            with st.expander("✏️ Mieter bearbeiten (Einzug/Auszug anpassen)", expanded=False):
                tenant_list = {
                    f"{r['vorname']} {r['nachname']} (ID: {r['id']})": r['id'] 
                    for _, r in df_tenants.iterrows()
                }
                
                selected_label = st.selectbox("Mieter zum Bearbeiten wählen", list(tenant_list.keys()))
                t_id_edit = tenant_list[selected_label]

                # Daten laden
                cur.execute("""
                    SELECT first_name, last_name, occupants, monthly_prepayment, apartment_id, move_in, move_out 
                    FROM tenants WHERE id = %s
                """, (t_id_edit,))
                curr = cur.fetchone()

                if curr:
                    with st.form("edit_tenant_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_f_name = st.text_input("Vorname", value=curr[0])
                            new_l_name = st.text_input("Nachname", value=curr[1])
                            new_occ = st.number_input("Personenanzahl", min_value=1, value=int(curr[2] or 1))
                            # EINZUG
                            einzug_val = curr[5] if curr[5] else datetime.now().date()
                            new_move_in = st.date_input("Einzugsdatum", value=einzug_val)
                            
                        with col2:
                            new_pre = st.number_input("NK-Vorschuss (€)", min_value=0.0, value=float(curr[3] or 0.0))
                            
                            # AUSZUG
                            auszug_aktiv = st.checkbox("Auszugsdatum setzen (Mieter zieht aus)", value=curr[6] is not None)
                            auszug_val = curr[6] if curr[6] else datetime.now().date()
                            new_move_out = st.date_input("Auszugsdatum", value=auszug_val)
                            
                            # Wohnung wählen
                            cur.execute("SELECT id, unit_name FROM apartments ORDER BY unit_name")
                            apts = cur.fetchall()
                            apt_dict = {a[1]: a[0] for a in apts}
                            apt_names = list(apt_dict.keys())
                            
                            current_apt_id = curr[4]
                            try:
                                current_apt_name = [name for name, aid in apt_dict.items() if aid == current_apt_id][0]
                                idx = apt_names.index(current_apt_name)
                            except:
                                idx = 0
                            new_apt_name = st.selectbox("Wohnung", apt_names, index=idx)

                        if st.form_submit_button("💾 Änderungen speichern"):
                            final_move_out = new_move_out if auszug_aktiv else None
                            cur.execute("""
                                UPDATE tenants 
                                SET first_name=%s, last_name=%s, occupants=%s, monthly_prepayment=%s, 
                                    apartment_id=%s, move_in=%s, move_out=%s
                                WHERE id=%s
                            """, (new_f_name, new_l_name, new_occ, new_pre, 
                                  apt_dict[new_apt_name], new_move_in, final_move_out, t_id_edit))
                            conn.commit()
                            st.success("✅ Mieterdaten inklusive Zeiträumen aktualisiert!")
                            st.rerun()
        else:
            st.info("Keine Mieter gefunden.")
            
    except Exception as e:
        st.error(f"Fehler: {e}")

    # --- NEUANLAGE ---
    st.divider()
    st.subheader("➕ Neuen Mieter hinzufügen")
    with st.form("add_tenant_form"):
        c1, c2 = st.columns(2)
        with c1:
            add_f_name = st.text_input("Vorname")
            add_l_name = st.text_input("Nachname")
            add_occ = st.number_input("Personenanzahl", min_value=1, value=1)
            add_in = st.date_input("Einzugsdatum")
        with c2:
            add_pre = st.number_input("Mtl. NK-Vorschuss (€)", min_value=0.0, step=10.0)
            cur.execute("SELECT id, unit_name FROM apartments ORDER BY unit_name")
            apts_new = cur.fetchall()
            if apts_new:
                apt_dict_new = {a[1]: a[0] for a in apts_new}
                add_apt = st.selectbox("Wohnung", list(apt_dict_new.keys()))
            else:
                st.warning("Bitte zuerst Wohnungen anlegen!")
        
        if st.form_submit_button("Mieter anlegen"):
            if add_f_name and add_l_name and apts_new:
                cur.execute("""
                    INSERT INTO tenants (first_name, last_name, occupants, monthly_prepayment, apartment_id, move_in)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (add_f_name, add_l_name, add_occ, add_pre, apt_dict_new[add_apt], add_in))
                conn.commit()
                st.success("Mieter angelegt!")
                st.rerun()

    cur.close()
    conn.close()