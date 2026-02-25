import streamlit as st
import pandas as pd
import psycopg2

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
    
    # WICHTIG: Wir vergeben hier klare Aliase, die wir später 1:1 im Python-Code nutzen
    query = """
        SELECT 
            t.id AS id, 
            t.first_name AS vorname, 
            t.last_name AS nachname, 
            a.unit_name AS wohnung, 
            t.occupants AS personen,
            t.move_in AS einzug,
            t.monthly_prepayment AS vorschuss
        FROM tenants t
        LEFT JOIN apartments a ON t.apartment_id = a.id
        WHERE t.move_out IS NULL
        ORDER BY t.last_name
    """
    
    try:
        # Daten laden
        df_tenants = pd.read_sql(query, conn)
        
        if not df_tenants.empty:
            # Anzeige für den Nutzer (mit schönen Spaltennamen)
            df_display = df_tenants.copy()
            df_display.columns = ["ID", "Vorname", "Nachname", "Wohnung", "Personen", "Einzug", "NK-Vorschuss (€)"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # --- BEARBEITUNGS-MODUS ---
            st.divider()
            with st.expander("✏️ Bestehenden Mieter bearbeiten", expanded=False):
                tenant_list = {
                    f"{r['vorname']} {r['nachname']} (ID: {r['id']})": r['id'] 
                    for _, r in df_tenants.iterrows()
                }
                
                selected_label = st.selectbox("Mieter zum Bearbeiten wählen", list(tenant_list.keys()))
                t_id_edit = tenant_list[selected_label]

                # JETZT AUCH move_in UND move_out LADEN
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
                            # --- NEU: EINZUG ---
                            new_move_in = st.date_input("Einzugsdatum", value=curr[5])
                            
                        with col2:
                            new_pre = st.number_input("NK-Vorschuss (€)", min_value=0.0, value=float(curr[3] or 0.0))
                            
                            # --- NEU: AUSZUG ---
                            # Falls move_out None ist, setzen wir heute als Standard-Vorschlag im Picker, 
                            # speichern es aber nur, wenn die Checkbox unten aktiv ist
                            auszug_aktiv = st.checkbox("Mieter ist ausgezogen / Auszugsdatum setzen", value=curr[6] is not None)
                            new_move_out = st.date_input("Auszugsdatum", value=curr[6] if curr[6] else datetime.now())
                            
                            # Wohnung laden
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
                            # Logik für das Auszugsdatum: Wenn Checkbox nicht an, dann NULL in DB
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
            st.info("Keine aktiven Mieter gefunden.")
            
    except Exception as e:
        st.error(f"Fehler: {e}")

    st.divider()
    # --- NEUANLAGE (wie bisher) ---
    st.subheader("➕ Neuen Mieter hinzufügen")
    # ... (Dein Code zum Anlegen kann hier bleiben)