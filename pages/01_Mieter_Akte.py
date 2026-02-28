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

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung.")
else:
    cur = conn.cursor()
    try:
        # Mieterliste für Sidebar
        cur.execute("SELECT id, first_name, last_name FROM tenants ORDER BY last_name")
        tenants_data = cur.fetchall()
        
        if tenants_data:
            t_opts = {f"{t[1]} {t[2]}": t[0] for t in tenants_data}
            sel_name = st.sidebar.selectbox("Mieter wählen", list(t_opts.keys()))
            t_id = t_opts[sel_name]
            jahr = st.sidebar.number_input("Abrechnungsjahr", value=2024)
            
            tab1, tab2 = st.tabs(["📋 Mieter-Details & Zahlungsfluss", "🧮 Nebenkostenabrechnung"])

            # --- TAB 1: DETAILS & INTELLIGENTER ZAHLUNGSABGLEICH ---
            with tab1:
                cur.execute("""
                    SELECT first_name, last_name, move_in, move_out, monthly_prepayment, occupants, base_rent 
                    FROM tenants WHERE id = %s
                """, (t_id,))
                t_data = cur.fetchone()
                
                if t_data:
                    m_in = t_data[2]
                    m_out = t_data[3]
                    kaltmiete = float(t_data[6] or 0)
                    vorschuss = float(t_data[4] or 0)
                    soll_gesamt = kaltmiete + vorschuss

                    st.subheader(f"Stammdaten: {t_data[0]} {t_data[1]}")
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Einzug:** {m_in}")
                    c1.write(f"**Auszug:** {m_out if m_out else 'unbefristet'}")
                    c2.write(f"**Kaltmiete:** {kaltmiete:.2f} €")
                    c2.write(f"**Vorauszahlung:** {vorschuss:.2f} €")
                    c3.metric("Monatliches Soll", f"{soll_gesamt:.2f} €")

                    st.divider()
                    st.subheader(f"📅 Zahlungsfluss & Saldo {jahr}")

                    cur.execute("""
                        SELECT payment_date, amount, note 
                        FROM payments 
                        WHERE tenant_id = %s AND EXTRACT(YEAR FROM payment_date) = %s
                        ORDER BY payment_date ASC
                    """, (t_id, jahr))
                    all_payments = cur.fetchall()

                    monats_daten = []
                    monate_namen = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
                                    "Juli", "August", "September", "Oktober", "November", "Dezember"]
                    
                    vortrag_saldo = 0.0
                    for m_idx, m_name in enumerate(monate_namen, 1):
                        erster_tag_monat = date(jahr, m_idx, 1)
                        letzter_tag_monat = date(jahr, m_idx, 28) # Vereinfachte Prüfung

                        ist_aktiv = True
                        if m_in and m_in > letzter_tag_monat: ist_aktiv = False
                        if m_out and m_out < erster_tag_monat: ist_aktiv = False

                        ist_monat = sum(float(p[1]) for p in all_payments if p[0].month == m_idx)
                        
                        if not ist_aktiv:
                            status, aktuelles_soll, diff_monat, vortrag_saldo = "💤 Inaktiv", 0.0, 0.0, 0.0
                        else:
                            aktuelles_soll = soll_gesamt
                            verfuegbar = ist_monat + vortrag_saldo
                            diff_monat = verfuegbar - aktuelles_soll
                            status = "✅ Bezahlt" if verfuegbar >= aktuelles_soll - 0.01 else ("⚠️ Teil" if verfuegbar > 0 else "❌ Rückstand")
                            vortrag_saldo = diff_monat

                        monats_daten.append({"Monat": m_name, "Soll (€)": f"{aktuelles_soll:.2f}", "Ist (€)": f"{ist_monat:.2f}", "Saldo (€)": f"{diff_monat:.2f}", "Status": status})

                    st.table(pd.DataFrame(monats_daten))

            # --- TAB 2: VOLL FUNKTIONSFÄHIGE NEBENKOSTENABRECHNUNG ---
            with tab2:
                st.subheader(f"Abrechnung für das Jahr {jahr}")
                
                # 1. Haus-Gesamtwerte & Mieter-Daten laden
                cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants, total_units FROM landlord_settings LIMIT 1")
                h_data = cur.fetchone()
                
                cur.execute("SELECT a.area, t.occupants, t.move_in, t.move_out, t.monthly_prepayment, a.unit_name, t.first_name, t.last_name FROM tenants t JOIN apartments a ON t.apartment_id = a.id WHERE t.id = %s", (t_id,))
                m_data = cur.fetchone()

                if h_data and m_data:
                    # Zeitraum berechnen
                    m_start = max(m_data[2] or date(jahr,1,1), date(jahr,1,1))
                    m_ende = min(m_data[3] or date(jahr,12,31), date(jahr,12,31))
                    mieter_tage = (m_ende - m_start).days + 1
                    jahr_tage = 366 if (jahr % 4 == 0 and (jahr % 100 != 0 or jahr % 400 == 0)) else 365
                    anteil_jahr = mieter_tage / jahr_tage

                    # Ausgaben laden
                    cur.execute("SELECT expense_type, amount, distribution_key FROM operating_expenses WHERE expense_year = %s", (jahr,))
                    expenses = cur.fetchall()
                    
                    rows = []
                    summe_mieter = 0
                    for exp in expenses:
                        name, gesamt_betrag, key = exp
                        betrag_f = float(gesamt_betrag)
                        
                        # Anteil berechnen
                        if key == "area" and h_data[5] > 0:
                            anteil = (betrag_f / float(h_data[5])) * float(m_data[0]) * anteil_jahr
                        elif key == "persons" and h_data[6] > 0:
                            anteil = (betrag_f / float(h_data[6])) * float(m_data[1]) * anteil_jahr
                        elif key == "unit" and h_data[7] > 0:
                            anteil = (betrag_f / float(h_data[7])) * anteil_jahr
                        else:
                            anteil = 0
                        
                        summe_mieter += anteil
                        rows.append([name, f"{betrag_f:.2f} €", DEUTSCHE_SCHLUESSEL.get(key, key), f"{anteil:.2f} €"])

                    st.table(pd.DataFrame(rows, columns=["Kostenart", "Gesamt Haus", "Verteilerschlüssel", "Anteil Mieter"]))
                    
                    voraus_anteilig = float(m_data[4]) * (mieter_tage / 30.4375) # Grobe Schätzung der Monate
                    saldo = summe_mieter - voraus_anteilig

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Gesamtkosten (anteilig)", f"{summe_mieter:.2f} €")
                    c2.metric("Gezahlte Vorauszahlung", f"{voraus_anteilig:.2f} €")
                    c3.metric("Saldo", f"{saldo:.2f} €", delta_color="inverse")

                    if st.button("🖨️ Abrechnung als PDF erstellen"):
                        try:
                            m_stats = {"area": m_data[0], "occupants": m_data[1]}
                            h_stats = {"name": h_data[0], "street": h_data[1], "city": h_data[2], "iban": h_data[3], "bank": h_data[4], "total_area": h_data[5], "total_occupants": h_data[6]}
                            pdf_path = generate_nebenkosten_pdf(f"{m_data[6]} {m_data[7]}", m_data[5], f"{m_start} - {m_ende}", mieter_tage, rows, summe_mieter, voraus_anteilig, saldo, m_stats, h_stats)
                            with open(pdf_path, "rb") as f:
                                st.download_button("📩 Download PDF", f, file_name=f"Abrechnung_{m_data[7]}.pdf")
                        except Exception as e:
                            st.error(f"PDF-Fehler: {e}")
                else:
                    st.warning("⚠️ Bitte Haus-Stammdaten und Mieterdaten prüfen.")

    except Exception as e:
        st.error(f"Fehler: {e}")
    finally:
        cur.close()
        conn.close()