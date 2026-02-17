import streamlit as st
import pandas as pd
from datetime import datetime
from database import get_conn

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Mieterverwaltung", layout="wide")
st.title("👥 Mieterverwaltung")

conn = get_conn()

if conn:
    cur = conn.cursor()

    # --- DATENBANK-STRUKTUR AUTOMATISCH ERWEITERN ---
    # Stellt sicher, dass alle für die Abrechnung wichtigen Spalten existieren
    try:
        cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS area NUMERIC(10,2) DEFAULT 0.00")
        cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS rent NUMERIC(10,2) DEFAULT 0.00")
        cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS utilities NUMERIC(10,2) DEFAULT 0.00")
        cur.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS occupants INTEGER DEFAULT 1")
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"Fehler beim Datenbank-Update: {e}")

    # --- TABELLENÜBERSICHT ---
    st.subheader("Aktuelle Mieterliste")
    df_tenants = pd.read_sql("""
        SELECT t.id, t.first_name as Vorname, t.last_name as Nachname, 
               a.unit_name as Wohnung, t.area as "m²", t.occupants as Personen,
               t.rent as Kaltmiete, t.utilities as Vorauszahlung, t.moved_in as Einzug
        FROM tenants t 
        LEFT JOIN apartments a ON t.apartment_id = a.id
        WHERE t.moved_out IS NULL
        ORDER BY t.last_name
    """, conn)
    
    if not df_tenants.empty:
        st.dataframe(df_tenants, use_container_width=True, hide_index=True)
    else:
        st.info("Noch keine aktiven Mieter erfasst.")

    st.divider()

    # --- BEREICH 1: NEUER EINZUG ---
    with st.expander("➕ Neuer Mieter / Einzug"):
        # Nur Wohnungen anzeigen, die aktuell nicht belegt sind
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
                    occ = st.number_input("Anzahl Personen", min_value=1, value=1, step=1)
                    area = st.number_input("Wohnfläche (m²)", min_value=0.0, step=0.01)
                with col2:
                    apt_name = st.selectbox("Wohnung wählen", options=list(free_apts.keys()))
                    in_date = st.date_input("Einzugsdatum", value=datetime.now())
                    rent = st.number_input("Monatliche Kaltmiete (€)", min_value=0.0, step=0.01)
                    utils = st.number_input("Monatliche NK-Vorauszahlung (€)", min_value=0.0, step=0.01)
                
                if st.form_submit_button("Einzug speichern"):
                    cur.execute("""
                        INSERT INTO tenants (first_name, last_name, apartment_id, moved_in, occupants, area, rent, utilities) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (fn, ln, free_apts[apt_name], in_date, occ, area, rent, utils))
                    conn.commit()
                    st.success(f"Mieter {fn} {ln} wurde erfolgreich angelegt!")
                    st.rerun()
        else:
            st.warning("Keine freien Wohnungen verfügbar.")

    st.divider()

    # --- BEREICH 2: BEARBEITEN & DATEN NACHPFLEGEN ---
    st.subheader("📝 Mieterdaten bearbeiten")
    cur.execute("SELECT id, first_name || ' ' || last_name FROM tenants WHERE moved_out IS NULL ORDER BY last_name")
    active_tenants = {name: tid for tid, name in cur.fetchall()}

    if active_tenants:
        t_edit_sel = st.selectbox("Mieter zum Bearbeiten wählen", options=["-- Bitte wählen --"] + list(active_tenants.keys()))
        
        if t_edit_sel != "-- Bitte wählen --":
            t_edit_id = active_tenants[t_edit_sel]
            
            # Aktuelle Daten des Mieters aus der DB laden
            cur.execute("SELECT area, occupants, utilities, rent FROM tenants WHERE id = %s", (t_edit_id,))
            current_data = cur.fetchone()

            with st.form(f"edit_form_{t_edit_id}"):
                st.info(f"Daten für **{t_edit_sel}** anpassen:")
                c1, c2, c3, c4 = st.columns(4)
                
                u_area = c1.number_input("Fläche (m²)", value=float(current_data[0] or 0.0), step=0.01)
                u_occ = c2.number_input("Personen", value=int(current_data[1] or 1), step=1)
                u_utils = c3.number_input("NK-Voraus (€)", value=float(current_data[2] or 0.0), step=0.01)
                u_rent = c4.number_input("Kaltmiete (€)", value=float(current_data[3] or 0.0), step=0.01)
                
                if st.form_submit_button("Änderungen speichern"):
                    cur.execute("""
                        UPDATE tenants 
                        SET area = %s, occupants = %s, utilities = %s, rent = %s 
                        WHERE id = %s
                    """, (u_area, u_occ, u_utils, u_rent, t_edit_id))
                    conn.commit()
                    st.success(f"Änderungen für {t_edit_sel} erfolgreich gespeichert!")
                    st.rerun()

            # Auszug registrieren
            st.write("---")
            if st.button("🔴 Mieter-Auszug (Vertrag beenden)"):
                cur.execute("UPDATE tenants SET moved_out = CURRENT_DATE WHERE id = %s", (t_edit_id,))
                conn.commit()
                st.success(f"Auszug für {t_edit_sel} wurde zum heutigen Datum registriert.")
                st.rerun()
    else:
        st.info("Keine aktiven Mieter zum Bearbeiten vorhanden.")

    cur.close()
    conn.close()
else:
    st.error("Datenbankverbindung fehlgeschlagen.")