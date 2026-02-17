#!/bin/bash

# 1. Nächste freie ID finden
CTID=$(pvesh get /cluster/nextid)

# --- STORAGE AUSWAHL LOGIK ---
echo "--- Storage-Konfiguration ---"

# Wir holen nur Storages, die 'vztmpl' (Templates) unterstützen
TEMPLATE_STORAGES=($(pvesm status --content vztmpl | awk 'NR>1 {print $1}' | grep "local"))
# Wir holen nur Storages, die 'rootdir' (Container Disks) unterstützen
DISK_STORAGES=($(pvesm status --content rootdir | awk 'NR>1 {print $1}'))

echo "Wähle den Storage für das TEMPLATE (muss Templates unterstützen):"
PS3="Nummer wählen (1-${#TEMPLATE_STORAGES[@]}): "
select TEMPLATE_STRG in "${TEMPLATE_STORAGES[@]}"; do
    if [ -n "$TEMPLATE_STRG" ]; then
        STORAGE=$TEMPLATE_STRG
        echo "Gewählt für Template: $STORAGE"
        break
    fi
done

echo ""
echo "Wähle den Storage für die DISK (wo der Container gespeichert wird):"
PS3="Nummer wählen (1-${#DISK_STORAGES[@]}): "
select DISK_STRG in "${DISK_STORAGES[@]}"; do
    if [ -n "$DISK_STRG" ]; then
        CT_STORAGE=$DISK_STRG
        echo "Gewählt für Disk: $CT_STORAGE"
        break
    fi
done

echo ""
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
echo "Lade Template $TEMPLATE_NAME auf $STORAGE herunter..."
pveam download $STORAGE $TEMPLATE_NAME

echo "--- Erstelle Container $CTID ---"
if pct create $CTID $STORAGE:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1; then
    echo "Container $CTID erfolgreich erstellt."
else
    echo "FEHLER beim Erstellen des Containers!"
    exit 1
fi

# 5. Startvorgang
pct start $CTID
echo "Warte auf Boot-Vorgang und Netzwerk (30s)..."
sleep 30

# 6. Software-Installation im Container
echo "--- Installiere System-Software (PostgreSQL, Git, Python) ---"
pct exec $CTID -- bash -c "apt update && apt install -y postgresql git python3 python3-pip python3-venv libpq-dev"

# 7. GitHub Projekt laden
GITHUB_USER="lanke-01"
REPO_NAME="hausverwaltung-app"

echo "--- Klone Repository von GitHub ---"
pct exec $CTID -- bash -c "git clone https://github.com/$GITHUB_USER/$REPO_NAME.git /opt/hausverwaltung"

# 8. Datenbank Einrichtung
echo "--- Richte PostgreSQL Datenbank ein ---"
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/database/init_schema.sql'"
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/database/seed_data.sql'"

# 9. Python Umgebung
echo "--- Richte Python Virtuelle Umgebung ein ---"
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install psycopg2-binary"

echo "================================================================="
echo "   INSTALLATION ERFOLGREICH ABGESCHLOSSEN!"
echo "================================================================="
echo "Container ID: $CTID"

# 11. BACKUP-PLAN (Jede Nacht um 03:00 Uhr)
echo "--- Richte tägliche Backups ein ---"
pct exec $CTID -- bash -c "mkdir -p /backups"
pct exec $CTID -- bash -c "(crontab -l 2>/dev/null; echo '0 3 * * * pg_dump -U postgres hausverwaltung > /backups/db_backup_\$(date +\%F).sql') | crontab -"