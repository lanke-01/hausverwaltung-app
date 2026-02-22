import streamlit as st
import subprocess
import os
import shutil
from database import get_conn, get_db_config
from datetime import datetime

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Einstellungen", layout="wide")
st.title("⚙️ Einstellungen & System")

BACKUP_DIR = "/opt/hausverwaltung/backups"
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

conn = get_conn()
db_conf = get_db_config() # Nutzt die sichere Methode aus database.py

if conn:
    cur = conn.cursor()
    
    # --- AUTOMATISCHES DATENBANK-UPDATE ---
    try:
        cur.execute("ALTER TABLE landlord_settings ADD COLUMN IF NOT EXISTS total_area NUMERIC(10,2) DEFAULT 0.00")
        cur.execute("ALTER TABLE landlord_settings ADD COLUMN IF NOT EXISTS total_occupants INTEGER DEFAULT 1")
        cur.execute("ALTER TABLE landlord_settings ADD COLUMN IF NOT EXISTS total_units INTEGER DEFAULT 1")
        conn.commit()
    except Exception:
        conn.rollback()

    # --- 1. STAMMDATEN LADEN ---
    cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants, total_units FROM landlord_settings WHERE id = 1")
    data = cur.fetchone()
    
    if not data:
        cur.execute("INSERT INTO landlord_settings (id, name) VALUES (1, 'Vermieter Name')")
        conn.commit()
        st.rerun()

    with st.form("settings_form"):
        st.subheader("🏠 Stammdaten & Haus-Konfiguration")
        col_a, col_b = st.columns(2)
        with col_a:
            name = st.text_input("Vermieter Name", value=data[0] or "")
            street = st.text_input("Straße, Nr.", value=data[1] or "")
            city = st.text_input("PLZ, Ort", value=data[2] or "")
        with col_b:
            iban = st.text_input("IBAN", value=data[3] or "")
            bank = st.text_input("Bankname", value=data[4] or "")

        st.write("---")
        c1, c2, c3 = st.columns(3)
        t_area = c1.number_input("Gesamtfläche Haus (m²)", value=float(data[5] or 0.0), step=0.01)
        t_occ = c2.number_input("Gesamt-Personen Haus", value=int(data[6] or 1), step=1)
        t_units = c3.number_input("Anzahl Wohneinheiten", value=int(data[7] or 1), step=1)

        if st.form_submit_button("Stammdaten speichern"):
            cur.execute("""UPDATE landlord_settings SET name=%s, street=%s, city=%s, iban=%s, bank_name=%s, 
                           total_area=%s, total_occupants=%s, total_units=%s WHERE id = 1""",
                        (name, street, city, iban, bank, t_area, t_occ, t_units))
            conn.commit()
            st.success("✅ Stammdaten gespeichert!")

    st.divider()

    # --- 2. BACKUP & RESTORE ---
    st.subheader("💾 Datensicherung (Backup & Restore)")
    tab_create, tab_upload, tab_restore = st.tabs(["Backup erstellen", "Backup hochladen", "Wiederherstellen"])

    with tab_create:
        if st.button("🔴 Server-Backup jetzt erstellen"):
            fname = f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.sql"
            path = os.path.join(BACKUP_DIR, fname)
            env = os.environ.copy()
            env["PGPASSWORD"] = db_conf["password"]
            cmd = f"pg_dump -h {db_conf['host']} -U {db_conf['user']} -d {db_conf['dbname']} -f '{path}'"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
            if res.returncode == 0: st.success(f"Backup erstellt: {fname}")
            else: st.error(f"Fehler: {res.stderr}")

    with tab_upload:
        uploaded_file = st.file_uploader("Backup-Datei (.sql) wählen", type=["sql"])
        if uploaded_file is not None:
            if st.button("Datei auf Server speichern"):
                save_path = os.path.join(BACKUP_DIR, uploaded_file.name)
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"✅ {uploaded_file.name} bereit zum Wiederherstellen.")

    with tab_restore:
        files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")], reverse=True)
        if files:
            selected_backup = st.selectbox("Wähle ein Backup", files)
            if st.button("⚠️ Restore jetzt starten", type="primary"):
                f_path = os.path.join(BACKUP_DIR, selected_backup)
                env = os.environ.copy()
                env["PGPASSWORD"] = db_conf["password"]
                with st.spinner("Wiederherstellung läuft..."):
                    kick = f"psql -h {db_conf['host']} -U {db_conf['user']} -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{db_conf['dbname']}' AND pid <> pg_backend_pid();\""
                    subprocess.run(kick, shell=True, env=env)
                    res_cmd = f"dropdb -h {db_conf['host']} -U {db_conf['user']} --if-exists {db_conf['dbname']} && createdb -h {db_conf['host']} -U {db_conf['user']} {db_conf['dbname']} && psql -h {db_conf['host']} -U {db_conf['user']} -d {db_conf['dbname']} -f '{f_path}'"
                    res = subprocess.run(res_cmd, shell=True, capture_output=True, env=env)
                    if res.returncode == 0:
                        st.success("✅ Datenbank wiederhergestellt!")
                        st.rerun()
                    else: st.error(f"Fehler: {res.stderr.decode() if isinstance(res.stderr, bytes) else res.stderr}")
        else:
            st.info("Keine Backups vorhanden.")

    st.divider()

    # --- 3. SOFTWARE-UPDATE (GIT PULL) ---
    st.subheader("🚀 System-Update")
    st.write("Lade die neuesten Funktionen direkt von GitHub.")
    if st.button("Update von GitHub laden"):
        try:
            # -C /opt/hausverwaltung führt den git Befehl im richtigen Verzeichnis aus
            update_result = subprocess.run(["git", "-C", "/opt/hausverwaltung", "pull"], capture_output=True, text=True)
            if "Already up to date" in update_result.stdout:
                st.info("ℹ️ Die Software ist bereits auf dem neuesten Stand.")
            else:
                st.success("✅ Update erfolgreich heruntergeladen!")
                # Optional: Neustart des Services (benötigt sudo-Rechte für den App-User)
                subprocess.run(["sudo", "systemctl", "restart", "hausverwaltung.service"])
                st.info("System wird neu gestartet...")
        except Exception as e:
            st.error(f"Update fehlgeschlagen: {e}")

    cur.close()
    conn.close()
else:
    st.error("❌ Keine Datenbankverbindung.")