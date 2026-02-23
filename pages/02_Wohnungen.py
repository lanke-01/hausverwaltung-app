import streamlit as st
import pandas as pd
from database import get_conn

st.set_page_config(page_title="Wohnungs-Verwaltung", layout="wide")
st.title("🏠 Wohnungs-Verwaltung")

conn = get_conn()
if conn:
    try:
        cur = conn.cursor()
        
        # Bereich: Neue Wohnung
        with st.expander("➕ Neue Wohnung anlegen"):
            with st.form("add_apt"):
                n_name = st.text_input("Name der Einheit (z.B. EG links)")
                n_area = st.number_input("Fläche (m²)", min_value=0.0, step=0.1)
                n_rent = st.number_input("Kaltmiete (EUR)", min_value=0.0, step=10.0)
                n_prepay = st.number_input("Nebenkostenvorschuss (EUR)", min_value=0.0, step=5.0)
                if st.form_submit_button("Speichern"):
                    cur.execute("""
                        INSERT INTO apartments (unit_name, area, base_rent, service_charge_propayment) 
                        VALUES (%s, %s, %s, %s)
                    """, (n_name, n_area, n_rent, n_prepay))
                    conn.commit()
                    st.success("Wohnung angelegt!")
                    st.rerun()

        st.subheader("Aktueller Bestand")
        # Korrektur der Spaltennamen für die Anzeige
        df_apts = pd.read_sql("""
            SELECT id as "ID", unit_name as "Einheit", area as "m²", 
                   base_rent as "Kaltmiete", service_charge_propayment as "NK-Vorschuss"
            FROM apartments ORDER BY unit_name
        """, conn)
        st.dataframe(df_apts, use_container_width=True, hide_index=True)

    finally:
        conn.close()
