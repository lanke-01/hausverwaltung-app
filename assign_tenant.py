import psycopg2

def link_tenant_to_apartment():
    try:
        conn = psycopg2.connect(dbname="hausverwaltung", user="postgres")
        cur = conn.cursor()

        # 1. Mieter ohne Wohnung anzeigen
        print("\n--- Mieter ohne Zuordnung ---")
        cur.execute("SELECT id, first_name, last_name FROM tenants WHERE apartment_id IS NULL;")
        tenants = cur.fetchall()
        for t in tenants:
            print(f"ID: {t[0]} | Name: {t[1]} {t[2]}")

        # 2. Alle Wohnungen anzeigen
        print("\n--- Verfügbare Wohnungen ---")
        cur.execute("SELECT id, unit_name FROM apartments;")
        apartments = cur.fetchall()
        for a in apartments:
            print(f"ID: {a[0]} | Wohnung: {a[1]}")

        # 3. Auswahl treffen
        t_id = input("\nWelche Mieter-ID soll umziehen? ")
        a_id = input("In welche Wohnungs-ID? ")

        # 4. Update in der Datenbank
        cur.execute("UPDATE tenants SET apartment_id = %s WHERE id = %s;", (a_id, t_id))
        conn.commit()

        print(f"\n✅ Mieter {t_id} wurde erfolgreich der Wohnung {a_id} zugeordnet!")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    link_tenant_to_apartment()