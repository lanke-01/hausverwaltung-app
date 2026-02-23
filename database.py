import psycopg2

def get_conn():
    try:
        # Wir geben NUR den Datenbanknamen und User an.
        # Ohne 'host' nutzt Python automatisch den lokalen Socket,
        # genau wie dein erfolgreicher 'psql' Befehl eben.
        conn = psycopg2.connect(
            dbname="hausverwaltung",
            user="postgres"
        )
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        # Falls es im Streamlit-Log auftaucht
        print(f"Verbindungsfehler: {e}")
        return None
