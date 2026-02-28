#!/bin/bash
# setup_lxc.sh - Vollautomatische Installation der Hausverwaltung

# 1. Nächste freie ID finden & Storage-Auswahl
CTID=$(pvesh get /cluster/nextid)
echo "Erstelle neuen LXC mit ID: $CTID"

echo "--- Storage-Konfiguration ---"
TEMPLATE_STORAGES=($(pvesm status --content vztmpl | awk 'NR>1 {print $1}'))
DISK_STORAGES=($(pvesm status --content rootdir | awk 'NR>1 {print $1}'))

echo "Wähle den Storage für das TEMPLATE (Debian Image):"
PS3="Nummer wählen: "
select TEMPLATE_STRG in "${TEMPLATE_STORAGES[@]}"; do
    [ -n "$TEMPLATE_STRG" ] && STORAGE=$TEMPLATE_STRG && break
done

echo "Wähle den Storage für die DISK (LXC-Root):"
select DISK_STRG in "${DISK_STORAGES[@]}"; do
    [ -n "$DISK_STRG" ] && CT_STORAGE=$DISK_STRG && break
done

echo -n "Root-Passwort für den neuen LXC: "
read -s PASSWORD
echo ""

# 2. Template laden & Container erstellen
pveam update
TEMPLATE_NAME=$(pveam available --section system | grep "debian-12" | awk '{print $2}' | head -n 1)
pveam download $STORAGE $TEMPLATE_NAME

pct create $CTID $STORAGE:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1

pct start $CTID
echo "Warte auf Bootvorgang & Netzwerk (20s)..."
sleep 20

# 3. System-Pakete installieren
pct exec $CTID -- apt update
pct exec $CTID -- apt install -y postgresql git python3 python3-pip python3-venv libpq-dev locales
pct exec $CTID -- bash -c "echo 'de_DE.UTF-8 UTF-8' > /etc/locale.gen && locale-gen"
pct exec $CTID -- bash -c "update-locale LANG=de_DE.UTF-8"

# 4. GitHub Projekt laden
echo "--- Klone Repository ---"
pct exec $CTID -- rm -rf /opt/hausverwaltung
pct exec $CTID -- git clone https://github.com/lanke-01/hausverwaltung-app.git /opt/hausverwaltung

# --- DER FIX: SQL-Datei aus dem install-Ordner für Postgres bereitstellen ---
pct exec $CTID -- cp /opt/hausverwaltung/install/init_db.sql /tmp/init_db.sql
pct exec $CTID -- chmod 644 /tmp/init_db.sql

# 5. Datenbank-Konfiguration (Berechtigungen)
echo "--- Datenbank-Rechte setzen ---"
pct exec $CTID -- bash -c "
sed -i '/local.*all.*postgres.*peer/s/peer/trust/' /etc/postgresql/15/main/pg_hba.conf
sed -i '/host.*all.*all.*127.0.0.1\/32.*scram-sha-256/s/scram-sha-256/trust/' /etc/postgresql/15/main/pg_hba.conf
systemctl restart postgresql
"
sleep 3

# 6. Datenbank & Tabellen initialisieren
echo "--- Datenbank-Schema erstellen ---"
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -f /tmp/init_db.sql\""

# Aufräumen der temporären SQL-Datei
pct exec $CTID -- rm /tmp/init_db.sql

# 7. Code-Fixes & Ordner-Rechte (Dein Original)
echo "--- System-Konfiguration ---"
pct exec $CTID -- bash -c "find /opt/hausverwaltung -type f -name '*.py' -exec sed -i 's/unit_id/apartment_id/g' {} +"
pct exec $CTID -- bash -c "
mkdir -p /opt/hausverwaltung/backups
chown -R postgres:postgres /opt/hausverwaltung/backups
chmod -R 777 /opt/hausverwaltung/backups
chmod 777 /var/run/postgresql
"

# 8. Python Venv & Pakete
echo "--- Python Umgebung einrichten ---"
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv"

# 9. Autostart Service einrichten
pct exec $CTID -- bash -c "cat <<EOF > /etc/systemd/system/hausverwaltung.service
[Unit]
Description=Streamlit Hausverwaltung
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hausverwaltung
ExecStart=/opt/hausverwaltung/venv/bin/streamlit run main.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

pct exec $CTID -- systemctl daemon-reload
pct exec $CTID -- systemctl enable hausverwaltung.service
pct exec $CTID -- systemctl start hausverwaltung.service

# IP Adresse für den Abschluss ermitteln
IP_ADDR=$(pct exec $CTID -- hostname -I | awk '{print $1}')

echo "-------------------------------------------------------"
echo "✅ FERTIG! Container $CTID wurde erstellt."
echo "🌍 App erreichbar unter: http://${IP_ADDR}:8501"
echo "-------------------------------------------------------"