import psycopg2

def check_erika_home():
   try:
        # Verbindung zur Datenbank aufbauen
        conn = psycopg2.connect(
        dbname="hausverwaltung",
        user="postgres",
        password="mertali99",
        host="localhost"
            )
        cur = conn.cursor()

        query = """
            SELECT t.first_name, t.last_name, a.unit_name, a.base_rent, a.size_sqm
            FROM tenants t
            JOIN apartments a ON t.apartment_id = a.id
            WHERE t.last_name = 'Mustermann';
        """
        cur.execute(query)
        res = cur.fetchone()

        if res:
            f_name, l_name, unit, rent, size = res
            sqm_price = rent / size
            print(f"✅ Daten erfolgreich geladen!")
            print(f"----------------------------------")
            print(f"👤 Mieter: {f_name} {l_name}")
            print(f"🏠 Wohnung: {unit} ({size} m²)")
            print(f"💰 Miete: {rent}€ ({sqm_price:.2f}€/m²)")
            print(f"----------------------------------")
        else:
            print("❌ Erika oder ihre Wohnung wurde nicht gefunden.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    check_erika_home()