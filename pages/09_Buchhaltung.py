import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
import re

def get_conn():
    conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
    conn.set_client_encoding('UTF8')
    return conn

st.set_page_config(page_title="Intelligente Buchhaltung", layout="wide")
st.title("🏦 Automatisierte Mietzuordnung")

# --- DATABASE LOGIC ---
conn = get_conn()
cur = conn.cursor()

# Tabelle für Keywords sicherstellen
cur.execute("CREATE TABLE IF NOT EXISTS tenant_keywords (id SERIAL PRIMARY KEY, tenant_id INTEGER REFERENCES tenants(id), keyword VARCHAR(255) UNIQUE)")
conn.commit()

# Mieter laden
cur.execute("SELECT id, first_name, last_name FROM tenants")
tenants_res = cur.fetchall()
tenants = {f"{r[1]} {r[2]}".strip(): r[0] for r in tenants_res}
id_to_name = {r[0]: f"{r[1]} {r[2]}".strip() for r in tenants_res}

# Keywords laden
cur.execute("SELECT keyword, tenant_id FROM tenant_keywords")
keywords = {row[0].lower(): row[1] for row in cur.fetchall()}

cur.close()
conn.close()

# --- UI TABS ---
tab_import, tab_settings = st.tabs(["📥 CSV Import", "⚙️ Suchbegriffe verwalten"])

with tab_settings:
    st.subheader("Suchbegriffe trainieren")
    st.write("Hier kannst du festlegen, welche Wörter in der CSV automatisch welchem Mieter zugeordnet werden.")
    
    with st.form("add_keyword"):
        c1, c2 = st.columns(2)
        new_word = c1.text_input("Suchbegriff (z.B. Teil des Namens oder 'Miete OG')")
        target_tenant = c2.selectbox("Zugehöriger Mieter", list(tenants.keys()))
        if st.form_submit_button("Begriff speichern"):
            try:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("INSERT INTO tenant_keywords (tenant_id, keyword) VALUES (%s, %s) ON CONFLICT (keyword) DO NOTHING", 
                            (tenants[target_tenant], new_word))
                conn.commit()
                cur.close()
                conn.close()
                st.success(f"'{new_word}' wird jetzt immer {target_tenant} zugeordnet.")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {e}")

with tab_import:
    uploaded_file = st.file_uploader("Sparkassen CSV hochladen", type=["csv"])

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, sep=';', encoding='latin-1', skip_blank_lines=True)
            df.columns = [c.strip() for c in df.columns]
            
            amt_col = next((c for c in ['Betrag', 'Umsatz'] if c in df.columns), None)
            df['Betrag_Num'] = df[amt_col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
            df = df[df['Betrag_Num'] > 0]
            
            payer_col = next((c for c in ['Begünstigter/Zahlungspflichtiger', 'Name Zahlungspflichtiger'] if c in df.columns), None)
            purpose_col = 'Verwendungszweck'
            date_col = 'Valutadatum'

            processed_data = []
            for _, row in df.iterrows():
                payer = str(row.get(payer_col, '')).lower()
                purpose = str(row.get(purpose_col, '')).lower()
                amount = row['Betrag_Num']
                
                # AUTOMATISCHE ZUORDNUNG
                match_name = "Nicht erkannt"
                
                # 1. Check Keywords
                for kw, t_id in keywords.items():
                    if kw in payer or kw in purpose:
                        match_name = id_to_name.get(t_id, "Nicht erkannt")
                        break
                
                # 2. Check direkte Namen (Fall-Back)
                if match_name == "Nicht erkannt":
                    for name in tenants.keys():
                        if name.lower() in payer or name.lower() in purpose:
                            match_name = name
                            break
                
                processed_data.append({
                    'Datum': str(row.get(date_col, '')),
                    'Zahler': row.get(payer_col, ''),
                    'Zweck': row.get(purpose_col, ''),
                    'Betrag': amount,
                    'Mieter': match_name
                })

            st.subheader("Vorschau der Zuordnung")
            edited_df = st.data_editor(
                processed_data,
                column_config={
                    "Mieter": st.column_config.SelectboxColumn("Zuweisung", options=["Nicht erkannt"] + list(tenants.keys())),
                    "Betrag": st.column_config.NumberColumn(format="%.2f €")
                },
                use_container_width=True,
                key="editor_v2"
            )

            if st.button("🚀 Alle erkannten Zahlungen verbuchen"):
                conn = get_conn()
                cur = conn.cursor()
                count = 0
                for row in edited_df:
                    if row['Mieter'] in tenants:
                        # Datum säubern
                        d_str = row['Datum']
                        try:
                            clean_date = datetime.strptime(d_str, '%d.%m.%Y' if len(d_str) > 8 else '%d.%m.%y').date()
                        except:
                            clean_date = datetime.now().date()
                            
                        cur.execute("""
                            INSERT INTO payments (tenant_id, amount, payment_date, note)
                            VALUES (%s, %s, %s, %s)
                        """, (tenants[row['Mieter']], row['Betrag'], clean_date, f"Auto-CSV: {row['Zweck']}"))
                        count += 1
                conn.commit()
                st.success(f"✅ {count} Zahlungen verbucht!")
                st.balloons()
        except Exception as e:
            st.error(f"Fehler: {e}")