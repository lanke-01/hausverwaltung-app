import streamlit as st
import psycopg2
import pandas as pd
#test
def get_conn():
    conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
    conn.set_client_encoding('UTF8')
    return conn

st.set_page_config(page_title="Korrektur", layout="wide")
st.title("🛠️ Korrektur-Modus")

conn = get_conn()
cur = conn.cursor()

st.subheader("Mietzahlungen")
df = pd.read_sql("SELECT p.id, t.last_name, p.amount, p.period_month FROM payments p JOIN tenants t ON p.tenant_id = t.id ORDER BY p.id DESC LIMIT 10", conn)

if not df.empty:
    # Hier auch der Fix für 2026
    st.dataframe(df, width="stretch")
    to_del = st.selectbox("ID zum Löschen wählen", df['id'])
    if st.button("Löschen"):
        cur.execute("DELETE FROM payments WHERE id = %s", (to_del,))
        conn.commit()
        st.rerun()

conn.close()