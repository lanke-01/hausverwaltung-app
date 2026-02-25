import streamlit as st
import pandas as pd
from database import get_conn
from datetime import datetime

st.set_page_config(page_title="Zählerstände", layout="wide")
st.title("📟 Zählerverwaltung & Differenzmessung")

conn = get_conn()
cur = conn.cursor()

# Tabellen-Initialisierung (für GitHub-Clean-Install)
cur.execute("""
    CREATE TABLE IF NOT EXISTS meters (
        id SERIAL PRIMARY KEY,
        apartment_id INTEGER,
        meter_type TEXT,
        meter_number TEXT,
        is_submeter BOOLEAN DEFAULT FALSE,
        parent_meter_id INTEGER
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS meter_readings (
        id SERIAL PRIMARY KEY,
        meter_id INTEGER REFERENCES meters(id),
        reading_date DATE DEFAULT CURRENT_DATE,
        reading_value NUMERIC(12,2)
    )
""")
conn.commit()

tab1, tab2, tab3 = st.tabs(["Zähler-Struktur", "Ablesung erfassen", "Verbrauchs-Monitor"])

with tab1:
    st.subheader("Zähler registrieren")
    cur.execute("SELECT id, unit_name FROM apartments ORDER BY unit_name")
    apts = {name: tid for tid, name in cur.fetchall()}
    
    # Hauptzähler für die Auswahl laden
    cur.execute("SELECT id, meter_number, meter_type FROM meters WHERE is_submeter = FALSE")
    main_meters = {f"{m[2]} (Nr: {m[1]})": m[0] for m in cur.fetchall()}

    with st.form("new_meter"):
        c1, c2 = st.columns(2)
        with c1:
            apt = st.selectbox("Wohnung / Bereich", ["Allgemein"] + list(apts.keys()))
            m_type = st.selectbox("Typ", ["Strom", "Wasser", "Gas"])
            num = st.text_input("Zählernummer")
        with c2:
            sub = st.checkbox("Ist ein Unterzähler? (Wallbox/Abzugszähler)")
            parent = st.selectbox("Gehört zu Hauptzähler", ["Keiner"] + list(main_meters.keys()))
        
        if st.form_submit_button("Speichern"):
            a_id = apts[apt] if apt != "Allgemein" else None
            p_id = main_meters[parent] if parent != "Keiner" else None
            cur.execute("""
                INSERT INTO meters (apartment_id, meter_type, meter_number, is_submeter, parent_meter_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (a_id, m_type, num, sub, p_id))
            conn.commit()
            st.success("Zähler angelegt!")
            st.rerun()

with tab2:
    st.subheader("Messwert eingeben")
    cur.execute("""
        SELECT m.id, COALESCE(a.unit_name, 'Haus'), m.meter_type, m.meter_number 
        FROM meters m LEFT JOIN apartments a ON m.apartment_id = a.id
    """)
    m_opts = {f"{d[1]} - {d[2]} ({d[3]})": d[0] for d in cur.fetchall()}
    
    if m_opts:
        with st.form("reading"):
            m_sel = st.selectbox("Zähler", list(m_opts.keys()))
            val = st.number_input("Zählerstand", step=0.01)
            dat = st.date_input("Datum", datetime.now())
            if st.form_submit_button("Speichern"):
                cur.execute("INSERT INTO meter_readings (meter_id, reading_value, reading_date) VALUES (%s, %s, %s)",
                            (m_opts[m_sel], val, dat))
                conn.commit()
                st.success("Gespeichert!")

with tab3:
    st.subheader("Berechnete Verbräuche & Kosten (Differenzmessung)")
    
    # Preis abfragen
    c_preis, c_jahr = st.columns(2)
    strom_preis = c_preis.number_input("Strompreis pro kWh (€)", value=0.35, step=0.01)
    abr_jahr = c_jahr.number_input("Abrechnungsjahr", value=2024)

    # Verbräuche aus DB laden
    cur.execute("""
        SELECT 
            m.id, m.meter_number, m.meter_type, COALESCE(a.unit_name, 'Haus'), m.is_submeter,
            (SELECT reading_value FROM meter_readings WHERE meter_id = m.id ORDER BY reading_date DESC LIMIT 1) -
            (SELECT reading_value FROM meter_readings WHERE meter_id = m.id ORDER BY reading_date ASC LIMIT 1) as verbrauch
        FROM meters m
        LEFT JOIN apartments a ON m.apartment_id = a.id
        WHERE m.meter_type = 'Strom'
    """)
    rows = cur.fetchall()
    
    if rows:
        # Erstelle DataFrame für die Übersicht
        df = pd.DataFrame(rows, columns=["ID", "Zähler", "Typ", "Bereich", "Unterzähler", "Verbrauch"])
        
        # Sicherstellen, dass 'Verbrauch' eine Zahl ist (kein None)
        df['Verbrauch'] = df['Verbrauch'].fillna(0)
        
        st.dataframe(df, use_container_width=True)
        
        # Differenz-Berechnung (Hier wird alles in float umgewandelt, um den Fehler zu vermeiden)
        haupt_v = float(df[df['Unterzähler'] == False]['Verbrauch'].sum())
        sub_v = float(df[df['Unterzähler'] == True]['Verbrauch'].sum())
        netto_allgemein = haupt_v - sub_v
        
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"⚡ **Allgemeinstrom (Netto)**")
            st.metric("Verbrauch", f"{netto_allgemein:.2f} kWh")
            st.write(f"Kosten für alle: **{(netto_allgemein * float(strom_preis)):.2f} €**")
            st.caption("Verteilung nach Wohnfläche (m²)")
            
        with col2:
            st.success(f"🔌 **Wallbox (Unterzähler)**")
            st.metric("Verbrauch", f"{sub_v:.2f} kWh")
            st.write(f"Kosten Wallbox: **{(sub_v * float(strom_preis)):.2f} €**")
            st.caption("Direktzuordnung zum Mieter")

        st.divider()
        if st.button("💾 Diese Werte in Betriebskosten übernehmen"):
            try:
                # 1. Allgemeinstrom speichern
                cur.execute("""
                    INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year)
                    VALUES (%s, %s, %s, %s)
                """, ("Allgemeinstrom (Netto)", netto_allgemein * float(strom_preis), "area", abr_jahr))
                
                # 2. Wallbox speichern
                cur.execute("""
                    INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year)
                    VALUES (%s, %s, %s, %s)
                """, ("Wallbox-Strom", sub_v * float(strom_preis), "direct", abr_jahr))
                
                conn.commit()
                st.success("✅ Kosten wurden erfolgreich in die Ausgaben-Tabelle übertragen!")
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")
    else:
        st.info("Keine Stromzähler-Daten gefunden. Bitte Zählerstände erfassen.")

conn.close()