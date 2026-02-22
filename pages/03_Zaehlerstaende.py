import streamlit as st
from database import get_conn
import pandas as pd

st.set_page_config(page_title="Zählerstände", layout="wide")
st.title("📟 Zählerverwaltung & Differenzmessung")

conn = get_conn()
cur = conn.cursor()

# --- DATENBANK-STRUKTUR SICHERSTELLEN ---
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

tab1, tab2, tab3 = st.tabs(["Zähler verwalten", "Ablesung erfassen", "Verbrauchs-Check"])

with tab1:
    st.subheader("Neuen Zähler anlegen")
    cur.execute("SELECT id, unit_name FROM apartments")
    apts = {name: tid for tid, name in cur.fetchall()}
    
    # Liste aller vorhandenen Zähler für die Auswahl als Hauptzähler
    cur.execute("SELECT id, meter_number, meter_type FROM meters WHERE is_submeter = FALSE")
    main_meters = {f"{m[2]} (Nr: {m[1]})": m[0] for m in cur.fetchall()}

    with st.form("new_meter_form"):
        col1, col2 = st.columns(2)
        with col1:
            apt_name = st.selectbox("Wohnung / Bereich", ["Allgemein"] + list(apts.keys()))
            m_type = st.selectbox("Zählertyp", ["Strom", "Wasser", "Gas", "Heizung"])
            m_num = st.text_input("Zählernummer")
        with col2:
            is_sub = st.checkbox("Ist dies ein Unterzähler? (z.B. Wallbox)")
            parent = st.selectbox("Gehört zu Hauptzähler (optional)", ["Keiner"] + list(main_meters.keys()))
        
        if st.form_submit_button("Zähler speichern"):
            a_id = apts[apt_name] if apt_name != "Allgemein" else None
            p_id = main_meters[parent] if parent != "Keiner" else None
            cur.execute("""
                INSERT INTO meters (apartment_id, meter_type, meter_number, is_submeter, parent_meter_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (a_id, m_type, m_num, is_sub, p_id))
            conn.commit()
            st.success("Zähler erfolgreich registriert!")
            st.rerun()

with tab2:
    st.subheader("Zählerstand eingeben")
    cur.execute("""
        SELECT m.id, COALESCE(a.unit_name, 'Allgemein'), m.meter_type, m.meter_number 
        FROM meters m LEFT JOIN apartments a ON m.apartment_id = a.id
    """)
    m_data = cur.fetchall()
    m_options = {f"{d[1]} - {d[2]} ({d[3]})": d[0] for d in m_data}
    
    if m_options:
        with st.form("reading_form"):
            selected_m = st.selectbox("Zähler auswählen", list(m_options.keys()))
            val = st.number_input("Zählerstand", step=0.01)
            r_date = st.date_input("Ablesedatum", datetime.now())
            if st.form_submit_button("Stand speichern"):
                cur.execute("INSERT INTO meter_readings (meter_id, reading_value, reading_date) VALUES (%s, %s, %s)",
                            (m_options[selected_m], val, r_date))
                conn.commit()
                st.success("Zählerstand gespeichert!")
    else:
        st.info("Bitte zuerst einen Zähler anlegen.")

with tab3:
    st.subheader("Berechnung Netto-Verbrauch")
    st.write("Hier wird der Wallbox-Verbrauch vom Hauptzähler abgezogen.")
    # Logik-Vorschau
    cur.execute("""
        SELECT m.meter_number, m.is_submeter, MAX(r.reading_value) - MIN(r.reading_value) as verbrauch
        FROM meters m JOIN meter_readings r ON m.id = r.meter_id
        GROUP BY m.id
    """)
    res = cur.fetchall()
    if res:
        df = pd.DataFrame(res, columns=["Zähler", "Ist Unterzähler", "Verbrauch (Zeitraum)"])
        st.table(df)

conn.close()