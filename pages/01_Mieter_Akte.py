import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="Nebenkostenabrechnung", layout="wide")

def get_conn():
    conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
    conn.set_client_encoding('UTF8')
    return conn

st.title("🔍 Mieter-Akte & Präzise Abrechnung")

conn = get_conn()
cur = conn.cursor()

# 1. Mieter auswählen
cur.execute("SELECT id, first_name || ' ' || last_name FROM tenants ORDER BY last_name")
tenant_map = {name: tid for tid, name in cur.fetchall()}

if tenant_map:
    search_name = st.selectbox("Mieter auswählen", options=list(tenant_map.keys()))
    t_id = tenant_map[search_name]
    
    cur.execute("""
        SELECT t.first_name, t.last_name, a.unit_name, a.size_sqm, t.occupants, 
               a.base_rent, a.service_charge_propayment, a.id, t.moved_in, t.moved_out
        FROM tenants t
        JOIN apartments a ON t.apartment_id = a.id
        WHERE t.id = %s
    """, (t_id,))
    t_data = cur.fetchone()
    
    t_name = f"{t_data[0]} {t_data[1]}"
    t_size = float(t_data[3])
    t_occ = int(t_data[4])
    t_prepay_mo = float(t_data[6])
    t_in = t_data[8]
    t_out = t_data[9]

    tab_info, tab_billing = st.tabs(["📋 Stammdaten", "📄 Abrechnung (Taggenau)"])

    with tab_info:
        st.write(f"**Mieter:** {t_name} | **Einzug:** {t_in} | **Auszug:** {t_out if t_out else 'Aktiv'}")

    with tab_billing:
        jahr = st.selectbox("Abrechnungsjahr", [2024, 2025, 2026], index=2)
        
        # --- ZEITRAUM BERECHNEN ---
        jahr_start = date(jahr, 1, 1)
        jahr_ende = date(jahr, 12, 31)
        
        # Tatsächlicher Start im Jahr (Einzugsdatum oder 01.01.)
        calc_start = max(jahr_start, t_in)
        
        # Tatsächliches Ende im Jahr (Auszugsdatum oder 31.12.)
        if t_out:
            calc_ende = min(jahr_ende, t_out)
        else:
            calc_ende = jahr_ende
            
        # Nutzungstage berechnen
        nutzungstage = (calc_ende - calc_start).days + 1
        if nutzungstage < 0: nutzungstage = 0
        
        st.info(f"Nutzungszeitraum im Jahr {jahr}: **{calc_start} bis {calc_ende} ({nutzungstage} Tage)**")

        # --- BASISWERTE ---
        cur.execute("SELECT SUM(size_sqm) FROM apartments")
        total_house_area = float(cur.fetchone()[0] or 1.0)
        
        cur.execute("SELECT COUNT(*) FROM apartments")
        total_units = cur.fetchone()[0] or 1
        
        # Gesamte Personentage des Hauses (Müsste idealerweise auch taggenau pro Mieter summiert werden)
        cur.execute("SELECT SUM(occupants * 365) FROM tenants")
        total_person_days_house = float(cur.fetchone()[0] or 1.0)
        
        mieter_person_days = float(t_occ * nutzungstage)

        # Kosten laden
        df_expenses = pd.read_sql("SELECT expense_type, amount, distribution_key FROM operating_expenses WHERE expense_year = %s", conn, params=(jahr,))
        
        if not df_expenses.empty and nutzungstage > 0:
            billing_rows = []
            total_tenant_share = 0.0
            
            for _, row in df_expenses.iterrows():
                g_cost = float(row['amount'])
                dist_key = row['distribution_key']
                
                # Anteil Zeit (Nutzungstage / 365)
                zeit_faktor = nutzungstage / 365.0
                
                if dist_key == 'area':
                    u_cost = (g_cost * (t_size / total_house_area)) * zeit_faktor
                    anteil_str = f"{t_size}m² / {total_house_area}m²"
                elif dist_key == 'unit':
                    u_cost = (g_cost / total_units) * zeit_faktor
                    anteil_str = f"1 / {total_units} Einheiten"
                elif dist_key == 'persons':
                    u_cost = g_cost * (mieter_person_days / total_person_days_house)
                    anteil_str = f"{int(mieter_person_days)} / {int(total_person_days_house)} Pers.Tage"
                else:
                    u_cost = g_cost * zeit_faktor
                    anteil_str = "Direkt"

                total_tenant_share += u_cost
                billing_rows.append({
                    "Kostenart": row['expense_type'],
                    "Gesamt Haus": f"{g_cost:.2f} €",
                    "Anteil": anteil_str,
                    "Ihre Kosten": f"{round(u_cost, 2):.2f} €"
                })

            st.table(pd.DataFrame(billing_rows))
            
            # --- VORAUSZAHLUNG BERECHNEN ---
            # (Monatlicher Betrag / 30.42 Tage im Schnitt * Nutzungstage)
            tages_prepay = (t_prepay_mo * 12) / 365
            total_prepaid_real = tages_prepay * nutzungstage
            
            diff = total_prepaid_real - total_tenant_share
            
            st.divider()
            col_a, col_b = st.columns(2)
            with col_b:
                st.write(f"Berechneter Kostenanteil: **{total_tenant_share:.2f} €**")
                st.write(f"Geleistete Vorauszahlung ({nutzungstage} Tage): **{total_prepaid_real:.2f} €**")
                if diff >= 0:
                    st.success(f"**Guthaben: {diff:.2f} €**")
                else:
                    st.error(f"**Nachzahlung: {abs(diff):.2f} €**")
        else:
            st.warning("Keine Daten für den Zeitraum verfügbar.")

conn.close()