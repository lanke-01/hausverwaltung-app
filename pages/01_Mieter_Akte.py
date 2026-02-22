import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_conn
from pdf_utils import generate_nebenkosten_pdf

st.set_page_config(page_title="Mieter-Akte", layout="wide")
st.title("🔍 Mieter-Akte & Abrechnung")

# --- HILFSFUNKTION FÜR DIE BERECHNUNG ---
def get_share(art, betrag, m_area, h_area, m_pers, h_pers, h_units, tage):
    """Berechnet Kostenanteil und gibt den Schlüssel als Text zurück."""
    area_keys = ["Grundsteuer", "Sach- und Haftpflichtversicherung", "Schornsteinfeger", "Sach- & Haftpflichtversicherung"]
    person_keys = ["Kaltwasser", "Entwässerung", "Straßenreinigung und Müll", "Allgemeinstrom", "Beleuchtung"]
    unit_keys = ["Gartenpflege", "Hausmeister", "Sonstiges", "Fernsehen"]

    zf = tage / 365.0
    
    if any(k in art for k in area_keys):
        schl = "m²"
        ant_s = f"{m_area}/{h_area}"
        kosten = (betrag / h_area) * m_area * zf
    elif any(k in art for k in person_keys):
        schl = "Pers.-Tage"
        # Anteilige Personenberechnung
        kosten = (betrag / h_pers) * m_pers * zf
        ant_s = f"{m_pers} Pers."
    elif any(k in art for k in unit_keys):
        schl = "Einheit"
        ant_s = f"1/{h_units}"
        kosten = (betrag / h_units) * zf
    else:
        schl = "Einheit"
        ant_s = f"1/{h_units}"
        kosten = (betrag / h_units) * zf
        
    return kosten, schl, ant_s

# --- LOGIK FÜR WALLBOX-DIFFERENZMESSUNG ---
def get_netto_strom_info(cur, jahr):
    """Berechnet den realen Allgemeinstrom abzüglich Wallbox-Verbräuche."""
    try:
        # 1. Hauptstromzähler finden und Verbrauch berechnen
        cur.execute("""
            SELECT m.id, 
                   (MAX(r.reading_value) - MIN(r.reading_value)) as verbrauch
            FROM meters m
            JOIN meter_readings r ON m.id = r.meter_id
            WHERE m.meter_type = 'Strom' AND m.is_submeter = FALSE
            AND EXTRACT(YEAR FROM r.reading_date) = %s
            GROUP BY m.id LIMIT 1
        """, (jahr,))
        res = cur.fetchone()
        
        if not res or res[1] is None or res[1] <= 0:
            return None
        
        main_id, main_verbrauch = res
        
        # 2. Alle Unterzähler (Wallboxen) zu diesem Hauptzähler finden
        cur.execute("""
            SELECT SUM(sub_usage) FROM (
                SELECT (MAX(r.reading_value) - MIN(r.reading_value)) as sub_usage
                FROM meters m
                JOIN meter_readings r ON m.id = r.meter_id
                WHERE m.parent_meter_id = %s AND m.is_submeter = TRUE
                AND EXTRACT(YEAR FROM r.reading_date) = %s
                GROUP BY m.id
            ) as sub_query
        """, (main_id, jahr))
        wb_verbrauch = cur.fetchone()[0] or 0
        
        return {
            "brutto": float(main_verbrauch),
            "wallbox": float(wb_verbrauch),
            "netto": float(main_verbrauch - wb_verbrauch)
        }
    except Exception:
        return None

