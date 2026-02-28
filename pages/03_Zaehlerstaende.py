import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, date

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
    cur.execute("ALTER TABLE operating_expenses ADD COLUMN IF NOT EXISTS tenant_id INTEGER")
    conn.commit()

    tab1, tab2, tab3, tab4 = st.tabs(["🏗️ Zähler anlegen", "📝 Stand erfassen", "⚖️ Differenzmessung", "⚙️ Stände bearbeiten"])

    with tab1:
        st.subheader("Neuen Zähler registrieren")
        with st.form("meter_form"):
            m_type = st.selectbox("Typ", ["Strom", "Wasser", "Gas", "Wärme"])
            m_num = st.text_input("Zählernummer")
            is_sub = st.checkbox("Unterzähler?")
            cur.execute("SELECT id, unit_name FROM apartments")
            apps = {row[1]: row[0] for row in cur.fetchall()}
            apps["Haus"] = None
            sel_app = st.selectbox("Einheit", list(apps.keys()))
            if st.form_submit_button("Speichern"):
                cur.execute("INSERT INTO meters (apartment_id, meter_type, meter_number, is_submeter) VALUES (%s, %s, %s, %s)", (apps[sel_app], m_type, m_num, is_sub))
                conn.commit()
                st.success("Zähler angelegt!")

    with tab2:
        st.subheader("Zählerstand eingeben")
        cur.execute("SELECT id, meter_type, meter_number FROM meters")
        m_list = {f"{r[1]} ({r[2]})": r[0] for r in cur.fetchall()}
        if m_list:
            sel_m = st.selectbox("Zähler wählen", list(m_list.keys()))
            val = st.number_input("Stand", step=0.01)
            d = st.date_input("Datum", datetime.now())
            if st.button("Stand speichern"):
                cur.execute("INSERT INTO meter_readings (meter_id, reading_value, reading_date) VALUES (%s, %s, %s)", (m_list[sel_m], val, d))
                conn.commit()
                st.success("Gespeichert!")

    with tab3:
    def get_consumption(m_id, jahr):
    # Stand vom Anfang des Jahres (z.B. 01.01.2025)
    cur.execute("""
        SELECT reading_value FROM meter_readings 
        WHERE meter_id = %s AND reading_date <= %s 
        ORDER BY reading_date DESC LIMIT 1
    """, (m_id, f"{jahr}-01-01"))
    res_start = cur.fetchone()

    # Stand vom Ende des Jahres / Anfang Folgejahr (z.B. 01.01.2026)
    cur.execute("""
        SELECT reading_value FROM meter_readings 
        WHERE meter_id = %s AND reading_date >= %s 
        ORDER BY reading_date ASC LIMIT 1
    """, (m_id, f"{jahr+1}-01-01"))
    res_ende = cur.fetchone()

    if res_start and res_ende:
        # Falls Zähler getauscht wurde oder Rückwärtstausch (wie im Screenshot): 
        # Wir nehmen den absoluten Unterschied
        return float(abs(res_ende[0] - res_start[0]))
    return 0.0

    with tab4:
        st.subheader("Historie bearbeiten")
        df = pd.read_sql("SELECT r.id, m.meter_number, m.meter_type, r.reading_date, r.reading_value FROM meter_readings r JOIN meters m ON r.meter_id = m.id ORDER BY r.reading_date DESC", conn)
        edited = st.data_editor(df, num_rows="dynamic", key="edit_m", column_config={"id": None})
        if st.button("💾 Speichern"):
            for _, row in edited.iterrows():
                cur.execute("UPDATE meter_readings SET reading_value = %s, reading_date = %s WHERE id = %s", (row['reading_value'], row['reading_date'], row['id']))
            conn.commit()
            st.success("Aktualisiert!")
            st.rerun()

    cur.close()
    conn.close()