import streamlit as st
import subprocess
import os
from database import get_conn, get_db_config

st.set_page_config(page_title="Einstellungen", layout="wide")
st.title("⚙️ Einstellungen & System")

BACKUP_DIR = "/opt/hausverwaltung/backups"
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

conn = get_conn()
db_conf = get_db_config() # Lädt Daten sicher aus der .env

if conn:
    cur = conn.cursor()
    
    # --- STAMMDATEN-BEREICH (wie bisher) ---
    cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants, total_units FROM landlord_settings WHERE id = 1")
    data = cur.fetchone()
    
    with st.form("settings_form"):
        st.subheader("🏠 Stammdaten & Haus-Konfiguration")
        # ... (deine Form-Eingabefelder wie im Original) ...
        # [Hier den Code deiner bestehenden Form einfügen]
        if st.form_submit_button("Speichern"):
            # Speichere Logik...
            st.success("Gespeichert!")

    st.divider()

    # --- BACKUP & RESTORE ÜBER WEB ---
    st.subheader("💾 Datensicherung (Web-Interface)")
    col_l, col_r = st.columns(2)

    with col_l:
        if st.button("🔴 Backup jetzt erstellen"):
            from datetime import datetime
            fname = f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.sql"
            path = os.path.join(BACKUP_DIR, fname)
            
            env = os.environ.copy()
            env["PGPASSWORD"] = db_conf["password"]
            
            cmd = f"pg_dump -h {db_conf['host']} -U {db_conf['user']} -d {db_conf['dbname']} -f '{path}'"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
            if res.returncode == 0: st.success(f"Backup erstellt: {fname}")
            else: st.error(f"Fehler: {res.stderr}")

    with col_r:
        files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")], reverse=True)
        if files:
            sel = st.selectbox("Backup wählen", files)
            if st.button("⚠️ Restore starten", type="primary"):
                f_path = os.path.join(BACKUP_DIR, sel)
                env = os.environ.copy()
                env["PGPASSWORD"] = db_conf["password"]
                
                with st.spinner("Datenbank wird wiederhergestellt..."):
                    # Verbindungen kicken, damit dropdb nicht blockiert
                    kick = f"psql -h {db_conf['host']} -U {db_conf['user']} -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{db_conf['dbname']}' AND pid <> pg_backend_pid();\""
                    subprocess.run(kick, shell=True, env=env)
                    
                    # Restore ausführen
                    res_cmd = f"dropdb -h {db_conf['host']} -U {db_conf['user']} --if-exists {db_conf['dbname']} && createdb -h {db_conf['host']} -U {db_conf['user']} {db_conf['dbname']} && psql -h {db_conf['host']} -U {db_conf['user']} -d {db_conf['dbname']} -f '{f_path}'"
                    res = subprocess.run(res_cmd, shell=True, capture_output=True, env=env)
                    
                    if res.returncode == 0:
                        st.success("✅ Fertig! Seite wird neu geladen.")
                        st.rerun()
                    else: st.error(f"Fehler: {res.stderr.decode() if isinstance(res.stderr, bytes) else res.stderr}")

    cur.close()
    conn.close()