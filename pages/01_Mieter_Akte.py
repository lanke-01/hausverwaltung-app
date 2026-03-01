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
        # Mieter für die Auswahl laden
        cur.execute("SELECT id, first_name, last_name FROM tenants ORDER BY last_name")
        tenants_data = cur.fetchall()
        
        if tenants_data:
            t_opts = {f"{t[1]} {t[2]}": t[0] for t in tenants_data}
            sel_name = st.sidebar.selectbox("Mieter wählen", list(t_opts.keys()))
            t_id = t_opts[sel_name]
            jahr = st.sidebar.number_input("Jahr", value=2024)
            
            tab1, tab2 = st.tabs(["📋 Zahlungsfluss (Kontoauszug)", "🧮 Nebenkostenabrechnung"])

            # --- TAB 1: ZAHLUNGSFLUSS ---
            with tab1:
                cur.execute("SELECT first_name, last_name, move_in, move_out, monthly_prepayment, base_rent FROM tenants WHERE id = %s", (t_id,))
                t_row = cur.fetchone()
                
                if t_row:
                    st.subheader(f"Zahlungsverlauf {jahr}: {t_row[0]} {t_row[1]}")
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
                        
                        history.append({
                            "Monat": m_name, 
                            "Soll (€)": f"{soll:.2f}", 
                            "Ist (€)": f"{ist:.2f}", 
                            "Saldo (€)": f"{saldo:.2f}", 
                            "Status": status
                        })
                        if aktiv: saldo_vortrag = saldo

                    st.table(pd.DataFrame(history))

                    if st.button("🖨️ Zahlungsverlauf als PDF"):
                        cur.execute("SELECT name, street, city, iban, bank_name FROM landlord_settings LIMIT 1")
                        h = cur.fetchone()
                        h_stats = {"name": h[0], "street": h[1], "city": h[2], "iban": h[3], "bank": h[4]}
                        path = generate_payment_history_pdf(f"{t_row[0]} {t_row[1]}", jahr, history, h_stats)
                        with open(path, "rb") as f:
                            st.download_button("💾 PDF Download", f, file_name=os.path.basename(path))

            # --- TAB 2: NEBENKOSTENABRECHNUNG ---
            with tab2:
                st.subheader(f"Abrechnung für das Jahr {jahr}")
                
                # Stammdaten Vermieter & Mieter für Kalkulation laden
                cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants, total_units FROM landlord_settings LIMIT 1")
                h_row = cur.fetchone()
                
                cur.execute("""
                    SELECT a.area, t.occupants, t.move_in, t.move_out, t.monthly_prepayment, 
                           a.unit_name, t.first_name, t.last_name 
                    FROM tenants t 
                    JOIN apartments a ON t.apartment_id = a.id 
                    WHERE t.id = %s
                """, (t_id,))
                m_row = cur.fetchone()

                if h_row and m_row:
                    # Zeitraum berechnen
                    m_start = max(m_row[2] or date(jahr,1,1), date(jahr,1,1))
                    m_ende = min(m_row[3] or date(jahr,12,31), date(jahr,12,31))
                    tage_mieter = (m_ende - m_start).days + 1
                    jahr_tage = 366 if (jahr % 4 == 0) else 365
                    zeit_faktor = tage_mieter / jahr_tage

                    # Kosten aus der DB laden
                    cur.execute("""
                        SELECT expense_type, amount, distribution_key, tenant_id 
                        FROM operating_expenses 
                        WHERE expense_year = %s 
                        AND (tenant_id IS NULL OR tenant_id = %s)
                        AND (tenant_id != -1 OR tenant_id IS NULL)
                    """, (jahr, t_id))
                    expenses = cur.fetchall()
                    
                    pdf_rows, display_rows, summe_mieter = [], [], 0.0
                    
                    for exp in expenses:
                        name, gesamt_h, key, exp_t_id = exp[0], float(exp[1]), exp[2], exp[3]
                        anteil = 0.0
                        
                        if exp_t_id is not None: # Direktzuordnung
                            anteil = gesamt_h * zeit_faktor
                            d_key = "Direktzuordnung"
                        else:
                            d_key = DEUTSCHE_SCHLUESSEL.get(key, key)
                            if key == "area" and h_row[5] > 0:
                                anteil = (gesamt_h / float(h_row[5])) * float(m_row[0]) * zeit_faktor
                            elif key == "persons" and h_row[6] > 0:
                                anteil = (gesamt_h / float(h_row[6])) * float(m_row[1]) * zeit_faktor
                            elif key == "unit":
                                anteil = (gesamt_h / (float(h_row[7]) or 6.0)) * zeit_faktor
                        
                        summe_mieter += anteil
                        display_rows.append([name, f"{gesamt_h:.2f} €", d_key, f"{anteil:.2f} €"])
                        pdf_rows.append({"Kostenart": name, "Gesamtkosten": f"{gesamt_h:.2f}", "Schlüssel": d_key, "Ihr Anteil": f"{anteil:.2f}"})

                    # Tabelle anzeigen
                    if display_rows:
                        st.table(pd.DataFrame(display_rows, columns=["Kostenart", "Gesamt Haus", "Verteilerschlüssel", "Anteil Mieter"]))
                        
                        # Vorauszahlungen (basierend auf Tagen)
                        voraus_gesamt = float(m_row[4]) * (tage_mieter / (jahr_tage/12))
                        saldo = summe_mieter - voraus_gesamt
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Anteilige Kosten", f"{summe_mieter:.2f} €")
                        c2.metric("Vorauszahlungen", f"{voraus_gesamt:.2f} €")
                        c3.metric("Saldo", f"{saldo:.2f} €", delta=f"{saldo:.2f} €", delta_color="inverse")

                        if st.button("🖨️ Abrechnungs-PDF erstellen"):
                            try:
                                m_stats = {"area": float(m_row[0]), "occupants": int(m_row[1])}
                                h_stats = {
                                    "name": str(h_row[0]), "street": str(h_row[1]), "city": str(h_row[2]), 
                                    "iban": str(h_row[3]), "bank": str(h_row[4]), "total_area": float(h_row[5]), 
                                    "total_occupants": int(h_row[6]), "total_units": int(h_row[7] or 6)
                                }
                                z_raum = f"{m_start.strftime('%d.%m.%Y')} - {m_ende.strftime('%d.%m.%Y')}"
                                
                                pdf_path = generate_nebenkosten_pdf(
                                    f"{m_row[6]} {m_row[7]}", str(m_row[5]), z_raum, tage_mieter, 
                                    pdf_rows, summe_mieter, voraus_gesamt, saldo, m_stats, h_stats
                                )
                                
                                with open(pdf_path, "rb") as f:
                                    st.download_button("📩 Download Abrechnung", f, file_name=f"NK_{m_row[7]}_{jahr}.pdf")
                            except Exception as e:
                                st.error(f"PDF-Fehler: {e}")
                    else:
                        st.warning(f"Keine Ausgaben für das Jahr {jahr} in der Datenbank gefunden.")
                else:
                    st.error("Stammdaten konnten nicht geladen werden. Bitte prüfen Sie die Vermieter-Einstellungen.")

    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
    finally:
        cur.close()
        conn.close()