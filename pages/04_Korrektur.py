import streamlit as st
import pandas as pd
import psycopg2

# --- VERBINDUNGSFUNKTION ---
def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Korrektur-Modus", layout="wide")
st.title("🛠️ Korrektur-Modus")
st.write("Hier können Sie fehlerhafte Einträge korrigieren oder löschen.")

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung möglich.")
else:
    # --- AUTO-FIX: TABELLE PAYMENTS SICHERSTELLEN ---
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id),
            amount NUMERIC(10,2),
            payment_date DATE DEFAULT CURRENT_DATE,
            payment_type VARCHAR(50),
            note TEXT
        )
    """)
    conn.commit()

    tab1, tab2 = st.tabs(["💰 Mietzahlungen", "👥 Mieter & Wohnungen"])

    with tab1:
        st.subheader("Letzte Zahlungen korrigieren")
        
        # Abfrage angepasst: payment_date statt period_month
        query = """
            SELECT p.id, t.last_name as Nachname, p.amount as Betrag, p.payment_date as Datum, p.payment_type as Typ
            FROM payments p
            JOIN tenants t ON p.tenant_id = t.id
            ORDER BY p.id DESC
            LIMIT 20
        """
        
        try:
            df = pd.read_sql(query, conn)
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                st.divider()
                col_del, col_edit = st.columns(2)
                
                with col_del:
                    st.write("**Eintrag löschen**")
                    delete_id = st.number_input("ID zum Löschen eingeben", min_value=1, step=1, key="del_pay")
                    if st.button("🗑️ Zahlung unwiderruflich löschen"):
                        cur.execute("DELETE FROM payments WHERE id = %s", (delete_id,))
                        conn.commit()
                        st.success(f"Eintrag {delete_id} gelöscht!")
                        st.rerun()
            else:
                st.info("Keine Zahlungen zum Korrigieren gefunden.")
        except Exception as e:
            st.error(f"Fehler beim Laden der Zahlungen: {e}")

    with tab2:
        st.subheader("Stammdaten-Bereinigung")
        st.warning("Vorsicht: Das Löschen von Mieter-Stammdaten kann verknüpfte Zahlungen beeinflussen.")
        
        # Übersicht Wohnungen
        st.write("**Wohnungen verwalten**")
        df_ap = pd.read_sql("SELECT id, unit_name, area, base_rent FROM apartments ORDER BY unit_name", conn)
        st.dataframe(df_ap, use_container_width=True, hide_index=True)
        
        del_ap_id = st.number_input("Wohnung ID löschen", min_value=1, step=1)
        if st.button("🗑️ Wohnung löschen"):
            try:
                cur.execute("DELETE FROM apartments WHERE id = %s", (del_ap_id,))
                conn.commit()
                st.success("Wohnung entfernt.")
                st.rerun()
            except Exception as e:
                st.error("Löschen nicht möglich (evtl. noch Mieter zugewiesen).")

    cur.close()
    conn.close()