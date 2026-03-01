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

st.set_page_config(page_title="Mieter-Akte", layout="wide")
st.title("🔍 Mieter-Akte & Abrechnung")

DEUTSCHE_SCHLUESSEL = {"area": "m²", "persons": "Pers.", "unit": "WE", "direct": "Direkt"}
MONATE_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]

conn = get_direct_conn()

if conn:
    cur = conn.cursor()
    cur.execute("SELECT id, first_name, last_name FROM tenants ORDER BY last_name")
    tenants = cur.fetchall()
    
    if tenants:
        t_opts = {f"{t[1]} {t[2]}": t[0] for t in tenants}
        sel_name = st.sidebar.selectbox("Mieter", list(t_opts.keys()))
        t_id = t_opts[sel_name]
        jahr = st.sidebar.number_input("Jahr", value=2025)
        
        tab1, tab2 = st.tabs(["📋 Zahlungsfluss", "🧮 Abrechnung"])

        # Gemeinsame Daten laden
        cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants, total_units FROM landlord_settings LIMIT 1")
        h_row = cur.fetchone()
        cur.execute("SELECT a.area, t.occupants, t.move_in, t.move_out, t.monthly_prepayment, a.unit_name, t.first_name, t.last_name, t.base_rent FROM tenants t JOIN apartments a ON t.apartment_id = a.id WHERE t.id = %s", (t_id,))
        m_row = cur.fetchone()

        if m_row and h_row:
            ein = m_row[2].strftime('%d.%m.%Y') if m_row[2] else "unbekannt"
            aus = m_row[3].strftime('%d.%m.%Y') if m_row[3] else "laufend"
            zeitraum_anzeige = f"von {ein} bis {aus}"

            with tab1:
                st.info(f"🏠 **Mietverhältnis:** {zeitraum_anzeige}")
                cur.execute("SELECT payment_date, amount FROM payments WHERE tenant_id = %s AND EXTRACT(YEAR FROM payment_date) = %s", (t_id, jahr))
                payments = cur.fetchall()
                history, vortrag = [], 0.0
                soll_fix = float(m_row[4] or 0) + float(m_row[8] or 0)
                for i, m_name in enumerate(MONATE_DE):
                    m_idx = i + 1
                    aktiv = True
                    if m_row[2] and m_row[2] > date(jahr, m_idx, 28): aktiv = False
                    if m_row[3] and m_row[3] < date(jahr, m_idx, 1): aktiv = False
                    ist = sum(float(p[1]) for p in payments if p[0].month == m_idx)
                    soll = soll_fix if aktiv else 0.0
                    saldo = (ist + vortrag) - soll
                    status = "✅ Bezahlt" if saldo >= -0.01 else "❌ Rückstand"
                    if not aktiv: status = "💤 Inaktiv"
                    history.append({"Monat": m_name, "Soll (€)": f"{soll:.2f}", "Ist (€)": f"{ist:.2f}", "Saldo (€)": f"{saldo:.2f}", "Status": status})
                    if aktiv: vortrag = saldo
                st.table(pd.DataFrame(history))
                
                if st.button("🖨️ PDF Kontoauszug"):
                    h_stats = {"name": h_row[0], "street": h_row[1], "city": h_row[2], "iban": h_row[3], "bank": h_row[4]}
                    path = generate_payment_history_pdf(f"{m_row[6]} {m_row[7]}", jahr, history, h_stats, zeitraum_anzeige)
                    with open(path, "rb") as f:
                        st.download_button("💾 Download", f, file_name=os.path.basename(path))

            with tab2:
                m_start = max(m_row[2] or date(jahr,1,1), date(jahr,1,1))
                m_ende = min(m_row[3] or date(jahr,12,31), date(jahr,12,31))
                tage = (m_ende - m_start).days + 1
                abr_zeitraum = f"{m_start.strftime('%d.%m.%Y')} - {m_ende.strftime('%d.%m.%Y')}"
                st.success(f"📅 **Abrechnungszeitraum:** {abr_zeitraum} ({tage} Tage)")
                
                cur.execute("SELECT expense_type, amount, distribution_key, tenant_id FROM operating_expenses WHERE expense_year = %s AND (tenant_id IS NULL OR tenant_id = %s)", (jahr, t_id))
                expenses = cur.fetchall()
                pdf_rows, summe_mieter = [], 0.0
                fakt = tage / (366 if jahr % 4 == 0 else 365)
                for exp in expenses:
                    name, g_h, key, tid = exp[0], float(exp[1]), exp[2], exp[3]
                    d_key = DEUTSCHE_SCHLUESSEL.get(key, key)
                    if tid: 
                        anteil = g_h * fakt
                        d_key = "Direkt"
                    else:
                        if key == "area": anteil = (g_h / float(h_row[5])) * float(m_row[0]) * fakt
                        elif key == "persons": anteil = (g_h / float(h_row[6])) * float(m_row[1]) * fakt
                        elif key == "unit": anteil = (g_h / (float(h_row[7]) or 6)) * fakt
                    summe_mieter += anteil
                    pdf_rows.append({"Kostenart": name, "Gesamtkosten": f"{g_h:.2f}", "Schlüssel": d_key, "Ihr Anteil": f"{anteil:.2f}"})
                
                st.table(pd.DataFrame(pdf_rows))
                voraus = float(m_row[4]) * (tage / 30.43)
                diff = summe_mieter - voraus
                st.metric("Saldo", f"{diff:.2f} EUR", delta_color="inverse")

                if st.button("🖨️ PDF Abrechnung"):
                    h_stats = {"name": h_row[0], "street": h_row[1], "city": h_row[2], "iban": h_row[3], "bank": h_row[4]}
                    # Wir übergeben hier "zeitraum_anzeige" für das Mietverhältnis im Header
                    path = generate_nebenkosten_pdf(f"{m_row[6]} {m_row[7]}", str(m_row[5]), zeitraum_anzeige, tage, pdf_rows, summe_mieter, voraus, diff, {}, h_stats)
                    with open(path, "rb") as f:
                        st.download_button("💾 Download", f, file_name=f"Abrechnung_{jahr}.pdf")
    cur.close()
    conn.close()