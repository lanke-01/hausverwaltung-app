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

# 1. Mieterliste laden
@st.cache_data(ttl=60)
def get_tenants_dict():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, first_name, last_name FROM tenants")
        rows = cur.fetchall()
        # "Vorname Nachname" als Key, ID als Value
        data = {f"{r[1]} {r[2]}".strip(): r[0] for r in rows}
        cur.close()
        conn.close()
        return data
    except Exception as e:
        st.error(f"Fehler beim Laden der Mieter: {e}")
        return {}

tenants = get_tenants_dict()
tenant_names = ["Nicht erkannt"] + list(tenants.keys())

if not tenants:
    st.warning("Keine Mieter in der Datenbank gefunden.")
    st.stop()

uploaded_file = st.file_uploader("Sparkassen CSV-Datei hochladen", type=["csv"])

if uploaded_file is not None:
    try:
        # CSV einlesen
        df = pd.read_csv(uploaded_file, sep=';', encoding='latin-1', skip_blank_lines=True)
        df.columns = [c.strip() for c in df.columns]
        
        # Betrag finden
        amt_col = next((c for c in ['Betrag', 'Umsatz', 'Betrag (EUR)'] if c in df.columns), None)
        if not amt_col:
            st.error("Spalte 'Betrag' nicht gefunden!")
            st.stop()
            
        df['Betrag_Num'] = df[amt_col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
        df = df[df['Betrag_Num'] > 0] # Nur Haben-Buchungen
            
        payer_col = next((c for c in ['Begünstigter/Zahlungspflichtiger', 'Name Zahlungspflichtiger'] if c in df.columns), None)
        purpose_col = next((c for c in ['Verwendungszweck'] if c in df.columns), None)
        date_col = next((c for c in ['Valutadatum', 'Buchungstag'] if c in df.columns), None)

        # Daten für den Editor aufbereiten
        display_data = []
        for index, row in df.iterrows():
            payer = str(row.get(payer_col, ''))
            purpose = str(row.get(purpose_col, ''))
            amount = row.get('Betrag_Num', 0.0)
            date_val = str(row.get(date_col, ''))
            
            # Automatisches Matching
            detected_name = "Nicht erkannt"
            for full_name in tenants.keys():
                parts = full_name.lower().split()
                # Wenn Vorname oder Nachname im Zahler-Feld auftaucht
                if any(p in payer.lower() for p in parts if len(p) > 2):
                    detected_name = full_name
                    break
            
            display_data.append({
                'Datum': date_val,
                'Zahler': payer,
                'Zweck': purpose,
                'Betrag': amount,
                'Mieter': detected_name
            })

        st.subheader("Vorschau & Zuordnung")
        st.write("Bitte kontrolliere die Spalte 'Mieter' und korrigiere sie falls nötig.")

        # WICHTIG: Der Data Editor
        edited_df_list = st.data_editor(
            display_data,
            column_config={
                "Mieter": st.column_config.SelectboxColumn(
                    "Mieter auswählen", 
                    options=tenant_names,
                    width="medium"
                ),
                "Betrag": st.column_config.NumberColumn(format="%.2f €"),
                "Zahler": st.column_config.TextColumn(width="medium"),
                "Zweck": st.column_config.TextColumn(width="large")
            },
            disabled=["Datum", "Zahler", "Zweck", "Betrag"],
            key="csv_editor",
            use_container_width=True,
            num_rows="fixed"
        )

        if st.button("💾 Alle oben angezeigten Zahlungen jetzt verbuchen"):
            conn = get_conn()
            cur = conn.cursor()
            count = 0
            
            # Wir gehen durch die (eventuell bearbeitete) Liste im Editor
            for row in edited_df_list:
                t_name = row['Mieter']
                
                # Nur verbuchen, wenn ein echter Mieter ausgewählt wurde
                if t_name in tenants:
                    t_id = tenants[t_name]
                    amount = row['Betrag']
                    note = f"CSV-Import: {row['Zweck']} (Zahler: {row['Zahler']})"
                    
                    # Datum parsen
                    try:
                        d_str = row['Datum']
                        if '.' in d_str:
                            fmt = '%d.%m.%Y' if len(d_str) > 8 else '%d.%m.%y'
                            clean_date = datetime.strptime(d_str, fmt).date()
                        else:
                            clean_date = datetime.now().date()
                    except:
                        clean_date = datetime.now().date()
                    
                    # In die Datenbank schreiben (Feld 'note' laut deinem Backup)
                    cur.execute("""
                        INSERT INTO payments (tenant_id, amount, payment_date, note)
                        VALUES (%s, %s, %s, %s)
                    """, (t_id, amount, clean_date, note))
                    count += 1
            
            conn.commit()
            cur.close()
            conn.close()
            
            if count > 0:
                st.success(f"✅ {count} Zahlungen wurden erfolgreich in die Datenbank übernommen!")
                st.balloons()
            else:
                st.warning("Es wurden keine Zahlungen verbucht. Bitte stelle sicher, dass bei den gewünschten Zeilen ein Mieter ausgewählt ist.")

    except Exception as e:
        st.error(f"Verarbeitungsfehler: {e}")