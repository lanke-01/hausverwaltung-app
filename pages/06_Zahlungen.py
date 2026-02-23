import streamlit as st
import pandas as pd
from datetime import datetime
from database import get_conn  # Zentraler Datenbank-Importt

st.set_page_config(page_title="Zahlungseingänge", layout="wide")

st.title("💰 Miet- & Nebenkostenzahlungen")
st.info("Erfassen Sie hier die monatlichen Geldeingänge Ihrer Mieter.")

conn = get_conn()

if conn:
    try:
        cur = conn.cursor()

        # --- BEREICH 1: ZAHLUNG ERFASSEN ---
        with st.expander("➕ Neue Zahlung verbuchen", expanded=True):
            # Nur aktive Mieter laden
            cur.execute("""
                SELECT t.id, t.first_name || ' ' || t.last_name || ' (' || a.unit_name || ')'
                FROM tenants t
                JOIN apartments a ON t.apartment_id = a.id
                WHERE t.moved_out IS NULL
                ORDER BY t.last_name
            """)
            tenants = cur.fetchall()
            tenant_options = {name: tid for tid, name in tenants}

            if tenant_options:
                with st.form("payment_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        selected_tenant = st.selectbox("Mieter / Wohnung", options=list(tenant_options.keys()))
                        # Betrag vorschlagen (Kaltmiete + NK aus der DB)
                        tid = tenant_options[selected_tenant]
                        cur.execute("SELECT base_rent + service_charge_propayment FROM apartments a JOIN tenants t ON t.apartment_id = a.id WHERE t.id = %s", (tid,))
                        suggested_amount = float(cur.fetchone()[0] or 0.0)
                        
                        amount = st.number_input("Eingegangener Betrag (Euro)", min_value=0.0, value=suggested_amount, step=10.0)
                    
                    with col2:
                        p_month = st.selectbox("Für Monat", range(1, 13), index=datetime.now().month - 1)
                        p_year = st.selectbox("Für Jahr", [2024, 2025, 2026], index=2)
                        p_date = st.date_input("Zahlungsdatum", value=datetime.now())

                    if st.form_submit_button("Zahlung speichern"):
                        cur.execute("""
                            INSERT INTO payments (tenant_id, amount, period_month, period_year, payment_date)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (tid, amount, p_month, p_year, p_date))
                        conn.commit()
                        st.success(f"Zahlung für {selected_tenant} gebucht!")
                        st.rerun()
            else:
                st.warning("Keine aktiven Mieter gefunden. Bitte legen Sie erst Mieter in der Mieterverwaltung an.")

        st.divider()

        # --- BEREICH 2: HISTORIE ---
        st.subheader("Letzte Zahlungseingänge")
        
        # Filter für die Ansicht
        view_year = st.selectbox("Filter Jahr", [2024, 2025, 2026], index=2)
        
        query = """
            SELECT p.id, t.first_name || ' ' || t.last_name as Mieter, 
                   p.amount as "Betrag (Euro)", p.period_month as Monat, 
                   p.period_year as Jahr, p.payment_date as "Eingang am"
            FROM payments p
            JOIN tenants t ON p.tenant_id = t.id
            WHERE p.period_year = %s
            ORDER BY p.payment_date DESC
        """
        df_pay = pd.read_sql(query, conn, params=(view_year,))

        if not df_pay.empty:
            st.dataframe(df_pay, use_container_width=True, hide_index=True)
            
            # Summe anzeigen
            total_received = df_pay["Betrag (Euro)"].sum()
            st.metric(f"Gesamteinnahmen {view_year}", f"{total_received:.2f} Euro")
            
            # Lösch-Option
            with st.expander("🗑️ Fehlbuchung entfernen"):
                del_id = st.number_input("ID der Zahlung", min_value=1, step=1)
                if st.button("Zahlung löschen"):
                    cur.execute("DELETE FROM payments WHERE id = %s", (del_id,))
                    conn.commit()
                    st.success("Zahlung gelöscht.")
                    st.rerun()
        else:
            st.info(f"Keine Zahlungen für das Jahr {view_year} erfasst.")

    except Exception as e:
        st.error(f"Fehler: {e}")
    finally:
        conn.close()
else:
    st.error("Keine Datenbankverbindung.")