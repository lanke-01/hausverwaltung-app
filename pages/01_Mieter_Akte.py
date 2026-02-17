import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_conn
from fpdf import FPDF

# --- HILFSFUNKTION FÜR BERECHNUNG ---
def berechne_anteil(art, haus_betrag, mieter_flaeche, haus_flaeche, mieter_personen, haus_personen, mieter_einheit, haus_einheiten, tage):
    # Zuordnung der Schlüssel gemäß Referenz-PDF
    sqm_keys = ["Grundsteuer", "Sach- & Haftpflichtversicherung", "Sach- und Haftpflichtversicherung", "Schornsteinfeger"]
    person_keys = ["Kaltwasser", "Entwässerung", "Straßenreinigung und Müll", "Beleuchtung", "Allgemeinstrom"]
    unit_keys = ["Gartenpflege", "Hausmeister", "Fernsehen", "Sonstiges"]

    zeit_faktor = tage / 365.0
    
    if art in sqm_keys:
        schl = f"{mieter_flaeche}/{haus_flaeche}"
        anteil = (haus_betrag / haus_flaeche) * mieter_flaeche * zeit_faktor
    elif art in person_keys:
        # Berechnung nach Personentagen: (Hauskosten / Gesamtpersonentage) * Mieterpersonentage
        ges_pers_tage = haus_personen * 365
        mieter_pers_tage = mieter_personen * tage
        schl = f"{mieter_pers_tage}/{ges_pers_tage}"
        anteil = (haus_betrag / ges_pers_tage) * mieter_pers_tage
    elif art in unit_keys:
        schl = f"1/{haus_einheiten}"
        anteil = (haus_betrag / haus_einheiten) * zeit_faktor
    else:
        # Standardfall m2
        schl = f"{mieter_flaeche}/{haus_flaeche}"
        anteil = (haus_betrag / haus_flaeche) * mieter_flaeche * zeit_faktor
        
    return round(anteil, 2), schl

# --- OPTIMIERTE ABRECHNUNGSLOGIK ---
# (In Ihrer 01_Mieter_Akte.py innerhalb des 'tab_billing' Blocks ersetzen)

# 1. Benötigte Gesamtwerte laden
cur.execute("SELECT total_area, total_occupants, total_units FROM landlord_settings WHERE id = 1")
haus_stats = cur.fetchone()
h_sqm, h_pers, h_units = float(haus_stats[0] or 1), int(haus_stats[1] or 1), int(haus_stats[2] or 1)

# 2. Mieterdaten
cur.execute("SELECT area, occupants FROM tenants WHERE id = %s", (t_id,))
m_stats = cur.fetchone()
m_sqm, m_pers = float(m_stats[0] or 0), int(m_stats[1] or 0)

# 3. Berechnungsschleife
billing_rows = []
total_share = 0.0

for _, row in df_expenses.iterrows():
    betrag = float(row['amount'])
    art = row['expense_type']
    
    anteil, schlüssel = berechne_anteil(
        art, betrag, m_sqm, h_sqm, m_pers, h_pers, 1, h_units, tage
    )
    
    total_share += anteil
    billing_rows.append({
        "Kostenart": art,
        "Haus Gesamt": f"{betrag:.2f}",
        "Verteilung": schlüssel,
        "Ihr Anteil": f"{anteil:.2f}"
    })