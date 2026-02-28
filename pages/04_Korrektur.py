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
st.title("🛠️ Korrektur & Stammdaten-Pflege")
st.info("Klicken Sie direkt in die Tabellen, um Werte zu ändern. Danach unten auf 'Speichern' klicken.")

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung möglich.")
else:
    cur = conn.cursor()

    tab1, tab2 = st.tabs(["💰 Mietzahlungen bearbeiten", "🏢 Wohnungen & Stammdaten"])

    # --- TAB 1: MIETZAHLUNGEN BEARBEITEN ---
    with tab1:
        st.subheader("Zahlungshistorie")
        
        # Wichtig: Wir laden die Spaltennamen exakt so, wie sie in der DB heißen
        query_pay = """
            SELECT p.id, t.last_name, p.amount, p.payment_date, p.payment_type, p.note
            FROM payments p
            JOIN tenants t ON p.tenant_id = t.id
            ORDER BY p.payment_date DESC
        """
        df_pay = pd.read_sql(query_pay, conn)

        if not df_pay.empty:
            edited_pay = st.data_editor(
                df_pay,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "last_name": st.column_config.TextColumn("Mieter", disabled=True),
                    "amount": st.column_config.NumberColumn("Betrag (€)", format="%.2f"),
                    "payment_date": st.column_config.DateColumn("Zahlungsdatum"),
                    "payment_type": st.column_config.SelectboxColumn("Typ", options=["Überweisung", "Bar", "Dauerauftrag"]),
                    "note": st.column_config.TextColumn("Notiz")
                },
                use_container_width=True,
                hide_index=True,
                key="editor_payments"
            )

            if st.button("💾 Änderungen Zahlungen speichern"):
                try:
                    for index, row in edited_pay.iterrows():
                        cur.execute("""
                            UPDATE payments 
                            SET amount = %s, payment_date = %s, payment_type = %s, note = %s
                            WHERE id = %s
                        """, (row['amount'], row['payment_date'], row['payment_type'], row['note'], row['id']))
                    conn.commit()
                    st.success("✅ Zahlungen wurden aktualisiert!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")
            
    # --- TAB 2: WOHNUNGEN BEARBEITEN ---
    with tab2:
        st.subheader("Wohnungsdaten anpassen")
        # Hier nutzen wir die echten DB-Spaltennamen: unit_name, area, base_rent
        df_ap = pd.read_sql("SELECT id, unit_name, area, base_rent FROM apartments ORDER BY unit_name", conn)
        
        if not df_ap.empty:
            edited_ap = st.data_editor(
                df_ap,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "unit_name": st.column_config.TextColumn("Einheit (Name)"),
                    "area": st.column_config.NumberColumn("m² Fläche", format="%.2f"),
                    "base_rent": st.column_config.NumberColumn("Kaltmiete (€)", format="%.2f")
                },
                use_container_width=True,
                hide_index=True,
                key="editor_apartments"
            )

            if st.button("💾 Änderungen Wohnungen speichern"):
                try:
                    for index, row in edited_ap.iterrows():
                        # Wir greifen auf 'unit_name' zu, nicht auf 'Einheit'
                        cur.execute("""
                            UPDATE apartments 
                            SET unit_name = %s, area = %s, base_rent = %s
                            WHERE id = %s
                        """, (row['unit_name'], row['area'], row['base_rent'], row['id']))
                    conn.commit()
                    st.success("✅ Wohnungsdaten aktualisiert!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")
        else:
            st.info("Keine Wohnungen gefunden.")

    cur.close()
    conn.close()