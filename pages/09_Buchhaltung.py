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
    keywords_map = {row[0].lower(): row[1] for row in cur.fetchall()}
    
    cur.close()
    conn.close()
except Exception as e:
    st.error(f"Datenbankfehler: {e}")

tab_import, tab_settings = st.tabs(["📥 Bank-Import", "⚙️ Suchbegriffe verwalten"])

# --- TAB: IMPORT ---
with tab_import:
    st.header("Bankumsätze (CSV) hochladen")
    uploaded_file = st.file_uploader("CSV Datei wählen", type=["csv"])

    if uploaded_file:
        try:
            # CSV einlesen (Passe Delimiter bei Bedarf an, z.B. ';' für deutsche Banken)
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
            
            # Spaltenzuordnung (Beispielhaft für viele Banken)
            st.write("Vorschau der hochgeladenen Daten:")
            st.dataframe(df.head(3))
            
            col_date = st.selectbox("Spalte für Datum", df.columns)
            col_amount = st.selectbox("Spalte für Betrag", df.columns)
            col_text = st.selectbox("Spalte für Verwendungszweck / Name", df.columns)

            if st.button("Zuordnung starten"):
                results = []
                for _, row in df.iterrows():
                    purpose = str(row[col_text]).lower()
                    amount = str(row[col_amount]).replace(',', '.')
                    try:
                        amount_float = float(re.sub(r'[^\d.-]', '', amount))
                    except:
                        amount_float = 0.0
                    
                    # Logik: Nur Haben-Buchungen (Eingänge) beachten
                    if amount_float <= 0:
                        continue
                    
                    found_tenant = "Unbekannt"
                    # Suche nach Keywords im Verwendungszweck
                    for kw, t_id in keywords_map.items():
                        if kw in purpose:
                            found_tenant = id_to_name.get(t_id, "Unbekannt")
                            break
                    
                    results.append({
                        "Datum": row[col_date],
                        "Betrag": amount_float,
                        "Zweck": row[col_text],
                        "Mieter": found_tenant
                    })
                
                st.session_state['import_results'] = results
                st.success("Analyse abgeschlossen!")

            if 'import_results' in st.session_state:
                res_df = pd.DataFrame(st.session_state['import_results'])
                st.subheader("Vorschlag zur Verbuchung")
                
                # Filter für unbekannte
                show_only_unknown = st.checkbox("Nur unbekannte Zahlungen anzeigen")
                if show_only_unknown:
                    res_df = res_df[res_df['Mieter'] == "Unbekannt"]
                
                st.data_editor(res_df, key="editor", use_container_width=True)

                if st.button("✅ Alle erkannten Zahlungen speichern"):
                    try:
                        conn = get_conn()
                        cur = conn.cursor()
                        count = 0
                        for row in st.session_state['import_results']:
                            if row['Mieter'] != "Unbekannt":
                                # Datumsformatierung
                                try:
                                    d_str = str(row['Datum'])
                                    clean_date = datetime.now().date() # Fallback
                                    if "." in d_str:
                                        parts = d_str.split(".")
                                        if len(parts[2]) == 2: # DD.MM.YY
                                            clean_date = datetime.strptime(d_str, '%d.%m.%y').date()
                                        else: # DD.MM.YYYY
                                            clean_date = datetime.strptime(d_str, '%d.%m.%Y').date()
                                except: pass
                                
                                cur.execute("""
                                    INSERT INTO payments (tenant_id, amount, payment_date, note)
                                    VALUES (%s, %s, %s, %s)
                                """, (tenants[row['Mieter']], row['Betrag'], clean_date, f"Auto-Import: {row['Zweck'][:50]}"))
                                count += 1
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success(f"{count} Zahlungen verbucht!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Fehler: {e}")

        except Exception as e:
            st.error(f"Datei-Fehler: {e}")

# --- TAB: EINSTELLUNGEN (Keywords) ---
with tab_settings:
    st.subheader("Suchbegriffe trainieren")
    st.write("Hier kannst du Wörter festlegen, die automatisch einem Mieter zugeordnet werden.")
    
    with st.form("new_kw_form"):
        c1, c2 = st.columns(2)
        new_word = c1.text_input("Suchwort (z.B. 'Miete OG', 'Kader', 'Al Masalmeh')")
        target_tenant = c2.selectbox("Zugehöriger Mieter", list(tenants.keys()))
        if st.form_submit_button("Speichern"):
            if new_word:
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO tenant_keywords (tenant_id, keyword) VALUES (%s, %s) ON CONFLICT (keyword) DO NOTHING", 
                                (tenants[target_tenant], new_word))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success(f"'{new_word}' gespeichert.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {e}")
    
    st.divider()
    
    # --- LISTE DER BEGRIFFE ANZEIGEN & LÖSCHEN ---
    st.subheader("Aktive Suchbegriffe")
    try:
        conn = get_conn()
        df_kw = pd.read_sql_query("""
            SELECT tk.id, tk.keyword as "Begriff", t.first_name || ' ' || t.last_name as "Mieter"
            FROM tenant_keywords tk
            JOIN tenants t ON tk.tenant_id = t.id
            ORDER BY t.last_name, tk.keyword
        """, conn)
        conn.close()

        if not df_kw.empty:
            # Tabelle anzeigen
            st.dataframe(df_kw[["Begriff", "Mieter"]], use_container_width=True)
            
            # Bereich zum Löschen
            with st.expander("🗑️ Begriff löschen"):
                del_word = st.selectbox("Welchen Begriff möchtest du entfernen?", df_kw["Begriff"].tolist())
                if st.button("Ausgewählten Begriff löschen"):
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM tenant_keywords WHERE keyword = %s", (del_word,))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success(f"'{del_word}' wurde entfernt.")
                    st.rerun()
        else:
            st.info("Noch keine Suchbegriffe vorhanden.")
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")