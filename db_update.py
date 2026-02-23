import psycopg2

def update_database():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        cur = conn.cursor()
        
        # Fügt die Spaltee für Nebenkosten-Vorauszahlung hinzu, falls sie fehlt
        cur.execute("""
            ALTER TABLE apartments 
            ADD COLUMN IF NOT EXISTS service_charge_propayment DECIMAL(10,2) DEFAULT 0.00;
        """)
        
        conn.commit()
        print("✅ Datenbank erfolgreich aktualisiert: Spalte 'service_charge_propayment' ist bereit.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Fehler beim Update: {e}")

if __name__ == "__main__":
    update_database()
