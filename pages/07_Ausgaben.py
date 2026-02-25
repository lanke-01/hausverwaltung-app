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

# Dictionary für die Übersetzung (Datenbank-Wert : Anzeigename)
DEUTSCHE_SCHLUESSEL = {
    "area": "m² Wohnfläche",
    "persons": "Anzahl Personen",
    "unit": "Wohneinheiten (1/6)",
    "direct": "Direktzuordnung"
}

conn = get_direct_conn()

if conn:
    try:
        cur = conn.cursor()
        
        # --- ÜBERSICHT ---
        st.subheader("Übersicht der Kosten")
        f_year = st.selectbox("Jahr filtern", [2023, 2024, 2025, 2026], index=1)

        cur.execute("SELECT id, expense_type, amount, distribution_key FROM operating_expenses WHERE expense_year = %s ORDER BY id ASC", (f_year,))
        rows = cur.fetchall()

        if rows:
            df = pd.DataFrame(rows, columns=["ID", "Kostenart", "Gesamtbetrag (€)", "Schlüssel"])
            
            # Hier übersetzen wir die Schlüssel von 'area' -> 'm² Wohnfläche' usw.
            df["Schlüssel"] = df["Schlüssel"].map(DEUTSCHE_SCHLUESSEL).fillna(df["Schlüssel"])
            
            st.table(df.set_index('ID'))
            st.metric("Gesamtsumme", f"{df['Gesamtbetrag (€)'].sum():.2f} €")
        else:
            st.info(f"Keine Einträge für {f_year} vorhanden.")

        st.divider()

        # --- AKTIONEN ---
        col_new, col_edit = st.columns(2)

        with col_new:
            st.subheader("➕ Neue Rechnung")
            with st.form("add_form", clear_on_submit=True):
                new_type = st.selectbox("Kategorie", [
                    "Grundsteuer", "Kaltwasser", "Entwässerung", 
                    "Straßenreinigung", "Müllabfuhr", "Hausmeister",
                    "Hausreinigung", "Gartenpflege", "Allgemeinstrom", 
                    "Schornsteinreinigung", "Versicherungen", "Sonstiges"
                ])
                c_name = st.text_input("Name für Sonstiges")
                new_amt = st.number_input("Gesamtbetrag (€)", min_value=0.0, step=0.01)
                
                # Auswahl auf Deutsch
                new_key_label = st.selectbox("Verteilungsschlüssel", list(DEUTSCHE_SCHLUESSEL.values()))
                # Zurück-Übersetzung für die Datenbank
                new_key_db = [k for k, v in DEUTSCHE_SCHLUESSEL.items() if v == new_key_label][0]
                
                if st.form_submit_button("Speichern"):
                    final_n = c_name if new_type == "Sonstiges" and c_name.strip() != "" else new_type
                    cur.execute("INSERT INTO operating_expenses (expense_type, amount, expense_year, distribution_key) VALUES (%s, %s, %s, %s)", 
                                (final_n, new_amt, f_year, new_key_db))
                    conn.commit()
                    st.rerun()

        with col_edit:
            if rows:
                st.subheader("✏️ Korrigieren / Löschen")
                ids = [r[0] for r in rows]
                edit_id = st.selectbox("ID wählen", ids)
                
                cur.execute("SELECT expense_type, amount, distribution_key FROM operating_expenses WHERE id = %s", (edit_id,))
                e_data = cur.fetchone()

                if e_data:
                    with st.form("edit_form"):
                        upd_type = st.text_input("Kostenart Name", value=e_data[0])
                        upd_amt = st.number_input("Betrag (€)", value=float(e_data[1]), step=0.01)
                        
                        # Schlüssel auf Deutsch vorselektieren
                        current_key_de = DEUTSCHE_SCHLUESSEL.get(e_data[2], e_data[2])
                        upd_key_label = st.selectbox("Schlüssel", list(DEUTSCHE_SCHLUESSEL.values()), 
                                                     index=list(DEUTSCHE_SCHLUESSEL.values()).index(current_key_de))
                        upd_key_db = [k for k, v in DEUTSCHE_SCHLUESSEL.items() if v == upd_key_label][0]
                        
                        btn_upd, btn_del = st.columns(2)
                        if btn_upd.form_submit_button("💾 Update"):
                            cur.execute("UPDATE operating_expenses SET expense_type=%s, amount=%s, distribution_key=%s WHERE id=%s", 
                                        (upd_type, upd_amt, upd_key_db, edit_id))
                            conn.commit()
                            st.rerun()
                            
                        if btn_del.form_submit_button("🗑️ Löschen"):
                            cur.execute("DELETE FROM operating_expenses WHERE id = %s", (edit_id,))
                            conn.commit()
                            st.rerun()

    except Exception as e:
        st.error(f"Fehler: {e}")
    finally:
        cur.close()
        conn.close()