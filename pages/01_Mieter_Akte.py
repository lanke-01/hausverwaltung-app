import streamlit as st
import pandas as pd
from datetime import datetime, date
import psycopg2
import os
# Import beider PDF-Funktionen aus deiner pdf_utils.py
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
        # Mieterliste laden
        cur.execute("SELECT id, first_name, last_name FROM tenants ORDER BY last_name")
        tenants_data = cur.fetchall()
        
        if tenants_data:
            t_opts = {f"{t[1]} {t[2]}": t[0] for t in tenants_data}
            sel_name = st.sidebar.selectbox("Mieter wählen", list(t_opts.keys()))
            t_id = t_opts[sel_name]
            jahr = st.sidebar.number_input("Jahr", value=2025)
            
            tab1, tab2 = st.tabs(["📋 Zahlungsfluss (Kontoauszug)", "🧮 Nebenkostenabrechnung"])

            # Gemeinsame Daten für beide Tabs laden
            cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants, total_units FROM landlord_settings LIMIT 1")
            h_row = cur.fetchone()
            
            cur.execute("""
                SELECT t.first_name, t.last_name, t.move_in, t.move_out, t.monthly_prepayment, 
                       a.unit_name, a.area, t.occupants, t.base_rent 
                FROM tenants t 
                JOIN apartments a ON t.apartment_id = a.id 
                WHERE t.id = %s
            """, (t_id,))
            m_row = cur.fetchone()

            if m_row and h_row:
                # --- TAB 1: ZAHLUNGSFLUSS ---
                with tab1:
                    ein = m_row[2].strftime('%d.%m.%Y') if m_row[2] else "unbekannt"
                    aus = m_row[3].strftime('%d.%m.%Y') if m_row[3] else "laufend"
                    st.info(f"🏠 **Mietverhältnis:** von {ein} bis {aus}")

                    cur.execute("SELECT payment_date, amount FROM payments WHERE tenant_id = %s AND EXTRACT(YEAR FROM payment_date) = %s", (t_id, jahr))
                    payments = cur.fetchall()
                    
                    history = []
                    saldo_vortrag = 0.0
                    soll_monat = float(m_row[4] or 0) + float(m_row[8] or 0) # Vorauszahlung + Kaltmiete
                    
                    for i, m_name in enumerate(MONATE_DE):
                        m_idx = i + 1
                        ist = sum(float(p[1]) for p in payments if p[0].month == m_idx)
                        aktiv = True
                        if m_row[2] and m_row[2] > date(jahr, m_idx, 28): aktiv = False
                        if m_row[3] and m_row[3] < date(jahr, m_idx, 1): aktiv = False
                        
                        soll = soll_monat if aktiv else 0.0
                        saldo = (ist + saldo_vortrag) - soll
                        status = "✅ Bezahlt" if saldo >= -0.01 else "❌ Rückstand"
                        if not aktiv: status = "💤 Inaktiv"
                        
                        history.append({
                            "Monat": m_name, 
                            "Soll (€)": f"{soll:.2f}", 
                            "Ist (€)": f"{ist:.2f}", 
                            "Saldo (€)": f"{saldo:.2f}", 
                            "Status": status
                        })
                        if aktiv: saldo_vortrag = saldo

                    st.table(pd.DataFrame(history))

                    if st.button("🖨️ PDF Kontoauszug erstellen"):
                        h_stats = {"name": h_row[0], "street": h_row[1], "city": h_row[2], "iban": h_row[3], "bank": h_row[4]}
                        zeitraum_info = f"von {ein} bis {aus}"
                        # Aufruf der Funktion in pdf_utils
                        path = generate_payment_history_pdf(f"{m_row[0]} {m_row[1]}", jahr, history, h_stats, zeitraum_info)
                        with open(path, "rb") as f:
                            st.download_button("💾 Download Kontoauszug", f, file_name=os.path.basename(path))

                # --- TAB 2: NEBENKOSTENABRECHNUNG ---
                with tab2:
                    m_start = max(m_row[2] or date(jahr,1,1), date(jahr,1,1))
                    m_ende = min(m_row[3] or date(jahr,12,31), date(jahr,12,31))
                    tage_mieter = (m_ende - m_start).days + 1
                    z_raum = f"{m_start.strftime('%d.%m.%Y')} - {m_ende.strftime('%d.%m.%Y')}"
                    st.success(f"📅 **Abrechnungszeitraum:** {z_raum} ({tage_mieter} Tage)")

                    cur.execute("""
                        SELECT expense_type, amount, distribution_key, tenant_id 
                        FROM operating_expenses 
                        WHERE expense_year = %s AND (tenant_id IS NULL OR tenant_id = %s)
                    """, (jahr, t_id))
                    expenses = cur.fetchall()
                    
                    pdf_rows, display_rows, summe_mieter = [], [], 0.0
                    zeit_faktor = tage_mieter / (366 if jahr % 4 == 0 else 365)

                    for exp in expenses:
                        name, gesamt_h, key, tid = exp[0], float(exp[1]), exp[2], exp[3]
                        anteil = 0.0
                        d_key = DEUTSCHE_SCHLUESSEL.get(key, key)
                        if tid:
                            anteil = gesamt_h * (tage_mieter / 365)
                            d_key = "Direkt"
                        else:
                            if key == "area": anteil = (gesamt_h / float(h_row[5])) * float(m_row[6]) * zeit_faktor
                            elif key == "persons": anteil = (gesamt_h / float(h_row[6])) * float(m_row[7]) * zeit_faktor
                            elif key == "unit": anteil = (gesamt_h / (float(h_row[7]) or 6.0)) * zeit_faktor
                        
                        summe_mieter += anteil
                        pdf_rows.append({"Kostenart": name, "Gesamtkosten": f"{gesamt_h:.2f}", "Schlüssel": d_key, "Ihr Anteil": f"{anteil:.2f}"})

                    st.table(pd.DataFrame(pdf_rows))
                    
                    voraus_gesamt = float(m_row[4]) * (tage_mieter / 30.4375)
                    saldo_nk = summe_mieter - voraus_gesamt
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Kostenanteil", f"{summe_mieter:.2f} €")
                    c2.metric("Vorauszahlungen", f"{voraus_gesamt:.2f} €")
                    c3.metric("Saldo", f"{saldo_nk:.2f} €", delta_color="inverse")

                    if st.button("🖨️ PDF Abrechnung erstellen"):
                        try:
                            m_stats = {"area": float(m_row[6]), "occupants": int(m_row[7])}
                            h_stats = {
                                "name": h_row[0], "street": h_row[1], "city": h_row[2], 
                                "iban": h_row[3], "bank": h_row[4], 
                                "total_area": float(h_row[5]), "total_occupants": int(h_row[6])
                            }
                            # Wichtig: zeitraum_anzeige für den Header mitschicken
                            zeitraum_anzeige = f"von {m_row[2].strftime('%d.%m.%Y')} bis {m_row[3].strftime('%d.%m.%Y') if m_row[3] else 'laufend'}"
                            
                            path = generate_nebenkosten_pdf(
                                f"{m_row[0]} {m_row[1]}", str(m_row[5]), zeitraum_anzeige, 
                                tage_mieter, pdf_rows, summe_mieter, voraus_gesamt, saldo_nk, m_stats, h_stats
                            )
                            with open(path, "rb") as f:
                                st.download_button("📩 Download Abrechnung", f, file_name=f"Abrechnung_{jahr}_{m_row[1]}.pdf")
                        except Exception as e:
                            st.error(f"Fehler beim Erstellen der PDF: {e}")

    except Exception as e:
        st.error(f"Datenbankfehler: {e}")
    finally:
        cur.close()
        conn.close()