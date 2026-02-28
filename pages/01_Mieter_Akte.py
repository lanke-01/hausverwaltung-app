import streamlit as st
import pandas as pd
from datetime import datetime, date
import psycopg2
import os
from pdf_utils import generate_nebenkosten_pdf

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

# Fix für deutsche Monate
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
            jahr = st.sidebar.number_input("Abrechnungsjahr", value=2024)
            
            tab1, tab2 = st.tabs(["📋 Mieter-Details & Zahlungsfluss", "🧮 Nebenkostenabrechnung"])

            # --- TAB 1: ZAHLUNGSFLUSS ---
            with tab1:
                cur.execute("SELECT first_name, last_name, move_in, move_out, monthly_prepayment, occupants, base_rent FROM tenants WHERE id = %s", (t_id,))
                t_data = cur.fetchone()
                if t_data:
                    m_in, m_out = t_data[2], t_data[3]
                    kaltmiete, vorschuss = float(t_data[6] or 0), float(t_data[4] or 0)
                    soll_gesamt = kaltmiete + vorschuss
                    st.subheader(f"Stammdaten: {t_data[0]} {t_data[1]}")
                    
                    cur.execute("SELECT payment_date, amount FROM payments WHERE tenant_id = %s AND EXTRACT(YEAR FROM payment_date) = %s", (t_id, jahr))
                    all_payments = cur.fetchall()
                    
                    monats_daten = []
                    vortrag_saldo = 0.0
                    for i, m_name in enumerate(MONATE_DE):
                        m_idx = i + 1
                        ist_monat = sum(float(p[1]) for p in all_payments if p[0].month == m_idx)
                        
                        ist_aktiv = True
                        if m_in and m_in > date(jahr, m_idx, 28): ist_aktiv = False
                        if m_out and m_out < date(jahr, m_idx, 1): ist_aktiv = False
                        
                        if not ist_aktiv:
                            aktuelles_soll, diff_monat, status = 0.0, 0.0, "💤 Inaktiv"
                        else:
                            aktuelles_soll = soll_gesamt
                            verfuegbar = ist_monat + vortrag_saldo
                            diff_monat = verfuegbar - aktuelles_soll
                            status = "✅ Bezahlt" if verfuegbar >= aktuelles_soll - 0.01 else "❌ Rückstand"
                            vortrag_saldo = diff_monat
                        
                        monats_daten.append({"Monat": m_name, "Soll (€)": f"{aktuelles_soll:.2f}", "Ist (€)": f"{ist_monat:.2f}", "Saldo (€)": f"{diff_monat:.2f}", "Status": status})
                    st.table(pd.DataFrame(monats_daten))

            # --- TAB 2: NEBENKOSTEN (DER FIX) ---
            with tab2:
                st.subheader(f"Abrechnung für das Jahr {jahr}")
                cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants, total_units FROM landlord_settings LIMIT 1")
                h_row = cur.fetchone()
                cur.execute("SELECT a.area, t.occupants, t.move_in, t.move_out, t.monthly_prepayment, a.unit_name, t.first_name, t.last_name FROM tenants t JOIN apartments a ON t.apartment_id = a.id WHERE t.id = %s", (t_id,))
                m_row = cur.fetchone()

                if h_row and m_row:
                    m_start = max(m_row[2] or date(jahr,1,1), date(jahr,1,1))
                    m_ende = min(m_row[3] or date(jahr,12,31), date(jahr,12,31))
                    tage_mieter = (m_ende - m_start).days + 1
                    jahr_tage = 366 if (jahr % 4 == 0) else 365
                    zeit_faktor = tage_mieter / jahr_tage

                  
                # Nur Kosten laden, die KEINEM Mieter gehören (NULL) ODER genau DIESEM (t_id)
        cur.execute("""
            SELECT expense_type, amount, distribution_key, tenant_id 
            FROM operating_expenses 
            WHERE expense_year = %s 
            AND (tenant_id IS NULL OR tenant_id = %s)
            AND (tenant_id != -1 OR tenant_id IS NULL)
        """, (jahr, t_id))
                    expenses = cur.fetchall()
                    
                    pdf_rows, display_rows, summe_mieter = [], [], 0
                    for exp in expenses:
                        name, gesamt_h, key, exp_tenant_id = exp[0], float(exp[1]), exp[2], exp[3]
                        anteil = 0.0
                        
                        # Spezialfall: Wenn eine tenant_id gesetzt ist, ist es IMMER eine Direktzuordnung
                        if exp_tenant_id is not None:
                            anteil = gesamt_h * zeit_faktor
                            display_key = "Direktzuordnung (Wallbox)"
                        else:
                            display_key = DEUTSCHE_SCHLUESSEL.get(key, key)
                            if key == "area" and h_row[5] > 0:
                                anteil = (gesamt_h / float(h_row[5])) * float(m_row[0]) * zeit_faktor
                            elif key == "persons" and h_row[6] > 0:
                                anteil = (gesamt_h / float(h_row[6])) * float(m_row[1]) * zeit_faktor
                            elif key == "unit":
                                anteil = (gesamt_h / (float(h_row[7]) or 6.0)) * zeit_faktor
                            elif key == "direct":
                                anteil = gesamt_h * zeit_faktor
                        
                        summe_mieter += anteil
                        display_rows.append([name, f"{gesamt_h:.2f} €", display_key, f"{anteil:.2f} €"])
                        pdf_rows.append({"Kostenart": name, "Gesamtkosten": f"{gesamt_h:.2f}", "Schlüssel": display_key, "Ihr Anteil": f"{anteil:.2f}"})

                    st.table(pd.DataFrame(display_rows, columns=["Kostenart", "Gesamt Haus", "Verteilerschlüssel", "Anteil Mieter"]))
                    
                    voraus_gesamt = float(m_row[4]) * (tage_mieter / 30.4375)
                    saldo = summe_mieter - voraus_gesamt
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Anteilige Kosten", f"{summe_mieter:.2f} €")
                    c2.metric("Vorauszahlungen", f"{voraus_gesamt:.2f} €")
                    c3.metric("Saldo", f"{saldo:.2f} €", delta_color="inverse")

                    if st.button("🖨️ Abrechnung als PDF erstellen"):
                        try:
                            m_stats = {"area": float(m_row[0]), "occupants": int(m_row[1])}
                            h_stats = {"name": str(h_row[0]), "street": str(h_row[1]), "city": str(h_row[2]), "iban": str(h_row[3]), "bank": str(h_row[4]), "total_area": float(h_row[5]), "total_occupants": int(h_row[6]), "total_units": int(h_row[7] or 6)}
                            z_raum = f"{m_start.strftime('%d.%m.%Y')} - {m_ende.strftime('%d.%m.%Y')}"
                            pdf_path = generate_nebenkosten_pdf(f"{m_row[6]} {m_row[7]}", str(m_row[5]), z_raum, tage_mieter, pdf_rows, summe_mieter, voraus_gesamt, saldo, m_stats, h_stats)
                            with open(pdf_path, "rb") as f:
                                st.download_button("📩 Download PDF", f, file_name=f"NK_{m_row[7]}_{jahr}.pdf")
                        except Exception as e:
                            st.error(f"PDF-Fehler: {e}")
    except Exception as e:
        st.error(f"Fehler: {e}")
    finally:
        cur.close()
        conn.close()