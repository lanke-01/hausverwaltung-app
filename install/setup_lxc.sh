#!/bin/bash

# =================================================================
# Hausverwaltungs-App - Automatischer LXC Installer
# =================================================================

# 1. Nächste freie ID finden
CTID=$(pvesh get /cluster/nextid)
echo "--- Verfügbare Storages auf diesem Knoten: ---"
pvesm status

# 2. Benutzereingaben
echo ""
echo "--- Installation startet für Container ID: $CTID ---"
echo -n "Storage für Template (z.B. local): "
read STORAGE
echo -n "Storage für Container-Disk (z.B. local-lvm): "
read CT_STORAGE
echo -n "Root-Passwort für den neuen LXC: "
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

# 4. Download & Container Erstellung
echo "Nutze Template: $TEMPLATE_NAME"
pveam download $STORAGE $TEMPLATE_NAME

echo "--- Erstelle Container $CTID ---"
pct create $CTID $STORAGE:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1

# 5. Aufräumen Template (spart Platz)
TEMPLATE_PATH=$(pvesm path $STORAGE:vztmpl/$TEMPLATE_NAME)
rm $TEMPLATE_PATH

# 6. Startvorgang
pct start $CTID
echo "Warte auf Boot-Vorgang und Netzwerk (30s)..."
sleep 30

# 7. Software-Installation im Container
echo "--- Installiere System-Software (PostgreSQL, Git, Python) ---"
pct exec $CTID -- bash -c "apt update && apt install -y postgresql git python3 python3-pip python3-venv libpq-dev"

# 8. GitHub Projekt laden (Öffentliches Repo)
GITHUB_USER="lanke-01"
REPO_NAME="hausverwaltung-app"

echo "--- Klone Repository von GitHub ---"
pct exec $CTID -- bash -c "git clone https://github.com/$GITHUB_USER/$REPO_NAME.git /opt/hausverwaltung"

# 9. Datenbank Einrichtung
echo "--- Richte PostgreSQL Datenbank ein ---"
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"

# Schema importieren
echo "--- Importiere Tabellen-Struktur ---"
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/database/init_schema.sql'"

# Testdaten importieren
echo "--- Importiere Standard-Kostenarten und Testmieter ---"
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/database/seed_data.sql'"

# 10. Python Umgebung (Venv) vorbereiten
echo "--- Richte Python Virtuelle Umgebung ein ---"
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install psycopg2-binary"

# 11. Abschluss
echo ""
echo "================================================================="
echo "   INSTALLATION ERFOLGREICH ABGESCHLOSSEN!"
echo "================================================================="
echo "Container ID:   $CTID"
echo "Hostname:       hausverwaltung-app"
echo "Projekt-Pfad:   /opt/hausverwaltung"
echo "Datenbank:      PostgreSQL (DB: hausverwaltung)"
echo ""
echo "Du kannst den Container jetzt betreten mit: pct enter $CTID"
echo "================================================================="