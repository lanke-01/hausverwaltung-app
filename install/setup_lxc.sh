#!/bin/bash
# setup_lxc.sh - Deine Version mit fix für "operating_expenses"

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

# --- NEU: RECHTE FÜR POSTGRES SETZEN ---
pct exec $CTID -- chown -R postgres:postgres /opt/hausverwaltung
pct exec $CTID -- chmod -R 755 /opt/hausverwaltung

# 5. Datenbank-Konfiguration
echo "--- Datenbank-Rechte setzen ---"
pct exec $CTID -- bash -c "
sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' /etc/postgresql/15/main/pg_hba.conf
sed -i 's/host    all             all             127.0.0.1\/32            scram-sha-256/host    all             all             127.0.0.1\/32            trust/' /etc/postgresql/15/main/pg_hba.conf
systemctl restart postgresql
"

# 6. Datenbank & Tabellen initialisieren
echo "--- Datenbank-Schema erstellen ---"
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"

# Führt deine init_db.sql aus
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -f /opt/hausverwaltung/init_db.sql\""

# --- FIX: operating_expenses Tabelle sicherstellen ---
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c '
  CREATE TABLE IF NOT EXISTS operating_expenses (
    id SERIAL PRIMARY KEY,
    expense_type VARCHAR(255),
    amount NUMERIC(12,2),
    distribution_key VARCHAR(50),
    expense_year INTEGER,
    tenant_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  
  -- Neue Tabelle für die CSV-Zuweisung (Keywords)
  CREATE TABLE IF NOT EXISTS tenant_keywords (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    keyword VARCHAR(255) UNIQUE NOT NULL
  );
'\""

# 7. DATEI-FIXING & RECHTE (Dein Original)
echo "--- System-Konfiguration ---"
pct exec $CTID -- bash -c "find /opt/hausverwaltung -type f -name '*.py' -exec sed -i 's/unit_id/apartment_id/g' {} +"
pct exec $CTID -- bash -c "
mkdir -p /opt/hausverwaltung/backups
chown -R postgres:postgres /opt/hausverwaltung/backups
chmod -R 777 /opt/hausverwaltung/backups
chmod 777 /var/run/postgresql
"

# 8. Python Venv & Pakete
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv"

# 9. Autostart Service
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
echo "✅ FERTIG! URL: http://$IP_ADDRESS:8501"
echo "-------------------------------------------------------"