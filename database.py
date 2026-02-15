import psycopg2
import os
from dotenv import load_dotenv

# Lädt die Variablen aus der .env Datei
load_dotenv()

def get_conn():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            host=os.getenv("DB_HOST")
        )
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        print(f"Fehler bei der Datenbankverbindung: {e}")
        return None
