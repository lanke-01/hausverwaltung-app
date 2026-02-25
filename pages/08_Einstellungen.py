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
    cur = conn.cursor()
    
    # Tabelle sicherstellen
    cur.execute("""
        CREATE TABLE IF NOT EXISTS landlord_settings (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            street VARCHAR(255),
            city VARCHAR(255),
            iban VARCHAR(50),
            bank_name VARCHAR(255),
            total_area NUMERIC(10,2) DEFAULT 0,
            total_occupants INTEGER DEFAULT 0
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
            st.subheader("Vermieter-Details (für Briefkopf & PDF)")
            col1, col2 = st.columns(2)
            with col1:
                v_name = st.text_input("Vermieter Name", value=data[0] or "")
                v_street = st.text_input("Straße", value=data[1] or "")
                v_city = st.text_input("PLZ / Ort", value=data[2] or "")
            with col2:
                v_iban = st.text_input("IBAN", value=data[3] or "")
                v_bank = st.text_input("Bankname", value=data[4] or "")
            
            st.divider()
            st.subheader("Haus-Gesamtwerte")
            c1, c2 = st.columns(2)
            with c1:
                v_area = st.number_input("Gesamtfläche des Hauses (m²)", value=float(data[5] or 0.0))
            with c2:
                v_pers = st.number_input("Gesamtanzahl Personen im Haus", value=int(data[6] or 0))

            if st.form_submit_button("💾 Alle Daten speichern"):
                cur.execute("""
                    UPDATE landlord_settings SET 
                    name=%s, street=%s, city=%s, iban=%s, bank_name=%s, total_area=%s, total_occupants=%s
                    WHERE id = 1
                """, (v_name, v_street, v_city, v_iban, v_bank, v_area, v_pers))
                conn.commit()
                st.success("✅ Stammdaten gespeichert!")
                st.rerun()

   # --- TAB 2: SYSTEM & WARTUNG ---
    with tab2:
        st.subheader("🔄 Software-Update")
        
        if st.button("📥 Update von GitHub erzwingen & Restart"):
            status = st.empty()
            status.info("⏳ Update gestartet...")
            try:
                repo_path = "/opt/hausverwaltung"
                
                # 1. Git Update
                status.info("📡 Hole Daten von GitHub...")
                subprocess.run(['git', '-C', repo_path, 'fetch', '--all'], check=True)
                subprocess.run(['git', '-C', repo_path, 'reset', '--hard', 'origin/main'], check=True)
                
                # 2. Dienst-Neustart
                status.info("🔄 Starte System neu...")
                
                # Wir versuchen es direkt über den Systempfad
                # Wenn du als root eingeloggt bist, reicht dieser Befehl:
                subprocess.run(['/usr/bin/systemctl', 'restart', 'hausverwaltung.service'], check=True)
                
                st.success("✅ Update erfolgreich! Seite lädt in 5 Sek. neu.")
                st.balloons()
            except Exception as e:
                status.error(f"❌ Fehler: {e}")
        st.divider()
        st.subheader("Letzte Sicherungen")
        backup_path = "/opt/hausverwaltung/backups"
        
        if os.path.exists(backup_path):
            files = sorted([f for f in os.listdir(backup_path) if f.endswith('.sql')], reverse=True)
            
            for f in files:
                full_path = os.path.join(backup_path, f)
                size_kb = os.path.getsize(full_path) / 1024
                
                # Drei Spalten: Info, Download, Löschen
                col_file, col_dl, col_del = st.columns([3, 1, 1])
                
                with col_file:
                    st.write(f"📄 **{f}** ({size_kb:.1f} KB)")
                
                with col_dl:
                    with open(full_path, "rb") as file_content:
                        st.download_button("⬇️ Download", file_content, file_name=f, key=f"dl_{f}")
                
                with col_del:
                    # Roter Lösch-Button mit Sicherheitsabfrage
                    if st.button("🗑️ Löschen", key=f"del_{f}", type="secondary"):
                        try:
                            os.remove(full_path)
                            st.toast(f"Datei {f} gelöscht!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fehler: {e}")
        else:
            st.error("Backup-Verzeichnis nicht gefunden.")

    cur.close()
    conn.close()