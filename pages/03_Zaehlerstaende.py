import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Zählerstände", layout="wide")

def get_conn():
    conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
    conn.set_client_encoding('UTF8')
    return conn

st.title("📟 Zählerverwaltung")
conn = get_conn()
cur = conn.cursor()

# Zähler anlegen
with st.expander("Neuen Zähler anlegen"):
    cur.execute("SELECT id, unit_name FROM apartments")
    apts = {name: tid for tid, name in cur.fetchall()}
    with st.form("new_meter"):
        apt = st.selectbox("Wohnung", list(apts.keys()))
        m_type = st.selectbox("Typ", ["Wasser", "Strom", "Gas", "Heizung"])
        num = st.text_input("Nummer")
        if st.form_submit_button("Speichern"):
            cur.execute("INSERT INTO meters (apartment_id, meter_type, meter_number) VALUES (%s, %s, %s)", (apts[apt], m_type, num))
            conn.commit()

# Ablesung
st.subheader("Ablesung erfassen")
cur.execute("SELECT m.id, a.unit_name || ' - ' || m.meter_type FROM meters m JOIN apartments a ON m.apartment_id = a.id")
m_list = {name: mid for mid, name in cur.fetchall()}
if m_list:
    with st.form("read"):
        m_sel = st.selectbox("Zähler", list(m_list.keys()))
        val = st.number_input("Stand")
        if st.form_submit_button("Speichern"):
            cur.execute("INSERT INTO meter_readings (meter_id, reading_value) VALUES (%s, %s)", (m_list[m_sel], val))
            conn.commit()
conn.close()