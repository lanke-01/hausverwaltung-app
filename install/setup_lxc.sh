#!/bin/bash

# =================================================================
# Hausverwaltungs-App - Automatischer LXC Installer
# =================================================================

# --- Funktion zur Storage-Auswahl ---
select_storage() {
    local prompt=$1
    echo "$prompt"
    # Holt alle Storages, die 'rootdir' (für CTs) oder 'vztmpl' (für Templates) erlauben
    mapfile -t storages < <(pvesm status | awk 'NR>1 {print $1}')
    
    for i in "${!storages[@]}"; do
        echo "$((i+1))) ${storages[$i]}"
    done

    while true; do
        read -p "Auswahl (Zahl): " choice
        if [[ "$choice" -gt 0 && "$choice" -le "${#storages[@]}" ]]; then
            selected_storage="${storages[$((choice-1))]}"
            break
        else
            echo "Ungültige Auswahl, bitte erneut versuchen."
        fi
    done
    echo "$selected_storage"
}

# 1. Nächste freie ID finden
CTID=$(pvesh get /cluster/nextid)

# 2. Abfragen mit Auswahlmenü
echo "--- Storage-Konfiguration ---"
STORAGE=$(select_storage "Wähle den Storage für das TEMPLATE (z.B. local):")
echo "Gewählt: $STORAGE"
echo ""
CT_STORAGE=$(select_storage "Wähle den Storage für die CONTAINER-DISK (z.B. local-lvm):")
echo "Gewählt: $CT_STORAGE"
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