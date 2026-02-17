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
        files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith(".sql")]
        # Sortieren nach Erstellungszeit (älteste zuerst)
        files.sort(key=os.path.getmtime)
        
        while len(files) > max_files:
            oldest_file = files.pop(0)
            os.remove(oldest_file)
            st.info(f"🗑️ Automatisches Aufräumen: Altes Backup {os.path.basename(oldest_file)} wurde gelöscht.")
    except Exception as e:
        st.error(f"Fehler beim automatischen Aufräumen: {e}")

if conn:
    cur = conn.cursor()
    
    # 1. STAMMDATEN LADEN & SPEICHERN
    cur.execute("SELECT name, street, city, iban, bank_name FROM landlord_settings WHERE id = 1")
    data = cur.fetchone()
    
    if not data:
        data = ("Bitte Name angeben", "", "", "", "")
    
    with st.form("settings_form"):
        st.subheader("🏠 Stammdaten & Bankverbindung")
        st.write("Diese Daten werden für die Erstellung von Briefen und Abrechnungen genutzt.")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Vermieter Name / Firma", value=data[0])
            street = st.text_input("Straße & Hausnummer", value=data[1])
            city = st.text_input("PLZ & Ort", value=data[2])
        with col2:
            bank_name = st.text_input("Bankbezeichnung", value=data[4])
            iban = st.text_input("IBAN", value=data[3])
        
        if st.form_submit_button("Stammdaten Speichern"):
            try:
                cur.execute("""
                    UPDATE landlord_settings 
                    SET name=%s, street=%s, city=%s, iban=%s, bank_name=%s, updated_at=NOW()
                    WHERE id = 1
                """, (name, street, city, iban, bank_name))
                conn.commit()
                st.success("✅ Stammdaten erfolgreich gespeichert!")
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")

    st.divider()

    # 2. DATENSICHERUNG (BACKUP, RESTORE, UPLOAD & DELETE)
    st.subheader("💾 Datensicherung & Wiederherstellung")
    
    col_b1, col_b2 = st.columns([1, 2])
    
    with col_b1:
        st.write("✨ **Aktionen**")
        
        # Backup erstellen
        if st.button("🔴 Backup jetzt erstellen"):
            backup_dir = "/opt/hausverwaltung/backups"
            backup_script = "/opt/hausverwaltung/install/backup_db.sh"
            
            if os.path.exists(backup_script):
                result = subprocess.run([backup_script], capture_output=True, text=True)
                if result.returncode == 0:
                    st.success("Backup erfolgreich erstellt!")
                    # Automatisches Aufräumen auf 5 Dateien
                    cleanup_old_backups(backup_dir, max_files=5)
                    st.rerun()
                else:
                    st.error(f"Fehler: {result.stderr}")
            else:
                st.error("Skript backup_db.sh nicht gefunden!")
        
        st.write("---")
        
        # Backup HOCHLADEN
        st.write("📤 **Backup hochladen (.sql)**")
        uploaded_file = st.file_uploader("Datei auswählen", type=["sql"])
        if uploaded_file is not None:
            backup_dir = "/opt/hausverwaltung/backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            file_path = os.path.join(backup_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Datei {uploaded_file.name} hochgeladen!")
            # Auch hier aufräumen, falls durch Upload das Limit überschritten wird
            cleanup_old_backups(backup_dir, max_files=5)
            st.rerun()

    with col_b2:
        st.write("📂 **Backup-Verwaltung (Limit: 5 Dateien)**")
        backup_dir = "/opt/hausverwaltung/backups"
        if os.path.exists(backup_dir):
            files = [f for f in os.listdir(backup_dir) if f.endswith(".sql")]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)
            
            if files:
                for f in files:
                    file_path = os.path.join(backup_dir, f)
                    st.write(f"---")
                    c1, c2, c3, c4 = st.columns([2, 0.8, 0.8, 0.8])
                    
                    c1.text(f"📄 {f}")
                    
                    with open(file_path, "rb") as fb:
                        c2.download_button("💾", fb, file_name=f, mime="application/sql", key=f"dl_{f}", help="Download")
                    
                    if c3.button("🔄", key=f"btn_res_{f}", help="Wiederherstellen"):
                        st.session_state[f"confirm_restore_{f}"] = True

                    if c4.button("🗑️", key=f"btn_del_{f}", help="Löschen"):
                        st.session_state[f"confirm_delete_{f}"] = True

                    # Sicherheitsabfrage RESTORE
                    if st.session_state.get(f"confirm_restore_{f}", False):
                        st.warning(f"⚠️ Backup **{f}** einspielen?")
                        col_r1, col_r2 = st.columns(2)
                        if col_r1.button(f"🔥 JA, RESTORE", key=f"fire_{f}"):
                            try:
                                restore_cmd = f"su - postgres -c 'psql -d hausverwaltung -f {file_path}'"
                                res = subprocess.run(restore_cmd, shell=True, capture_output=True, text=True)
                                if res.returncode == 0:
                                    st.success("Erfolgreich!")
                                    subprocess.run(["systemctl", "restart", "hausverwaltung.service"])
                                else:
                                    st.error(f"Fehler: {res.stderr}")
                            except Exception as e:
                                st.error(f"Systemfehler: {e}")
                        if col_r2.button("Abbrechen", key=f"can_res_{f}"):
                            st.session_state[f"confirm_restore_{f}"] = False
                            st.rerun()

                    # Sicherheitsabfrage LÖSCHEN
                    if st.session_state.get(f"confirm_delete_{f}", False):
                        st.error(f"Datei **{f}** löschen?")
                        col_d1, col_d2 = st.columns(2)
                        if col_d1.button(f"✔️ LÖSCHEN", key=f"real_del_{f}"):
                            os.remove(file_path)
                            st.session_state[f"confirm_delete_{f}"] = False
                            st.rerun()
                        if col_d2.button("Abbrechen", key=f"can_del_{f}"):
                            st.session_state[f"confirm_delete_{f}"] = False
                            st.rerun()
            else:
                st.info("Keine Backups vorhanden.")

    st.divider()

    # 3. SOFTWARE-UPDATE
    st.subheader("🚀 System-Update")
    if st.button("Update von GitHub laden"):
        try:
            update_result = subprocess.run(["git", "-C", "/opt/hausverwaltung", "pull"], capture_output=True, text=True)
            if "Already up to date" in update_result.stdout:
                st.info("ℹ️ Bereits aktuell.")
            else:
                st.success("✅ Update erfolgreich!")
                subprocess.run(["systemctl", "restart", "hausverwaltung.service"])
        except Exception as e:
            st.error(f"Update fehlgeschlagen: {e}")

    conn.close()