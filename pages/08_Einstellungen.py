import streamlit as st
from database import get_conn

st.set_page_config(page_title="Einstellungen", layout="wide")
st.title("⚙️ Systemeinstellungen")

conn = get_conn()
if not conn:
    st.error("❌ Keine Datenbankverbindung. Bitte prüfen Sie, ob PostgreSQL im LXC läuft.")
else:
    cur = conn.cursor()
    
    # Sicherstellen, dass ein Datensatz existiert
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

        if st.form_submit_button("Speichern"):
            cur.execute("""
                UPDATE landlord_settings SET 
                name=%s, street=%s, city=%s, iban=%s, bank_name=%s, total_area=%s, total_occupants=%s
                WHERE id = 1
            """, (name, street, city, iban, bank, t_area, t_pers))
            conn.commit()
            st.success("✅ Einstellungen gespeichert!")

    conn.close()
