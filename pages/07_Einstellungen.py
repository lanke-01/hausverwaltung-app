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
    
    # Falls Tabelle leer ist, Standardwerte setzen
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

    # 2. DATENSICHERUNG (BACKUP)
    st.subheader("💾 Datensicherung (Backup)")
    st.write("Erstellen Sie eine manuelle Sicherungskopie der Datenbank.")
    
    col_b1, col_b2 = st.columns([1, 2])
    
    with col_b1:
        if st.button("🔴 Backup jetzt erstellen"):
            backup_script = "/opt/hausverwaltung/install/backup_db.sh"
            if os.path.exists(backup_script):
                result = subprocess.run([backup_script], capture_output=True, text=True)
                if result.returncode == 0:
                    st.success("Backup erfolgreich!")
                    st.toast("Backup erstellt", icon="💾")
                else:
                    st.error(f"Fehler: {result.stderr}")
            else:
                st.error("Skript backup_db.sh nicht gefunden!")

    with col_b2:
        if st.checkbox("Vorhandene Backups anzeigen"):
            backup_dir = "/opt/hausverwaltung/backups"
            if os.path.exists(backup_dir):
                files = os.listdir(backup_dir)
                files.sort(reverse=True)
                if files:
                    for f in files:
                        st.text(f"📄 {f}")
                else:
                    st.write("Keine Backups gefunden.")

    st.divider()

    # 3. SOFTWARE-UPDATE (GIT PULL)
    st.subheader("🚀 System-Update")
    st.write("Hier können Sie die neueste Version von GitHub laden.")
    
    if st.button("Update von GitHub laden"):
        try:
            # Git Pull im Projektverzeichnis
            update_result = subprocess.run(["git", "-C", "/opt/hausverwaltung", "pull"], capture_output=True, text=True)
            
            if "Already up to date" in update_result.stdout:
                st.info("ℹ️ Die Software ist bereits auf dem neuesten Stand.")
            else:
                st.success("✅ Update erfolgreich heruntergeladen!")
                st.code(update_result.stdout)
                
                # Dienst neu starten (erfordert sudo Rechte für den user, 
                # im LXC als root meist kein Problem)
                st.warning("🔄 Starte App neu...")
                subprocess.run(["systemctl", "restart", "hausverwaltung.service"])
        except Exception as e:
            st.error(f"Update fehlgeschlagen: {e}")

    conn.close()
else:
    st.error("❌ Keine Datenbankverbindung möglich. Bitte prüfen Sie die Verbindungseinstellungen.")