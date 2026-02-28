import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
import io

# --- DATENBANK VERBINDUNG ---
def get_conn():
    return psycopg2.connect(dbname="hausverwaltung", user="postgres")

st.set_page_config(page_title="Buchhaltung & CSV", layout="wide")
st.title("🏦 Mieteingänge aus CSV zuordnen")

# 1. Mieterliste laden für die Zuordnung
conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT id, name FROM tenants")
tenants = {name: tid for tid, name in cur.fetchall()}
cur.close()
conn.close()

st.info("""
**Anleitung:**
1. Exportiere deine Umsätze bei der Sparkasse als **CSV-Datei**.
2. Lade die Datei hier hoch.
3. Das System versucht, den Mieter anhand des Namens im Feld 'Begünstigter/Zahlungspflichtiger' automatisch zu finden.
""")

uploaded_file = st.file_uploader("Sparkassen CSV-Datei hochladen", type=["csv"])

if uploaded_file is not None:
    try:
        # Sparkassen CSV nutzt oft Semikolon und latin-1 Encoding
        df = pd.read_csv(uploaded_file, sep=';', encoding='latin-1', skip_blank_lines=True)
        
        # Wichtige Spalten bei der Sparkasse (Standard):
        # 'Begünstigter/Zahlungspflichtiger', 'Verwendungszweck', 'Betrag', 'Valutadatum'
        
        # Bereinigung: Wir brauchen nur Zeilen mit positivem Betrag (Haben-Buchungen)
        # Sparkasse formatiert Beträge oft mit Komma als String "1.250,50"
        if 'Betrag' in df.columns:
            df['Betrag_Clean'] = df['Betrag'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
            df = df[df['Betrag_Clean'] > 0] # Nur Eingänge
        
        st.subheader("Gefundene Zahlungseingänge")
        
        results = []
        for index, row in df.iterrows():
            payer = str(row.get('Begünstigter/Zahlungspflichtiger', ''))
            purpose = str(row.get('Verwendungszweck', ''))
            amount = row.get('Betrag_Clean', 0.0)
            date_str = str(row.get('Valutadatum', datetime.now().strftime('%d.%m.%y')))
            
            # Automatische Suche nach Mietername im Payer-Feld
            detected_tenant_id = None
            detected_name = "Nicht erkannt"
            
            for t_name, t_id in tenants.items():
                if t_name.lower() in payer.lower() or payer.lower() in t_name.lower():
                    detected_tenant_id = t_id
                    detected_name = t_name
                    break
            
            results.append({
                'Datum': date_str,
                'Zahler': payer,
                'Zweck': purpose,
                'Betrag': amount,
                'Zugeordneter Mieter': detected_name,
                'tenant_id': detected_tenant_id
            })

        # Tabelle zur Kontrolle anzeigen
        edit_df = st.data_editor(
            results,
            column_config={
                "Zugeordneter Mieter": st.column_config.SelectboxColumn(
                    "Mieter wählen",
                    options=list(tenants.keys()),
                    help="Wähle den Mieter manuell aus, falls nicht erkannt"
                )
            },
            disabled=["Datum", "Zahler", "Zweck", "Betrag"],
            key="payment_editor"
        )

        if st.button("✅ Markierte Zahlungen verbuchen"):
            conn = get_conn()
            cur = conn.cursor()
            count = 0
            
            for row in edit_df:
                t_name = row['Zugeordneter Mieter']
                if t_name in tenants:
                    t_id = tenants[t_name]
                    # Datum umwandeln (Sparkasse DD.MM.YY)
                    try:
                        clean_date = datetime.strptime(row['Datum'], '%d.%m.%y').date()
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
        st.error(f"Fehler beim Lesen der CSV: {e}")
        st.info("Hinweis: Stellen Sie sicher, dass die CSV das Standard-Format der Sparkasse hat.")