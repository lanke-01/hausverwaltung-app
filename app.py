import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# --- 1. KONFIGURATION --
st.set_page_config(page_title="Hausverwaltung Dashboard", layout="wide")

def get_conn():
    conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
    conn.set_client_encoding('UTF8')
    return conn

st.title("📊 Immobilien-Dashboard")

# --- 2. DATEN LADEN ---
current_month, current_year = datetime.now().month, datetime.now().year
conn = get_conn()
cur = conn.cursor()

# Einnahmen
cur.execute("SELECT SUM(amount) FROM payments WHERE period_month = %s AND period_year = %s", (current_month, current_year))
total_income = cur.fetchone()[0] or 0.0

# Leerstand
cur.execute("SELECT COUNT(*) FROM apartments WHERE id NOT IN (SELECT apartment_id FROM tenants WHERE moved_out IS NULL)")
vacant_count = cur.fetchone()[0]

# Metriken anzeigen
col1, col2 = st.columns(2)
col1.metric("Einnahmen (Feb. 2026)", f"{total_income:.2f} Euro")
col2.metric("Freie Wohnungen", vacant_count)

st.divider()

# Offene Posten
st.subheader("⚠️ Offene Mieten")
query = """
    SELECT t.last_name as Mieter, a.unit_name as Wohnung, a.base_rent as Soll, 
           COALESCE(SUM(p.amount), 0) as Gezahlt,
           (a.base_rent - COALESCE(SUM(p.amount), 0)) as Differenz
    FROM tenants t
    JOIN apartments a ON t.apartment_id = a.id
    LEFT JOIN payments p ON t.id = p.tenant_id AND p.period_month = %s AND p.period_year = %s
    WHERE t.moved_out IS NULL
    GROUP BY t.id, t.last_name, a.unit_name, a.base_rent
    HAVING COALESCE(SUM(p.amount), 0) < a.base_rent;
"""
df_debtors = pd.read_sql(query, conn, params=(current_month, current_year))

if not df_debtors.empty:
    # Hier der Fix für die Terminal-Warnung (width="stretch")
    st.dataframe(df_debtors, width="stretch")
else:
    st.success("Alle Mieten für Februar 2026 sind eingegangen.")

conn.close()