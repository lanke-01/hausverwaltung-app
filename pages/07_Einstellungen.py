import streamlit as st
import subprocess
import os
from database import get_conn, DB_CONFIG

st.set_page_config(page_title="Einstellungen", layout="wide")
st.title("⚙️ Einstellungen & Backup")

BACKUP_DIR = "/opt/hausverwaltung/backups"

# --- RECHTS-UPDATE & STAMMDATEN (Teil gekürzt für Übersicht) ---
# ... (Deine Stammdaten-Form bleibt wie sie ist) ...

st.divider()

# --- BACKUP-LOGIK FÜR DIE WEB-OBERFLÄCHE ---
st.subheader("💾 Datensicherung & Restore")

col1, col2 = st.columns(2)

with col1:
    if st.button("🔴 Backup jetzt erstellen"):
        from datetime import datetime
        fname = f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.sql"
        path = os.path.join(BACKUP_DIR, fname)
        # Nutzt die Config aus database.py
        cmd = f"PGPASSWORD='{DB_CONFIG['password']}' pg_dump -h {DB_CONFIG['host']} -U {DB_CONFIG['user']} -d {DB_CONFIG['dbname']} -f {path}"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            st.success(f"Backup erstellt: {fname}")
        else:
            st.error(f"Fehler: {res.stderr}")

with col2:
    if os.path.exists(BACKUP_DIR):
        files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")], reverse=True)
        sel = st.selectbox("Backup zum Einspielen wählen", files)
        
        if st.button("⚠️ Restore starten (Web)", type="primary"):
            f_path = os.path.join(BACKUP_DIR, sel)
            db = DB_CONFIG['dbname']
            user = DB_CONFIG['user']
            pw = DB_CONFIG['password']
            
            with st.spinner("Datenbank wird überschrieben..."):
                # 1. Alle anderen Verbindungen kicken (wichtig für dropdb)
                kick_cmd = f"PGPASSWORD='{pw}' psql -U {user} -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{db}' AND pid <> pg_backend_pid();\""
                subprocess.run(kick_cmd, shell=True)
                
                # 2. Löschen, Neu erstellen, Einspielen
                restore_cmd = f"PGPASSWORD='{pw}' dropdb --if-exists -U {user} {db} && PGPASSWORD='{pw}' createdb -U {user} {db} && PGPASSWORD='{pw}' psql -U {user} -d {db} -f {f_path}"
                
                res = subprocess.run(restore_cmd, shell=True, capture_output=True, text=True)
                if res.returncode == 0:
                    st.success("✅ Restore erfolgreich!")
                    st.rerun()
                else:
                    st.error(f"Fehler: {res.stderr}")