import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_conn
from pdf_utils import generate_nebenkosten_pdf  # Import der ausgelagerten Logik

st.set_page_config(page_title="Mieter-Akte", layout="wide")
st.title("🔍 Mieter-Akte & Abrechnung")

# --- HILFSFUNKTION FÜR DIE BERECHNUNG IN DER UI ---
def get_share(art, betrag, m_area, h_area, m_pers, h_pers, h_units, tage):
    """Berechnet Kostenanteil und gibt den Schlüssel als Text zurück."""
    area_keys = ["Grundsteuer", "Sach- und Haftpflichtversicherung", "Schornsteinfeger", "Sach- & Haftpflichtversicherung"]
    person_keys = ["Kaltwasser", "Entwässerung", "Straßenreinigung und Müll", "Allgemeinstrom", "Beleuchtung"]
    unit_keys = ["Gartenpflege", "Hausmeister", "Sonstiges", "Fernsehen"]

    zf = tage / 365.0
    
    if any(k in art for k in area_keys):
        schl = "m2"
        ant_s = f"{m_area}/{h_area}"
        kosten = (betrag / h_area) * m_area * zf
    elif any(k in art for k in person_keys):
        schl = "Pers.-Tage"
        m_pt = m_pers * tage
        h_pt = h_pers * 365
        ant_s = f"{m_pt}/{h_pt}"
        kosten = (betrag / h_pt) * m_pt
    elif any(k in art for k in unit_keys):
        schl = "Einheit"
        ant_s = f"1/{h_units}"
        # Wohneinheiten werden oft pro Einheit voll gerechnet, zeitanteilig bei Mieterwechsel
        kosten = (betrag / h_units) * zf
    else:
        schl = "m2" # Standard
        ant_s = f"{m_area}/{h_area}"
        kosten = (betrag / h_area) * m_area * zf
        
    return round(kosten, 2), schl, ant_s

# --- HAUPTLOGIK ---
conn = get_conn()
if conn:
    cur = conn.cursor()
    
    try:
        # 1. Vermieter- & Haus-Gesamtwerte laden
        cur.execute("""
            SELECT name, street, city, iban, bank_name, total_area, total_occupants, total_units 
            FROM landlord_settings WHERE id = 1
        """)
        h_res = cur.fetchone()
        
        if not h_res:
            st.error("Bitte zuerst Stammdaten in den Einstellungen pflegen!")
            st.stop()
            
        ld = {"name": h_res[0], "street": h_res[1], "city": h_res[2], "iban": h_res[3], "bank": h_res[4]}
        h_stats = {"area": float(h_res[5] or 1), "pers": int(h_res[6] or 1), "units": int(h_res[7] or 1)}

        # 2. Mieter-Auswahl
        cur.execute("SELECT id, first_name || ' ' || last_name FROM tenants WHERE moved_out IS NULL ORDER BY last_name")
        tenants = cur.fetchall()
        
        if tenants:
            tenant_map = {name: tid for tid, name in tenants}
            sel_name = st.selectbox("Mieter auswählen", options=["-- Bitte wählen --"] + list(tenant_map.keys()))
            
            if sel_name != "-- Bitte wählen --":
                tid = tenant_map[sel_name]
                
                # Mieterdetails laden
                cur.execute("""
                    SELECT a.unit_name, t.area, t.occupants, t.moved_in, t.utilities, t.last_name
                    FROM tenants t 
                    JOIN apartments a ON t.apartment_id = a.id 
                    WHERE t.id = %s
                """, (tid,))
                t_res = cur.fetchone()
                
                m_stats = {
                    "apt": t_res[0], 
                    "area": float(t_res[1] or 0), 
                    "pers": int(t_res[2] or 1), 
                    "in": t_res[3], 
                    "pre": float(t_res[4] or 0),
                    "lname": t_res[5]
                }
                
                tab1, tab2 = st.tabs(["📋 Stammdaten", "📄 Abrechnung erstellen"])
                
                with tab1:
                    st.subheader(f"Akte: {sel_name}")
                    st.write(f"**Wohnung:** {m_stats['apt']}")
                    st.write(f"**Fläche:** {m_stats['area']} m²")
                    st.write(f"**Personen im Haushalt:** {m_stats['pers']}")
                
                with tab2:
                    jahr = st.selectbox("Abrechnungsjahr", [2024, 2025, 2026], index=1)
                    # Zeitraum-Berechnung
                    j_start = date(jahr, 1, 1)
                    j_ende = date(jahr, 12, 31)
                    calc_start = max(j_start, m_stats['in'])
                    tage = (j_ende - calc_start).days + 1
                    
                    st.info(f"Abrechnungszeitraum: {calc_start} bis {j_ende} ({tage} Tage)")
                    
                    # Ausgaben aus DB laden
                    df_exp = pd.read_sql("SELECT expense_type, amount FROM operating_expenses WHERE expense_year = %s", conn, params=(jahr,))
                    
                    if not df_exp.empty:
                        rows = []
                        total_share = 0.0
                        
                        for _, r in df_exp.iterrows():
                            amt = float(r['amount'])
                            kosten, schl, ant_s = get_share(
                                r['expense_type'], amt, m_stats['area'], h_stats['area'], 
                                m_stats['pers'], h_stats['pers'], h_stats['units'], tage
                            )
                            total_share += kosten
                            rows.append({
                                "Kostenart": r['expense_type'], 
                                "Haus Gesamt": f"{amt:.2f}", 
                                "Verteilung": schl, 
                                "Anteil": ant_s, 
                                "Ihr Anteil": f"{kosten:.2f}"
                            })
                        
                        st.table(pd.DataFrame(rows))
                        
                        # Finanzen
                        voraus_ges = m_stats['pre'] * 12 * (tage / 365.0)
                        diff = voraus_ges - total_share
                        
                        c1, c2 = st.columns(2)
                        c1.metric("Gesamtkosten Anteil", f"{total_share:.2f} €")
                        c1.metric("Vorauszahlungen", f"{voraus_ges:.2f} €")
                        c2.metric("Ergebnis", f"{diff:.2f} €", delta=round(diff, 2))
                        
                        # PDF DOWNLOAD
                        if st.button("📄 Abrechnung als PDF generieren"):
                            pdf_bytes = generate_nebenkosten_pdf(
                                ld, sel_name, m_stats['apt'], 
                                f"{calc_start.strftime('%d.%m.%Y')} - {j_ende.strftime('%d.%m.%Y')}", 
                                tage, rows, total_share, voraus_ges, diff, m_stats, h_stats
                            )
                            st.download_button(
                                label="💾 PDF herunterladen",
                                data=pdf_bytes,
                                file_name=f"NK_Abrechnung_{m_stats['lname']}_{jahr}.pdf",
                                mime="application/pdf"
                            )
                    else:
                        st.warning(f"Keine Haus-Gesamtkosten für das Jahr {jahr} gefunden.")

        else:
            st.info("Keine aktiven Mieter in der Datenbank.")
            
    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {e}")
    finally:
        cur.close()
        conn.close()
else:
    st.error("Keine Verbindung zur Datenbank.")