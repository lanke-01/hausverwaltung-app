import streamlit as st
import pandas as pd
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

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Haus-Ausgaben erfassen", layout="wide")

st.title("💸 Haus-Ausgaben (Gesamtkosten)")
st.info("Tragen Sie hier die Rechnungen für das gesamte Haus ein. Diese werden basierend auf dem Schlüssel (qm, Personen oder Einheiten) verteilt.")

# Verbindung herstellen
conn = get_direct_conn()

if conn:
    try:
        cur = conn.cursor()

        # --- AUTO-REPAIR: Tabelle erstellen falls sie fehlt ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS operating_expenses (
                id SERIAL PRIMARY KEY,
                expense_type VARCHAR(255) NOT NULL,
                amount NUMERIC(10,2) NOT NULL,
                expense_year INTEGER NOT NULL,
                distribution_key VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # --- BEREICH 1: NEUE AUSGABE ERFASSEN ---
        with st.expander("➕ Neue Rechnung hinzufügen", expanded=True):
            with st.form("expense_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    e_type = st.selectbox("Kostenart", [
                        "Grundsteuer", 
                        "Kaltwasser", 
                        "Entwässerung", 
                        "Straßenreinigung und Müll", 
                        "Schornsteinfeger", 
                        "Sach- und Haftpflichtversicherung", 
                        "Allgemeinstrom", 
                        "Hausreinigung",
                        "Gartenpflege",
                        "Sonstiges"
                    ])
                    e_amount = st.number_input("Gesamtbetrag Haus (Euro)", min_value=0.0, step=0.01, format="%.2f")
                    
                with col2:
                    current_year = datetime.now().year
                    e_year = st.selectbox("Abrechnungsjahr", [current_year-1, current_year, current_year+1], index=1)
                    
                    # Schlüssel-Mapping
                    keys = {
                        "qm Wohnfläche (area)": "area",
                        "Personen (persons)": "persons",
                        "Wohneinheiten (unit)": "unit",
                        "Direkt (direct)": "direct"
                    }
                    e_key_label = st.selectbox("Verteilungsschlüssel", options=list(keys.keys()))
                    e_key_val = keys[e_key_label]
                    
                if st.form_submit_button("💾 Ausgabe speichern"):
                    cur.execute("""
                        INSERT INTO operating_expenses (expense_type, amount, expense_year, distribution_key) 
                        VALUES (%s, %s, %s, %s)
                    """, (e_type, e_amount, e_year, e_key_val))
                    conn.commit()
                    st.success(f"✅ {e_type} für {e_year} gespeichert!")
                    st.rerun()

        st.divider()

        # --- BEREICH 2: ÜBERSICHT & FILTER ---
        st.subheader("Eingetragene Gesamtkosten")
        filter_year = st.selectbox("Jahr filtern", [2024, 2025, 2026], index=1)

        # Daten laden (Nutze direkt SQL statt pd.read_sql für stabilere Verbindung)
        cur.execute("""
            SELECT id, expense_type, amount, distribution_key 
            FROM operating_expenses 
            WHERE expense_year = %s 
            ORDER BY id DESC
        """, (filter_year,))
        rows = cur.fetchall()

        if rows:
            # Tabelle anzeigen
            df_display = pd.DataFrame(rows, columns=["ID", "Kostenart", "Betrag (Euro)", "Schlüssel"])
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Summen-Anzeige
            total_sum = df_display["Betrag (Euro)"].sum()
            st.metric(f"Gesamtsumme Haus {filter_year}", f"{total_sum:.2f} Euro")

            # Lösch-Funktion
            with st.expander("🗑️ Eintrag löschen"):
                del_id = st.number_input("ID zum Löschen eingeben", min_value=1, step=1)
                if st.button("Endgültig löschen"):
                    cur.execute("DELETE FROM operating_expenses WHERE id = %s", (del_id,))
                    conn.commit()
                    st.success(f"Eintrag {del_id} wurde entfernt.")
                    st.rerun()
        else:
            st.info(f"Für das Jahr {filter_year} sind noch keine Ausgaben erfasst.")

    except Exception as e:
        st.error(f"Datenbankfehler: {e}")
    finally:
        cur.close()
        conn.close()
else:
    st.error("❌ Keine Verbindung zur Datenbank möglich.")