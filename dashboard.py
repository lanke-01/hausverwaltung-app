import psycopg2
from datetime import datetime

def show_dashboard():
    # Aktuelles Datum für die Abfrage holen
    current_month = datetime.now().month
    current_year = datetime.now().year

    try:
        # Verbindung zur Datenbank
        conn = psycopg2.connect(
            dbname="hausverwaltung", 
            user="postgres"
        )
        cur = conn.cursor()

        print(f"\n==========================================")
        print(f"📊 HAUSVERWALTUNG DASHBOARD - {current_month:02d}/{current_year}")
        print(f"==========================================\n")

        # 1. Gesamteinnahmen diesen Monat berechnen
        cur.execute("""
            SELECT SUM(amount) FROM payments 
            WHERE period_month = %s AND period_year = %s;
        """, (current_month, current_year))
        total = cur.fetchone()[0] or 0.0
        print(f"💰 Einnahmen diesen Monat: {total:.2f} €")

        # 2. Mieter mit Zahlungsrückstand finden
        # Wir vergleichen die Summe der Zahlungen (Ist) mit der base_rent (Soll)
        query = """
            SELECT 
                t.first_name, 
                t.last_name, 
                a.base_rent, 
                COALESCE(SUM(p.amount), 0) as gezahlt
            FROM tenants t
            JOIN apartments a ON t.apartment_id = a.id
            LEFT JOIN payments p ON t.id = p.tenant_id 
                AND p.period_month = %s 
                AND p.period_year = %s
            GROUP BY t.id, t.first_name, t.last_name, a.base_rent
            HAVING COALESCE(SUM(p.amount), 0) < a.base_rent;
        """
        cur.execute(query, (current_month, current_year))
        debtors = cur.fetchall()

        print(f"\n⚠️  Zahlungsrückstand / Offene Mieten:")
        print(f"------------------------------------------")
        
        if not debtors:
            print("   ✅ Alle Mieten sind vollständig bezahlt!")
        else:
            for d in debtors:
                vorname, nachname, soll, ist = d
                offen = soll - ist
                print(f"   ❌ {vorname} {nachname}:")
                print(f"      Noch {offen:.2f} € offen (Soll: {soll:.2f} € | Gezahlt: {ist:.2f} €)")

        print(f"\n==========================================")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    show_dashboard()