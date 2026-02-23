import streamlit as st
import psycopg2
from datetime import datetime

def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Zahlungen", layout="wide")
st.title("💰 Miet- & Nebenkostenzahlungen")

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung möglich.")
else:
    cur = conn.cursor()
    
    # 1. Aktive Mieter laden
    cur.execute("""
        SELECT t.id, t.first_name, t.last_name, a.unit_name 
        FROM tenants t
        LEFT JOIN apartments a ON t.apartment_id = a.id
        WHERE t.move_out IS NULL 
        ORDER BY t.last_name
    """)
    tenants = cur.fetchall()

    st.subheader("➕ Neue Zahlung verbuchen")
    
    if not tenants:
        st.warning("⚠️ Keine aktiven Mieter gefunden.")
        st.info("Bitte lege zuerst in der Mieterverwaltung einen Mieter an.")
    else:
        # Auswahl & Eingabe ohne st.form (sicherer gegen Streamlit-Bugs)
        t_options = {f"{t[1]} {t[2]} (Wohnung: {t[3] or 'N/A'})": t[0] for t in tenants}
        sel_tenant = st.selectbox("Mieter auswählen", list(t_options.keys()))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            amount = st.number_input("Betrag (€)", min_value=0.0, step=10.0)
        with col2:
            pay_date = st.date_input("Zahlungsdatum", value=datetime.now())
        with col3:
            pay_type = st.selectbox("Typ", ["Miete", "Nebenkosten-Nachzahlung", "Sonstiges"])
        
        note = st.text_input("Notiz (optional)")

        if st.button("💾 Zahlung jetzt speichern", use_container_width=True):
            try:
                cur.execute("""
                    INSERT INTO payments (tenant_id, amount, payment_date, payment_type, note)
                    VALUES (%s, %s, %s, %s, %s)
                """, (t_options[sel_tenant], amount, pay_date, pay_type, note))
                conn.commit()
                st.success(f"✅ Zahlung für {sel_tenant} verbucht!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {e}")

    st.divider()

    # --- HISTORIE ---
    st.subheader("Letzte 20 Geldeingänge")
    try:
        cur.execute("""
            SELECT p.payment_date, t.first_name, t.last_name, p.amount, p.payment_type
            FROM payments p
            JOIN tenants t ON p.tenant_id = t.id
            ORDER BY p.id DESC LIMIT 20
        """)
        rows = cur.fetchall()
        if rows:
            df = [{"Datum": r[0], "Mieter": f"{r[1]} {r[2]}", "Betrag": f"{r[3]:.2f} €", "Typ": r[4]} for r in rows]
            st.table(df)
        else:
            st.info("Noch keine Zahlungen vorhanden.")
    except:
        st.info("Zahlungstabelle ist noch leer.")

    cur.close()
    conn.close()