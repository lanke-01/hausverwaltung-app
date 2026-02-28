import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
import re

# --- DATENBANK VERBINDUNG ---
def get_conn():
    conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
    conn.set_client_encoding('UTF8')
    return conn

st.set_page_config(page_title="Intelligente Buchhaltung", layout="wide")
st.title("🏦 Automatisierte Mietzuordnung")

# --- DATABASE LOGIC ---
try:
    conn = get_conn()
    cur = conn.cursor()

    # Tabelle für Keywords sicherstellen
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tenant_keywords (
            id SERIAL PRIMARY KEY, 
            tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE, 
            keyword VARCHAR(255) UNIQUE NOT NULL
        )
    """)
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
except Exception as e:
    st.error(f"Datenbankfehler: {e}")
    st.stop()

# --- UI TABS ---
tab_import, tab_settings = st.tabs(["📥 CSV Import", "⚙️ Suchbegriffe verwalten"])

# --- TAB: EINSTELLUNGEN ---
with tab_settings:
    st.subheader("Suchbegriffe trainieren")
    st.write("Ordne Wörter aus dem Verwendungszweck oder Namen fest einem Mieter zu.")
    
    with st.form("add_keyword"):
        c1, c2 = st.columns(2)
        new_word = c1.text_input("Suchbegriff (z.B. 'Miete OG' oder Teil des Nachnamens)")
        target_tenant = c2.selectbox("Zugehöriger Mieter", list(tenants.keys()))
        if st.form_submit_button("Begriff speichern"):
            if new_word:
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO tenant_keywords (tenant_id, keyword) 
                        VALUES (%s, %s) 
                        ON CONFLICT (keyword) DO NOTHING
                    """, (tenants[target_tenant], new_word))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success(f"'{new_word}' wird jetzt immer {target_tenant} zugeordnet.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")
            else:
                st.warning("Bitte einen Begriff eingeben.")

# --- TAB: IMPORT ---
with tab_import:
    st.info("Unterstützt Sparkassen-Format (Spalte: 'Beguenstigter/Zahlungspflichtiger')")
    uploaded_file = st.file_uploader("Sparkassen CSV hochladen", type=["csv"])

    if uploaded_file:
        try:
            # CSV einlesen mit Berücksichtigung von Sparkassen-Formaten
            df = pd.read_csv(uploaded_file, sep=';', encoding='latin-1', skip_blank_lines=True)
            
            # Spaltennamen säubern (Leerzeichen entfernen)
            df.columns = [c.strip() for c in df.columns]
            
            # 1. Betrags-Spalte finden und konvertieren
            amt_col = next((c for c in ['Betrag', 'Umsatz'] if c in df.columns), None)
            if not amt_col:
                st.error("Konnte Spalte für 'Betrag' oder 'Umsatz' nicht finden.")
                st.stop()
                
            # Konvertierung von "1.200,50" zu Float
            df['Betrag_Num'] = df[amt_col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
            
            # Nur Zahlungseingänge (positive Beträge)
            df = df[df['Betrag_Num'] > 0]
            
            # 2. Relevante Spalten identifizieren (Speziell für Sparkasse angepasst)
            payer_col = next((c for c in ['Beguenstigter/Zahlungspflichtiger', 'Begünstigter/Zahlungspflichtiger', 'Name Zahlungspflichtiger', 'Name'] if c in df.columns), None)
            purpose_col = next((c for c in ['Verwendungszweck', 'VWZ'] if c in df.columns), 'Verwendungszweck')
            date_col = next((c for c in ['Valutadatum', 'Buchungstag', 'Datum'] if c in df.columns), None)

            if not payer_col:
                st.warning(f"Spalte 'Beguenstigter/Zahlungspflichtiger' nicht gefunden. Verfügbare Spalten: {list(df.columns)}")
                st.stop()

            processed_data = []
            for _, row in df.iterrows():
                val_payer = str(row.get(payer_col, '')).strip()
                val_purpose = str(row.get(purpose_col, '')).strip()
                payer_lower = val_payer.lower()
                purpose_lower = val_purpose.lower()
                amount = row['Betrag_Num']
                
                # --- AUTOMATISCHE ZUORDNUNGSLOGIK ---
                match_name = "Nicht erkannt"
                
                # Regel 1: Suche in trainierten Keywords
                for kw, t_id in keywords.items():
                    if kw in payer_lower or kw in purpose_lower:
                        match_name = id_to_name.get(t_id, "Nicht erkannt")
                        break
                
                # Regel 2: Suche nach exakten Mieter-Namen (Fall-back)
                if match_name == "Nicht erkannt":
                    for name in tenants.keys():
                        if name.lower() in payer_lower or name.lower() in purpose_lower:
                            match_name = name
                            break
                
                processed_data.append({
                    'Datum': str(row.get(date_col, '')),
                    'Zahler': val_payer,
                    'Zweck': val_purpose,
                    'Betrag': amount,
                    'Mieter': match_name
                })

            # Vorschau und manuelle Korrektur
            st.subheader("Vorschau & Validierung")
            edited_df = st.data_editor(
                processed_data,
                column_config={
                    "Mieter": st.column_config.SelectboxColumn(
                        "Zuweisung (Manuell anpassen falls nötig)", 
                        options=["Nicht erkannt"] + list(tenants.keys()),
                        width="medium"
                    ),
                    "Betrag": st.column_config.NumberColumn("Betrag (€)", format="%.2f €"),
                    "Zahler": st.column_config.TextColumn("Zahler (aus CSV)", disabled=True),
                    "Zweck": st.column_config.TextColumn("Verwendungszweck", disabled=True)
                },
                use_container_width=True,
                key="accounting_editor"
            )

            # Verbuchen in die Datenbank
            if st.button("🚀 Markierte Zahlungen verbuchen"):
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    count = 0
                    
                    for row in edited_df:
                        if row['Mieter'] in tenants:
                            # Datumsformatierung
                            d_str = str(row['Datum']).strip()
                            try:
                                # Verschiedene Formate probieren
                                if "." in d_str:
                                    parts = d_str.split(".")
                                    if len(parts[2]) == 2: # DD.MM.YY
                                        clean_date = datetime.strptime(d_str, '%d.%m.%y').date()
                                    else: # DD.MM.YYYY
                                        clean_date = datetime.strptime(d_str, '%d.%m.%Y').date()
                                else:
                                    clean_date = datetime.now().date()
                            except:
                                clean_date = datetime.now().date()
                                
                            cur.execute("""
                                INSERT INTO payments (tenant_id, amount, payment_date, note)
                                VALUES (%s, %s, %s, %s)
                            """, (
                                tenants[row['Mieter']], 
                                row['Betrag'], 
                                clean_date, 
                                f"Auto-Import: {row['Zweck'][:50]}..."
                            ))
                            count += 1
                    
                    conn.commit()
                    cur.close()
                    conn.close()
                    
                    st.success(f"✅ {count} Zahlungen erfolgreich im System verbucht!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Fehler beim Verbuchen: {e}")
                    
        except Exception as e:
            st.error(f"Fehler beim Verarbeiten der Datei: {e}")