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
    except Exception as e:
        return None

st.set_page_config(page_title="Hausverwaltung Dashboard", layout="wide")

st.title("🏠 Hausverwaltung Dashboard")
current_month = datetime.now().strftime("%B %Y")
st.subheader(f"Statusübersicht für {current_month}")

conn = get_direct_conn()

if conn:
    cur = conn.cursor()
    
    # --- AUTO-HEILUNG: ALLE TABELLEN SICHERSTELLEN ---
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS apartments (
                id SERIAL PRIMARY KEY,
                unit_name VARCHAR(255) NOT NULL,
                area NUMERIC(10,2) DEFAULT 0,
                base_rent NUMERIC(10,2) DEFAULT 0,
                service_charge_prepayment NUMERIC(10,2) DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS tenants (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                apartment_id INTEGER REFERENCES apartments(id),
                move_in DATE,
                move_out DATE,
                monthly_prepayment NUMERIC(10,2) DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER REFERENCES tenants(id),
                amount NUMERIC(10,2) DEFAULT 0,
                payment_date DATE DEFAULT CURRENT_DATE,
                payment_type VARCHAR(50),
                note TEXT
            );
        """)
        conn.commit()
    except Exception as e:
        st.error(f"Fehler beim Initialisieren der Tabellen: {e}")

    # --- DATEN ABFRAGEN ---
    try:
        # 1. Wohnungen & Fläche
        cur.execute("SELECT SUM(area), COUNT(*) FROM apartments")
        apt_data = cur.fetchone()
        total_area = apt_data[0] if apt_data and apt_data[0] else 0.0
        total_apts = apt_data[1] if apt_data and apt_data[1] else 0

        # 2. Aktive Mieter
        cur.execute("SELECT COUNT(*) FROM tenants WHERE move_out IS NULL")
        active_tenants = cur.fetchone()[0] if cur.rowcount > 0 else 0

        # 3. Monatliche Soll-Miete
        cur.execute("""
            SELECT SUM(a.base_rent + t.monthly_prepayment) 
            FROM tenants t 
            JOIN apartments a ON t.apartment_id = a.id 
            WHERE t.move_out IS NULL
        """)
        target_res = cur.fetchone()
        target_rent = target_res[0] if target_res and target_res[0] else 0.0

        # 4. Tatsächliche Zahlungen
        this_month_start = datetime.now().replace(day=1)
        cur.execute("SELECT SUM(amount) FROM payments WHERE payment_date >= %s", (this_month_start,))
        actual_res = cur.fetchone()
        actual_rent = actual_res[0] if actual_res and actual_res[0] else 0.0

        # --- METRIKEN ANZEIGEN ---
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

        # --- LISTEN ---
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📍 Aktuelle Belegung")
            df_occ = pd.read_sql("""
                SELECT a.unit_name as Einheit, t.last_name as Mieter, t.move_in as Einzug
                FROM apartments a
                LEFT JOIN tenants t ON a.id = t.apartment_id AND t.move_out IS NULL
                ORDER BY a.unit_name
            """, conn)
            st.dataframe(df_occ, use_container_width=True, hide_index=True)

        with c2:
            st.subheader("🕒 Letzte Zahlungen")
            df_pay = pd.read_sql("""
                SELECT p.payment_date as Datum, t.last_name as Mieter, p.amount as Betrag
                FROM payments p
                JOIN tenants t ON p.tenant_id = t.id
                ORDER BY p.payment_date DESC LIMIT 5
            """, conn)
            if not df_pay.empty:
                st.dataframe(df_pay, use_container_width=True, hide_index=True)
            else:
                st.info("Noch keine Zahlungen erfasst.")

    except Exception as e:
        st.error(f"Fehler bei der Datenverarbeitung: {e}")
    finally:
        cur.close()
        conn.close()
else:
    st.error("Keine Verbindung zur Datenbank.")