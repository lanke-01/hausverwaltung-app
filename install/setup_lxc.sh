#!/bin/bash

# 1. Nächste freie ID finden
CTID=$(pvesh get /cluster/nextid)

# --- STORAGE AUSWAHL LOGIK ---
TEMPLATE_STORAGES=($(pvesm status --content vztmpl | awk 'NR>1 {print $1}' | grep "local"))
DISK_STORAGES=($(pvesm status --content rootdir | awk 'NR>1 {print $1}'))

echo "Wähle Storage für TEMPLATE:"
select TEMPLATE_STRG in "${TEMPLATE_STORAGES[@]}"; do [ -n "$TEMPLATE_STRG" ] && STORAGE=$TEMPLATE_STRG && break; done
echo "Wähle Storage für DISK:"
select DISK_STRG in "${DISK_STORAGES[@]}"; do [ -n "$DISK_STRG" ] && CT_STORAGE=$DISK_STRG && break; done

echo -n "Root-Passwort: "
read -s PASSWORD
echo ""

# 2. Container Erstellung
pveam update
TEMPLATE_NAME=$(pveam available --section system | grep "debian-12" | awk '{print $2}' | head -n 1)
pveam download $STORAGE $TEMPLATE_NAME

pct create $CTID $STORAGE:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1

pct start $CTID
echo "Warte auf Netzwerk (20s)..."
sleep 20

# 3. Installation & UTF-8 (IM CONTAINER)
pct exec $CTID -- bash -c "apt update && apt install -y postgresql git python3 python3-pip python3-venv libpq-dev locales"
pct exec $CTID -- bash -c "echo 'de_DE.UTF-8 UTF-8' > /etc/locale.gen && locale-gen"
pct exec $CTID -- bash -c "update-locale LANG=de_DE.UTF-8"

# 4. GitHub Projekt laden
pct exec $CTID -- bash -c "git clone https://github.com/lanke-01/hausverwaltung-app.git /opt/hausverwaltung"

# 5. Datenbank & Rechte (Trust-Modus erzwingen)
pct exec $CTID -- bash -c "
sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' /etc/postgresql/15/main/pg_hba.conf
sed -i 's/host    all             all             127.0.0.1\/32            scram-sha-256/host    all             all             127.0.0.1\/32            trust/' /etc/postgresql/15/main/pg_hba.conf
systemctl restart postgresql
"

# 6. DB Initialisierung & Fix für updated_at
pct exec $CTID -- bash -c "until pg_isready; do sleep 1; done"
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
# Erstellt die Tabelle direkt mit der richtigen Spalte
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c 'CREATE TABLE IF NOT EXISTS landlord_settings (id SERIAL PRIMARY KEY, name VARCHAR(255), street VARCHAR(255), city VARCHAR(255), iban VARCHAR(50), bank_name VARCHAR(255), updated_at TIMESTAMP DEFAULT NOW()); INSERT INTO landlord_settings (id, name) SELECT 1, '\''Vermieter Name'\'' WHERE NOT EXISTS (SELECT 1 FROM landlord_settings);'\""

# 7. .env & Python Setup
pct exec $CTID -- bash -c "printf 'DB_NAME=hausverwaltung\nDB_USER=postgres\nDB_PASS=\nDB_HOST=127.0.0.1\nDB_PORT=5432\n' > /opt/hausverwaltung/.env"
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv && /opt/hausverwaltung/venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv"

# 8. Systemd Service
pct exec $CTID -- bash -c "cat <<EOF > /etc/systemd/system/hausverwaltung.service
[Unit]
Description=Streamlit Hausverwaltung App
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hausverwaltung
Environment=PYTHONUTF8=1
Environment=PYTHONIOENCODING=utf-8
ExecStart=/opt/hausverwaltung/venv/bin/streamlit run main.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

pct exec $CTID -- bash -c "systemctl daemon-reload && systemctl enable hausverwaltung.service && systemctl restart hausverwaltung.service"

IP_ADDRESS=$(pct exec $CTID -- hostname -I | awk '{print $1}')
echo "================================================================="
echo " 🎉 INSTALLATION FERTIG! URL: http://$IP_ADDRESS:8501"
echo "================================================================="