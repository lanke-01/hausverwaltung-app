#!/bin/bash

# 1. Nächste freie ID finden
CTID=$(pvesh get /cluster/nextid)

# --- STORAGE AUSWAHL LOGIK ---
echo "--- Storage-Konfiguration ---"
TEMPLATE_STORAGES=($(pvesm status --content vztmpl | awk 'NR>1 {print $1}' | grep "local"))
DISK_STORAGES=($(pvesm status --content rootdir | awk 'NR>1 {print $1}'))

echo "Wähle den Storage für das TEMPLATE:"
PS3="Nummer wählen: "
select TEMPLATE_STRG in "${TEMPLATE_STORAGES[@]}"; do
    [ -n "$TEMPLATE_STRG" ] && STORAGE=$TEMPLATE_STRG && break
done

echo "Wähle den Storage für die DISK:"
select DISK_STRG in "${DISK_STORAGES[@]}"; do
    [ -n "$DISK_STRG" ] && CT_STORAGE=$DISK_STRG && break
done

echo -n "Root-Passwort für den neuen LXC: "
read -s PASSWORD
echo ""

# 3. Debian 12 Template herunterladen
echo "--- Lade Debian Template herunter ---"
pveam update
TEMPLATE_NAME=$(pveam available --section system | grep "debian-12" | awk '{print $2}' | head -n 1)
pveam download $STORAGE $TEMPLATE_NAME

# 4. Container Erstellung
echo "--- Erstelle Container $CTID ---"
pct create $CTID $STORAGE:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1

if [ $? -ne 0 ]; then
    echo "FEHLER beim Erstellen des Containers!"
    exit 1
fi

# 5. Startvorgang
pct start $CTID
echo "Warte auf Netzwerk (20s)..."
sleep 20

# 6. Software-Installation
echo "--- Installiere System-Software (Postgres, Git, Python) ---"
pct exec $CTID -- bash -c "apt update && apt install -y postgresql git python3 python3-pip python3-venv libpq-dev"

# 7. GitHub Projekt laden
GITHUB_USER="lanke-01"
REPO_NAME="hausverwaltung-app"
echo "--- Klone Repository ---"
pct exec $CTID -- bash -c "git clone https://github.com/$GITHUB_USER/$REPO_NAME.git /opt/hausverwaltung"

# 8. Datenbank Einrichtung
echo "--- Richte Datenbank ein ---"
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
# Falls die SQL-Dateien existieren, werden sie importiert
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/database/init_schema.sql'" 2>/dev/null
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/database/seed_data.sql'" 2>/dev/null

# Sicherheitshalber die landlord_settings Tabelle anlegen, falls init_schema fehlte
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -c \"CREATE TABLE IF NOT EXISTS landlord_settings (id SERIAL PRIMARY KEY, name VARCHAR(255), street VARCHAR(255), city VARCHAR(255), iban VARCHAR(50), bank_name VARCHAR(255)); INSERT INTO landlord_settings (id, name) SELECT 1, \'Bitte Daten eintragen\' WHERE NOT EXISTS (SELECT 1 FROM landlord_settings WHERE id = 1);\"'"

# 9. Python Umgebung & Module
echo "--- Richte Python Umgebung ein ---"
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install --upgrade pip"
# Installiere aus requirements.txt oder manuell
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv"

# 10. AUTOSTART DIENST ERSTELLEN
echo "--- Erstelle Systemd-Service ---"
pct exec $CTID -- bash -c "cat <<EOF > /etc/systemd/system/hausverwaltung.service
[Unit]
Description=Streamlit Hausverwaltung App
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hausverwaltung
ExecStart=/opt/hausverwaltung/venv/bin/streamlit run main.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF"

# Dienst aktivieren
pct exec $CTID -- bash -c "systemctl daemon-reload && systemctl enable hausverwaltung.service && systemctl start hausverwaltung.service"

# 11. IP ADRESSE AUSGEBEN
IP_ADDRESS=$(pct exec $CTID -- hostname -I | awk '{print $1}')

echo ""
echo "================================================================="
echo " 🎉 INSTALLATION ERFOLGREICH!"
echo "================================================================="
echo " Die App ist nun erreichbar unter:"
echo " URL:  http://$IP_ADDRESS:8501"
echo "================================================================="
echo " Container ID: $CTID"
echo " Viel Erfolg mit deiner Hausverwaltung!"
echo "================================================================="