# --- HAUPTPROGRAMM ---
conn = get_conn()
if conn:
    try:
        cur = conn.cursor()
        
        # Mieterliste laden
        cur.execute("SELECT id, first_name, last_name, unit_id FROM tenants ORDER BY last_name")
        tenants = cur.fetchall()
        
        if tenants:
            t_options = {f"{t[1]} {t[2]}": t[0] for t in tenants}
            sel_name = st.sidebar.selectbox("Mieter wählen", list(t_options.keys()))
            t_id = t_options[sel_name]
            
            jahr = st.sidebar.number_input("Abrechnungsjahr", value=datetime.now().year - 1)
            
            tab1, tab2 = st.tabs(["Mieter-Details", "Abrechnung erstellen"])
            
            with tab1:
                st.subheader(f"Akte: {sel_name}")
                st.info("Hier können später Mietverträge und Dokumente verwaltet werden.")

            with tab2:
                st.subheader(f"Nebenkostenabrechnung {jahr}")
                
                # Mieter-Spezifische Daten
                cur.execute("""
                    SELECT a.unit_name, a.area, t.occupants, t.move_in, t.move_out, t.monthly_prepayment, t.last_name
                    FROM tenants t
                    JOIN apartments a ON t.unit_id = a.id
                    WHERE t.id = %s
                """, (t_id,))
                m_data = cur.fetchone()
                
                # Haus-Gesamtdaten
                cur.execute("SELECT total_area, total_occupants, total_units, name, street, city, iban, bank_name FROM landlord_settings WHERE id = 1")
                h_data = cur.fetchone()
                
                if m_data and h_data:
                    m_stats = {'apt': m_data[0], 'area': float(m_data[1]), 'pers': m_data[2], 'lname': m_data[6]}
                    h_stats = {'area': float(h_data[0]), 'pers': h_data[1], 'units': h_data[2]}
                    ld = {'name': h_data[3], 'street': h_data[4], 'city': h_data[5], 'iban': h_data[6], 'bank': h_data[7]}
                    
                    # Zeitraum berechnen
                    j_start = date(jahr, 1, 1)
                    j_ende = date(jahr, 12, 31)
                    calc_start = max(j_start, m_data[3])
                    calc_ende = min(j_ende, m_data[4]) if m_data[4] else j_ende
                    tage = (calc_ende - calc_start).days + 1
                    
                    # Ausgaben laden
                    cur.execute("SELECT expense_type, amount FROM expenses WHERE EXTRACT(YEAR FROM expense_date) = %s", (jahr,))
                    expenses = cur.fetchall()
                    
                    if expenses:
                        rows = []
                        total_share = 0
                        
                        # Strom-Spezial-Info für Differenzrechnung abrufen
                        strom_info = get_netto_strom_info(cur, jahr)
                        
                        for exp in expenses:
                            art, betrag = exp[0], float(exp[1])
                            
                            # Prüfung auf Strom-Kostenart und Wallbox-Abzug
                            if ("Strom" in art or "Beleuchtung" in art) and strom_info:
                                if strom_info['brutto'] > 0:
                                    preis_pro_kwh = betrag / strom_info['brutto']
                                    abzug_euro = strom_info['wallbox'] * preis_pro_kwh
                                    betrag = betrag - abzug_euro
                                    st.caption(f"⚡ {art}: {strom_info['wallbox']:.1f} kWh Wallbox-Abzug ({abzug_euro:.2f}€) berücksichtigt.")

                            share, schl, ant_s = get_share(art, betrag, m_stats['area'], h_stats['area'], 
                                                           m_stats['pers'], h_stats['pers'], h_stats['units'], tage)
                            
                            rows.append({
                                "Kostenart": art,
                                "Haus Gesamt": f"{betrag:.2f}",
                                "Verteilung": schl,
                                "Anteil": ant_s,
                                "Ihr Anteil": f"{share:.2f}"
                            })
                            total_share += share
                        
                        st.table(pd.DataFrame(rows))
                        
                        # Vorauszahlungen (Anteilig nach Tagen)
                        voraus_monat = float(m_data[5] or 0)
                        voraus_ges = (voraus_monat * 12) * (tage / 365.0)
                        diff = voraus_ges - total_share
                        
                        c1, c2 = st.columns(2)
                        c1.metric("Anteil Gesamtkosten", f"{total_share:.2f} €")
                        c1.metric("Vorauszahlungen (anteilig)", f"{voraus_ges:.2f} €")
                        
                        label = "Guthaben" if diff >= 0 else "Nachforderung"
                        c2.metric(label, f"{abs(diff):.2f} €", delta=round(diff, 2))
                        
                        if st.button("📄 Abrechnung als PDF generieren"):
                            pdf_bytes = generate_nebenkosten_pdf(
                                ld, sel_name, m_stats['apt'], 
                                f"{calc_start.strftime('%d.%m.%Y')} - {calc_ende.strftime('%d.%m.%Y')}", 
                                tage, rows, total_share, voraus_ges, diff, m_stats, h_stats
                            )
                            st.download_button(
                                label="💾 PDF herunterladen",
                                data=pdf_bytes,
                                file_name=f"NK_{jahr}_{m_stats['lname']}.pdf",
                                mime="application/pdf"
                            )
                    else:
                        st.warning(f"Keine Ausgaben für {jahr} gefunden.")
                else:
                    st.error("Stammdaten fehlen (Haus-Konfiguration oder Mieterdaten).")
        else:
            st.info("Keine Mieter in der Datenbank.")
            
    except Exception as e:
        st.error(f"Fehler bei der Abrechnung: {e}")
    finally:
        cur.close()
        conn.close()