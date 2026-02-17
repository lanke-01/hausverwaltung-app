import psycopg2

def add_new_apartment():
    print("--- Neue Wohnung anlegen ---")
    name = input("Bezeichnung (z.B. OG rechts): ")
    sqm = float(input("Größe in m²: "))
    rent = float(input("Kaltmiete in Euro: "))

    try:
        # Tipp: Wir lassen host weg, um den lokalen Socket zu nutzen (einfacher)
        conn = psycopg2.connect(
            dbname="hausverwaltung",
            user="postgres"
        )
        cur = conn.cursor()

        # SQL Befehl mit Platzhaltern (Sicher gegen SQL-Injection!)
        query = "INSERT INTO apartments (unit_name, size_sqm, base_rent) VALUES (%s, %s, %s) RETURNING id;"
        cur.execute(query, (name, sqm, rent))
        
        new_id = cur.fetchone()[0]
        conn.commit()

        print(f"✅ Erfolg! Wohnung '{name}' wurde mit ID {new_id} angelegt.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    add_new_apartment()