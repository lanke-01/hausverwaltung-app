import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Haus-Ausgaben", layout="wide")
st.title("💸 Haus-Ausgaben (Gesamtkosten)")

DEUTSCHE_SCHLUESSEL = {
    "area": "m² Wohnfläche",
    "persons": "Anzahl Personen",
    "unit": "Wohneinheiten",
    "direct": "Direktzuordnung"
}

conn = get_direct_conn()

if conn:
    try:
        cur = conn.cursor()
        
        # Sicherstellen, dass die Tabelle existiert (Selbstheilung)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS operating_expenses (
                id SERIAL PRIMARY KEY,
                expense_type VARCHAR(255),
                amount NUMERIC(12,2),
                distribution_key VARCHAR(50),
                expense_year INTEGER,
                tenant_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # --- ÜBERSICHT ---
        st.subheader("Übersicht der Kosten")
        f_year = st.selectbox("Jahr filtern", [2024, 2025, 2026], index=0)

        # SQL-Abfrage mit JOIN zu den Mietern, um Namen bei Direktzuordnungen zu sehen
        cur.execute("""
            SELECT e.id, e.expense_type, e.amount, e.distribution_key, 
                   t.first_name, t.last_name 
            FROM operating_expenses e
            LEFT JOIN tenants t ON e.tenant_id = t.id
            WHERE e.expense_year = %s 
            ORDER BY e.id ASC
        """, (f_year,))
        rows = cur.fetchall()

        if rows:
            # Wir bauen die Liste so um, dass der Mietername in der Spalte "Hinweis/Mieter" erscheint
            display_data = []
            for r in rows:
                mieter_name = f"{r[4]} {r[5]}" if r[4] else "Alle Mieter"
                display_data.append([r[0], r[1], r[2], DEUTSCHE_SCHLUESSEL.get(r[3], r[3]), mieter_name])
            
            df = pd.DataFrame(display_data, columns=["ID", "Kostenart", "Betrag (€)", "Schlüssel", "Zuordnung"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info(f"Noch keine Ausgaben für {f_year} erfasst.")

        st.divider()

        # --- NEUE AUSGABE ---
        with st.expander("➕ Neue Ausgabe hinzufügen"):
            with st.form("add_expense"):
                e_type = st.text_input("Kostenart (z.B. Grundsteuer, Wallbox...)")
                e_amount = st.number_input("Gesamtbetrag (€)", step=0.01)
                e_key = st.selectbox("Verteilungsschlüssel", list(DEUTSCHE_SCHLUESSEL.keys()), 
                                    format_func=lambda x: DEUTSCHE_SCHLUESSEL[x])
                
                # Mieter-Auswahl, falls "direct" gewählt wird
                cur.execute("SELECT id, first_name, last_name FROM tenants WHERE move_out IS NULL")
                tenants = {f"{t[1]} {t[2]}": t[0] for t in cur.fetchall()}
                target_tenant = st.selectbox("Nur für Mieter (bei Direktzuordnung)", ["Keine / Alle"] + list(tenants.keys()))
                
                if st.form_submit_button("Speichern"):
                    t_id = tenants[target_tenant] if target_tenant != "Keine / Alle" else None
                    cur.execute("""
                        INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year, tenant_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (e_type, e_amount, e_key, f_year, t_id))
                    conn.commit()
                    st.success("Gespeichert!")
                    st.rerun()

    except Exception as e:
        st.error(f"Fehler: {e}")
    finally:
        cur.close()
        conn.close()