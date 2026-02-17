import streamlit as st
import pandas as pd
from datetime import datetime
from database import get_conn  # Zentraler Import

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="Hausverwaltung Dashboard", layout="wide")

st.title("🏠 Hausverwaltung Dashboard")
st.write(f"Statusübersicht für **{datetime.now().strftime('%B %Y')}**")

conn = get_conn()

if conn:
    try:
        cur = conn.cursor()

        # --- 1. KENNZAHLEN (METRIKEN) ---
        col1, col2, col3, col4 = st.columns(4)
        
        # Gesamtfläche & Einheiten
        cur.execute("SELECT SUM(size_sqm), COUNT(*) FROM apartments")
        stats = cur.fetchone()
        total_sqm = float(stats[0] or 0.0)
        total_apts = stats[1] or 0
        
        # Aktive Mieter
        cur.execute("SELECT COUNT(*) FROM tenants WHERE moved_out IS NULL")
        active_tenants = cur.fetchone()[0] or 0
        
        with col1:
            st.metric("Gesamtfläche", f"{total_sqm:.2f} qm")
        with col2:
            st.metric("Wohneinheiten", total_apts)
        with col3:
            st.metric("Aktive Mieter", active_tenants)
        with col4:
            leerstand = total_apts - active_tenants
            st.metric("Leerstand", leerstand, delta=-leerstand, delta_color="inverse")

        st.divider()

        # --- 2. MIET-TRACKER (WER HAT NOCH NICHT GEZAHLT?) ---
        st.subheader("📌 Mietzahlungen aktueller Monat")
        
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Abfrage: Alle Mieter, die diesen Monat noch NICHT in der 'payments' Tabelle stehen
        query_missing = """
            SELECT t.first_name || ' ' || t.last_name as Mieter, 
                   a.unit_name as Wohnung, 
                   (a.base_rent + a.service_charge_propayment) as "Soll-Miete (Euro)"
            FROM tenants t
            JOIN apartments a ON t.apartment_id = a.id
            WHERE t.moved_out IS NULL
            AND t.id NOT IN (
                SELECT tenant_id FROM payments 
                WHERE period_month = %s AND period_year = %s
            )
        """
        df_missing = pd.read_sql(query_missing, conn, params=(current_month, current_year))
        
        c_left, c_right = st.columns([2, 1])
        
        with c_left:
            if not df_missing.empty:
                st.warning(f"⚠️ Folgende {len(df_missing)} Mieter haben diesen Monat noch nicht bezahlt:")
                st.table(df_missing)
            else:
                st.success("✅ Alle Mieter haben für diesen Monat bereits bezahlt!")

        with c_right:
            # Einnahmen-Statistik
            cur.execute("""
                SELECT SUM(amount) FROM payments 
                WHERE period_month = %s AND period_year = %s
            """, (current_month, current_year))
            ist_summe = float(cur.fetchone()[0] or 0.0)
            
            soll_summe = df_missing["Soll-Miete (Euro)"].sum() + ist_summe
            
            st.write("**Finanz-Check**")
            st.write(f"Soll-Einnahmen: {soll_summe:.2f} Euro")
            st.write(f"Ist-Einnahmen: {ist_summe:.2f} Euro")
            
            progress = (ist_summe / soll_summe) if soll_summe > 0 else 0
            st.progress(progress)
            st.write(f"{progress*100:.1f}% der Mieten sind eingegangen.")

        st.divider()

        # --- 3. LETZTE AKTIVITÄTEN ---
        st.subheader("🕒 Letzte Zahlungseingänge")
        df_recent = pd.read_sql("""
            SELECT t.last_name as Mieter, p.amount as "Betrag (Euro)", p.payment_date as Datum
            FROM payments p
            JOIN tenants t ON p.tenant_id = t.id
            ORDER BY p.payment_date DESC LIMIT 5
        """, conn)
        
        if not df_recent.empty:
            st.dataframe(df_recent, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Fehler im Dashboard: {e}")
    finally:
        conn.close()
else:
    st.error("Keine Datenbankverbindung möglich.")