import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

# --- DATENBANK VERBINDUNG ---
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

    # Tabellen & Spalten sicherstellen
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
            meter_id INTEGER REFERENCES meters(id) ON DELETE CASCADE,
            reading_date DATE DEFAULT CURRENT_DATE,
            reading_value NUMERIC(12,2)
        )
    """)
    # NEU: Spalte für Mieter-Zuordnung in den Ausgaben sicherstellen
    cur.execute("ALTER TABLE operating_expenses ADD COLUMN IF NOT EXISTS tenant_id INTEGER")
    conn.commit()

    # Vier Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏗️ Zähler-Struktur", 
        "✍️ Ablesung erfassen", 
        "📊 Verbrauchs-Monitor", 
        "📜 Verlauf & Korrektur"
    ])

    # --- TAB 1: ZÄHLER REGISTRIEREN ---
    with tab1:
        st.subheader("Neuen Zähler anlegen")
        cur.execute("SELECT id, unit_name FROM apartments ORDER BY unit_name")
        apts = {name: tid for tid, name in cur.fetchall()}
        
        with st.form("new_meter"):
            m_type = st.selectbox("Typ", ["Strom", "Wasser", "Heizung", "Gas"])
            m_num = st.text_input("Zählernummer (z.B. 1ISK...)")
            m_apt = st.selectbox("Zuordnung Wohneinheit", ["Haus (Allgemein)"] + list(apts.keys()))
            is_sub = st.checkbox("Ist ein Unterzähler? (z.B. Wallbox)")
            
            if st.form_submit_button("Zähler speichern"):
                apt_id = apts[m_apt] if m_apt != "Haus (Allgemein)" else None
                cur.execute("""
                    INSERT INTO meters (apartment_id, meter_type, meter_number, is_submeter)
                    VALUES (%s, %s, %s, %s)
                """, (apt_id, m_type, m_num, is_sub))
                conn.commit()
                st.success(f"Zähler {m_num} registriert!")
                st.rerun()

    # --- TAB 2: ABLESUNG ERFASSEN ---
    with tab2:
        st.subheader("Zählerstand eingeben")
        cur.execute("""
            SELECT m.id, COALESCE(a.unit_name, 'Haus'), m.meter_type, m.meter_number 
            FROM meters m LEFT JOIN apartments a ON m.apartment_id = a.id
        """)
        m_opts = {f"{d[1]} - {d[2]} ({d[3]})": d[0] for d in cur.fetchall()}
        
        if m_opts:
            with st.form("reading_form"):
                m_sel = st.selectbox("Zähler wählen", list(m_opts.keys()))
                val = st.number_input("Aktueller Zählerstand", step=0.01)
                dat = st.date_input("Ablesedatum", datetime.now())
                if st.form_submit_button("💾 Stand speichern"):
                    cur.execute("""
                        INSERT INTO meter_readings (meter_id, reading_value, reading_date) 
                        VALUES (%s, %s, %s)
                    """, (m_opts[m_sel], val, dat))
                    conn.commit()
                    st.success("Erfolgreich gespeichert!")
        else:
            st.warning("Bitte erst Zähler in Tab 1 anlegen.")

    # --- TAB 3: VERBRAUCHS-MONITOR (MIT MIETER-ZUWEISUNG) ---
    with tab3:
        st.subheader("Berechnete Verbräuche & Kosten")
        
        c_p, c_j = st.columns(2)
        strom_preis = c_p.number_input("Strompreis pro kWh (€)", value=0.35, step=0.01)
        abr_jahr = c_j.number_input("Abrechnungsjahr", value=2024)

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
            df = pd.DataFrame(rows, columns=["ID", "Zähler", "Typ", "Bereich", "Unterzähler", "Verbrauch"])
            df['Verbrauch'] = df['Verbrauch'].fillna(0)
            st.dataframe(df, use_container_width=True)
            
            haupt_v = float(df[df['Unterzähler'] == False]['Verbrauch'].sum())
            sub_v = float(df[df['Unterzähler'] == True]['Verbrauch'].sum())
            netto_allgemein = haupt_v - sub_v
            
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.info("⚡ Allgemeinstrom (Netto)")
                st.metric("Verbrauch", f"{netto_allgemein:.2f} kWh")
                st.write(f"Kosten: **{(netto_allgemein * float(strom_preis)):.2f} €**")
                st.caption("Verteilung auf alle m²")
            with col2:
                st.success("🔌 Wallbox (Unterzähler)")
                st.metric("Verbrauch", f"{sub_v:.2f} kWh")
                st.write(f"Kosten: **{(sub_v * float(strom_preis)):.2f} €**")
                st.caption("Direktzuordnung zu einem Mieter")

            st.divider()
            st.subheader("💾 Kosten verbuchen")
            
            # Mieter für Zuweisung laden
            cur.execute("SELECT id, first_name, last_name FROM tenants WHERE move_out IS NULL")
            tenants = {f"{t[1]} {t[2]}": t[0] for t in cur.fetchall()}
            
            if tenants:
                c_sel, c_btn = st.columns([2, 1])
                target_tenant = c_sel.selectbox("Welcher Mieter nutzt die Wallbox?", list(tenants.keys()))
                
                if c_btn.button("Jetzt in Betriebskosten speichern"):
                    try:
                        # 1. Allgemeinstrom für alle (tenant_id bleibt NULL)
                        cur.execute("""
                            INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year)
                            VALUES (%s, %s, %s, %s)
                        """, ("Allgemeinstrom (Netto)", netto_allgemein * float(strom_preis), "area", abr_jahr))
                        
                        # 2. Wallbox NUR für gewählten Mieter (mit tenant_id)
                        cur.execute("""
                            INSERT INTO operating_expenses (expense_type, amount, distribution_key, expense_year, tenant_id)
                            VALUES (%s, %s, %s, %s, %s)
                        """, ("Wallbox-Strom", sub_v * float(strom_preis), "direct", abr_jahr, tenants[target_tenant]))
                        
                        conn.commit()
                        st.success(f"✅ Gebucht! Wallbox wurde {target_tenant} zugewiesen.")
                    except Exception as e:
                        st.error(f"Fehler: {e}")
            else:
                st.warning("Keine aktiven Mieter für die Wallbox-Zuweisung gefunden.")
        else:
            st.info("Keine Stromzähler gefunden.")

    # --- TAB 4: VERLAUF & KORREKTUR ---
    with tab4:
        st.subheader("Ablesehistorie")
        cur.execute("""
            SELECT r.id, m.meter_number, m.meter_type, r.reading_date, r.reading_value, COALESCE(a.unit_name, 'Haus')
            FROM meter_readings r
            JOIN meters m ON r.meter_id = m.id
            LEFT JOIN apartments a ON m.apartment_id = a.id
            ORDER BY r.reading_date DESC, r.id DESC LIMIT 50
        """)
        history = cur.fetchall()
        for rid, m_num, m_type, r_date, r_val, unit in history:
            c1, c2, c3, c4 = st.columns([2,2,2,1])
            c1.write(f"{r_date}")
            c2.write(f"**{m_type}** ({m_num})")
            c3.write(f"{unit}: **{r_val}**")
            if c4.button("🗑️", key=f"del_{rid}"):
                cur.execute("DELETE FROM meter_readings WHERE id = %s", (rid,))
                conn.commit()
                st.rerun()
            st.divider()

    cur.close()
    conn.close()