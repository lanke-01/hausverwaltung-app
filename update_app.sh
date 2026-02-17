#!/bin/bash

APP_DIR="/opt/hausverwaltung"

echo "🔄 Suche nach Updates auf GitHub..."
cd $APP_DIR

# 1. Neuesten Code laden
git pull origin main

# 2. Abhängigkeiten prüfen (falls du neue Bibliotheken hinzugefügt hast)
echo "📦 Aktualisiere Python-Pakete..."
./venv/bin/pip install -r requirements.txt --upgrade 2>/dev/null || ./venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv



echo "✅ Update erfolgreich abgeschlossen!"
# In deinem update_app.sh statt der alten Restart-Zeile:
systemctl restart hausverwaltung && echo "✅ Dienst neu gestartet!" || echo "❌ Fehler beim Neustart!"