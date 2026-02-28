import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, date

def get_direct_conn():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        conn.set_client_encoding('UTF8')
        return conn
    except:
        return None

st.set_page_config(page_title="Zählerstände", layout="wide")
st.title("📟 Zählerverwaltung & Differenzmessung")

conn = get_direct_conn()

if not conn:
    st.error("❌ Keine Datenbankverbindung möglich.")
else:
    cur = conn.cursor()
    cur.execute("ALTER TABLE operating_expenses ADD COLUMN IF NOT EXISTS tenant_id INTEGER")
    conn.commit()

    tab1, tab2, tab3, tab4 = st.tabs(["🏗️ Zähler anlegen", "📝 Stand erfassen", "⚖️ Differenzmessung", "⚙️ Stände bearbeiten"])

    with tab1:
        st.subheader("Neuen Zähler registrieren")
        with st.form("meter_form"):
            m_type = st.selectbox("Typ", ["Strom", "Wasser", "Gas", "Wärme"])
            m_num = st.text_input("Zählernummer")
            is_sub = st.checkbox("Unterzähler (z.B. Wallbox)?")
            cur.execute("SELECT id, unit_name FROM apartments")
            apps = {row[1]: row[0] for row in cur.fetchall()}
            apps["Haus / Allgemein"] = None
            sel_app = st.selectbox("Einheit", list(apps.keys()))
            if st.form_submit_button("Speichern"):
                cur.execute("INSERT INTO meters (apartment_id, meter_type, meter_number, is_submeter) VALUES (%s, %s, %s, %s)", (apps[sel_app], m_type, m_num, is_sub))
                conn.commit()
                st.success("Zähler angelegt!")

    with tab2:
        st.subheader("Zählerstand eingeben")
        cur.execute("SELECT id, meter_type, meter_number FROM meters")
        m_list = {f"{r[1]} ({r[2]})": r[0] for r in cur.fetchall()}
        if m_list:
            sel_m = st.selectbox("Zähler wählen", list(m_list.keys()))
            val = st.number_input("Stand", step=0.01)
            d = st.date_input("Datum", datetime.now())
            if st.button("Stand speichern"):
                cur.execute("INSERT INTO meter_readings (meter_id, reading_value, reading_date) VALUES (%s, %s, %s)", (m_list[sel_m], val, d))
                conn.commit()
                st.success("Gespeichert!")

    with tab3:
        st.subheader("Wallbox-Differenzmessung")
        cur.execute("SELECT id, meter_number FROM meters WHERE meter_type = 'Strom' AND is_submeter = FALSE")
        main_m = cur.fetchall()
        cur.execute("SELECT id, meter_number FROM meters WHERE meter_type = 'Strom' AND is_submeter = TRUE")
        sub_m = cur.fetchall()

        if main_m and sub_m:
            m_id = st.selectbox("Hauptzähler", [m[0] for m in main_m], format_func=lambda x: next(m[1] for m in main_m if m[0] == x))
            s_id = st.selectbox("Wallbox", [m[0] for m in sub_m], format_func=lambda x: next(m[1] for m in sub_m if m[0] == x))
            preis = st.number_input("Preis pro kWh", value=0.35)
            jahr = st.number_input("Abrechnungsjahr", value=2024)

            if st.button("Verbrauch berechnen"):
                def get_c(mid, j):
                    cur.execute("SELECT reading_value FROM meter_readings WHERE meter_id = %s AND reading_date <= %s ORDER BY reading_date DESC LIMIT 1", (mid, f"{j}-01-01"))
                    r1 = cur.fetchone()
                    cur.execute("SELECT reading_value FROM meter_readings WHERE meter_id = %s AND reading_date >= %s ORDER BY reading_date ASC LIMIT 1", (mid, f"{j+1}-01-01"))
                    r2 = cur.fetchone()
                    if r1 and r2: return float(abs(r2[0] - r1[0]))
                    return 0.0
                
                mv, sv = get_c(m_id, jahr), get_c(s_id, jahr)
                st.session_state['calc'] = {'netto': (mv-sv)*preis, 'sub': sv*preis, 'jahr': jahr}
                st.write(f"Gesamt Haus: {mv:.2f} kWh | Wallbox: {sv:.2f} kWh")
                st.write(f"Differenz (Allgemein): **{(mv-sv):.2f} kWh**")

            if 'calc' in st.session_state:
                cur.execute("SELECT id, first_name, last_name FROM tenants")
                t_data = cur.fetchall()
                t_list = {f"{r[1]} {r[2]}": r[0] for r in t_data}
                target = st.selectbox("Wallbox Mieter zuweisen", list(t_list.keys()))
                if st.button("Kosten jetzt buchen"):
                    cur.execute("INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year, tenant_id) VALUES (%s, %s, %s, %s, -1)", ("Allgemeinstrom (Netto)", st.session_state['calc']['netto'], "area", st.session_state['calc']['jahr']))
                    cur.execute("INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year, tenant_id) VALUES (%s, %s, %s, %s, %s)", ("Wallbox-Strom", st.session_state['calc']['sub'], "direct", st.session_state['calc']['jahr'], t_list[target]))
                    conn.commit()
                    st.success("Erfolgreich gebucht!")

    with tab4:
        st.subheader("Historie bearbeiten")
        df = pd.read_sql("SELECT r.id, m.meter_number, m.meter_type, r.reading_date, r.reading_value FROM meter_readings r JOIN meters m ON r.meter_id = m.id ORDER BY r.reading_date DESC", conn)
        edited = st.data_editor(df, num_rows="dynamic", key="edit_m", column_config={"id": None})
        if st.button("💾 Alle Änderungen speichern"):
            for _, row in edited.iterrows():
                cur.execute("UPDATE meter_readings SET reading_value = %s, reading_date = %s WHERE id = %s", (row['reading_value'], row['reading_date'], row['id']))
            conn.commit()
            st.success("Datenbank aktualisiert!")
            st.rerun()

    cur.close()
    conn.close()