import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "hausverwaltung"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASS", ""),
            host=os.getenv("DB_HOST", "127.0.0.1"), # WICHTIG
            port=os.getenv("DB_PORT", "5432")
        )
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        print(f"Verbindung fehlgeschlagen: {e}")
        return None