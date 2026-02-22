#!/bin/bash

# 1. Nächste freie ID finden
CTID=$(pvesh get /cluster/nextid)

# --- STORAGE AUSWAHL LOGIK (Zeigt alle verfügbaren Platten) ---
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
echo "--- Lade Debian Template herunter ---"
pveam update
TEMPLATE_NAME=$(pveam available --section system | grep "debian-12" | awk '{print $2}' | head -n 1)
pveam download $STORAGE $TEMPLATE_NAME

echo "--- Erstelle Container $CTID ---"
pct create $CTID $STORAGE:vztmpl/$TEMPLATE_NAME --hostname hausverwaltung-app \
  --password "$PASSWORD" --storage $CT_STORAGE \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp --unprivileged 1 --features nesting=1

pct start $CTID
echo "Warte auf Netzwerk (20s)..."
sleep 20

# 3. Software-Installation & UTF-8 Locales
echo "--- Installiere System-Software & Locales ---"
pct exec $CTID -- bash -c "apt update && apt install -y postgresql git python3 python3-pip python3-venv libpq-dev locales"
pct exec $CTID -- bash -c "echo 'de_DE.UTF-8 UTF-8' > /etc/locale.gen && locale-gen"
pct exec $CTID -- bash -c "update-locale LANG=de_DE.UTF-8"

# 4. GitHub Projekt laden
echo "--- Klone Repository ---"
pct exec $CTID -- bash -c "git clone https://github.com/lanke-01/hausverwaltung-app.git /opt/hausverwaltung"

# 5. Datenbank-Konfiguration (Rechte setzen)
echo "--- Konfiguriere PostgreSQL Rechte ---"
pct exec $CTID -- bash -c "
sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' /etc/postgresql/15/main/pg_hba.conf
sed -i 's/host    all             all             127.0.0.1\/32            scram-sha-256/host    all             all             127.0.0.1\/32            trust/' /etc/postgresql/15/main/pg_hba.conf
systemctl restart postgresql
"

# Warten bis DB bereit ist
pct exec $CTID -- bash -c "until pg_isready; do sleep 1; done"

# 6. Datenbank & Tabellen initialisieren
echo "--- Erstelle Datenbank-Struktur ---"
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
# Führt deine init_db.sql aus dem /install Unterordner aus
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/install/init_db.sql'"

# 7. FINALER FIX: Alle fehlenden Spalten erzwingen
echo "--- Synchronisiere Datenbank-Spalten (Wallbox-Update) ---"
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c '
-- Bestehende Fixes
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS occupants INTEGER DEFAULT 1;

-- NEU: Wallbox-Fixes für Zähler
ALTER TABLE meters ADD COLUMN IF NOT EXISTS is_submeter BOOLEAN DEFAULT FALSE;
ALTER TABLE meters ADD COLUMN IF NOT EXISTS parent_meter_id INTEGER;

-- Fix für Betriebskosten (Stichwort: operating_expenses vs expenses)
CREATE TABLE IF NOT EXISTS operating_expenses (
    id SERIAL PRIMARY KEY,
    expense_type VARCHAR(255),
    amount NUMERIC(10,2),
    expense_year INTEGER,
    distribution_key VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
'\""

# 8. .env Datei generieren
echo "--- Erstelle Umgebungsvariablen ---"
pct exec $CTID -- bash -c "printf 'DB_NAME=hausverwaltung\nDB_USER=postgres\nDB_PASS=\nDB_HOST=127.0.0.1\nDB_PORT=5432\n' > /opt/hausverwaltung/.env"

# 9. Python Venv und Pakete
echo "--- Setup Python Environment ---"
pct exec $CTID -- bash -c "python3 -m venv /opt/hausverwaltung/venv"
pct exec $CTID -- bash -c "/opt/hausverwaltung/venv/bin/pip install streamlit pandas psycopg2-binary fpdf python-dotenv"

# 10. Systemd Service für Autostart
echo "--- Erstelle Autostart-Service ---"
pct exec $CTID -- bash -c "cat <<EOF > /etc/systemd/system/hausverwaltung.service
[Unit]
Description=Streamlit Hausverwaltung
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


# --- BACKUP SYSTEM EINRICHTEN ---
# Skript ausführbar machen
pct exec $CTID -- chmod +x /opt/hausverwaltung/install/backup_db.sh

# Cronjob erstellen (täglich um 03:00 Uhr)
pct exec $CTID -- bash -c "(crontab -l 2>/dev/null; echo '0 3 * * * /opt/hausverwaltung/install/backup_db.sh') | crontab -"




# 11. Abschluss
IP_ADDRESS=$(pct exec $CTID -- hostname -I | awk '{print $1}')
echo ""
echo "================================================================="
echo " 🎉 INSTALLATION FERTIG!"
echo " URL: http://$IP_ADDRESS:8501"
echo "================================================================="

