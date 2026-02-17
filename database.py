import psycopg2
import os
from dotenv import load_dotenv

# Lädt die Variablen aus der .env Datei
load_dotenv()

def get_conn():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "hausverwaltung"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASS", ""),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432")
        )
        return conn
    except Exception as e:
        print(f"Verbindung zur Datenbank fehlgeschlagen: {e}")
        return None
