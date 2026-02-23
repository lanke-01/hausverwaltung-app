#!/bin/bash
# setup_lxc.sh - Komplett-Fix für Hausverwaltung

# ... (Deine Variablen: CTID, PW, etc. bleiben hier oben stehen) ...

echo "--- 1. Datenbank-Berechtigungen (Trust) ---"
pct exec $CTID -- bash -c "
sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' /etc/postgresql/15/main/pg_hba.conf
sed -i 's/host    all             all             127.0.0.1\/32            scram-sha-256/host    all             all             127.0.0.1\/32            trust/' /etc/postgresql/15/main/pg_hba.conf
systemctl restart postgresql
"

echo "--- 2. Datenbank & Schema initialisieren ---"
pct exec $CTID -- bash -c "
su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'
su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/install/init_db.sql'
"

echo "--- 3. Schema-Anpassung (Spaltennamen Fix) ---"
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c '
ALTER TABLE tenants RENAME COLUMN unit_id TO apartment_id;
ALTER TABLE meters ADD COLUMN IF NOT EXISTS is_submeter BOOLEAN DEFAULT FALSE;
ALTER TABLE meters ADD COLUMN IF NOT EXISTS parent_meter_id INTEGER;
'\"" 2>/dev/null

echo "--- 4. Ordner & Rechte für Backups ---"
pct exec $CTID -- bash -c "
mkdir -p /opt/hausverwaltung/backups
chmod -R 777 /opt/hausverwaltung/backups
chmod +x /opt/hausverwaltung/install/backup_db.sh
chmod 777 /var/run/postgresql
"

echo "--- 5. Datei-Fixing (Suchen & Ersetzen im Code) ---"
# Dieser Teil korrigiert den Code direkt im Container, falls im Git noch Fehler sind
pct exec $CTID -- bash -c "
  # Ersetze unit_id durch apartment_id in allen Dateien
  find /opt/hausverwaltung -type f -name '*.py' -exec sed -i 's/unit_id/apartment_id/g' {} +
  
  # Optional: Falls area in size_sqm umbenannt wurde (je nach init_db.sql)
  # find /opt/hausverwaltung -type f -name '*.py' -exec sed -i 's/area/size_sqm/g' {} +
"

echo "--- 6. Systemd Service (als Root für Update-Funktion) ---"
pct exec $CTID -- bash -c "
cat <<EOF > /etc/systemd/system/hausverwaltung.service
[Unit]
Description=Hausverwaltung Streamlit App
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hausverwaltung
ExecStart=/opt/hausverwaltung/venv/bin/streamlit run main.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hausverwaltung.service
systemctl restart hausverwaltung.service
"

echo "-------------------------------------------------------"
echo "✅ Installation auf LXC $CTID erfolgreich!"
echo "-------------------------------------------------------"
