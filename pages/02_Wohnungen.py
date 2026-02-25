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

st.set_page_config(page_title="Wohnungsverwaltung", layout="wide")
st.title("🏢 Wohnungsverwaltung")

conn = get_direct_conn()

if not conn:
    st.error("❌ Datenbankverbindung fehlgeschlagen.")
else:
    cur = conn.cursor()
    try:
        # 1. Übersicht der vorhandenen Wohnungen
        st.subheader("Aktuelle Wohnungsliste")
        cur.execute("SELECT id, unit_name, area FROM apartments ORDER BY unit_name ASC")
        rows = cur.fetchall()
        
        if rows:
            df = pd.DataFrame(rows, columns=["ID", "Wohnung Name", "Fläche (m²)"])
            st.table(df.set_index("ID"))
        else:
            st.info("Noch keine Wohnungen angelegt.")

        st.divider()

        # 2. Aktionen: Neu anlegen oder Bearbeiten
        col_neu, col_edit = st.columns(2)

        with col_neu:
            st.subheader("➕ Neue Wohnung hinzufügen")
            with st.form("add_apartment"):
                new_name = st.text_input("Bezeichnung (z.B. EG links)")
                new_area = st.number_input("Fläche in m²", min_value=0.0, step=0.01)
                if st.form_submit_button("Speichern"):
                    if new_name:
                        cur.execute("INSERT INTO apartments (unit_name, area) VALUES (%s, %s)", (new_name, new_area))
                        conn.commit()
                        st.success(f"Wohnung '{new_name}' angelegt!")
                        st.rerun()
                    else:
                        st.error("Bitte einen Namen angeben.")

        with col_edit:
            if rows:
                st.subheader("✏️ Wohnung bearbeiten / löschen")
                # IDs für die Auswahl holen
                apt_ids = [r[0] for r in rows]
                selected_id = st.selectbox("Wohnung (ID) wählen", apt_ids)
                
                # Daten der gewählten Wohnung laden
                cur.execute("SELECT unit_name, area FROM apartments WHERE id = %s", (selected_id,))
                apt_data = cur.fetchone()

                with st.form("edit_apartment"):
                    upd_name = st.text_input("Bezeichnung", value=apt_data[0])
                    upd_area = st.number_input("Fläche (m²)", value=float(apt_data[1]), step=0.01)
                    
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("💾 Änderungen speichern"):
                        cur.execute("UPDATE apartments SET unit_name = %s, area = %s WHERE id = %s", 
                                    (upd_name, upd_area, selected_id))
                        conn.commit()
                        st.success("Wohnung aktualisiert!")
                        st.rerun()
                    
                    if c2.form_submit_button("🗑️ Wohnung löschen"):
                        # Vorsicht: Löschen nur möglich, wenn kein Mieter mehr zugeordnet ist (Fremdschlüssel)
                        try:
                            cur.execute("DELETE FROM apartments WHERE id = %s", (selected_id,))
                            conn.commit()
                            st.warning("Wohnung gelöscht.")
                            st.rerun()
                        except Exception as e:
                            st.error("Löschen nicht möglich: Es sind noch Mieter dieser Wohnung zugeordnet!")

    except Exception as e:
        st.error(f"Fehler: {e}")
    finally:
        cur.close()
        conn.close()