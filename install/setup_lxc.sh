#!/bin/bash
# setup_lxc.sh

# ... (Hier bleibt dein bisheriger Anfang: CTID Suche, Storage Wahl, Passwort Abfrage, Git Clone, etc.) ...

# 5. DATENBANK-AUTHENTIFIZIERUNG FIXEN
echo "--- Datenbank-Berechtigungen (Trust) einrichten ---"
pct exec $CTID -- bash -c "
sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' /etc/postgresql/15/main/pg_hba.conf
sed -i 's/host    all             all             127.0.0.1\/32            scram-sha-256/host    all             all             127.0.0.1\/32            trust/' /etc/postgresql/15/main/pg_hba.conf
systemctl restart postgresql
"

# 6. DATENBANK INITIALISIEREN
echo "--- Datenbank initialisieren ---"
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/install/init_db.sql'"

# 7. SCHEMA-UPDATE & FIXES
echo "--- Schema-Updates ausführen ---"
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c '
ALTER TABLE tenants RENAME COLUMN unit_id TO apartment_id;
ALTER TABLE meters ADD COLUMN IF NOT EXISTS is_submeter BOOLEAN DEFAULT FALSE;
ALTER TABLE meters ADD COLUMN IF NOT EXISTS parent_meter_id INTEGER;
'\"" 2>/dev/null # 2>/dev/null unterdrückt Fehler, falls Spalten schon umbenannt sind

# 8. AUTOMATISCHE ORDNERSTRUKTUR & RECHTE
echo "--- Verzeichnisse erstellen und Berechtigungen setzen ---"
pct exec $CTID -- bash -c "
  # Backup-Ordner erstellen
  mkdir -p /opt/hausverwaltung/backups
  
  # Volle Rechte für Backups und App-Ordner (für Streamlit-Prozess)
  chmod -R 777 /opt/hausverwaltung/backups
  
  # Sicherstellen, dass Skripte ausführbar sind
  chmod +x /opt/hausverwaltung/install/backup_db.sh
  
  # Socket-Berechtigung für DB-Verbindung
  chmod 777 /var/run/postgresql
"

# 9. SYSTEMD SERVICE EINRICHTEN (Optimiert für Update-Funktion)
echo "--- Systemd Service einrichten ---"
pct exec $CTID -- bash -c "
cat <<EOF > /etc/systemd/system/hausverwaltung.service
[Unit]
Description=Hausverwaltung Streamlit App
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hausverwaltung
# Pfad zum venv muss stimmen - ggf. anpassen
ExecStart=/opt/hausverwaltung/venv/bin/streamlit run main.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hausverwaltung.service
systemctl restart hausverwaltung.service
"

echo "-------------------------------------------------------"
echo "✅ Installation abgeschlossen!"
echo "Die App ist erreichbar unter: http://<LXC-IP>:8501"
echo "Backups werden in /opt/hausverwaltung/backups gespeichert."
echo "-------------------------------------------------------"
