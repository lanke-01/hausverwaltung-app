#!/bin/bash
# setup_lxc.sh - Optimiert für Git-Deployment & Hausverwaltung App

# 1. Nächste freie ID finden & Storage abfragen
CTID=$(pvesh get /cluster/nextid)
echo "Erstelle neuen LXC mit ID: $CTID"

TEMPLATE_STORAGES=($(pvesm status --content vztmpl | awk 'NR>1 {print $1}'))
DISK_STORAGES=($(pvesm status --content rootdir | awk 'NR>1 {print $1}'))

echo "Wähle Storage für das TEMPLATE (Debian):"
select TEMPLATE_STRG in "${TEMPLATE_STORAGES[@]}"; do [ -n "$TEMPLATE_STRG" ] && STORAGE=$TEMPLATE_STRG && break; done

echo "Wähle Storage für die DISK (LXC-Root):"
select DISK_STRG in "${DISK_STORAGES[@]}"; do [ -n "$DISK_STRG" ] && CT_STORAGE=$DISK_STRG && break; done

echo -n "Root-Passwort für den neuen LXC: "
read -s PASSWORD
echo ""

# 2. Container erstellen (Debian 12)
pveam update
TEMPLATE_NAME=$(pveam available --section system | grep "debian-12" | awk '{print $2}' | head -n 1)
pveam download $STORAGE $TEMPLATE_NAME

pct create $CTID $STORAGE:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --memory 2048 --cores 2 --start 1

echo "Warte 10 Sekunden auf Bootvorgang..."
sleep 10

# 3. System-Updates & Abhängigkeiten installieren
pct exec $CTID -- apt update
pct exec $CTID -- apt install -y git python3 python3-venv python3-pip postgresql postgresql-contrib libpq-dev build-essential

# 4. GitHub Projekt laden
pct exec $CTID -- bash -c "git clone https://github.com/lanke-01/hausverwaltung-app.git /opt/hausverwaltung"


# 5. Datenbank initialisieren
echo "--- Datenbank wird konfiguriert ---"
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"

# Datenbank-Schema (Inklusive Keywords-Tabelle für CSV-Automatik)
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -f /opt/hausverwaltung/init_db.sql\""
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c '
  CREATE TABLE IF NOT EXISTS tenant_keywords (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    keyword VARCHAR(255) UNIQUE NOT NULL
  );
  INSERT INTO landlord_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
'\""

# 6. Verzeichnisse & Rechte
pct exec $CTID -- bash -c "mkdir -p /opt/hausverwaltung/backups"
pct exec $CTID -- bash -c "chown -R root:root /opt/hausverwaltung"
pct exec $CTID -- bash -c "chmod -R 777 /opt/hausverwaltung/backups"

# 7. Python Venv & Pakete
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install --upgrade pip"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv"

# 8. Autostart Service erstellen
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

[Install]
WantedBy=multi-user.target
EOF"

pct exec $CTID -- systemctl daemon-reload
pct exec $CTID -- systemctl enable hausverwaltung.service
pct exec $CTID -- systemctl start hausverwaltung.service

echo "-------------------------------------------------------"
echo "✅ LXC Container $CTID erfolgreich eingerichtet!"
echo "🌐 App erreichbar unter: http://<LXC_IP>:8501"
echo "-------------------------------------------------------"