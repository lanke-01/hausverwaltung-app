import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_conn  # Zentraler Import

st.set_page_config(page_title="Nebenkostenabrechnung", layout="wide")

st.title("🔍 Mieter-Akte & Präzise Abrechnung")

conn = get_conn()
if conn:
    cur = conn.cursor()
    # Mieter auswählen
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
        
        t_name, t_size, t_occ = f"{t_data[0]} {t_data[1]}", float(t_data[3]), int(t_data[4])
        t_prepay_mo, t_in, t_out = float(t_data[6]), t_data[8], t_data[9]

        tab_info, tab_billing = st.tabs(["📋 Stammdaten", "📄 Abrechnung (Taggenau)"])

        with tab_billing:
            jahr = st.selectbox("Abrechnungsjahr", [2024, 2025, 2026], index=2)
            
            # Zeitraum berechnen
            jahr_start, jahr_ende = date(jahr, 1, 1), date(jahr, 12, 31)
            calc_start = max(jahr_start, t_in)
            calc_ende = min(jahr_ende, t_out) if t_out else jahr_ende
            nutzungstage = max((calc_ende - calc_start).days + 1, 0)
            
            st.info(f"Nutzungszeitraum: {calc_start} bis {calc_ende} ({nutzungstage} Tage)")

            # Haus-Gesamtwerte automatisch berechnen
            cur.execute("SELECT SUM(size_sqm) FROM apartments")
            total_house_area = float(cur.fetchone()[0] or 1.0)
            cur.execute("SELECT COUNT(*) FROM apartments")
            total_units = cur.fetchone()[0] or 1
            cur.execute("SELECT SUM(occupants * 365) FROM tenants")
            total_person_days_house = float(cur.fetchone()[0] or 1.0)
            
            mieter_person_days = float(t_occ * nutzungstage)

            df_expenses = pd.read_sql("SELECT expense_type, amount, distribution_key FROM operating_expenses WHERE expense_year = %s", conn, params=(jahr,))
            
            if not df_expenses.empty and nutzungstage > 0:
                billing_rows = []
                total_tenant_share = 0.0
                
                for _, row in df_expenses.iterrows():
                    g_cost, dist_key = float(row['amount']), row['distribution_key']
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
                        u_cost, anteil_str = g_cost * zeit_faktor, "Direkt"

                    total_tenant_share += u_cost
                    billing_rows.append({"Kostenart": row['expense_type'], "Gesamt Haus": f"{g_cost:.2f} €", "Anteil": anteil_str, "Ihre Kosten": f"{u_cost:.2f} €"})

                st.table(pd.DataFrame(billing_rows))
                total_prepaid_real = ((t_prepay_mo * 12) / 365) * nutzungstage
                diff = total_prepaid_real - total_tenant_share
                
                col_a, col_b = st.columns(2)
                with col_b:
                    st.write(f"Kostenanteil: **{total_tenant_share:.2f} €**")
                    st.write(f"Vorauszahlung: **{total_prepaid_real:.2f} €**")
                    if diff >= 0: st.success(f"**Guthaben: {diff:.2f} €**")
                    else: st.error(f"**Nachzahlung: {abs(diff):.2f} €**")
    conn.close()