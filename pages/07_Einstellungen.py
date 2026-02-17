import streamlit as st
from database import get_conn

st.set_page_config(page_title="Einstellungen", layout="wide")
st.title("⚙️ Vermieter-Einstellungen")

conn = get_conn()
if conn:
    cur = conn.cursor()
    
    # Aktuelle Daten laden
    cur.execute("SELECT name, street, city, iban, bank_name FROM landlord_settings WHERE id = 1")
    data = cur.fetchone()
    
    with st.form("settings_form"):
        st.subheader("Stammdaten & Bankverbindung")
        name = st.text_input("Vermieter Name / Firma", value=data[0] if data[0] else "")
        street = st.text_input("Straße & Hausnummer", value=data[1] if data[1] else "")
        city = st.text_input("PLZ & Ort", value=data[2] if data[2] else "")
        st.divider()
        bank_name = st.text_input("Bankbezeichnung", value=data[4] if data[4] else "")
        iban = st.text_input("IBAN", value=data[3] if data[3] else "")
        
        if st.form_submit_button("Speichern"):
            cur.execute("""
                UPDATE landlord_settings 
                SET name=%s, street=%s, city=%s, iban=%s, bank_name=%s, updated_at=NOW()
                WHERE id = 1
            """, (name, street, city, iban, bank_name))
            conn.commit()
            st.success("Daten erfolgreich gespeichert!")
            st.rerun()
    conn.close()