import streamlit as st
import subprocess
import os
import shutil
from database import get_conn
from datetime import datetime

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Einstellungen", layout="wide")
st.title("⚙️ Einstellungen & System")

conn = get_conn()

if conn:
    cur = conn.cursor()
    
    # --- AUTOMATISCHES DATENBANK-UPDATE (Sicherstellen der neuen Spalten) ---
    try:
        cur.execute("ALTER TABLE landlord_settings ADD COLUMN IF NOT EXISTS total_area NUMERIC(10,2) DEFAULT 0.00")
        cur.execute("ALTER TABLE landlord_settings ADD COLUMN IF NOT EXISTS total_occupants INTEGER DEFAULT 1")
        cur.execute("ALTER TABLE landlord_settings ADD COLUMN IF NOT EXISTS total_units INTEGER DEFAULT 1")
        conn.commit()
    except Exception as e:
        conn.rollback()

    # --- 1. STAMMDATEN & HAUS-KENNZAHLEN LADEN ---
    cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants, total_units FROM landlord_settings WHERE id = 1")
    data = cur.fetchone()
    
    if not data:
        cur.execute("INSERT INTO landlord_settings (id, name) VALUES (1, 'Vermieter Name')")
        conn.commit()
        st.rerun()

    with st.form("settings_form"):
        st.subheader("🏠 Stammdaten & Haus-Konfiguration")
        st.write("Diese Daten sind die Basis für alle Berechnungen und Dokumente.")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Vermieter Name / Firma", value=data[0])
            street = st.text_input("Straße & Hausnummer", value=data[1])
            city = st.text_input("PLZ & Ort", value=data[2])
        with col2:
            bank_name = st.text_input("Bankbezeichnung", value=data[4])
            iban = st.text_input("IBAN", value=data[3])

        st.write("---")
        st.write("📊 **Verteilungsschlüssel (Gesamtwerte Haus)**")
        c_area, c_pers, c_units = st.columns(3)
        t_area = c_area.number_input("Gesamtfläche (m²)", value=float(data[5] or 447.0), step=0.1)
        t_pers = c_pers.number_input("Gesamtpersonen im Haus", value=int(data[6] or 15), step=1)
        t_unit = c_units.number_input("Anzahl Wohneinheiten", value=int(data[7] or 6), step=1)
        
        if st.form_submit_button("Stammdaten & Hauswerte Speichern"):
            try:
                cur.execute("""
                    UPDATE landlord_settings 
                    SET name=%s, street=%s, city=%s, iban=%s, bank_name=%s, 
                        total_area=%s, total_occupants=%s, total_units=%s, updated_at=NOW()
                    WHERE id = 1
                """, (name, street, city, iban, bank_name, t_area, t_pers, t_unit))
                conn.commit()
                st.success("✅ Alle Daten erfolgreich gespeichert!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")

    st.divider()

    # --- 2. DATENSICHERUNG (BACKUP, RESTORE & UPLOAD) ---
    st.subheader("💾 Datensicherung & Wiederherstellung")
    
    col_b1, col_b2 = st.columns([1, 2])
    
    with col_b1:
        st.write("✨ **Aktionen**")
        
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
        
        st.write("---")
        st.write("📤 **Backup hochladen (.sql)**")
        uploaded_file = st.file_uploader("Datei auswählen", type=["sql"])
        if uploaded_file is not None:
            backup_dir = "/opt/hausverwaltung/backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            file_path = os.path.join(backup_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Datei {uploaded_file.name} erfolgreich hochgeladen!")
            st.rerun()

    with col_b2:
        st.write("📂 **Backup-Verwaltung**")
        backup_dir = "/opt/hausverwaltung/backups"
        if os.path.exists(backup_dir):
            files = [f for f in os.listdir(backup_dir) if f.endswith(".sql")]
            files.sort(reverse=True)
            
            if files:
                for f in files:
                    file_path = os.path.join(backup_dir, f)
                    st.write(f"---")
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.text(f"📄 {f}")
                    
                    with open(file_path, "rb") as fb:
                        c2.download_button("Download", fb, file_name=f, mime="application/sql", key=f"dl_{f}")
                    
                    if c3.button("Restore", key=f"btn_res_{f}"):
                        st.session_state[f"confirm_restore_{f}"] = True

                    if st.session_state.get(f"confirm_restore_{f}", False):
                        st.error(f"⚠️ Backup **{f}** wirklich einspielen?")
                        col_f1, col_f2 = st.columns(2)
                        if col_f1.button(f"🔥 JA, ÜBERSCHREIBEN", key=f"fire_{f}"):
                            try:
                                restore_cmd = f"su - postgres -c 'psql -d hausverwaltung -f {file_path}'"
                                res = subprocess.run(restore_cmd, shell=True, capture_output=True, text=True)
                                if res.returncode == 0:
                                    st.success("✅ Wiederherstellung erfolgreich!")
                                    subprocess.run(["systemctl", "restart", "hausverwaltung.service"])
                                else:
                                    st.error(f"Fehler: {res.stderr}")
                            except Exception as e:
                                st.error(f"Systemfehler: {e}")
                        if col_f2.button("Abbrechen", key=f"cancel_{f}"):
                            st.session_state[f"confirm_restore_{f}"] = False
                            st.rerun()
            else:
                st.info("Keine Backups vorhanden.")

    st.divider()

    # --- 3. SOFTWARE-UPDATE ---
    st.subheader("🚀 System-Update")
    if st.button("Update von GitHub laden"):
        try:
            update_result = subprocess.run(["git", "-C", "/opt/hausverwaltung", "pull"], capture_output=True, text=True)
            if "Already up to date" in update_result.stdout:
                st.info("ℹ️ Software ist aktuell.")
            else:
                st.success("✅ Update erfolgreich!")
                subprocess.run(["systemctl", "restart", "hausverwaltung.service"])
        except Exception as e:
            st.error(f"Update fehlgeschlagen: {e}")

    conn.close()
else:
    st.error("❌ Keine Datenbankverbindung.")