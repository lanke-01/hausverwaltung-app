import streamlit as st
import pandas as pd
from database import get_conn
from datetime import datetime

st.set_page_config(page_title="Zählerstände", layout="wide")
st.title("📟 Zählerverwaltung & Differenzmessung")

conn = get_conn()
cur = conn.cursor()

# Tabellen-Initialisierung (für GitHub-Clean-Install)
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
        meter_id INTEGER REFERENCES meters(id),
        reading_date DATE DEFAULT CURRENT_DATE,
        reading_value NUMERIC(12,2)
    )
""")
conn.commit()

tab1, tab2, tab3 = st.tabs(["Zähler-Struktur", "Ablesung erfassen", "Verbrauchs-Monitor"])

with tab1:
    st.subheader("Zähler registrieren")
    cur.execute("SELECT id, unit_name FROM apartments ORDER BY unit_name")
    apts = {name: tid for tid, name in cur.fetchall()}
    
    # Hauptzähler für die Auswahl laden
    cur.execute("SELECT id, meter_number, meter_type FROM meters WHERE is_submeter = FALSE")
    main_meters = {f"{m[2]} (Nr: {m[1]})": m[0] for m in cur.fetchall()}

    with st.form("new_meter"):
        c1, c2 = st.columns(2)
        with c1:
            apt = st.selectbox("Wohnung / Bereich", ["Allgemein"] + list(apts.keys()))
            m_type = st.selectbox("Typ", ["Strom", "Wasser", "Gas"])
            num = st.text_input("Zählernummer")
        with c2:
            sub = st.checkbox("Ist ein Unterzähler? (Wallbox/Abzugszähler)")
            parent = st.selectbox("Gehört zu Hauptzähler", ["Keiner"] + list(main_meters.keys()))
        
        if st.form_submit_button("Speichern"):
            a_id = apts[apt] if apt != "Allgemein" else None
            p_id = main_meters[parent] if parent != "Keiner" else None
            cur.execute("""
                INSERT INTO meters (apartment_id, meter_type, meter_number, is_submeter, parent_meter_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (a_id, m_type, num, sub, p_id))
            conn.commit()
            st.success("Zähler angelegt!")
            st.rerun()

with tab2:
    st.subheader("Messwert eingeben")
    cur.execute("""
        SELECT m.id, COALESCE(a.unit_name, 'Haus'), m.meter_type, m.meter_number 
        FROM meters m LEFT JOIN apartments a ON m.apartment_id = a.id
    """)
    m_opts = {f"{d[1]} - {d[2]} ({d[3]})": d[0] for d in cur.fetchall()}
    
    if m_opts:
        with st.form("reading"):
            m_sel = st.selectbox("Zähler", list(m_opts.keys()))
            val = st.number_input("Zählerstand", step=0.01)
            dat = st.date_input("Datum", datetime.now())
            if st.form_submit_button("Speichern"):
                cur.execute("INSERT INTO meter_readings (meter_id, reading_value, reading_date) VALUES (%s, %s, %s)",
                            (m_opts[m_sel], val, dat))
                conn.commit()
                st.success("Gespeichert!")

with tab3:
    st.subheader("Berechnete Verbräuche (Netto)")
    # SQL-Logik zur Berechnung der Differenz
    cur.execute("""
        SELECT 
            m.meter_number,
            m.meter_type,
            COALESCE(a.unit_name, 'Haus'),
            (SELECT reading_value FROM meter_readings WHERE meter_id = m.id ORDER BY reading_date DESC LIMIT 1) -
            (SELECT reading_value FROM meter_readings WHERE meter_id = m.id ORDER BY reading_date ASC LIMIT 1) as verbrauch,
            m.is_submeter
        FROM meters m
        LEFT JOIN apartments a ON m.apartment_id = a.id
    """)
    data = cur.fetchall()
    if data:
        df = pd.DataFrame(data, columns=["Zähler", "Typ", "Bereich", "Verbrauch", "Unterzähler"])
        st.dataframe(df, use_container_width=True)

conn.close()