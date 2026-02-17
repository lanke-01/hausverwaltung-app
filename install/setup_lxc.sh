#!/bin/bash

# 1. Nächste freie ID finden
CTID=$(pvesh get /cluster/nextid)

# --- STORAGE AUSWAHL LOGIK (Alle Storages anzeigen) ---
echo "--- Storage-Konfiguration ---"
TEMPLATE_STORAGES=($(pvesm status --content vztmpl | awk 'NR>1 {print $1}'))
DISK_STORAGES=($(pvesm status --content rootdir | awk 'NR>1 {print $1}'))

echo "Wähle den Storage für das TEMPLATE:"
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
echo "Warte auf Netzwerk..."
sleep 20

# 3. Software & Locales
pct exec $CTID -- bash -c "apt update && apt install -y postgresql git python3 python3-pip python3-venv libpq-dev locales"
pct exec $CTID -- bash -c "echo 'de_DE.UTF-8 UTF-8' > /etc/locale.gen && locale-gen"
pct exec $CTID -- bash -c "update-locale LANG=de_DE.UTF-8"

# 4. Repo klonen & Sonderzeichen fixen
pct exec $CTID -- bash -c "git clone https://github.com/lanke-01/hausverwaltung-app.git /opt/hausverwaltung"
pct exec $CTID -- bash -c "find /opt/hausverwaltung -name '*.py' -exec sed -i 's/€/Euro/g' {} +"
pct exec $CTID -- bash -c "find /opt/hausverwaltung -name '*.py' -exec sed -i 's/m²/qm/g' {} +"

# 5. Datenbank-Power-Setup (Rechte & Struktur)
pct exec $CTID -- bash -c "
sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' /etc/postgresql/15/main/pg_hba.conf
systemctl restart postgresql
until pg_isready; do sleep 1; done
su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'
"

# Alle Tabellen auf einmal erstellen (Dashboard, Zähler, Einstellungen)
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c '
CREATE TABLE IF NOT EXISTS apartments (id SERIAL PRIMARY KEY, unit_name VARCHAR(255), size_sqm NUMERIC(10,2), base_rent NUMERIC(10,2), service_charge_propayment NUMERIC(10,2));
CREATE TABLE IF NOT EXISTS meters (id SERIAL PRIMARY KEY, apartment_id INTEGER REFERENCES apartments(id), meter_type VARCHAR(50), meter_number VARCHAR(100), unit VARCHAR(20) DEFAULT '\''kWh'\'');
CREATE TABLE IF NOT EXISTS landlord_settings (id SERIAL PRIMARY KEY, name VARCHAR(255), street VARCHAR(255), city VARCHAR(255), iban VARCHAR(50), bank_name VARCHAR(255), updated_at TIMESTAMP DEFAULT NOW());
INSERT INTO landlord_settings (id, name) SELECT 1, '\''Vermieter Name'\'' WHERE NOT EXISTS (SELECT 1 FROM landlord_settings);
'\""

# 6. .env & Python
pct exec $CTID -- bash -c "printf 'DB_NAME=hausverwaltung\nDB_USER=postgres\nDB_PASS=\nDB_HOST=127.0.0.1\nDB_PORT=5432\n' > /opt/hausverwaltung/.env"
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv && /opt/hausverwaltung/venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv"

# 7. Autostart
pct exec $CTID -- bash -c "cat <<EOF > /etc/systemd/system/hausverwaltung.service
[Unit]
Description=Streamlit App
After=network.target postgresql.service
[Service]
Type=simple
User=root
WorkingDirectory=/opt/hausverwaltung
Environment=PYTHONUTF8=1
ExecStart=/opt/hausverwaltung/venv/bin/streamlit run main.py --server.port 8501 --server.address 0.0.0.0
Restart=always
[Install]
WantedBy=multi-user.target
EOF"

pct exec $CTID -- bash -c "systemctl daemon-reload && systemctl enable hausverwaltung.service && systemctl restart hausverwaltung.service"

IP_ADDRESS=$(pct exec $CTID -- hostname -I | awk '{print $1}')
echo "URL: http://$IP_ADDRESS:8501"