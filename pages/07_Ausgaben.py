import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Haus-Ausgaben", layout="wide")
st.title("💸 Haus-Ausgaben (Gesamtkosten)")

DEUTSCHE_SCHLUESSEL = {
    "area": "m² Wohnfläche",
    "persons": "Anzahl Personen",
    "unit": "Wohneinheiten",
    "direct": "Direktzuordnung"
}

conn = get_direct_conn()

if conn:
    try:
        cur = conn.cursor()
        
        # Sicherstellen, dass die Tabelle existiert
        cur.execute("""
            CREATE TABLE IF NOT EXISTS operating_expenses (
                id SERIAL PRIMARY KEY,
                expense_type VARCHAR(255),
                amount NUMERIC(12,2),
                distribution_key VARCHAR(50),
                expense_year INTEGER,
                tenant_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        tab1, tab2, tab3 = st.tabs(["📊 Übersicht & Bearbeitung", "➕ Neue Ausgabe", "📋 Vorjahr übernehmen"])

        # --- TAB 1: ÜBERSICHT & BEARBEITUNG ---
        with tab1:
            st.subheader("Kosten anpassen")
            f_year = st.selectbox("Jahr filtern", [2024, 2025, 2026], index=1)

            cur.execute("""
                SELECT id, expense_type, amount, distribution_key, tenant_id
                FROM operating_expenses 
                WHERE expense_year = %s 
                ORDER BY id ASC
            """, (f_year,))
            rows = cur.fetchall()

            if rows:
                df = pd.DataFrame(rows, columns=["ID", "Kostenart", "Betrag", "Schlüssel", "Mieter_ID"])
                
                edited_df = st.data_editor(
                    df, 
                    column_config={
                        "ID": st.column_config.NumberColumn("ID", disabled=True),
                        "Betrag": st.column_config.NumberColumn("Betrag (€)", format="%.2f"),
                        "Schlüssel": st.column_config.SelectboxColumn("Verteilerschlüssel", options=list(DEUTSCHE_SCHLUESSEL.keys())),
                        "Mieter_ID": st.column_config.NumberColumn("Mieter-ID (-1 = Intern)")
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="expense_editor"
                )

                if st.button("💾 Änderungen speichern"):
                    for _, row in edited_df.iterrows():
                        cur.execute("""
                            UPDATE operating_expenses 
                            SET expense_type = %s, amount = %s, distribution_key = %s, tenant_id = %s
                            WHERE id = %s
                        """, (row['Kostenart'], row['Betrag'], row['Schlüssel'], 
                              int(row['Mieter_ID']) if pd.notnull(row['Mieter_ID']) else None, 
                              row['ID']))
                    conn.commit()
                    st.success("Änderungen übernommen!")
                    st.rerun()
                
                st.divider()
                st.subheader("🗑️ Löschen")
                for index, row in df.iterrows():
                    c1, c2, c3 = st.columns([4, 2, 1])
                    c1.write(f"**{row['Kostenart']}** ({row['Betrag']:.2f} €)")
                    if c3.button("Löschen", key=f"del_{row['ID']}"):
                        cur.execute("DELETE FROM operating_expenses WHERE id = %s", (row['ID'],))
                        conn.commit()
                        st.rerun()
            else:
                st.info(f"Keine Daten für {f_year} gefunden.")

        # --- TAB 2: EINZELNE NEUE AUSGABE ---
        with tab2:
            with st.form("add_expense"):
                e_type = st.text_input("Kostenart")
                e_amount = st.number_input("Gesamtbetrag (€)", step=0.01)
                e_key = st.selectbox("Verteilungsschlüssel", list(DEUTSCHE_SCHLUESSEL.keys()), 
                                    format_func=lambda x: DEUTSCHE_SCHLUESSEL[x])
                e_year = st.number_input("Jahr", value=f_year)
                
                if st.form_submit_button("Speichern"):
                    cur.execute("""
                        INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year)
                        VALUES (%s, %s, %s, %s)
                    """, (e_type, e_amount, e_key, e_year))
                    conn.commit()
                    st.success("Gespeichert!")
                    st.rerun()

        # --- TAB 3: VORJAHR ÜBERNEHMEN ---
        with tab3:
            st.subheader("Kostenarten aus dem Vorjahr kopieren")
            st.write("Dies kopiert alle Positionen (außer Wallbox/Direktkosten) in ein neues Jahr.")
            
            col_from, col_to = st.columns(2)
            source_j = col_from.number_input("Quelljahr", value=2024)
            target_j = col_to.number_input("Zieljahr", value=2025)
            
            if st.button(f"🚀 Daten von {source_j} nach {target_j} kopieren"):
                # Wir filtern tenant_id IS NULL, damit wir keine alten Wallbox-Buchungen mitkopieren
                cur.execute("""
                    SELECT expense_type, amount, distribution_key 
                    FROM operating_expenses 
                    WHERE expense_year = %s AND tenant_id IS NULL
                """, (source_j,))
                old_data = cur.fetchall()
                
                if old_data:
                    for item in old_data:
                        cur.execute("""
                            INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year)
                            VALUES (%s, %s, %s, %s)
                        """, (item[0], item[1], item[2], target_j))
                    conn.commit()
                    st.success(f"Erfolg! {len(old_data)} Positionen wurden für {target_j} angelegt. Du kannst sie jetzt in Tab 1 anpassen.")
                else:
                    st.error(f"Keine Basisdaten in {source_j} gefunden.")

    except Exception as e:
        st.error(f"Fehler: {e}")
    finally:
        cur.close()
        conn.close()