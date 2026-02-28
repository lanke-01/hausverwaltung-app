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

    # Tabellen sicherstellen
    cur.execute("ALTER TABLE operating_expenses ADD COLUMN IF NOT EXISTS tenant_id INTEGER")
    conn.commit()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🏗️ Zähler anlegen", 
        "📝 Stand erfassen", 
        "⚖️ Differenzmessung (Wallbox)", 
        "⚙️ Stände bearbeiten"
    ])

    # ... (Tabs 1 & 2 bleiben gleich) ...
    with tab1:
        st.subheader("Neuen Zähler registrieren")
        with st.form("meter_form"):
            m_type = st.selectbox("Typ", ["Strom", "Wasser", "Gas", "Wärme"])
            m_num = st.text_input("Zählernummer")
            is_sub = st.checkbox("Ist ein Unterzähler? (z.B. Wallbox hängt an Hausstrom)")
            cur.execute("SELECT id, unit_name FROM apartments")
            apps = {row[1]: row[0] for row in cur.fetchall()}
            apps["Haus / Allgemein"] = None
            sel_app = st.selectbox("Zugehörigkeit", list(apps.keys()))
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
        st.subheader("Wallbox-Strom vs. Allgemeinstrom")
        cur.execute("SELECT id, meter_number FROM meters WHERE meter_type = 'Strom' AND is_submeter = FALSE")
        main_meters = cur.fetchall()
        cur.execute("SELECT id, meter_number FROM meters WHERE meter_type = 'Strom' AND is_submeter = TRUE")
        sub_meters = cur.fetchall()

        if main_meters and sub_meters:
            col1, col2 = st.columns(2)
            main_id = col1.selectbox("Hauptzähler (Haus)", [m[0] for m in main_meters], format_func=lambda x: next(m[1] for m in main_meters if m[0] == x))
            sub_id = col2.selectbox("Unterzähler (Wallbox)", [m[0] for m in sub_meters], format_func=lambda x: next(m[1] for m in sub_meters if m[0] == x))
            strom_preis = st.text_input("Strompreis pro kWh", "0.35")
            abr_jahr = st.number_input("Abrechnungsjahr", value=2024)

            if st.button("Verbrauch berechnen"):
                def get_consumption(m_id, jahr):
                    cur.execute("""
                        (SELECT reading_value FROM meter_readings WHERE meter_id = %s AND EXTRACT(YEAR FROM reading_date) = %s ORDER BY reading_date ASC LIMIT 1)
                        UNION ALL
                        (SELECT reading_value FROM meter_readings WHERE meter_id = %s AND EXTRACT(YEAR FROM reading_date) = %s ORDER BY reading_date DESC LIMIT 1)
                    """, (m_id, jahr, m_id, jahr))
                    res = cur.fetchall()
                    return float(res[1][0] - res[0][0]) if len(res) == 2 else 0.0

                main_v = get_consumption(main_id, abr_jahr)
                sub_v = get_consumption(sub_id, abr_jahr)
                netto_allgemein = main_v - sub_v

                st.session_state['calc_done'] = {
                    'netto': netto_allgemein * float(strom_preis),
                    'sub': sub_v * float(strom_preis),
                    'jahr': abr_jahr
                }
                st.write(f"Netto-Allgemeinstrom: **{netto_allgemein:.2f} kWh ({st.session_state['calc_done']['netto']:.2f} €)**")
                st.write(f"Wallbox: **{sub_v:.2f} kWh ({st.session_state['calc_done']['sub']:.2f} €)**")

            if 'calc_done' in st.session_state:
                cur.execute("SELECT id, first_name, last_name FROM tenants WHERE move_in <= %s AND (move_out IS NULL OR move_out >= %s)", (date(st.session_state['calc_done']['jahr'], 12, 31), date(st.session_state['calc_done']['jahr'], 1, 1)))
                t_data = cur.fetchall()
                t_list = {f"{r[1]} {r[2]}": r[0] for r in t_data}
                target_tenant = st.selectbox("Wallbox Mieter zuweisen", list(t_list.keys()))

                if st.button("Kosten jetzt buchen"):
                    # Netto Allgemein bekommt tenant_id = -1 (unsichtbar für Mieter)
                    cur.execute("INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year, tenant_id) VALUES (%s, %s, %s, %s, -1)", 
                               ("Allgemeinstrom (Netto)", st.session_state['calc_done']['netto'], "area", st.session_state['calc_done']['jahr']))
                    # Wallbox bekommt echte tenant_id
                    cur.execute("INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year, tenant_id) VALUES (%s, %s, %s, %s, %s)", 
                               ("Wallbox-Strom", st.session_state['calc_done']['sub'], "direct", st.session_state['calc_done']['jahr'], t_list[target_tenant]))
                    conn.commit()
                    st.success("Erfolgreich gebucht!")

    with tab4:
        st.subheader("Zählerstände bearbeiten")
        df = pd.read_sql("SELECT r.id, m.meter_number, m.meter_type, r.reading_date, r.reading_value FROM meter_readings r JOIN meters m ON r.meter_id = m.id ORDER BY r.reading_date DESC", conn)
        edited_df = st.data_editor(df, num_rows="dynamic", key="editor_readings", column_config={"id": None})
        if st.button("Änderungen speichern"):
            for _, row in edited_df.iterrows():
                cur.execute("UPDATE meter_readings SET reading_value = %s, reading_date = %s WHERE id = %s", (row['reading_value'], row['reading_date'], row['id']))
            conn.commit()
            st.success("Gespeichert!")
            st.rerun()