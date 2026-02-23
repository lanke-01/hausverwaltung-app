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

conn = get_direct_conn()

if not conn:
    st.error("❌ Datenbankverbindung fehlgeschlagen.")
else:
    tab1, tab2 = st.tabs(["🏠 Stammdaten", "🛠️ System & Wartung"])

    # --- TAB 1: STAMMDATEN ---
    with tab1:
        cur = conn.cursor()
        cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants FROM landlord_settings WHERE id = 1")
        data = cur.fetchone()

        with st.form("settings_form"):
            st.subheader("Vermieter-Details (für Briefkopf)")
            col1, col2 = st.columns(2)
            with col1:
                v_name = st.text_input("Vermieter Name", value=data[0] or "")
                v_street = st.text_input("Straße", value=data[1] or "")
                v_city = st.text_input("PLZ / Ort", value=data[2] or "")
            with col2:
                v_iban = st.text_input("IBAN", value=data[3] or "")
                v_bank = st.text_input("Bankname", value=data[4] or "")
            
            st.divider()
            st.subheader("Haus-Gesamtwerte (für Abrechnungsschlüssel)")
            c1, c2 = st.columns(2)
            with c1:
                v_area = st.number_input("Gesamtfläche (m²)", value=float(data[5] or 0.0))
            with c2:
                v_pers = st.number_input("Gesamtpersonen", value=int(data[6] or 0))

            if st.form_submit_button("💾 Alle Daten speichern"):
                cur.execute("""
                    UPDATE landlord_settings SET 
                    name=%s, street=%s, city=%s, iban=%s, bank_name=%s, total_area=%s, total_occupants=%s
                    WHERE id = 1
                """, (v_name, v_street, v_city, v_iban, v_bank, v_area, v_pers))
                conn.commit()
                st.success("✅ Stammdaten erfolgreich aktualisiert!")

    # --- TAB 2: SYSTEM & WARTUNG ---
    with tab2:
        # Sektion: Backup
        st.subheader("🗄️ Datenbank-Sicherung")
        c_back1, c_back2 = st.columns([1, 2])
        
        with c_back1:
            if st.button("🚀 Backup jetzt erstellen"):
                try:
                    # Führt das vorhandene Backup-Skript aus
                    res = subprocess.run(['/bin/bash', '/opt/hausverwaltung/install/backup_db.sh'], capture_output=True, text=True)
                    if res.returncode == 0:
                        st.success("Backup erstellt!")
                    else:
                        st.error(f"Fehler: {res.stderr}")
                except Exception as e:
                    st.error(f"Fehler: {e}")

        with c_back2:
            st.write("**Letzte Sicherungen:**")
            backup_path = "/opt/hausverwaltung/backups"
            if os.path.exists(backup_path):
                files = sorted([f for f in os.listdir(backup_path) if f.endswith('.sql')], reverse=True)[:5]
                for f in files:
                    st.caption(f"📄 {f}")
            else:
                st.info("Noch keine Backups vorhanden.")

        st.divider()

        # Sektion: Update
        st.subheader("🔄 Software-Update")
        st.write("Code vom Server ziehen und App neu starten.")
        
        if st.button("📥 Update ausführen"):
            with st.spinner("Update läuft..."):
                try:
                    # 1. Code-Update
                    subprocess.run(['git', '-C', '/opt/hausverwaltung', 'pull'], capture_output=True)
                    # 2. Neustart des Services
                    subprocess.run(['systemctl', 'restart', 'hausverwaltung.service'])
                    st.success("Update abgeschlossen! Die App startet neu...")
                except Exception as e:
                    st.error(f"Update fehlgeschlagen: {e}")

    conn.close()
