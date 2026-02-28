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

        # --- ÜBERSICHT & BEARBEITUNG ---
        st.subheader("Übersicht der Kosten")
        f_year = st.selectbox("Jahr filtern", [2024, 2025, 2026], index=1) # 2025 als Standard

        # Daten für den Editor laden
        cur.execute("""
            SELECT id, expense_type, amount, distribution_key, tenant_id
            FROM operating_expenses 
            WHERE expense_year = %s 
            ORDER BY id ASC
        """, (f_year,))
        rows = cur.fetchall()

        if rows:
            df = pd.DataFrame(rows, columns=["ID", "Kostenart", "Betrag", "Schlüssel", "Mieter_ID"])
            
            # Interaktiver Editor für schnelle Korrekturen
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

            c1, c2 = st.columns([1, 4])
            if c1.button("💾 Änderungen speichern"):
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

            # --- EINZELNE EINTRÄGE LÖSCHEN ---
            st.divider()
            st.subheader("🗑️ Einträge endgültig löschen")
            # Wir zeigen eine Liste mit Lösch-Buttons für die "Geister-Einträge"
            for index, row in df.iterrows():
                col_name, col_val, col_tid, col_btn = st.columns([3, 2, 2, 1])
                # Markierung für den User, was gelöscht werden sollte
                warn_text = "⚠️ KEINE ZUORDNUNG" if pd.isnull(row['Mieter_ID']) and row['Kostenart'] == 'Wallbox-Strom' else ""
                
                col_name.write(f"**{row['Kostenart']}** {warn_text}")
                col_val.write(f"{row['Betrag']:.2f} €")
                col_tid.write(f"ID: {row['Mieter_ID'] if pd.notnull(row['Mieter_ID']) else 'Haus'}")
                
                if col_btn.button("Löschen", key=f"del_{row['ID']}"):
                    cur.execute("DELETE FROM operating_expenses WHERE id = %s", (row['ID'],))
                    conn.commit()
                    st.warning(f"Eintrag {row['ID']} gelöscht.")
                    st.rerun()

        else:
            st.info(f"Noch keine Ausgaben für {f_year} erfasst.")

        st.divider()

        # --- NEUE AUSGABE HINZUFÜGEN (Bleibt wie gehabt) ---
        with st.expander("➕ Neue Ausgabe hinzufügen"):
            with st.form("add_expense"):
                e_type = st.text_input("Kostenart (z.B. Grundsteuer, Wallbox...)")
                e_amount = st.number_input("Gesamtbetrag (€)", step=0.01)
                e_key = st.selectbox("Verteilungsschlüssel", list(DEUTSCHE_SCHLUESSEL.keys()), 
                                    format_func=lambda x: DEUTSCHE_SCHLUESSEL[x])
                
                cur.execute("SELECT id, first_name, last_name FROM tenants WHERE move_out IS NULL")
                tenants = {f"{t[1]} {t[2]}": t[0] for t in cur.fetchall()}
                target_tenant = st.selectbox("Nur für Mieter (Direktzuordnung)", ["Keine / Alle"] + list(tenants.keys()))
                
                if st.form_submit_button("Speichern"):
                    t_id = tenants[target_tenant] if target_tenant != "Keine / Alle" else None
                    cur.execute("""
                        INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year, tenant_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (e_type, e_amount, e_key, f_year, t_id))
                    conn.commit()
                    st.success("Gespeichert!")
                    st.rerun()

    except Exception as e:
        st.error(f"Fehler: {e}")
    finally:
        cur.close()
        conn.close()