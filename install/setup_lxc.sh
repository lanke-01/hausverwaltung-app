#!/bin/bash
# setup_lxc.sh - Vollautomatische Installation der Hausverwaltung

# 1. LXC ID finden
CTID=$(pvesh get /cluster/nextid)
echo "Erstelle neuen LXC mit ID: $CTID"

# Storage Auswahl
TEMPLATE_STRG=$(pvesm status --content vztmpl | awk 'NR>1 {print $1}' | head -n 1)
CT_STORAGE=$(pvesm status --content rootdir | awk 'NR>1 {print $1}' | head -n 1)

echo -n "Root-Passwort für den neuen LXC: "
read -s PASSWORD
echo ""

# 2. Template laden & Container erstellen
pveam update
TEMPLATE_NAME=$(pveam available --section system | grep "debian-12" | awk '{print $2}' | head -n 1)
pveam download $TEMPLATE_STRG $TEMPLATE_NAME

pct create $CTID $TEMPLATE_STRG:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --onboot 1 --cores 2 --memory 2048

pct start $CTID
sleep 10

# 3. System-Pakete installieren
echo "--- Installiere System-Pakete ---"
pct exec $CTID -- apt update
pct exec $CTID -- apt install -y git python3 python3-pip python3-venv postgresql postgresql-contrib sudo

# 4. Datenbank erstellen
echo "--- Datenbank einrichten ---"
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"

# 5. Git Repository klonen
echo "--- Software klonen ---"
pct exec $CTID -- git clone https://github.com/DEIN_USERNAME/hausverwaltung.git /opt/hausverwaltung

# 6. DATENBANK-SCHEMA INITIALISIEREN (Alles automatisch)
echo "--- Datenbank-Tabellen & Spalten erstellen ---"
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c '
  -- Mieter und Wohnungen
  CREATE TABLE IF NOT EXISTS apartments (id SERIAL PRIMARY KEY, unit_name TEXT, area NUMERIC);
  CREATE TABLE IF NOT EXISTS tenants (id SERIAL PRIMARY KEY, apartment_id INTEGER, first_name TEXT, last_name TEXT, move_out DATE);
  
  -- Zähler-Struktur
  CREATE TABLE IF NOT EXISTS meters (
    id SERIAL PRIMARY KEY, 
    apartment_id INTEGER, 
    meter_type TEXT, 
    meter_number TEXT, 
    is_submeter BOOLEAN DEFAULT FALSE
  );

  -- Zählerstände
  CREATE TABLE IF NOT EXISTS meter_readings (
    id SERIAL PRIMARY KEY, 
    meter_id INTEGER REFERENCES meters(id) ON DELETE CASCADE, 
    reading_date DATE DEFAULT CURRENT_DATE, 
    reading_value NUMERIC(12,2)
  );

  -- Betriebskosten inkl. tenant_id für Wallbox
  CREATE TABLE IF NOT EXISTS operating_expenses (
    id SERIAL PRIMARY KEY,
    expense_type VARCHAR(255),
    amount NUMERIC(12,2),
    distribution_key VARCHAR(50),
    expense_year INTEGER,
    tenant_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- Vermieter Stammdaten
  CREATE TABLE IF NOT EXISTS landlord_settings (
    id SERIAL PRIMARY KEY, 
    name VARCHAR(255), street VARCHAR(255), city VARCHAR(255),
    iban VARCHAR(50), bank_name VARCHAR(255),
    total_area NUMERIC(10,2) DEFAULT 0,
    total_occupants INTEGER DEFAULT 0
  );
  INSERT INTO landlord_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
'\""

# 7. RECHTE & VERZEICHNISSE
echo "--- Berechtigungen setzen ---"
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

# 9. Autostart Service
echo "--- Systemd Service einrichten ---"
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

echo "--- INSTALLATION ABGESCHLOSSEN ---"
echo "Die App ist erreichbar unter: http://$(pct exec $CTID -- hostname -I | awk '{print $1}'):8501"