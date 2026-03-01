import streamlit as st
import pandas as pd
from datetime import datetime, date
import psycopg2
import os
from pdf_utils import generate_nebenkosten_pdf, generate_payment_history_pdf

def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Mieter-Akte & Abrechnung", layout="wide")
st.title("🔍 Mieter-Akte & Abrechnung")

MONATE_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
             "Juli", "August", "September", "Oktober", "November", "Dezember"]

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung.")
else:
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, first_name, last_name FROM tenants ORDER BY last_name")
        tenants_data = cur.fetchall()
        
        if tenants_data:
            t_opts = {f"{t[1]} {t[2]}": t[0] for t in tenants_data}
            sel_name = st.sidebar.selectbox("Mieter wählen", list(t_opts.keys()))
            t_id = t_opts[sel_name]
            jahr = st.sidebar.number_input("Jahr", value=datetime.now().year)
            
            tab1, tab2 = st.tabs(["📋 Zahlungsfluss", "🧮 Abrechnung"])

            with tab1:
                cur.execute("SELECT first_name, last_name, move_in, move_out, monthly_prepayment, base_rent FROM tenants WHERE id = %s", (t_id,))
                t_row = cur.fetchone()
                
                if t_row:
                    st.subheader(f"Kontoauszug {jahr}: {t_row[0]} {t_row[1]}")
                    soll_monat = float(t_row[4] or 0) + float(t_row[5] or 0)
                    
                    cur.execute("SELECT payment_date, amount FROM payments WHERE tenant_id = %s AND EXTRACT(YEAR FROM payment_date) = %s", (t_id, jahr))
                    payments = cur.fetchall()
                    
                    history = []
                    saldo_vortrag = 0.0
                    for i, m_name in enumerate(MONATE_DE):
                        m_idx = i + 1
                        ist = sum(float(p[1]) for p in payments if p[0].month == m_idx)
                        
                        # Aktivitätsprüfung
                        aktiv = True
                        if t_row[2] and t_row[2] > date(jahr, m_idx, 28): aktiv = False
                        if t_row[3] and t_row[3] < date(jahr, m_idx, 1): aktiv = False
                        
                        soll = soll_monat if aktiv else 0.0
                        saldo = (ist + saldo_vortrag) - soll
                        status = "✅ Bezahlt" if saldo >= -0.01 else "❌ Rückstand"
                        if not aktiv: status = "💤 Inaktiv"
                        
                        history.append({"Monat": m_name, "Soll (€)": f"{soll:.2f}", "Ist (€)": f"{ist:.2f}", "Saldo (€)": f"{saldo:.2f}", "Status": status})
                        if aktiv: saldo_vortrag = saldo

                    st.table(pd.DataFrame(history))

                    if st.button("🖨️ Zahlungsverlauf als PDF"):
                        cur.execute("SELECT name, street, city, iban, bank_name FROM landlord_settings LIMIT 1")
                        h = cur.fetchone()
                        h_stats = {"name": h[0], "street": h[1], "city": h[2], "iban": h[3], "bank": h[4]}
                        path = generate_payment_history_pdf(f"{t_row[0]} {t_row[1]}", jahr, history, h_stats)
                        with open(path, "rb") as f:
                            st.download_button("💾 PDF Download", f, file_name=os.path.basename(path))

            with tab2:
                # Hier kommt dein bestehender Abrechnungscode hin (wie zuvor besprochen)
                st.info("Abrechnungs-Bereich (Tabellen & Kalkulation)")
                # ... (Der Code für Tab 2 bleibt wie in der letzten Version)

    except Exception as e:
        st.error(f"Fehler: {e}")
    finally:
        cur.close()
        conn.close()