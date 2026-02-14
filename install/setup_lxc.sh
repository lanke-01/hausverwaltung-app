#!/bin/bash

# 1. Nächste freie ID finden
CTID=$(pvesh get /cluster/nextid)
echo "--- Verfügbare Storages auf diesem Knoten: ---"
pvesm status

# 2. Abfragen
echo ""
echo -n "Storage für Template (z.B. local): "
read STORAGE
echo -n "Storage für Container-Disk (z.B. local-lvm): "
read CT_STORAGE
echo -n "Root-Passwort für LXC: "
read -s PASSWORD
echo ""

# 3. Das aktuellste Debian 12 Template automatisch finden
echo "--- Suche aktuelles Debian 12 Template ---"
pveam update
TEMPLATE_NAME=$(pveam available --section system | grep "debian-12" | awk '{print $2}' | head -n 1)

if [ -z "$TEMPLATE_NAME" ]; then
    echo "FEHLER: Kein Debian 12 Template gefunden!"
    exit 1
fi

# 4. Download & Erstellen
echo "Nutze Template: $TEMPLATE_NAME"
pveam download $STORAGE $TEMPLATE_NAME

echo "--- Erstelle Container $CTID ---"
pct create $CTID $STORAGE:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1

# 5. Aufräumen Template
TEMPLATE_PATH=$(pvesm path $STORAGE:vztmpl/$TEMPLATE_NAME)
rm $TEMPLATE_PATH

# 6. Start
pct start $CTID
echo "Warte auf Boot-Vorgang und Netzwerk (30s)..."
sleep 30

# 7. Software-Installation
echo "--- Installiere System-Software ---"
pct exec $CTID -- bash -c "apt update && apt install -y postgresql git python3 python3-pip python3-venv libpq-dev"

# 8. GitHub & Datenbank Setup
echo -n "GitHub-Benutzername: "
read GITHUB_USER
echo -n "GitHub Personal Access Token (PAT): "
read -s GITHUB_TOKEN
echo ""

echo "--- Klone Repository und richte Datenbank ein ---"
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
# Klonen mit Token für reibungslosen Ablauf
pct exec $CTID -- bash -c "git clone https://$GITHUB_USER:$GITHUB_TOKEN@github.com/$GITHUB_USER/hausverwaltung-app.git /opt/hausverwaltung"

# 9. Automatisierte Konfiguration (Schema & Python)
echo "--- Führe automatisierte Konfiguration aus ---"

# Datenbank-Tabellen anlegen
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/database/init_schema.sql'"

# Python venv und Abhängigkeiten
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install psycopg2-binary"

# Optional: Falls du eine seed_data.sql hast, hier importieren
 pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/database/seed_data.sql'"

echo "--- INSTALLATION ERFOLGREICH ---"
echo "Container ID: $CTID"
echo "Hostname: hausverwaltung-app"