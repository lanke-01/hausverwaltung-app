# database.py
import psycopg2
import os
from dotenv import load_dotenv

# Lädt Variablen aus einer .env Datei (falls vorhanden)
load_dotenv()

def get_conn():
    """Zentrale Funktion für den Datenbankzugriff."""
    try:
        # Priorität 1: Umgebungsvariablen (für LXC/Docker)
        # Priorität 2: Standardwerte (localhost/postgres)
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "hausverwaltung"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASS", ""),
            host=os.getenv("DB_HOST", "127.0.0.1"), 
            port=os.getenv("DB_PORT", "5432")
        )
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        # Dies wird in Streamlit als Fehlermeldung angezeigt
        print(f"❌ Database Connection Error: {e}")
        return None
