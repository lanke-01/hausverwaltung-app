import psycopg2

def get_conn():
    try:
        # Verbindung über den lokalen Unix-Socket (Standard im LXC)
        conn = psycopg2.connect(
            dbname="hausverwaltung",
            user="postgres",
            host="/var/run/postgresql"  # Erzwingt den lokalen Socket
        )
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        return None
