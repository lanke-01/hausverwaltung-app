#!/bin/bash

# 1. Nächste freie ID finden
CTID=$(pvesh get /cluster/nextid)

# --- STORAGE AUSWAHL ---
TEMPLATE_STORAGES=($(pvesm status --content vztmpl | awk 'NR>1 {print $1}' | grep "local"))
DISK_STORAGES=($(pvesm status --content rootdir | awk 'NR>1 {print $1}'))

echo "Wähle Storage für TEMPLATE:"
select TEMPLATE_STRG in "${TEMPLATE_STORAGES[@]}"; do [ -n "$TEMPLATE_STRG" ] && STORAGE=$TEMPLATE_STRG && break; done
echo "Wähle Storage für DISK:"
select DISK_STRG in "${DISK_STORAGES[@]}"; do [ -n "$DISK_STRG" ] && CT_STORAGE=$DISK_STRG && break; done

echo -n "Root-Passwort: "
read -s PASSWORD
echo ""

# 3. Container Erstellung
pveam update
TEMPLATE_NAME=$(pveam available --section system | grep "debian-12" | awk '{print $2}' | head -n 1)
pveam download $STORAGE $TEMPLATE_NAME

pct create $CTID $STORAGE:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1

pct start $CTID
echo "Warte auf Netzwerk..."
sleep 20

# 4. Installation & UTF-8 Locales (IM CONTAINER)
pct exec $CTID -- bash -c "apt update && apt install -y postgresql git python3 python3-pip python3-venv libpq-dev locales"
pct exec $CTID -- bash -c "echo 'de_DE.UTF-8 UTF-8' > /etc/locale.gen && locale-gen"
pct exec $CTID -- bash -c "update-locale LANG=de_DE.UTF-8 LC_ALL=de_DE.UTF-8"

# 5. GitHub Projekt laden
pct exec $CTID -- bash -c "git clone https://github.com/lanke-01/hausverwaltung-app.git /opt/hausverwaltung"

# 6. Sonderzeichen im Code bereinigen (Falls im Repo noch € oder m² sind)
pct exec $CTID -- bash -c "find /opt/hausverwaltung -name '*.py' -exec sed -i 's/€/Euro/g' {} +"
pct exec $CTID -- bash -c "find /opt/hausverwaltung -name '*.py' -exec sed -i 's/m²/qm/g' {} +"

# 7. Datenbank & Rechte (Trust Modus für 127.0.0.1)
pct exec $CTID -- bash -c "
sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' /etc/postgresql/15/main/pg_hba.conf
sed -i 's/host    all             all             127.0.0.1\/32            scram-sha-256/host    all             all             127.0.0.1\/32            trust/' /etc/postgresql/15/main/pg_hba.conf
systemctl restart postgresql
"

# 8. DB Initialisierung
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/install/init_db.sql' || true"
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c \\\"INSERT INTO landlord_settings (id, name) SELECT 1, 'Bitte Daten eintragen' WHERE NOT EXISTS (SELECT 1 FROM landlord_settings);\\\"\""

# 9. .env & Python Setup
pct exec $CTID -- bash -c "printf 'DB_NAME=hausverwaltung\nDB_USER=postgres\nDB_PASS=\nDB_HOST=127.0.0.1\nDB_PORT=5432\n' > /opt/hausverwaltung/.env"
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv && /opt/hausverwaltung/venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv"

# 10. Systemd Service (mit UTF-8 Umgebung)
pct exec $CTID -- bash -c "cat <<EOF > /etc/systemd/system/hausverwaltung.service
[Unit]
Description=Streamlit Hausverwaltung App
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hausverwaltung
Environment=PYTHONUTF8=1
Environment=LANG=de_DE.UTF-8
Environment=LC_ALL=de_DE.UTF-8
ExecStart=/opt/hausverwaltung/venv/bin/streamlit run main.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

pct exec $CTID -- bash -c "systemctl daemon-reload && systemctl enable hausverwaltung.service && systemctl restart hausverwaltung.service"

IP_ADDRESS=$(pct exec $CTID -- hostname -I | awk '{print $1}')
echo "Fertig! URL: http://$IP_ADDRESS:8501"