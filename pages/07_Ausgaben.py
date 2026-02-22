import streamlit as st
import pandas as pd
from database import get_conn  # WICHTIG: Nutzt deine neue zentrale Verbindung

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Haus-Ausgaben erfassen", layout="wide")

st.title("💸 Haus-Ausgaben (Gesamtkosten)")
st.info("Tragen Sie hier die Rechnungen für das gesamte Haus ein. Diese werden basierend auf dem Schlüssel (qm, Personen oder Einheiten) verteilt.")

# Verbindung herstellen
conn = get_conn()

if conn:
    try:
        cur = conn.cursor()

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
                    e_year = st.selectbox("Abrechnungsjahr", [2024, 2025, 2026], index=2)
                    # Schlüssel-Mapping für die Datenbank (Anzeigename, DB-Wert)
                    keys = {
                        "qm Wohnfläche (z.B. Grundsteuer)": "area",
                        "Personen / Personentage (z.B. Wasser)": "persons",
                        "Wohneinheiten (z.B. Schornstein)": "unit",
                        "Direkt (1/1)": "direct"
                    }
                    e_key_label = st.selectbox("Verteilungsschlüssel", options=list(keys.keys()))
                    e_key_val = keys[e_key_label]
                    
                if st.form_submit_button("Ausgabe speichern"):
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
        filter_year = st.selectbox("Jahr filtern", [2024, 2025, 2026], index=2)

        # Daten mit Pandas laden
        query = "SELECT id, expense_type, amount, distribution_key FROM operating_expenses WHERE expense_year = %s ORDER BY id DESC"
        df_exp = pd.read_sql(query, conn, params=(filter_year,))

        if not df_exp.empty:
            # Tabelle verschönern
            df_display = df_exp.copy()
            df_display.columns = ["ID", "Kostenart", "Betrag (Euro)", "Schlüssel-Code"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Summen-Anzeige
            total_sum = df_exp["amount"].sum()
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
        conn.close()
else:
    st.error("Keine Verbindung zur Datenbank möglich. Bitte prüfe die Datei '.env' und 'database.py'!")