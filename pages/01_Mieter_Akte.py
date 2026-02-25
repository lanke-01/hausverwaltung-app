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
        tenants = cur.fetchall()
        
        if tenants:
            t_opts = {f"{t[1]} {t[2]}": t[0] for t in tenants}
            sel_name = st.sidebar.selectbox("Mieter wählen", list(t_opts.keys()))
            t_id = t_opts[sel_name]
            jahr = st.sidebar.number_input("Abrechnungsjahr", value=2024)
            
            tab1, tab2 = st.tabs(["📋 Mieter-Details", "📄 Abrechnung Vorschau"])
            
            with tab1:
                cur.execute("SELECT first_name, last_name, move_in, move_out, monthly_prepayment, occupants FROM tenants WHERE id = %s", (t_id,))
                t_data = cur.fetchone()
                if t_data:
                    st.subheader(f"Stammdaten: {t_data[0]} {t_data[1]}")
                    c1, c2 = st.columns(2)
                    c1.write(f"**Einzug:** {t_data[2]}")
                    c1.write(f"**Personen im Haushalt:** {t_data[5] or 1}")
                    c2.write(f"**Mtl. Vorauszahlung:** {t_data[4]:.2f} €")

            with tab2:
                # 1. Daten laden (Inklusive Stammdaten für den PDF-Footer)
                cur.execute("""
                    SELECT a.unit_name, a.area, t.occupants, t.move_in, t.move_out, t.monthly_prepayment, t.first_name, t.last_name 
                    FROM tenants t JOIN apartments a ON t.apartment_id = a.id WHERE t.id = %s
                """, (t_id,))
                m_data = cur.fetchone()
                
                # Hier wurde der Fehler behoben: Abfrage der Vermieter-Daten
                cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants FROM landlord_settings WHERE id = 1")
                h_data = cur.fetchone()

                cur.execute("SELECT expense_type, amount, distribution_key FROM operating_expenses WHERE expense_year = %s", (jahr,))
                expenses = cur.fetchall()

                if m_data and h_data and expenses:
                    # 2. Zeitberechnung
                    abr_start, abr_ende = date(jahr, 1, 1), date(jahr, 12, 31)
                    m_start = max(m_data[3], abr_start)
                    m_ende = min(m_data[4] or abr_ende, abr_ende)
                    mieter_tage = (m_ende - m_start).days + 1
                    tage_jahr = (abr_ende - abr_start).days + 1
                    zeit_faktor = mieter_tage / tage_jahr

                    # 3. Kosten-Berechnung
                    rows = []
                    summe_mieter = 0.0
                    for exp in expenses:
                        name, gesamt_h, key = exp
                        if key == "area":
                            anteil = (float(gesamt_h) / float(h_data[5])) * float(m_data[1]) * zeit_faktor
                        elif key == "persons":
                            anteil = (float(gesamt_h) / (float(h_data[6]) * tage_jahr)) * (float(m_data[2] or 1) * mieter_tage)
                        elif key == "unit":
                            anteil = (float(gesamt_h) / 6.0) * zeit_faktor
                        else:
                            anteil = float(gesamt_h) * zeit_faktor
                        
                        summe_mieter += anteil
                        rows.append({
                            "Kostenart": name, 
                            "Gesamtkosten": f"{float(gesamt_h):.2f} €", 
                            "Schlüssel": DEUTSCHE_SCHLUESSEL.get(key, key), 
                            "Ihr Anteil": f"{anteil:.2f} €"
                        })

                    st.table(pd.DataFrame(rows))
                    
                    voraus_anteilig = float(m_data[5]) * (mieter_tage / 30.4375)
                    saldo = summe_mieter - voraus_anteilig

                    st.divider()

                    # 4. PDF Erstellung
                    if st.button("🖨️ Abrechnung als PDF erstellen"):
                        try:
                            m_stats = {"area": m_data[1], "occupants": m_data[2]}
                            # h_stats enthält nun alle Daten für den Footer
                            h_stats = {
                                "name": h_data[0],
                                "street": h_data[1],
                                "city": h_data[2],
                                "iban": h_data[3],
                                "bank": h_data[4],
                                "total_area": h_data[5],
                                "total_occupants": h_data[6]
                            }
                            z_raum = f"{m_start.strftime('%d.%m.%Y')} - {m_ende.strftime('%d.%m.%Y')}"
                            
                            pdf_path = generate_nebenkosten_pdf(
                                f"{m_data[6]} {m_data[7]}", m_data[0], z_raum, mieter_tage, 
                                rows, summe_mieter, voraus_anteilig, saldo, m_stats, h_stats
                            )
                            
                            with open(pdf_path, "rb") as f:
                                st.download_button("📩 Download PDF", f, file_name=f"Abrechnung_{m_data[7]}.pdf")
                        except Exception as e:
                            st.error(f"Fehler bei PDF-Erstellung: {e}")
                else:
                    st.warning("⚠️ Es fehlen Daten: Bitte Haus-Gesamtwerte und Ausgaben prüfen.")

    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
    finally:
        cur.close()
        conn.close()