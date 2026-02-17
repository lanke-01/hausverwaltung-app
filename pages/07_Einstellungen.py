import streamlit as st
from database import get_conn

st.set_page_config(page_title="Einstellungen", layout="wide")
st.title("⚙️ Vermieter-Einstellungen")

conn = get_conn()
if conn:
    cur = conn.cursor()
    cur.execute("SELECT name, street, city, iban, bank_name FROM landlord_settings WHERE id = 1")
    data = cur.fetchone()
    
    # Falls Tabelle leer, Dummy-Daten setzen
    if not data:
        data = ("", "", "", "", "")

    with st.form("settings_form"):
        name = st.text_input("Vermieter Name", value=data[0])
        street = st.text_input("Straße", value=data[1])
        city = st.text_input("PLZ / Ort", value=data[2])
        bank_name = st.text_input("Bank", value=data[4])
        iban = st.text_input("IBAN", value=data[3])
        
        if st.form_submit_button("Speichern"):
            cur.execute("""
                UPDATE landlord_settings 
                SET name=%s, street=%s, city=%s, iban=%s, bank_name=%s, updated_at=NOW()
                WHERE id = 1
            """, (name, street, city, iban, bank_name))
            conn.commit()
            st.success("Gespeichert!")
            st.rerun()
    conn.close()