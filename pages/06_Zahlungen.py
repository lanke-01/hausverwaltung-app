import streamlit as st
import psycopg2
from datetime import datetime

# --- DIREKTE VERBINDUNGSFUNKTION ---
def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Zahlungen", layout="wide")
st.title("💰 Miet- & Nebenkostenzahlungen")
st.write("Erfassen Sie hier die monatlichen Geldeingänge Ihrer Mieter.")

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung.")
else:
    cur = conn.cursor()
    
    # Formular zum Verbuchen einer neuen Zahlung
    with st.expander("➕ Neue Zahlung verbuchen", expanded=True):
        with st.form("payment_form"):
            # Mieter laden, die noch nicht ausgezogen sind (Wichtig: move_out statt moved_out)
            cur.execute("""
                SELECT t.id, t.first_name, t.last_name, a.unit_name 
                FROM tenants t
                JOIN apartments a ON t.apartment_id = a.id
                WHERE t.move_out IS NULL 
                ORDER BY t.last_name
            """)
            tenants = cur.fetchall()
            
            if tenants:
                t_options = {f"{t[1]} {t[2]} ({t[3]})": t[0] for t in tenants}
                sel_tenant = st.selectbox("Mieter auswählen", list(t_options.keys()))
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    amount = st.number_input("Betrag (€)", min_value=0.0, step=10.0)
                with col2:
                    pay_date = st.date_input("Zahlungsdatum", value=datetime.now())
                with col3:
                    pay_type = st.selectbox("Typ", ["Miete", "Nebenkosten-Nachzahlung", "Sonstiges"])
                
                note = st.text_input("Notiz (optional)")
                
                if st.form_submit_button("Zahlung speichern"):
                    try:
                        cur.execute("""
                            INSERT INTO payments (tenant_id, amount, payment_date, payment_type, note)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (t_options[sel_tenant], amount, pay_date, pay_type, note))
                        conn.commit()
                        st.success(f"✅ Zahlung für {sel_tenant} erfolgreich verbucht!")
                    except Exception as e:
                        st.error(f"Fehler beim Speichern: {e}")
            else:
                st.warning("Keine aktiven Mieter gefunden.")

    st.divider()

    # Übersicht der letzten Zahlungen
    st.subheader("Last 20 Geldeingänge")
    cur.execute("""
        SELECT p.payment_date, t.first_name, t.last_name, p.amount, p.payment_type, p.note
        FROM payments p
        JOIN tenants t ON p.tenant_id = t.id
        ORDER BY p.payment_date DESC
        LIMIT 20
    """)
    recent_pays = cur.fetchall()
    
    if recent_pays:
        df = list(recent_pays)
        st.table([{"Datum": r[0], "Mieter": f"{r[1]} {r[2]}", "Betrag": f"{r[3]:.2f} €", "Typ": r[4], "Notiz": r[5]} for r in df])
    else:
        st.info("Noch keine Zahlungen erfasst.")

    cur.close()
    conn.close()