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
            
            tab1, tab2 = st.tabs(["📋 Mieter-Details & Zahlungen", "🧮 Nebenkostenabrechnung"])

            # --- TAB 1: DETAILS & ZAHLUNGSÜBERSICHT ---
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
                    st.subheader(f"📅 Zahlungsabgleich {jahr}")

                    # Zahlungen laden
                    cur.execute("""
                        SELECT payment_date, amount, note 
                        FROM payments 
                        WHERE tenant_id = %s AND EXTRACT(YEAR FROM payment_date) = %s
                        ORDER BY payment_date DESC
                    """, (t_id, jahr))
                    all_payments = cur.fetchall()

                    monats_daten = []
                    monate_namen = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
                                    "Juli", "August", "September", "Oktober", "November", "Dezember"]
                    
                    for m_idx, m_name in enumerate(monate_namen, 1):
                        # Erster und letzter Tag des zu prüfenden Monats
                        erster_tag_monat = date(jahr, m_idx, 1)
                        if m_idx == 12:
                            letzter_tag_monat = date(jahr, 12, 31)
                        else:
                            letzter_tag_monat = date(jahr, m_idx + 1, 1) # Grobe Prüfung reicht hier
                        
                        # Prüfen, ob der Mieter in diesem Monat einen aktiven Vertrag hatte
                        ist_aktiv = True
                        if m_in and m_in > letzter_tag_monat:
                            ist_aktiv = False
                        if m_out and m_out < erster_tag_monat:
                            ist_aktiv = False

                        ist_summe = sum(float(p[1]) for p in all_payments if p[0].month == m_idx)
                        
                        if not ist_aktiv:
                            status = "💤 Inaktiv"
                            aktuelles_soll = 0.0
                        else:
                            aktuelles_soll = soll_gesamt
                            diff = ist_summe - aktuelles_soll
                            if ist_summe == 0:
                                status = "⚪ Keine Zahlung"
                            elif diff >= -0.01:
                                status = "✅ Bezahlt"
                            else:
                                status = "❌ Rückstand"

                        monats_daten.append({
                            "Monat": m_name,
                            "Soll (€)": f"{aktuelles_soll:.2f}",
                            "Ist (€)": f"{ist_summe:.2f}",
                            "Differenz (€)": f"{(ist_summe - aktuelles_soll):.2f}",
                            "Status": status
                        })

                    st.table(pd.DataFrame(monats_daten))

                    with st.expander("🔍 Einzelne Buchungen einsehen"):
                        if all_payments:
                            df_p = pd.DataFrame(all_payments, columns=["Datum", "Betrag", "Notiz"])
                            st.dataframe(df_p, use_container_width=True)
                        else:
                            st.info("Keine Einzelbuchungen vorhanden.")

            # --- TAB 2: NEBENKOSTENABRECHNUNG ---
            with tab2:
                st.info(f"Berechnung für {jahr}...")
                # (Hier bleibt dein bestehender Abrechnungs-Code)

    except Exception as e:
        st.error(f"Fehler: {e}")
    finally:
        cur.close()
        conn.close()