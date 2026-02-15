import streamlit as st
import psycopg2
from datetime import datetime

st.set_page_config(page_title="Zahlungen", layout="wide")

def get_conn():
    conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
    conn.set_client_encoding('UTF8')
    return conn

st.title("💰 Mietzahlungen buchen")
conn = get_conn()
cur = conn.cursor()

cur.execute("SELECT id, last_name FROM tenants WHERE moved_out IS NULL")
tenants = {name: tid for tid, name in cur.fetchall()}

with st.form("pay"):
    t_name = st.selectbox("Mieter", list(tenants.keys()))
    amt = st.number_input("Betrag €", min_value=0.0)
    mo = st.selectbox("Monat", range(1,13), index=datetime.now().month-1)
    if st.form_submit_button("Buchen"):
        cur.execute("INSERT INTO payments (tenant_id, amount, period_month, period_year) VALUES (%s, %s, %s, %s)", (tenants[t_name], amt, mo, datetime.now().year))
        conn.commit()
        st.success("Gebucht!")
conn.close()