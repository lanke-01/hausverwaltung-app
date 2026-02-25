import streamlit as st
import psycopg2
import subprocess
import os
from datetime import datetime

def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Einstellungen & System", layout="wide")
st.title("⚙️ Einstellungen & System")

conn = get_direct_conn()
if not conn:
    st.error("❌ Datenbankverbindung fehlgeschlagen.")
else:
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_settings (
            id SERIAL PRIMARY KEY, name VARCHAR(255), street VARCHAR(255), city VARCHAR(255),
            iban VARCHAR(50), bank_name VARCHAR(255), total_area NUMERIC(10,2) DEFAULT 0, total_occupants INTEGER DEFAULT 0
        )
    """)
    cur.execute("INSERT INTO landlord_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
    conn.commit()

    cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants FROM landlord_settings WHERE id = 1")
    data = cur.fetchone()

    tab1, tab2, tab3 = st.tabs(["🏠 Stammdaten", "🛠️ System & Wartung", "🗄️ Datenbank-Sicherung"])

    with tab1:
        with st.form("settings_form"):
            st.subheader("Vermieter-Details")
            c1, c2 = st.columns(2)
            v_name = c1.text_input("Vermieter Name", value=data[0] or "")
            v_street = c1.text_input("Straße", value=data[1] or "")
            v_city = c1.text_input("PLZ / Ort", value=data[2] or "")
            v_iban = c2.text_input("IBAN", value=data[3] or "")
            v_bank = c2.text_input("Bankname", value=data[4] or "")
            v_area = st.number_input("Gesamtfläche (m²)", value=float(data[5] or 0.0))
            v_pers = st.number_input("Gesamtpersonen", value=int(data[6] or 0))
            if st.form_submit_button("💾 Speichern"):
                cur.execute("UPDATE landlord_settings SET name=%s, street=%s, city=%s, iban=%s, bank_name=%s, total_area=%s, total_occupants=%s WHERE id = 1",
                            (v_name, v_street, v_city, v_iban, v_bank, v_area, v_pers))
                conn.commit()
                st.rerun()

    with tab2:
        st.subheader("🔄 Software-Update")
        if st.button("📥 Update von GitHub erzwingen"):
            try:
                subprocess.run(['git', '-C', '/opt/hausverwaltung', 'fetch', '--all'], check=True)
                subprocess.run(['git', '-C', '/opt/hausverwaltung', 'reset', '--hard', 'origin/main'], check=True)
                subprocess.run(['/usr/bin/systemctl', 'restart', 'hausverwaltung.service'], check=True)
                st.success("Update erfolgreich!")
            except Exception as e:
                st.error(f"Fehler: {e}")

    # --- TAB 3: DATENBANK-SICHERUNG & RESTORE ---
    with tab3:
        st.subheader("🗄️ Datenbank-Verwaltung")
        
        col_back, col_rest = st.columns(2)
        
        with col_back:
            st.markdown("### Sicherung")
            if st.button("🚀 Neues Backup jetzt erstellen", key="btn_new_backup"):
                try:
                    res = subprocess.run(['/bin/bash', '/opt/hausverwaltung/install/backup_db.sh'], capture_output=True, text=True)
                    if res.returncode == 0:
                        st.success("✅ Backup erfolgreich!")
                        st.rerun()
                    else:
                        st.error(f"Fehler: {res.stderr}")
                except Exception as e:
                    st.error(f"Fehler: {e}")

        with col_rest:
            st.markdown("### Wiederherstellung")
            uploaded_file = st.file_uploader("Backup-Datei (.sql) hochladen", type=["sql"])
            if uploaded_file is not None:
                if st.button("⚠️ Backup jetzt einspielen (Restore)"):
                    try:
                        # Datei temporär speichern
                        temp_path = "/tmp/restore_db.sql"
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        # Restore-Befehl ausführen (psql nutzt die trust-Verbindung)
                        env = os.environ.copy()
                        env["PGPASSWORD"] = "" # Nicht nötig bei trust, aber sicherheitshalber
                        res = subprocess.run([
                            'psql', '-h', 'localhost', '-U', 'postgres', '-d', 'hausverwaltung', '-f', temp_path
                        ], capture_output=True, text=True)
                        
                        if res.returncode == 0:
                            st.success("✅ Datenbank wurde erfolgreich wiederhergestellt!")
                            st.balloons()
                        else:
                            st.error(f"Restore-Fehler: {res.stderr}")
                    except Exception as e:
                        st.error(f"Systemfehler: {e}")

        st.divider()
        st.subheader("Vorhandene Dateien auf dem Server")
        backup_path = "/opt/hausverwaltung/backups"
        
        if os.path.exists(backup_path):
            files = sorted([f for f in os.listdir(backup_path) if f.endswith('.sql')], reverse=True)
            for f in files:
                full_path = os.path.join(backup_path, f)
                c_file, c_dl, c_del = st.columns([3, 1, 1])
                c_file.write(f"📄 {f}")
                
                with open(full_path, "rb") as file_content:
                    c_dl.download_button("⬇️", file_content, file_name=f, key=f"dl_{f}")
                
                if c_del.button("🗑️", key=f"del_{f}"):
                    os.remove(full_path)
                    st.rerun()
        else:
            st.error("Backup-Ordner fehlt.")

    cur.close()
    conn.close()