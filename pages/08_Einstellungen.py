import streamlit as st
import psycopg2

# --- DIREKTE VERBINDUNGSFUNKTION (Umgeht Import-Fehler) ---
def get_direct_conn():
    try:
        # Wir nutzen den Socket-Weg, der in deiner Konsole funktioniert hat
        conn = psycopg2.connect(
            dbname="hausverwaltung",
            user="postgres"
        )
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        return None

st.set_page_config(page_title="Einstellungen", layout="wide")
st.title("⚙️ Systemeinstellungen")

# Verbindung versuchen
conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung in der App.")
    st.info("💡 psql funktioniert zwar in der Konsole, aber die App kann nicht zugreifen.")
    st.code("Lösung: Führe im Terminal aus: chmod 777 /var/run/postgresql")
else:
    cur = conn.cursor()
    
    # Sicherstellen, dass die Tabelle existiert (Auto-Reparatur)
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

    # Aktuelle Daten laden
    cur.execute("SELECT name, street, city, iban, bank_name, total_area, total_occupants FROM landlord_settings WHERE id = 1")
    set_data = cur.fetchone()

    st.subheader("Vermieter-Stammdaten (für Abrechnungen)")
    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Vermieter Name", value=set_data[0] or "")
            street = st.text_input("Straße", value=set_data[1] or "")
            city = st.text_input("PLZ / Ort", value=set_data[2] or "")
        with col2:
            iban = st.text_input("IBAN", value=set_data[3] or "")
            bank = st.text_input("Bankname", value=set_data[4] or "")
            
        st.divider()
        st.subheader("Haus-Gesamtwerte")
        c3, c4 = st.columns(2)
        with c3:
            t_area = st.number_input("Gesamtfläche Haus (m²)", value=float(set_data[5] or 0.0))
        with c4:
            t_pers = st.number_input("Gesamtpersonen im Haus", value=int(set_data[6] or 0))

        if st.form_submit_button("💾 Speichern"):
            cur.execute("""
                UPDATE landlord_settings SET 
                name=%s, street=%s, city=%s, iban=%s, bank_name=%s, total_area=%s, total_occupants=%s
                WHERE id = 1
            """, (name, street, city, iban, bank, t_area, t_pers))
            conn.commit()
            st.success("✅ Einstellungen gespeichert!")
            st.rerun()

    conn.close()
