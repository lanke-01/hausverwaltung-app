#!/bin/bash
# setup_lxc.sh - Interaktive Version mit allen Datenbank-Fixes

# 1. Nächste freie ID finden
CTID=$(pvesh get /cluster/nextid)
echo "Erstelle neuen LXC mit ID: $CTID"

echo "--- Storage-Konfiguration ---"
# Hier holen wir die Listen der verfügbaren Speicher
TEMPLATE_STORAGES=($(pvesm status --content vztmpl | awk 'NR>1 {print $1}'))
DISK_STORAGES=($(pvesm status --content rootdir | awk 'NR>1 {print $1}'))

# INTERAKTIVE ABFRAGE FÜR TEMPLATE STORAGE
echo "Wähle den Storage für das ISO/Template (meistens 'local'):"
select T_STRG in "${TEMPLATE_STORAGES[@]}"; do
    if [ -n "$T_STRG" ]; then
        STORAGE=$T_STRG
        break
    fi
done

# INTERAKTIVE ABFRAGE FÜR CONTAINER STORAGE
echo "Wähle den Storage für die LXC-Festplatte (meistens 'local-lvm' oder 'local'):"
select D_STRG in "${DISK_STORAGES[@]}"; do
    if [ -n "$D_STRG" ]; then
        CT_STORAGE=$D_STRG
        break
    fi
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

# 5. Datenbank-Schema (Fix für relation operating_expenses does not exist)
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c '
  CREATE TABLE IF NOT EXISTS apartments (id SERIAL PRIMARY KEY, unit_name TEXT, area NUMERIC);
  CREATE TABLE IF NOT EXISTS tenants (id SERIAL PRIMARY KEY, apartment_id INTEGER, first_name TEXT, last_name TEXT, move_out DATE);
  CREATE TABLE IF NOT EXISTS operating_expenses (
    id SERIAL PRIMARY KEY,
    expense_type VARCHAR(255),
    amount NUMERIC(12,2),
    distribution_key VARCHAR(50),
    expense_year INTEGER,
    tenant_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS landlord_settings (
    id SERIAL PRIMARY KEY, name VARCHAR(255), street VARCHAR(255), city VARCHAR(255),
    iban VARCHAR(50), bank_name VARCHAR(255), total_area NUMERIC(10,2) DEFAULT 0, total_occupants INTEGER DEFAULT 0
  );
  INSERT INTO landlord_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
'\""

# 6. RECHTE & SERVICE
pct exec $CTID -- bash -c "
mkdir -p /opt/hausverwaltung/backups
chown -R postgres:postgres /opt/hausverwaltung/backups
chmod -R 777 /opt/hausverwaltung/backups
python3 -m venv /opt/hausverwaltung/venv
/opt/hausverwaltung/venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv
"

# 7. Systemd Service
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

pct exec $CTID -- bash -c "systemctl daemon-reload && systemctl enable hausverwaltung.service && systemctl start hausverwaltung.service"

IP_ADDRESS=$(pct exec $CTID -- hostname -I | awk '{print $1}')
echo "-------------------------------------------------------"
echo "✅ FERTIG! URL: http://$IP_ADDRESS:8501"