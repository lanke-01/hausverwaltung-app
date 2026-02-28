import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Zahlungen", layout="wide")
st.title("💰 Miet- & Nebenkostenzahlungen")

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung möglich.")
else:
    cur = conn.cursor()
    
    # 1. Alle Mieter laden
    cur.execute("""
        SELECT t.id, t.first_name, t.last_name, a.unit_name 
        FROM tenants t
        LEFT JOIN apartments a ON t.apartment_id = a.id
        ORDER BY t.last_name
    """)
    tenants = cur.fetchall()
    tenant_options = {f"{t[1]} {t[2]} (Wohnung: {t[3] or 'N/A'})": t[0] for t in tenants}

    # --- EINGABE-BEREICH ---
    st.subheader("➕ Neue Zahlung verbuchen")
    if not tenants:
        st.warning("⚠️ Keine Mieter gefunden.")
    else:
        sel_tenant = st.selectbox("Mieter auswählen", list(tenant_options.keys()), key="input_tenant")
        
        col1, col2, col3 = st.columns(3)
        amount = col1.number_input("Betrag (€)", min_value=0.0, step=10.0)
        pay_date = col2.date_input("Zahlungsdatum", value=datetime.now())
        pay_type = col3.selectbox("Typ", ["Miete", "Nebenkosten-Nachzahlung", "Sonstiges"])
        
        note = st.text_input("Notiz (optional)")

        if st.button("💾 Zahlung jetzt speichern", use_container_width=True):
            try:
                cur.execute("""
                    INSERT INTO payments (tenant_id, amount, payment_date, payment_type, note)
                    VALUES (%s, %s, %s, %s, %s)
                """, (tenant_options[sel_tenant], amount, pay_date, pay_type, note))
                conn.commit()
                st.success(f"✅ Zahlung für {sel_tenant} verbucht!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {e}")

    st.divider()

    # --- FILTER- & HISTORIE-BEREICH ---
    st.subheader("🔍 Zahlungsverlauf & Korrektur")
    
    filter_tenant = st.selectbox("Nach Mieter filtern", ["Alle anzeigen"] + list(tenant_options.keys()))
    
    try:
        query = """
            SELECT p.id, p.payment_date, t.first_name, t.last_name, p.amount, p.payment_type, p.note
            FROM payments p
            JOIN tenants t ON p.tenant_id = t.id
        """
        params = []
        if filter_tenant != "Alle anzeigen":
            query += " WHERE p.tenant_id = %s"
            params.append(tenant_options[filter_tenant])
        
        query += " ORDER BY p.id DESC" # Neueste (höchste ID) zuerst
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        if rows:
            # Tabelle anzeigen
            df_data = []
            for r in rows:
                df_data.append({
                    "ID": r[0],
                    "Datum": r[1].strftime("%d.%m.%Y"),
                    "Mieter": f"{r[2]} {r[3]}",
                    "Betrag": f"{r[4]:.2f} €",
                    "Typ": r[5],
                    "Notiz": r[6] or ""
                })
            
            st.dataframe(df_data, use_container_width=True, hide_index=True)

            # --- LÖSCH-BEREICH FÜR DUBLETTEN ---
            with st.expander("🗑️ Dubletten löschen / Einträge entfernen"):
                st.write("Wähle die ID des Eintrags, den du löschen möchtest:")
                delete_id = st.number_input("ID eingeben", min_value=0, step=1)
                if st.button("❌ Eintrag mit dieser ID unwiderruflich löschen"):
                    cur.execute("DELETE FROM payments WHERE id = %s", (delete_id,))
                    conn.commit()
                    st.warning(f"Eintrag #{delete_id} wurde gelöscht.")
                    st.rerun()

            # Statistik
            total_sum = sum(r[4] for r in rows)
            st.metric(f"Summe ({filter_tenant})", f"{total_sum:.2f} €")
            
        else:
            st.info("Keine Zahlungen gefunden.")
            
    except Exception as e:
        st.error(f"Fehler beim Laden der Historie: {e}")

    cur.close()
    conn.close()