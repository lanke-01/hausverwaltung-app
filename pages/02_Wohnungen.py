import streamlit as st
import pandas as pd
from database import get_conn  # Nutzt die zentrale database.py

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Wohnungs-Verwaltung", layout="wide")

st.title("🏠 Wohnungs-Verwaltung")

# Verbindung herstellen
conn = get_conn()

if conn:
    try:
        cur = conn.cursor()

        # --- BEREICH 1: BEARBEITEN & LÖSCHEN ---
        st.subheader("📝 Wohnung bearbeiten oder löschen")
        
        # Alle Wohnungen laden für das Auswahlmenü
        cur.execute("SELECT id, unit_name FROM apartments ORDER BY unit_name, id")
        apts = cur.fetchall()
        apt_options = {f"{name} (ID: {aid})": aid for aid, name in apts}

        if apt_options:
            selected_label = st.selectbox(
                "Wohnung zum Bearbeiten auswählen", 
                options=["-- Bitte wählen --"] + list(apt_options.keys())
            )
            
            if selected_label != "-- Bitte wählen --":
                aid = apt_options[selected_label]
                
                # Aktuelle Daten der Wohnung aus DB holen
                cur.execute("SELECT unit_name, size_sqm, base_rent, service_charge_propayment FROM apartments WHERE id = %s", (aid,))
                current_data = cur.fetchone()
                
                if current_data:
                    with st.form("edit_delete_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_name = st.text_input("Bezeichnung", value=current_data[0])
                            new_size = st.number_input("Fläche (m²)", value=float(current_data[1]), step=0.1)
                        with col2:
                            new_rent = st.number_input("Kaltmiete (€)", value=float(current_data[2]), step=1.0)
                            new_prepay = st.number_input("NK-Vorauszahlung (€)", value=float(current_data[3]), step=1.0)
                        
                        btn_save, btn_delete = st.columns([1, 1])
                        
                        with btn_save:
                            if st.form_submit_button("💾 Änderungen speichern"):
                                cur.execute("""
                                    UPDATE apartments 
                                    SET unit_name = %s, size_sqm = %s, base_rent = %s, service_charge_propayment = %s 
                                    WHERE id = %s
                                """, (new_name, new_size, new_rent, new_prepay, aid))
                                conn.commit()
                                st.success(f"Wohnung '{new_name}' (ID: {aid}) aktualisiert!")
                                st.rerun()
                        
                        with btn_delete:
                            confirm = st.checkbox("Sicher löschen?")
                            if st.form_submit_button("🗑️ Datensatz löschen"):
                                if confirm:
                                    try:
                                        cur.execute("DELETE FROM apartments WHERE id = %s", (aid,))
                                        conn.commit()
                                        st.success("Wohnung wurde gelöscht!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error("Löschen nicht möglich: Wohnung ist wahrscheinlich noch einem Mieter zugeordnet!")
                                else:
                                    st.warning("Bitte erst das Häkchen bei 'Sicher löschen' setzen.")
        else:
            st.info("Noch keine Wohnungen vorhanden.")

        st.divider()

        # --- BEREICH 2: NEU ANLEGEN ---
        with st.expander("➕ Neue Wohneinheit hinzufügen"):
            with st.form("apt_form_new"):
                c1, c2 = st.columns(2)
                with c1:
                    n_name = st.text_input("Bezeichnung (z.B. Wohnung 5)")
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
                    st.success("Wohnung erfolgreich angelegt!")
                    st.rerun()

        st.divider()

        # --- BEREICH 3: TABELLE ---
        st.subheader("Aktueller Bestand")
        # Wir laden die Daten direkt mit Pandas, um sie anzuzeigen
        df_apts = pd.read_sql("""
            SELECT id as "ID", 
                   unit_name as "Einheit", 
                   size_sqm as "m²", 
                   base_rent as "Kalt (€)", 
                   service_charge_propayment as "NK-Vorschuss (€)"
            FROM apartments 
            ORDER BY unit_name ASC
        """, conn)

        if not df_apts.empty:
            st.dataframe(df_apts, use_container_width=True, hide_index=True)
            
            # Bonus: Haus-Gesamtwert zur Kontrolle
            total_sqm = df_apts["m²"].sum()
            st.write(f"**Gesamtfläche des Hauses:** {total_sqm:.2f} m²")
        else:
            st.info("Die Datenbank ist leer. Bitte lege eine Wohnung an.")

    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
    finally:
        conn.close()
else:
    st.error("Verbindung zur Datenbank fehlgeschlagen. Bitte prüfe die Datei '.env' und 'database.py'.")