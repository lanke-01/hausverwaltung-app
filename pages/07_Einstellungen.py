import streamlit as st
import subprocess
import os
from database import get_conn
from datetime import datetime

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Einstellungen", layout="wide")
st.title("⚙️ Vermieter-Einstellungen & System")

conn = get_conn()

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

    # 2. DATENSICHERUNG (BACKUP & RESTORE)
    st.subheader("💾 Datensicherung & Wiederherstellung")
    st.write("Verwalten Sie Ihre Backups. **Vorsicht:** Ein Restore überschreibt alle aktuellen Daten!")
    
    col_b1, col_b2 = st.columns([1, 2])
    
    with col_b1:
        st.write("✨ **Neues Backup**")
        if st.button("🔴 Backup jetzt erstellen"):
            backup_script = "/opt/hausverwaltung/install/backup_db.sh"
            if os.path.exists(backup_script):
                result = subprocess.run([backup_script], capture_output=True, text=True)
                if result.returncode == 0:
                    st.success("Backup erfolgreich erstellt!")
                    st.rerun()
                else:
                    st.error(f"Fehler: {result.stderr}")
            else:
                st.error("Skript backup_db.sh nicht gefunden!")

    with col_b2:
        st.write("📂 **Backup-Verwaltung**")
        backup_dir = "/opt/hausverwaltung/backups"
        if os.path.exists(backup_dir):
            files = [f for f in os.listdir(backup_dir) if f.endswith(".sql")]
            files.sort(reverse=True)
            
            if files:
                for f in files:
                    file_path = os.path.join(backup_dir, f)
                    c1, c2, c3 = st.columns([2, 1, 1])
                    
                    c1.text(f"📄 {f}")
                    
                    # DOWNLOAD
                    with open(file_path, "rb") as fb:
                        c2.download_button("Download", fb, file_name=f, mime="application/sql", key=f"dl_{f}")
                    
                    # RESTORE (Wiederherstellung)
                    if c3.button("Restore", key=f"res_{f}"):
                        st.warning(f"Soll das Backup {f} wirklich eingespielt werden?")
                        confirm = st.checkbox("Ja, aktuelle Daten überschreiben", key=f"conf_{f}")
                        if confirm:
                            if st.button("🔥 JETZT WIEDERHERSTELLEN", key=f"fire_{f}"):
                                try:
                                    # Restore-Befehl ausführen
                                    # Wir nutzen psql, um das Backup einzuspielen
                                    restore_cmd = f"su - postgres -c 'psql -d hausverwaltung -f {file_path}'"
                                    res = subprocess.run(restore_cmd, shell=True, capture_output=True, text=True)
                                    
                                    if res.returncode == 0:
                                        st.success("✅ Wiederherstellung erfolgreich!")
                                        st.info("App startet neu...")
                                        subprocess.run(["systemctl", "restart", "hausverwaltung.service"])
                                    else:
                                        st.error(f"Fehler beim Restore: {res.stderr}")
                                except Exception as e:
                                    st.error(f"Systemfehler: {e}")
            else:
                st.info("Keine Backups vorhanden.")

    st.divider()

    # 3. SOFTWARE-UPDATE
    st.subheader("🚀 System-Update")
    if st.button("Update von GitHub laden"):
        try:
            update_result = subprocess.run(["git", "-C", "/opt/hausverwaltung", "pull"], capture_output=True, text=True)
            if "Already up to date" in update_result.stdout:
                st.info("ℹ️ Die Software ist bereits auf dem neuesten Stand.")
            else:
                st.success("✅ Update erfolgreich!")
                st.warning("🔄 Starte App neu...")
                subprocess.run(["systemctl", "restart", "hausverwaltung.service"])
        except Exception as e:
            st.error(f"Update fehlgeschlagen: {e}")

    conn.close()
else:
    st.error("❌ Keine Datenbankverbindung.")