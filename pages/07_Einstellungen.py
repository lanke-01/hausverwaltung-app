import streamlit as st
import subprocess
import os
from database import get_conn
from datetime import datetime

st.set_page_config(page_title="Einstellungen", layout="wide")
st.title("⚙️ Vermieter-Einstellungen & System")

def cleanup_old_backups(backup_dir, max_files=5):
    try:
        if not os.path.exists(backup_dir): return
        files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith(".sql")]
        files.sort(key=os.path.getmtime)
        while len(files) > max_files:
            os.remove(files.pop(0))
    except Exception as e:
        st.error(f"Fehler beim Aufräumen: {e}")

conn = get_conn()

if conn:
    cur = conn.cursor()
    
    # --- DB UPDATE LOGIK (Spalten sicherstellen) ---
    try:
        cur.execute("ALTER TABLE landlord_settings ADD COLUMN IF NOT EXISTS total_area NUMERIC(10,2) DEFAULT 0.00")
        cur.execute("ALTER TABLE landlord_settings ADD COLUMN IF NOT EXISTS total_occupants INTEGER DEFAULT 1")
        cur.execute("ALTER TABLE landlord_settings ADD COLUMN IF NOT EXISTS total_units INTEGER DEFAULT 1")
        conn.commit()
    except Exception as e:
        conn.rollback()

    # --- DATEN LADEN ---
    cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants, total_units FROM landlord_settings WHERE id = 1")
    data = cur.fetchone()
    
    if not data:
        cur.execute("INSERT INTO landlord_settings (id, name) VALUES (1, 'Vermieter Name')")
        conn.commit()
        st.rerun()

    # --- BEREICH 1: STAMMDATEN & HAUS-KENNZAHLEN ---
    st.subheader("🏠 Stammdaten & Haus-Konfiguration")
    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Vermieter Name", value=data[0])
            street = st.text_input("Straße & Hausnr.", value=data[1])
            city = st.text_input("PLZ & Ort", value=data[2])
        with col2:
            bank_name = st.text_input("Bankbezeichnung", value=data[4])
            iban = st.text_input("IBAN", value=data[3])

        st.write("---")
        st.write("📊 **Verteilungsschlüssel (Gesamtwerte für das Haus)**")
        c_area, c_pers, c_units = st.columns(3)
        t_area = c_area.number_input("Gesamtfläche (m²)", value=float(data[5] or 447.0), step=0.1)
        t_pers = c_pers.number_input("Gesamtpersonen im Haus", value=int(data[6] or 15), step=1)
        t_unit = c_units.number_input("Anzahl Wohneinheiten", value=int(data[7] or 6), step=1)
        
        # DER UPDATE BUTTON
        submit = st.form_submit_button("✅ Einstellungen Speichern")
        
        if submit:
            cur.execute("""
                UPDATE landlord_settings 
                SET name=%s, street=%s, city=%s, iban=%s, bank_name=%s, 
                    total_area=%s, total_occupants=%s, total_units=%s, updated_at=NOW()
                WHERE id = 1
            """, (name, street, city, iban, bank_name, t_area, t_pers, t_unit))
            conn.commit()
            st.success("Änderungen erfolgreich gespeichert!")
            st.rerun()

    st.divider()

    # --- BEREICH 2: BACKUP SYSTEM ---
    st.subheader("💾 Datensicherung")
    st.info("Klicken Sie auf den Button, um ein manuelles Datenbank-Backup zu erstellen. Die letzten 5 Dateien werden auf dem Server gespeichert.")
    
    if st.button("🔴 Backup jetzt erstellen"):
        backup_dir = "/opt/hausverwaltung/backups"
        try:
            # Stelle sicher, dass der Ordner existiert
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                
            res = subprocess.run(["/opt/hausverwaltung/install/backup_db.sh"], capture_output=True, text=True)
            if res.returncode == 0:
                cleanup_old_backups(backup_dir, max_files=5)
                st.success(f"Backup erfolgreich erstellt um {datetime.now().strftime('%H:%M:%S')}")
            else:
                st.error(f"Backup-Skript Fehler: {res.stderr}")
        except Exception as e:
            st.error(f"Systemfehler beim Backup: {e}")

    cur.close()
    conn.close()
else:
    st.error("Keine Verbindung zur Datenbank möglich.")