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
st.info("Klicken Sie direkt in die Tabellen, um Werte zu ändern. Vergessen Sie nicht, unten auf 'Speichern' zu klicken.")

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung möglich.")
else:
    cur = conn.cursor()

    tab1, tab2 = st.tabs(["💰 Mietzahlungen bearbeiten", "🏢 Wohnungen & Stammdaten"])

    # --- TAB 1: MIETZAHLUNGEN BEARBEITEN ---
    with tab1:
        st.subheader("Zahlungshistorie")
        
        # Wir laden die Daten in ein DataFrame
        query_pay = """
            SELECT p.id, t.last_name as Mieter, p.amount as Betrag, p.payment_date as Datum, p.payment_type as Typ, p.note as Notiz
            FROM payments p
            JOIN tenants t ON p.tenant_id = t.id
            ORDER BY p.payment_date DESC
        """
        df_pay = pd.read_sql(query_pay, conn)

        if not df_pay.empty:
            # Der Data Editor ermöglicht direktes Bearbeiten
            edited_pay = st.data_editor(
                df_pay,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "Mieter": st.column_config.TextColumn("Mieter", disabled=True), # Mieter-Zuordnung fixiert
                    "Betrag": st.column_config.NumberColumn("Betrag (€)", format="%.2f"),
                    "Datum": st.column_config.DateColumn("Zahlungsdatum"),
                    "Typ": st.column_config.SelectboxColumn("Zahlungsart", options=["Überweisung", "Bar", "Dauerauftrag"]),
                    "Notiz": st.column_config.TextColumn("Notiz")
                },
                use_container_width=True,
                hide_index=True,
                key="editor_payments"
            )

            col1, col2 = st.columns([1, 4])
            if col1.button("💾 Änderungen Zahlungen speichern"):
                try:
                    for index, row in edited_pay.iterrows():
                        cur.execute("""
                            UPDATE payments 
                            SET amount = %s, payment_date = %s, payment_type = %s, note = %s
                            WHERE id = %s
                        """, (row['Betrag'], row['Datum'], row['Typ'], row['Notiz'], row['id']))
                    conn.commit()
                    st.success("✅ Zahlungen wurden aktualisiert!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")
            
            # Lösch-Funktion bleibt als 'Notfall-Option'
            with st.expander("🗑️ Eine Zahlung komplett löschen"):
                del_id = st.number_input("ID eingeben", min_value=1, step=1)
                if st.button("Unwiderruflich löschen"):
                    cur.execute("DELETE FROM payments WHERE id = %s", (del_id,))
                    conn.commit()
                    st.rerun()
        else:
            st.info("Keine Zahlungen vorhanden.")

    # --- TAB 2: WOHNUNGEN BEARBEITEN ---
    with tab2:
        st.subheader("Wohnungsdaten anpassen")
        df_ap = pd.read_sql("SELECT id, unit_name as Einheit, area as Flaeche, base_rent as Kaltmiete FROM apartments ORDER BY unit_name", conn)
        
        if not df_ap.empty:
            edited_ap = st.data_editor(
                df_ap,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "Einheit": st.column_config.TextColumn("Bezeichnung"),
                    "Flaeche": st.column_config.NumberColumn("m² Fläche", format="%.2f"),
                    "Kaltmiete": st.column_config.NumberColumn("Basis-Kaltmiete (€)", format="%.2f")
                },
                use_container_width=True,
                hide_index=True,
                key="editor_apartments"
            )

            if st.button("💾 Änderungen Wohnungen speichern"):
                try:
                    for index, row in edited_ap.iterrows():
                        cur.execute("""
                            UPDATE apartments 
                            SET unit_name = %s, area = %s, base_rent = %s
                            WHERE id = %s
                        """, (row['Einheit'], row['Flaeche'], row['Kaltmiete'], row['id']))
                    conn.commit()
                    st.success("✅ Wohnungsdaten aktualisiert!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {e}")
        else:
            st.info("Keine Wohnungen gefunden.")

    cur.close()
    conn.close()