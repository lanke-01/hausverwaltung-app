import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

# --- DATENBANK VERBINDUNG ---
def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Zählerstände", layout="wide")
st.title("📟 Zählerverwaltung & Differenzmessung")

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung möglich.")
else:
    cur = conn.cursor()

    # Tabellen & Spalten sicherstellen
    cur.execute("""
        CREATE TABLE IF NOT EXISTS meters (
            id SERIAL PRIMARY KEY,
            apartment_id INTEGER,
            meter_type TEXT,
            meter_number TEXT,
            is_submeter BOOLEAN DEFAULT FALSE,
            parent_meter_id INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS meter_readings (
            id SERIAL PRIMARY KEY,
            meter_id INTEGER REFERENCES meters(id) ON DELETE CASCADE,
            reading_date DATE DEFAULT CURRENT_DATE,
            reading_value NUMERIC(12,2)
        )
    """)
    cur.execute("ALTER TABLE operating_expenses ADD COLUMN IF NOT EXISTS tenant_id INTEGER")
    conn.commit()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🏗️ Zähler anlegen", 
        "📝 Stand erfassen", 
        "⚖️ Differenzmessung (Wallbox)", 
        "⚙️ Stände bearbeiten"
    ])

    # --- TAB 1: ZÄHLER ANLEGEN ---
    with tab1:
        st.subheader("Neuen Zähler registrieren")
        with st.form("meter_form"):
            m_type = st.selectbox("Typ", ["Strom", "Wasser", "Gas", "Wärme"])
            m_num = st.text_input("Zählernummer")
            is_sub = st.checkbox("Ist ein Unterzähler? (z.B. Wallbox hängt an Hausstrom)")
            
            cur.execute("SELECT id, unit_name FROM apartments")
            apps = {row[1]: row[0] for row in cur.fetchall()}
            apps["Haus / Allgemein"] = None
            sel_app = st.selectbox("Zugehörigkeit", list(apps.keys()))
            
            if st.form_submit_button("Speichern"):
                cur.execute("""
                    INSERT INTO meters (apartment_id, meter_type, meter_number, is_submeter)
                    VALUES (%s, %s, %s, %s)
                """, (apps[sel_app], m_type, m_num, is_sub))
                conn.commit()
                st.success("Zähler angelegt!")

    # --- TAB 2: STAND ERFASSEN ---
    with tab2:
        st.subheader("Zählerstand eingeben")
        cur.execute("SELECT id, meter_type, meter_number FROM meters")
        m_list = {f"{r[1]} ({r[2]})": r[0] for r in cur.fetchall()}
        
        if m_list:
            sel_m = st.selectbox("Zähler wählen", list(m_list.keys()))
            val = st.number_input("Stand", step=0.01)
            d = st.date_input("Datum", datetime.now())
            
            if st.button("Stand speichern"):
                cur.execute("""
                    INSERT INTO meter_readings (meter_id, reading_value, reading_date)
                    VALUES (%s, %s, %s)
                """, (m_list[sel_m], val, d))
                conn.commit()
                st.success("Gespeichert!")
        else:
            st.info("Noch keine Zähler vorhanden.")

    # --- TAB 3: DIFFERENZMESSUNG (WALLBOX) ---
    with tab3:
        st.subheader("Wallbox-Strom vs. Allgemeinstrom")
        cur.execute("SELECT id, meter_number FROM meters WHERE meter_type = 'Strom' AND is_submeter = FALSE")
        main_meters = cur.fetchall()
        cur.execute("SELECT id, meter_number FROM meters WHERE meter_type = 'Strom' AND is_submeter = TRUE")
        sub_meters = cur.fetchall()

        if main_meters and sub_meters:
            col1, col2 = st.columns(2)
            main_id = col1.selectbox("Hauptzähler (Haus)", [m[0] for m in main_meters], format_func=lambda x: next(m[1] for m in main_meters if m[0] == x))
            sub_id = col2.selectbox("Unterzähler (Wallbox)", [m[0] for m in sub_meters], format_func=lambda x: next(m[1] for m in sub_meters if m[0] == x))
            
            strom_preis = st.text_input("Strompreis pro kWh (z.B. 0.35)", "0.35")
            abr_jahr = st.number_input("Abrechnungsjahr", value=2024)

            if st.button("Verbrauch berechnen & Buchen"):
                def get_consumption(m_id, jahr):
                    cur.execute("""
                        (SELECT reading_value FROM meter_readings WHERE meter_id = %s AND EXTRACT(YEAR FROM reading_date) = %s ORDER BY reading_date ASC LIMIT 1)
                        UNION ALL
                        (SELECT reading_value FROM meter_readings WHERE meter_id = %s AND EXTRACT(YEAR FROM reading_date) = %s ORDER BY reading_date DESC LIMIT 1)
                    """, (m_id, jahr, m_id, jahr))
                    res = cur.fetchall()
                    return float(res[1][0] - res[0][0]) if len(res) == 2 else 0.0

                main_v = get_consumption(main_id, abr_jahr)
                sub_v = get_consumption(sub_id, abr_jahr)
                netto_allgemein = main_v - sub_v

                st.write(f"Gesamtverbrauch Hausstrom: **{main_v:.2f} kWh**")
                st.write(f"Davon Wallbox: **{sub_v:.2f} kWh**")
                st.write(f"Netto-Allgemeinstrom (Flur/Keller): **{netto_allgemein:.2f} kWh**")

                cur.execute("SELECT id, first_name, last_name FROM tenants WHERE move_in <= %s AND (move_out IS NULL OR move_out >= %s)", (date(abr_jahr, 12, 31), date(abr_jahr, 1, 1)))
                tenants = {f"{r[1]} {r[2]}": r[0] for r in cur.fetchall()}
                target_tenant = st.selectbox("Wallbox Mieter zuweisen", list(tenants.keys()))

                if st.button("Kosten in Betriebskosten übernehmen"):
                    try:
                        # 1. Netto Allgemeinstrom (Marker: tenant_id = -1 damit es nicht in der Mieter-Abrechnung landet)
                        cur.execute("""
                            INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year, tenant_id)
                            VALUES (%s, %s, %s, %s, -1)
                        """, ("Allgemeinstrom (Netto)", netto_allgemein * float(strom_preis), "area", abr_jahr))
                        
                        # 2. Wallbox-Strom (Direktzuordnung zum Mieter)
                        cur.execute("""
                            INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year, tenant_id)
                            VALUES (%s, %s, %s, %s, %s)
                        """, ("Wallbox-Strom", sub_v * float(strom_preis), "direct", abr_jahr, tenants[target_tenant]))
                        
                        conn.commit()
                        st.success("✅ Buchung erfolgreich!")
                    except Exception as e:
                        st.error(f"Fehler: {e}")

    # --- TAB 4: VERLAUF & KORREKTUR (MIT EDITOR) ---
    with tab4:
        st.subheader("Ablesehistorie bearbeiten")
        query = """
            SELECT r.id, m.meter_number, m.meter_type, r.reading_date, r.reading_value, COALESCE(a.unit_name, 'Haus') as einheit
            FROM meter_readings r
            JOIN meters m ON r.meter_id = m.id
            LEFT JOIN apartments a ON m.apartment_id = a.id
            ORDER BY r.reading_date DESC
        """
        df_history = pd.read_sql(query, conn)
        
        # Der Data Editor erlaubt direktes Ändern
        edited_df = st.data_editor(
            df_history,
            column_config={
                "id": None, # ID bleibt versteckt
                "reading_date": st.column_config.DateColumn("Datum"),
                "reading_value": st.column_config.NumberColumn("Zählerstand", format="%.2f"),
                "meter_number": st.column_config.TextColumn("Zählernummer", disabled=True),
                "meter_type": st.column_config.TextColumn("Typ", disabled=True),
                "einheit": st.column_config.TextColumn("Einheit", disabled=True)
            },
            use_container_width=True,
            num_rows="dynamic",
            key="meter_editor"
        )

        if st.button("💾 Alle Änderungen speichern"):
            try:
                for index, row in edited_df.iterrows():
                    cur.execute("""
                        UPDATE meter_readings 
                        SET reading_value = %s, reading_date = %s 
                        WHERE id = %s
                    """, (row['reading_value'], row['reading_date'], row['id']))
                conn.commit()
                st.success("✅ Datenbank wurde aktualisiert!")
                st.rerun()
            except Exception as e:
                st.error(f"Speicherfehler: {e}")

    cur.close()
    conn.close()