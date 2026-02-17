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

# 6. Software-Installation im Container
echo "--- Installiere System-Software ---"
pct exec $CTID -- bash -c "apt update && apt install -y postgresql git python3 python3-pip python3-venv libpq-dev locales"

# 7. Sprachumgebung (Locales) auf UTF-8 setzen (Wichtig gegen den ASCII-Fehler)
echo "--- Konfiguriere UTF-8 Locales ---"
pct exec $CTID -- bash -c "sed -i '/de_DE.UTF-8/s/^# //g' /etc/locale.gen && locale-gen"
pct exec $CTID -- bash -c "echo 'LANG=de_DE.UTF-8' > /etc/default/locale"
pct exec $CTID -- bash -c "echo 'LC_ALL=de_DE.UTF-8' >> /etc/default/locale"

# 8. GitHub Projekt laden
GITHUB_USER="lanke-01"
REPO_NAME="hausverwaltung-app"
echo "--- Klone Repository ---"
pct exec $CTID -- bash -c "git clone https://github.com/$GITHUB_USER/$REPO_NAME.git /opt/hausverwaltung"

# 9. Automatische Bereinigung von Sonderzeichen im Code (€ und m²)
echo "--- Bereinige Sonderzeichen im Python-Code ---"
pct exec $CTID -- bash -c "find /opt/hausverwaltung -name '*.py' -exec sed -i 's/€/Euro/g' {} +"
pct exec $CTID -- bash -c "find /opt/hausverwaltung -name '*.py' -exec sed -i 's/m²/qm/g' {} +"

# 10. Datenbank Einrichtung & Rechte (Trust-Modus)
echo "--- Richte PostgreSQL ein ---"
pct exec $CTID -- bash -c "sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' /etc/postgresql/15/main/pg_hba.conf"
pct exec $CTID -- bash -c "systemctl restart postgresql"

# Datenbank erstellen (falls nicht vorhanden)
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"

# Schema importieren (versucht beide gängigen Pfade)
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/install/init_db.sql'" || \
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/database/init_schema.sql'"

# 11. .env Datei im Container erstellen
echo "--- Erstelle .env Datei ---"
pct exec $CTID -- bash -c "cat <<EOF > /opt/hausverwaltung/.env
DB_NAME=hausverwaltung
DB_USER=postgres
DB_PASS=
DB_HOST=127.0.0.1
DB_PORT=5432
EOF"

# 12. Python Umgebung & Module
echo "--- Richte Python Venv ein ---"
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install --upgrade pip"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv"

# 13. Autostart Dienst (Systemd) erstellen
echo "--- Erstelle Systemd-Service ---"
pct exec $CTID -- bash -c "cat <<EOF > /etc/systemd/system/hausverwaltung.service
[Unit]
Description=Streamlit Hausverwaltung App
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hausverwaltung
Environment=PYTHONIOENCODING=utf-8
Environment=LANG=de_DE.UTF-8
Environment=LC_ALL=de_DE.UTF-8
ExecStart=/opt/hausverwaltung/venv/bin/streamlit run main.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

# Dienst aktivieren und starten
pct exec $CTID -- bash -c "systemctl daemon-reload && systemctl enable hausverwaltung.service && systemctl start hausverwaltung.service"

# 14. IP Adresse auslesen und Erfolg melden
IP_ADDRESS=$(pct exec $CTID -- hostname -I | awk '{print $1}')

echo ""
echo "================================================================="
echo " 🎉 INSTALLATION ERFOLGREICH!"
echo "================================================================="
echo " App-URL: http://$IP_ADDRESS:8501"
echo " Container ID: $CTID"
echo "================================================================="