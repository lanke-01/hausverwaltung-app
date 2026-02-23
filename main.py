import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# --- VERBINDUNGSFUNKTION ---
def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Hausverwaltung Dashboard", layout="wide")

st.title("🏠 Hausverwaltung Dashboard")
current_month = datetime.now().strftime("%B %Y")
st.subheader(f"Statusübersicht für {current_month}")

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Verbindung zur Datenbank möglich. Bitte prüfen Sie, ob PostgreSQL läuft.")
else:
    cur = conn.cursor()

    # --- KENNZAHLEN BERECHNEN ---
    try:
        # 1. Wohnungen & Gesamtfläche (Fix: area statt size_sqm)
        cur.execute("SELECT SUM(area), COUNT(*) FROM apartments")
        apt_data = cur.fetchone()
        total_area = apt_data[0] if apt_data[0] else 0
        total_apts = apt_data[1] if apt_data[1] else 0

        # 2. Aktive Mieter
        cur.execute("SELECT COUNT(*) FROM tenants WHERE move_out IS NULL")
        active_tenants = cur.fetchone()[0]

        # 3. Monatliche Soll-Miete (Summe der Kaltmieten der aktiven Mieter)
        # Hinweis: Falls in deiner Tabelle 'base_rent' statt 'rent' steht:
        cur.execute("""
            SELECT SUM(a.base_rent) 
            FROM tenants t 
            JOIN apartments a ON t.apartment_id = a.id 
            WHERE t.move_out IS NULL
        """)
        target_rent = cur.fetchone()[0] if cur.fetchone() else 0
        if not target_rent: target_rent = 0

        # 4. Tatsächliche Zahlungen im aktuellen Monat
        this_month_start = datetime.now().replace(day=1)
        cur.execute("SELECT SUM(amount) FROM payments WHERE payment_date >= %s", (this_month_start,))
        actual_rent = cur.fetchone()[0] if cur.fetchone() else 0
        if not actual_rent: actual_rent = 0

        # --- DASHBOARD LAYOUT (METRIKEN) ---
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Wohneinheiten", f"{total_apts}")
        with col2:
            st.metric("Gesamtfläche", f"{total_area:,.2f} m²")
        with col3:
            st.metric("Aktive Mieter", f"{active_tenants}")
        with col4:
            st.metric("Eingänge (lfd. Monat)", f"{actual_rent:,.2f} €")

        st.divider()

        # --- GRAFIKEN & LISTEN ---
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Schnellzugriff: Belegung")
            query_occ = """
                SELECT a.unit_name as Einheit, t.last_name as Mieter, t.move_in as Seit
                FROM apartments a
                LEFT JOIN tenants t ON a.id = t.apartment_id AND t.move_out IS NULL
                ORDER BY a.unit_name
            """
            df_occ = pd.read_sql(query_occ, conn)
            st.dataframe(df_occ, use_container_width=True, hide_index=True)

        with c2:
            st.subheader("Letzte Aktivitäten")
            query_pay = """
                SELECT p.payment_date as Datum, t.last_name as Mieter, p.amount as Betrag
                FROM payments p
                JOIN tenants t ON p.tenant_id = t.id
                ORDER BY p.payment_date DESC
                LIMIT 5
            """
            try:
                df_pay = pd.read_sql(query_pay, conn)
                if not df_pay.empty:
                    st.table(df_pay)
                else:
                    st.info("Noch keine Zahlungen vorhanden.")
            except:
                st.info("Zahlungstabelle noch leer oder im Aufbau.")

    except Exception as e:
        st.error(f"Fehler im Dashboard: {e}")

    cur.close()
    conn.close()

# --- SIDEBAR INFO ---
st.sidebar.info("📌 **Tipp:** Nutzen Sie das Menü links, um Mieter anzulegen oder Zahlungen zu verbuchen.")