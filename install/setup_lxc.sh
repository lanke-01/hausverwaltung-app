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

echo "Nutze Template: $TEMPLATE_NAME"

# 4. Download
echo "--- Lade Template herunter ---"
pveam download $STORAGE $TEMPLATE_NAME

# 5. Container erstellen
echo "--- Erstelle Container $CTID ---"
pct create $CTID $STORAGE:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1

# 6. Aufräumen
TEMPLATE_PATH=$(pvesm path $STORAGE:vztmpl/$TEMPLATE_NAME)
echo "--- Lösche Template-Datei: $TEMPLATE_PATH ---"
rm $TEMPLATE_PATH

# 7. Start und Einrichtung
pct start $CTID
echo "Warte auf Boot-Vorgang (20s)..."
sleep 20

echo "--- Installiere Software im Container ---"
# Fix: Wir erzwingen eine kurze Pause, damit das Netzwerk im CT sicher da ist
pct exec $CTID -- bash -c "apt update && apt install -y postgresql git python3 python3-pip python3-venv"

echo -n "GitHub-Benutzername: "
read GITHUB_USER

pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
pct exec $CTID -- bash -c "git clone https://github.com/$GITHUB_USER/hausverwaltung-app.git /opt/hausverwaltung"
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/database/init_schema.sql'"

echo "--- INSTALLATION ERFOLGREICH ---"
echo "Container ID: $CTID"