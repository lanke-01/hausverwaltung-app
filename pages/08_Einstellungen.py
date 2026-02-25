import streamlit as st
import psycopg2
import subprocess
import os
from datetime import datetime

# --- VERBINDUNG ---
def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Einstellungen & System", layout="wide")
st.title("⚙️ Einstellungen & System")

# Pfad zum Backup-Ordner
BACKUP_DIR = "/opt/hausverwaltung/backups"

# --- SESSION STATE ---
if "restore_mode" not in st.session_state:
    st.session_state.restore_mode = False

conn = get_direct_conn()

if not conn:
    st.error("❌ Datenbankverbindung fehlgeschlagen.")
else:
    cur = conn.cursor()
    
    # Tabelle sicherstellen
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_settings (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255), street VARCHAR(255), city VARCHAR(255),
            iban VARCHAR(50), bank_name VARCHAR(255), 
            total_area NUMERIC(10,2) DEFAULT 0, total_occupants INTEGER DEFAULT 0
        )
    """)
    cur.execute("INSERT INTO landlord_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
    conn.commit()

    # Daten laden
    cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants FROM landlord_settings WHERE id = 1")
    data = cur.fetchone()

    tab1, tab2, tab3 = st.tabs(["🏠 Stammdaten", "🛠️ System & Wartung", "🗄️ Datenbank-Sicherung"])

    # --- TAB 1: STAMMDATEN ---
    with tab1:
        with st.form("settings_form"):
            st.subheader("Vermieter-Details")
            c1, c2 = st.columns(2)
            v_name = c1.text_input("Vermieter Name", value=data[0] or "")
            v_street = c1.text_input("Straße", value=data[1] or "")
            v_city = c1.text_input("PLZ / Ort", value=data[2] or "")
            v_iban = c2.text_input("IBAN", value=data[3] or "")
            v_bank = c2.text_input("Bankname", value=data[4] or "")
            v_area = st.number_input("Gesamtfläche Haus (m²)", value=float(data[5] or 0.0))
            v_pers = st.number_input("Gesamtpersonen Haus", value=int(data[6] or 0))
            
            if st.form_submit_button("💾 Stammdaten speichern"):
                cur.execute("UPDATE landlord_settings SET name=%s, street=%s, city=%s, iban=%s, bank_name=%s, total_area=%s, total_occupants=%s WHERE id = 1",
                            (v_name, v_street, v_city, v_iban, v_bank, v_area, v_pers))
                conn.commit()
                st.success("Gespeichert!")
                st.rerun()

    # --- TAB 2: SYSTEM (FIXED GIT PULL) ---
    with tab2:
        st.subheader("🔄 Software-Update")
        st.info("Hinweis: Ein Update überschreibt lokale Dateiänderungen im Programmcode.")
        if st.button("📥 Update von GitHub erzwingen"):
            try:
                # 1. Lokale Änderungen verwerfen und neuesten Stand holen
                subprocess.run(['git', '-C', '/opt/hausverwaltung', 'fetch', '--all'], check=True)
                subprocess.run(['git', '-C', '/opt/hausverwaltung', 'reset', '--hard', 'origin/main'], check=True)
                
                st.success("Update erfolgreich! Starte Dienst neu...")
                # 2. Dienst neu starten
                subprocess.run(['systemctl', 'restart', 'hausverwaltung.service'])
            except Exception as e:
                st.error(f"Fehler beim Update: {e}")

    # --- TAB 3: BACKUP & RESTORE ---
    with tab3:
        st.subheader("🗄️ Datenbank-Verwaltung")
        col_back, col_rest = st.columns(2)
        
        with col_back:
            st.markdown("### 1. Sicherung erstellen")
            if st.button("🚀 Neues Backup erzeugen"):
                res = subprocess.run(['/bin/bash', '/opt/hausverwaltung/install/backup_db.sh'], capture_output=True, text=True)
                if res.returncode == 0:
                    st.success("Backup erfolgreich!")
                    st.rerun()

        with col_rest:
            st.markdown("### 2. Wiederherstellung (Upload)")
            
            if not st.session_state.restore_mode:
                uploaded_file = st.file_uploader("SQL-Datei hochladen", type=["sql"])
                if uploaded_file is not None:
                    if st.button("📂 Datei auf Server speichern & Restore vorbereiten"):
                        if not os.path.exists(BACKUP_DIR):
                            os.makedirs(BACKUP_DIR)
                        save_path = os.path.join(BACKUP_DIR, uploaded_file.name)
                        with open(save_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        st.session_state.restore_mode = save_path
                        st.rerun()
            else:
                st.warning(f"Datei geladen: {os.path.basename(st.session_state.restore_mode)}")
                if st.button("⚠️ JETZT RESTORE STARTEN"):
                    try:
                        env = os.environ.copy()
                        env["PGPASSWORD"] = ""
                        # Nutze -U postgres und verzichte auf -h localhost für Socket-Verbindung
                        res = subprocess.run([
                            'psql', '-U', 'postgres', '-d', 'hausverwaltung', '-f', st.session_state.restore_mode
                        ], capture_output=True, text=True, env=env)
                        
                        if res.returncode == 0:
                            st.success("✅ Datenbank erfolgreich wiederhergestellt!")
                            st.balloons()
                            st.session_state.restore_mode = False
                        else:
                            st.error(f"Fehler beim Einspielen: {res.stderr}")
                    except Exception as e:
                        st.error(f"Systemfehler: {e}")
                
                if st.button("❌ Abbrechen"):
                    st.session_state.restore_mode = False
                    st.rerun()

        st.divider()
        st.subheader("Vorhandene Dateien in /opt/hausverwaltung/backups")
        
        if os.path.exists(BACKUP_DIR):
            files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.sql')], reverse=True)
            for f in files:
                full_path = os.path.join(BACKUP_DIR, f)
                c_file, c_dl, c_del = st.columns([3, 1, 1])
                c_file.write(f"📄 {f}")
                
                with open(full_path, "rb") as file_content:
                    c_dl.download_button("⬇️", file_content, file_name=f, key=f"dl_{f}")
                
                if c_del.button("🗑️", key=f"del_{f}"):
                    os.remove(full_path)
                    st.rerun()
        else:
            st.info("Kein Backup-Ordner gefunden.")

    cur.close()
    conn.close()