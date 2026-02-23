import streamlit as st
from database import get_conn
from datetime import datetime

st.set_page_config(page_title="Zählerstände", layout="wide")
st.title("📟 Zählerverwaltung")

conn = get_conn()
if conn:
    cur = conn.cursor()
    tab1, tab2 = st.tabs(["Zähler anlegen", "Ablesung erfassen"])

    with tab1:
        st.subheader("Neuen Zähler registrieren")
        cur.execute("SELECT id, unit_name FROM apartments")
        apts = {name: aid for aid, name in cur.fetchall()}
        
        with st.form("new_meter"):
            m_type = st.selectbox("Typ", ["Strom", "Kaltwasser", "Heizung"])
            m_num = st.text_input("Zählernummer")
            m_apt = st.selectbox("Zugeordnete Wohnung", list(apts.keys()))
            is_wb = st.checkbox("Ist Wallbox / Unterzähler?")
            if st.form_submit_button("Registrieren"):
                cur.execute("""
                    INSERT INTO meters (apartment_id, meter_type, meter_number, is_submeter)
                    VALUES (%s, %s, %s, %s)
                """, (apts[m_apt], m_type, m_num, is_wb))
                conn.commit()
                st.success("Zähler registriert!")

    with tab2:
        st.subheader("Messwert eingeben")
        cur.execute("SELECT m.id, m.meter_number, a.unit_name FROM meters m JOIN apartments a ON m.apartment_id = a.id")
        m_list = {f"{row[1]} ({row[2]})": row[0] for row in cur.fetchall()}
        
        if m_list:
            with st.form("reading"):
                sel_m = st.selectbox("Zähler wählen", list(m_list.keys()))
                val = st.number_input("Zählerstand", step=0.01)
                dat = st.date_input("Ablesedatum", datetime.now())
                if st.form_submit_button("Speichern"):
                    cur.execute("INSERT INTO meter_readings (meter_id, reading_value, reading_date) VALUES (%s, %s, %s)",
                                (m_list[sel_m], val, dat))
                    conn.commit()
                    st.success("Stand gespeichert!")
    conn.close()
