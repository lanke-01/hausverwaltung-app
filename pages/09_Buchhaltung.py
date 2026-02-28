import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
import io

# --- DATENBANK VERBINDUNG ---
def get_conn():
    conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
    conn.set_client_encoding('UTF8')
    return conn

st.set_page_config(page_title="Buchhaltung & CSV", layout="wide")
st.title("🏦 Mieteingänge aus CSV zuordnen")

# 1. Mieterliste laden (Kombiniert first_name und last_name aus deinem Backup)
@st.cache_data(ttl=60)
def get_tenants_dict():
    conn = get_conn()
    cur = conn.cursor()
    try:
        # Abfrage basierend auf deiner test.sql Struktur
        cur.execute("SELECT id, first_name, last_name FROM tenants")
        rows = cur.fetchall()
        # Wir bauen einen Full Name für die Anzeige: "Vorname Nachname"
        data = {f"{r[1]} {r[2]}".strip(): r[0] for r in rows}
        cur.close()
        conn.close()
        return data
    except Exception as e:
        st.error(f"Fehler beim Laden der Mieter: {e}")
        return {}

tenants = get_tenants_dict()

if not tenants:
    st.warning("Keine Mieter in der Datenbank gefunden.")
    st.stop()

st.info("Laden Sie Ihre Sparkassen-CSV hoch. Das System sucht in 'Zahlungspflichtiger' nach den Mieter-Namen.")

uploaded_file = st.file_uploader("Sparkassen CSV-Datei hochladen", type=["csv"])

if uploaded_file is not None:
    try:
        # CSV einlesen (Sparkasse Standard)
        df = pd.read_csv(uploaded_file, sep=';', encoding='latin-1', skip_blank_lines=True)
        df.columns = [c.strip() for c in df.columns]
        
        # Betrag finden und in Zahl umwandeln
        amt_col = next((c for c in ['Betrag', 'Umsatz', 'Betrag (EUR)'] if c in df.columns), None)
        if not amt_col:
            st.error("Spalte 'Betrag' nicht gefunden!")
            st.stop()
            
        df['Betrag_Num'] = df[amt_col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
        df = df[df['Betrag_Num'] > 0] # Nur Eingänge
            
        results = []
        # Spalten für Details identifizieren
        payer_col = next((c for c in ['Begünstigter/Zahlungspflichtiger', 'Name Zahlungspflichtiger'] if c in df.columns), None)
        purpose_col = next((c for c in ['Verwendungszweck'] if c in df.columns), None)
        date_col = next((c for c in ['Valutadatum', 'Buchungstag'] if c in df.columns), None)

        for index, row in df.iterrows():
            payer = str(row.get(payer_col, '')) if payer_col else ""
            purpose = str(row.get(purpose_col, '')) if purpose_col else ""
            amount = row.get('Betrag_Num', 0.0)
            date_val = str(row.get(date_col, ''))
            
            # Matching: Prüfe ob Vorname oder Nachname im Payer-Text vorkommen
            detected_name = "Nicht erkannt"
            for full_name in tenants.keys():
                # Wir splitten den Namen um auch Teil-Treffer (nur Nachname) zu finden
                parts = full_name.lower().split()
                if any(p in payer.lower() for p in parts if len(p) > 2):
                    detected_name = full_name
                    break
            
            results.append({
                'Datum': date_val,
                'Zahler': payer,
                'Zweck': purpose,
                'Betrag': amount,
                'Zugeordneter Mieter': detected_name
            })

        # Anzeige im Data Editor
        edit_df = st.data_editor(
            results,
            column_config={
                "Zugeordneter Mieter": st.column_config.SelectboxColumn("Mieter auswählen", options=list(tenants.keys())),
                "Betrag": st.column_config.NumberColumn(format="%.2f €")
            },
            disabled=["Datum", "Zahler", "Zweck", "Betrag"],
            key="csv_editor",
            use_container_width=True
        )

        if st.button("💾 Alle markierten Buchungen speichern"):
            conn = get_conn()
            cur = conn.cursor()
            count = 0
            for row in edit_df:
                t_name = row['Zugeordneter Mieter']
                if t_name in tenants:
                    t_id = tenants[t_name]
                    # Einfaches Datum-Handling
                    try:
                        d_str = row['Datum']
                        dt = datetime.strptime(d_str, '%d.%m.%Y' if '.' in d_str and len(d_str)>8 else '%d.%m.%y')
                        clean_date = dt.date()
                    except:
                        clean_date = datetime.now().date()
                    
                    cur.execute("""
                        INSERT INTO payments (tenant_id, amount, payment_date, note)
                        VALUES (%s, %s, %s, %s)
                    """, (t_id, row['Betrag'], clean_date, f"CSV: {row['Zweck']}"))
                    count += 1
            conn.commit()
            st.success(f"{count} Zahlungen verbucht!")
            st.balloons()
            st.rerun()

    except Exception as e:
        st.error(f"Verarbeitungsfehler: {e}")