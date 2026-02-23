#!/bin/bash

# Konfiguration
BACKUP_DIR="/opt/hausverwaltung/backups"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="$BACKUP_DIR/hausverwaltung_backup_$TIMESTAMP.sql"

# Verzeichnis erstellen falls nicht vorhanden
mkdir -p $BACKUP_DIR

# Backup erstellen (pg_dump)
su - postgres -c "pg_dump hausverwaltung" > $BACKUP_FILE

# Alte Backups löschen (behält nur die letzten 7 Tage)
find $BACKUP_DIR -type f -name "*.sql" -mtime +7 -delete

echo "Backup erfolgreich erstellt: $BACKUP_FILE"