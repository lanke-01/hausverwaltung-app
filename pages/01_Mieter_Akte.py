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

DEUTSCHE_SCHLUESSEL = {
    "area": "m² Wohnfläche",
    "persons": "Anzahl Personen",
    "unit": "Wohneinheiten (1/6)",
    "direct": "Direktzuordnung"
}

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
            jahr = st.sidebar.number_input("Jahr", value=2024)
            
            tab1, tab2 = st.tabs(["📋 Zahlungsfluss", "🧮 Abrechnung"])

            # --- TAB 1: KONTOAUSZUG ---
            with tab1:
                cur.execute("SELECT first_name, last_name, move_in, move_out, monthly_prepayment, base_rent FROM tenants WHERE id = %s", (t_id,))
                t_row = cur.fetchone()
                if t_row:
                    st.subheader(f"Kontoauszug {jahr}")
                    soll_monat = float(t_row[4] or 0) + float(t_row[5] or 0)
                    cur.execute("SELECT payment_date, amount FROM payments WHERE tenant_id = %s AND EXTRACT(YEAR FROM payment_date) = %s", (t_id, jahr))
                    payments = cur.fetchall()
                    
                    history = []
                    saldo_vortrag = 0.0
                    for i, m_name in enumerate(MONATE_DE):
                        m_idx = i + 1
                        ist = sum(float(p[1]) for p in payments if p[0].month == m_idx)
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

                    if st.button("🖨️ PDF Kontoauszug", key="btn_p"):
                        cur.execute("SELECT name, street, city, iban, bank_name FROM landlord_settings LIMIT 1")
                        h = cur.fetchone()
                        h_stats = {"name": h[0], "street": h[1], "city": h[2], "iban": h[3], "bank": h[4]}
                        path = generate_payment_history_pdf(f"{t_row[0]} {t_row[1]}", jahr, history, h_stats)
                        with open(path, "rb") as f:
                            st.download_button("💾 Download", f, file_name=os.path.basename(path), key="dl_p")

            # --- TAB 2: NEBENKOSTEN ---
            with tab2:
                cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants, total_units FROM landlord_settings LIMIT 1")
                h_row = cur.fetchone()
                cur.execute("SELECT a.area, t.occupants, t.move_in, t.move_out, t.monthly_prepayment, a.unit_name, t.first_name, t.last_name FROM tenants t JOIN apartments a ON t.apartment_id = a.id WHERE t.id = %s", (t_id,))
                m_row = cur.fetchone()

                if h_row and m_row:
                    # ZEITRAUM BERECHNEN
                    m_start = max(m_row[2] or date(jahr,1,1), date(jahr,1,1))
                    m_ende = min(m_row[3] or date(jahr,12,31), date(jahr,12,31))
                    tage_mieter = (m_ende - m_start).days + 1
                    zeit_faktor = tage_mieter / (366 if jahr % 4 == 0 else 365)
                    z_raum = f"{m_start.strftime('%d.%m.%Y')} - {m_ende.strftime('%d.%m.%Y')}"

                    st.info(f"📅 **Mietzeitraum im Jahr {jahr}:** {z_raum} ({tage_mieter} Tage)")

                    cur.execute("SELECT expense_type, amount, distribution_key, tenant_id FROM operating_expenses WHERE expense_year = %s AND (tenant_id IS NULL OR tenant_id = %s)", (jahr, t_id))
                    expenses = cur.fetchall()
                    
                    pdf_rows, display_rows, gesamt_mieter = [], [], 0.0
                    for exp in expenses:
                        name, betrag, key, tid = exp[0], float(exp[1]), exp[2], exp[3]
                        anteil = 0.0
                        if tid:
                            anteil = betrag * zeit_faktor
                            d_key = "Direkt"
                        else:
                            d_key = DEUTSCHE_SCHLUESSEL.get(key, key)
                            if key == "area": anteil = (betrag / float(h_row[5])) * float(m_row[0]) * zeit_faktor
                            elif key == "persons": anteil = (betrag / float(h_row[6])) * float(m_row[1]) * zeit_faktor
                            elif key == "unit": anteil = (betrag / float(h_row[7] or 6)) * zeit_faktor
                        
                        gesamt_mieter += anteil
                        display_rows.append([name, f"{betrag:.2f} €", d_key, f"{anteil:.2f} €"])
                        pdf_rows.append({"Kostenart": name, "Gesamtkosten": f"{betrag:.2f}", "Schlüssel": d_key, "Ihr Anteil": f"{anteil:.2f}"})

                    st.table(pd.DataFrame(display_rows, columns=["Kostenart", "Haus", "Schlüssel", "Mieter"]))
                    voraus = float(m_row[4]) * (tage_mieter / 30.43) # Durchschnittsmonat
                    diff = gesamt_mieter - voraus
                    
                    st.metric("Saldo", f"{diff:.2f} €", delta_color="inverse")

                    if st.button("🖨️ PDF Abrechnung", key="btn_n"):
                        h_stats = {"name": h_row[0], "street": h_row[1], "city": h_row[2], "iban": h_row[3], "bank": h_row[4]}
                        path = generate_nebenkosten_pdf(f"{m_row[6]} {m_row[7]}", str(m_row[5]), z_raum, tage_mieter, pdf_rows, gesamt_mieter, voraus, diff, {}, h_stats)
                        with open(path, "rb") as f:
                            st.download_button("💾 Download", f, file_name=os.path.basename(path), key="dl_n")
    except Exception as e:
        st.error(f"Fehler: {e}")
    finally:
        cur.close()
        conn.close()