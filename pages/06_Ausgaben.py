import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Haus-Ausgaben erfassen", layout="wide")

def get_conn():
    conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
    conn.set_client_encoding('UTF8')
    return conn

st.title("💸 Haus-Ausgaben (Gesamtkosten)")
st.info("Trage hier die Rechnungen für das gesamte Haus ein. Das System verteilt diese dann automatisch auf die Mieter.")

conn = get_conn()
cur = conn.cursor()

# --- BEREICH 1: NEUE AUSGABE ERFASSEN ---
with st.expander("➕ Neue Rechnung / Kostenart hinzufügen", expanded=True):
    with st.form("expense_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            e_type = st.selectbox("Kostenart (Bezeichnung)", [
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
            e_amount = st.number_input("Gesamtbetrag Haus (€)", min_value=0.0, step=0.01, format="%.2f")
            
        with col2:
            e_year = st.selectbox("Abrechnungsjahr", [2024, 2025, 2026], index=2)
            # Hier sind die Schlüssel exakt wie im PDF
            e_key = st.selectbox("Verteilungsschlüssel (wie im PDF)", [
                ("m² Wohnfläche (z.B. Grundsteuer, Vers.)", "area"), 
                ("Personen / Personentage (z.B. Wasser, Müll)", "persons"), 
                ("Wohneinheiten (z.B. Schornsteinfeger)", "unit"),
                ("Direkte Zuordnung (1/1)", "direct")
            ], format_func=lambda x: x[0])
            
        if st.form_submit_button("Kosten speichern"):
            cur.execute("""
                INSERT INTO operating_expenses (expense_type, amount, expense_year, distribution_key) 
                VALUES (%s, %s, %s, %s)
            """, (e_type, e_amount, e_year, e_key[1]))
            conn.commit()
            st.success(f"✅ {e_type} für {e_year} wurde gespeichert!")
            st.rerun()

st.divider()

# --- BEREICH 2: ÜBERSICHT & LÖSCHEN ---
st.subheader("Eingetragene Gesamtkosten")
selected_year = st.selectbox("Jahr filtern", [2024, 2025, 2026], index=2)

# Daten laden
query = """
    SELECT id, expense_type, amount, distribution_key 
    FROM operating_expenses 
    WHERE expense_year = %s 
    ORDER BY id DESC
"""
df_exp = pd.read_sql(query, conn, params=(selected_year,))

if not df_exp.empty:
    # Namen für die Anzeige verschönern
    df_display = df_exp.copy()
    df_display.columns = ["ID", "Kostenart", "Betrag (€)", "Schlüssel"]
    st.dataframe(df_display, width="stretch")
    
    # Lösch-Option für Tippfehler
    with st.expander("🗑️ Fehlbuchung löschen"):
        del_id = st.selectbox("ID zum Löschen auswählen", df_exp["id"])
        if st.button("Endgültig löschen"):
            cur.execute("DELETE FROM operating_expenses WHERE id = %s", (del_id,))
            conn.commit()
            st.success(f"Eintrag {del_id} gelöscht.")
            st.rerun()
            
    # Summe zur Kontrolle
    total_sum = df_exp["amount"].astype(float).sum()
    st.metric(f"Gesamtkosten Haus {selected_year}", f"{total_sum:.2f} €")
else:
    st.info(f"Noch keine Ausgaben für {selected_year} eingetragen.")

conn.close()