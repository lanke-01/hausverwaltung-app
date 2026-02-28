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

# 1. Mieterliste laden (Spaltenname an deine DB angepasst: tenant_name)
try:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, tenant_name FROM tenants")
    # Wir erstellen ein Dictionary { Name: ID }
    tenants = {row[1]: row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()
except Exception as e:
    st.error(f"Fehler beim Laden der Mieter: {e}")
    tenants = {}

st.info("""
**Anleitung:**
1. Exportiere deine Umsätze bei der Sparkasse als **CSV-Datei**.
2. Lade die Datei hier hoch. Das System erkennt automatisch Zahlungseingänge.
""")

uploaded_file = st.file_uploader("Sparkassen CSV-Datei hochladen", type=["csv"])

if uploaded_file is not None:
    try:
        # Sparkassen CSV nutzt oft Semikolon und latin-1
        df = pd.read_csv(uploaded_file, sep=';', encoding='latin-1', skip_blank_lines=True)
        
        # Spaltennamen normalisieren (Sparkasse variiert manchmal zwischen 'Betrag' und 'Umsatz')
        df.columns = [c.strip() for c in df.columns]
        
        # Betrag-Spalte finden und säubern
        amt_col = None
        for c in ['Betrag', 'Umsatz', 'Betrag (EUR)']:
            if c in df.columns:
                amt_col = c
                break
        
        if amt_col:
            # Deutsche Zahlenformate (1.000,50) in Floats umwandeln
            df['Betrag_Clean'] = df[amt_col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
            # Nur Zahlungseingänge (Haben)
            df = df[df['Betrag_Clean'] > 0]
        else:
            st.error("Spalte 'Betrag' nicht in CSV gefunden!")
            st.stop()
            
        st.subheader("Gefundene Zahlungseingänge")
        
        results = []
        # Identifiziere Spalten für Name und Zweck
        payer_col = next((c for c in ['Begünstigter/Zahlungspflichtiger', 'Name Zahlungspflichtiger'] if c in df.columns), None)
        purpose_col = next((c for c in ['Verwendungszweck', 'Verwendungszweck 1'] if c in df.columns), None)
        date_col = next((c for c in ['Valutadatum', 'Buchungstag'] if c in df.columns), None)

        for index, row in df.iterrows():
            payer = str(row.get(payer_col, '')) if payer_col else ""
            purpose = str(row.get(purpose_col, '')) if purpose_col else ""
            amount = row.get('Betrag_Clean', 0.0)
            date_val = str(row.get(date_col, datetime.now().strftime('%d.%m.%y')))
            
            # Automatische Suche nach Mietername
            detected_name = "Nicht erkannt"
            for t_name in tenants.keys():
                if t_name.lower() in payer.lower() or payer.lower() in t_name.lower() or t_name.lower() in purpose.lower():
                    detected_name = t_name
                    break
            
            results.append({
                'Datum': date_val,
                'Zahler': payer,
                'Zweck': purpose,
                'Betrag': amount,
                'Zugeordneter Mieter': detected_name
            })

        # Tabelle zur Kontrolle anzeigen
        edit_df = st.data_editor(
            results,
            column_config={
                "Zugeordneter Mieter": st.column_config.SelectboxColumn(
                    "Mieter wählen",
                    options=list(tenants.keys()),
                    help="Wähle den Mieter manuell aus"
                ),
                "Betrag": st.column_config.NumberColumn(format="%.2f €")
            },
            disabled=["Datum", "Zahler", "Zweck", "Betrag"],
            key="payment_editor",
            use_container_width=True
        )

        if st.button("✅ Markierte Zahlungen verbuchen"):
            conn = get_conn()
            cur = conn.cursor()
            count = 0
            
            for row in edit_df:
                t_name = row['Zugeordneter Mieter']
                if t_name in tenants:
                    t_id = tenants[t_name]
                    # Datum parsen (versucht verschiedene Sparkassen Formate)
                    try:
                        d_str = row['Datum']
                        if len(d_str) > 8: # DD.MM.YYYY
                            clean_date = datetime.strptime(d_str, '%d.%m.%Y').date()
                        else: # DD.MM.YY
                            clean_date = datetime.strptime(d_str, '%d.%m.%y').date()
                    except:
                        clean_date = datetime.now().date()
                    
                    cur.execute("""
                        INSERT INTO payments (tenant_id, amount, payment_date, remarks)
                        VALUES (%s, %s, %s, %s)
                    """, (t_id, row['Betrag'], clean_date, f"CSV-Import: {row['Zweck']}"))
                    count += 1
            
            conn.commit()
            cur.close()
            conn.close()
            st.success(f"Erfolgreich {count} Zahlungen verbucht!")
            st.balloons()

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten: {e}")