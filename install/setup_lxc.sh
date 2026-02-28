#!/bin/bash
# setup_lxc.sh - DEINE ORIGINAL VERSION mit Keyword-Erweiterung

# 1. Nächste freie ID finden
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

# HIER: Deine pct create Zeile (angepasst auf deine Bedürfnisse)
pct create $CTID $STORAGE:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --memory 2048 --cores 2 --start 1

echo "Warte auf Bootvorgang..."
sleep 20

# 3. System-Pakete
pct exec $CTID -- bash -c "apt update && apt install -y postgresql git python3 python3-pip python3-venv libpq-dev locales"
pct exec $CTID -- bash -c "echo 'de_DE.UTF-8 UTF-8' > /etc/locale.gen && locale-gen"
pct exec $CTID -- bash -c "update-locale LANG=de_DE.UTF-8"


# 4. Git Projekt klonen (HIER DEIN REPO EINTRAGEN)
pct exec $CTID -- bash -c "git clone https://github.com/lanke-01/hausverwaltung-app.git /opt/hausverwaltung"

# 5. Datenbank initialisieren
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"

# Führt deine init_db.sql aus
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -f /opt/hausverwaltung/init_db.sql\""

# --- DAS IST DER NEUE TEIL FÜR DIE CSV-AUTOMATIK ---
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c '
  CREATE TABLE IF NOT EXISTS tenant_keywords (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    keyword VARCHAR(255) UNIQUE NOT NULL
  );
'\""
# --------------------------------------------------

# 6. Python Venv & Pakete
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv"

# 7. Autostart Service
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

echo "✅ Container $CTID ist fertig!"