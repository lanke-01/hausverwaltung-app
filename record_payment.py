import psycopg2
from datetime import datetime

def record_payment():
    print("--- Mietzahlung erfassen ---")
    t_id = input("Mieter-ID: ")
    amount = float(input("Betrag in Euro: "))
    month = int(input("Für Monat (1-12): "))
    year = datetime.now().year

    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        cur = conn.cursor()

        query = """
            INSERT INTO payments (tenant_id, amount, period_month, period_year)
            VALUES (%s, %s, %s, %s);
        """
        cur.execute(query, (t_id, amount, month, year))
        conn.commit()

        print(f"✅ Zahlung von {amount}Euro für Monat {month}/{year} wurde gespeichert.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    record_payment()
    
    