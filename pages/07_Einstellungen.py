import streamlit as st
import subprocess
import os
import shutil
from database import get_conn
from datetime import datetime

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Einstellungen", layout="wide")
st.title("⚙️ Vermieter-Einstellungen & System")

conn = get_conn()

def cleanup_old_backups(backup_dir, max_files=5):
    """Löscht die ältesten Backups, wenn mehr als max_files vorhanden sind."""
    try:
        if not os.path.exists(backup_dir):
            return
        files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith(".sql")]
        files.sort(key=os.path.getmtime)
        
        while len(files) > max_files:
            oldest_file = files.pop(0)
            os.remove(oldest_file)
            st.info(f"🗑️ Automatisches Aufräumen: {os.path.basename(oldest_file)} wurde entfernt.")
    except Exception as e:
        st.error(f"Fehler beim Aufräumen: {e}")

if conn:
    cur = conn.cursor()
    
    # 1. STAMMDATEN LADEN (Inklusive Gesamtfläche für korrekte Abrechnung)
    # Falls die Spalte 'total_area' noch nicht existiert, fangen wir das ab
    try:
        cur.execute("SELECT name, street, city, iban, bank_name, total_area FROM landlord_settings WHERE id = 1")
        data = cur.fetchone()
    except:
        # Falls total_area fehlt, Tabelle erweitern
        cur.execute("ALTER TABLE landlord_settings ADD COLUMN IF NOT EXISTS total_area NUMERIC(10,2) DEFAULT 0.00")
        conn.commit()
        cur.execute("SELECT name, street, city, iban, bank_name, total_area FROM landlord_settings WHERE id = 1")
        data = cur.fetchone()
    
    if not data:
        data = ("Name angeben", "", "", "", "", 0.00)
    
    with st.form("settings_form"):
        st.subheader("🏠 Stammdaten & Haus-Konfiguration")
        st.write("Diese Daten sind die Basis für die anteilige Berechnung der Nebenkosten.")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Vermieter Name / Firma", value=data[0])
            street = st.text_input("Straße & Hausnummer", value=data[1])
            city = st.text_input("PLZ & Ort", value=data[2])
            # NEU: Gesamtfläche des Hauses (wichtig für Beispiel-PDF Logik)
            total_area = st.number_input("Gesamtwohnfläche des Hauses (m²)", value=float(data[5] or 0.0), step=0.01)
            
        with col2:
            bank_name = st.text_input("Bankbezeichnung", value=data[4])
            iban = st.text_input("IBAN", value=data[3])
        
        if st.form_submit_button("Einstellungen Speichern"):
            try:
                cur.execute("""
                    UPDATE landlord_settings 
                    SET name=%s, street=%s, city=%s, iban=%s, bank_name=%s, total_area=%s, updated_at=NOW()
                    WHERE id = 1
                """, (name, street, city, iban, bank_name, total_area))
                conn.commit()
                st.success("✅ Stammdaten und Hausfläche gespeichert!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")

    st.divider()

    # 2. DATENSICHERUNG (BACKUP, RESTORE, UPLOAD & DELETE)
    st.subheader("💾 Datensicherung & Wiederherstellung")
    col_b1, col_b2 = st.columns([1, 2])
    
    with col_b1:
        st.write("✨ **Aktionen**")
        if st.button("🔴 Backup jetzt erstellen"):
            backup_dir = "/opt/hausverwaltung/backups"
            backup_script = "/opt/hausverwaltung/install/backup_db.sh"
            if os.path.exists(backup_script):
                result = subprocess.run([backup_script], capture_output=True, text=True)
                if result.returncode == 0:
                    st.success("Backup erstellt!")
                    cleanup_old_backups(backup_dir, max_files=5)
                    st.rerun()
                else:
                    st.error(f"Fehler: {result.stderr}")
            else:
                st.error("Backup-Skript nicht gefunden!")
        
        st.write("---")
        uploaded_file = st.file_uploader("📤 Backup hochladen (.sql)", type=["sql"])
        if uploaded_file:
            backup_dir = "/opt/hausverwaltung/backups"
            if not os.path.exists(backup_dir): os.makedirs(backup_dir)
            with open(os.path.join(backup_dir, uploaded_file.name), "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("Hochgeladen!")
            cleanup_old_backups(backup_dir, max_files=5)
            st.rerun()

    with col_b2:
        st.write("📂 **Backup-Verwaltung (Limit: 5)**")
        backup_dir = "/opt/hausverwaltung/backups"
        if os.path.exists(backup_dir):
            files = [f for f in os.listdir(backup_dir) if f.endswith(".sql")]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)
            for f in files:
                file_path = os.path.join(backup_dir, f)
                st.write(f"---")
                c1, c2, c3, c4 = st.columns([2, 0.8, 0.8, 0.8])
                c1.text(f"📄 {f}")
                with open(file_path, "rb") as fb:
                    c2.download_button("💾", fb, file_name=f, key=f"dl_{f}")
                if c3.button("🔄", key=f"res_{f}"): st.session_state[f"conf_res_{f}"] = True
                if c4.button("🗑️", key=f"del_{f}"): st.session_state[f"conf_del_{f}"] = True

                if st.session_state.get(f"conf_res_{f}"):
                    if st.button(f"🔥 JA, RESTORE {f}", key=f"fire_{f}"):
                        subprocess.run(f"su - postgres -c 'psql -d hausverwaltung -f {file_path}'", shell=True)
                        subprocess.run(["systemctl", "restart", "hausverwaltung.service"])
                    if st.button("Abbrechen", key=f"can_res_{f}"):
                        st.session_state[f"conf_res_{f}"] = False
                        st.rerun()

                if st.session_state.get(f"conf_del_{f}"):
                    if st.button(f"✔️ LÖSCHEN {f}", key=f"real_del_{f}"):
                        os.remove(file_path)
                        st.rerun()
                    if st.button("Abbrechen", key=f"can_del_{f}"):
                        st.session_state[f"conf_del_{f}"] = False
                        st.rerun()

    st.divider()

    # 3. SOFTWARE-UPDATE
    st.subheader("🚀 System-Update")
    if st.button("Update von GitHub laden"):
        try:
            res = subprocess.run(["git", "-C", "/opt/hausverwaltung", "pull"], capture_output=True, text=True)
            st.success("Update-Vorgang abgeschlossen.")
            st.code(res.stdout)
            subprocess.run(["systemctl", "restart", "hausverwaltung.service"])
        except Exception as e:
            st.error(f"Fehler: {e}")

    cur.close()
    conn.close()