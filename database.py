# database.py
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    """Erstellt eine Verbindung zur PostgreSQL Datenbank."""
    try:
        # Im LXC-Container (nach dem Trust-Fix) reicht oft der lokale Zugriff
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "hausverwaltung"),
            user=os.getenv("DB_USER", "postgres"),
            host=os.getenv("DB_HOST", "127.0.0.1"),
            password=os.getenv("DB_PASS", "")
        )
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        print(f"❌ Datenbankverbindung fehlgeschlagen: {e}")
        return None
