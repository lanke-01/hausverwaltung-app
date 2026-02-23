#!/bin/bash
# setup_lxc.sh - Komplett-Version inkl. Fixes

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

pct create $CTID $STORAGE:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1

pct start $CTID
echo "Warte auf Netzwerk (20s)..."
sleep 20

# 3. Software-Installation
pct exec $CTID -- bash -c "apt update && apt install -y postgresql git python3 python3-pip python3-venv libpq-dev locales"
pct exec $CTID -- bash -c "echo 'de_DE.UTF-8 UTF-8' > /etc/locale.gen && locale-gen"
pct exec $CTID -- bash -c "update-locale LANG=de_DE.UTF-8"

# 4. GitHub Projekt laden
pct exec $CTID -- bash -c "git clone https://github.com/lanke-01/hausverwaltung-app.git /opt/hausverwaltung"

# 5. Datenbank-Konfiguration (Berechtigungen fixen)
echo "--- Datenbank-Rechte setzen ---"
pct exec $CTID -- bash -c "
sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' /etc/postgresql/15/main/pg_hba.conf
sed -i 's/host    all             all             127.0.0.1\/32            scram-sha-256/host    all             all             127.0.0.1\/32            trust/' /etc/postgresql/15/main/pg_hba.conf
systemctl restart postgresql
"

# 6. Datenbank & Tabellen initialisieren
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/install/init_db.sql'"

# 7. SCHEMA-UPDATE & FIXES (Wichtig!)
echo "--- Schema-Anpassungen (unit_id -> apartment_id) ---"
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c '
  ALTER TABLE tenants RENAME COLUMN unit_id TO apartment_id;
  ALTER TABLE meters ADD COLUMN IF NOT EXISTS is_submeter BOOLEAN DEFAULT FALSE; 
  ALTER TABLE meters ADD COLUMN IF NOT EXISTS parent_meter_id INTEGER;
'\"" 2>/dev/null

# 8. DATEI-FIXING (Brechstange: Falls im Git noch unit_id steht)
echo "--- Code-Patches anwenden ---"
pct exec $CTID -- bash -c "find /opt/hausverwaltung -type f -name '*.py' -exec sed -i 's/unit_id/apartment_id/g' {} +"

# 9. BACKUP-ORDNER & RECHTE
echo "--- System-Verzeichnisse einrichten ---"
pct exec $CTID -- bash -c "
mkdir -p /opt/hausverwaltung/backups
chmod -R 777 /opt/hausverwaltung/backups
chmod 777 /var/run/postgresql
chmod +x /opt/hausverwaltung/install/backup_db.sh
"

# 10. Python Venv & Pakete
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv"

# 11. Autostart Service (Optimiert für Update-Button)
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

pct exec $CTID -- bash -c "systemctl daemon-reload && systemctl enable hausverwaltung.service && systemctl restart hausverwaltung.service"

IP_ADDRESS=$(pct exec $CTID -- hostname -I | awk '{print $1}')
echo "-------------------------------------------------------"
echo "✅ FERTIG! LXC ID: $CTID"
echo "URL: http://$IP_ADDRESS:8501"
echo "-------------------------------------------------------"