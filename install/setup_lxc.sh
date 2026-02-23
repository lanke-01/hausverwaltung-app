#!/bin/bash
# setup_lxc.sh

# ... [Deine ID-Suche und Storage-Wahl bleibt gleich] ...

# 5. Datenbank-Konfiguration (Rechte setzen)
echo "--- Konfiguriere PostgreSQL Rechte ---"
pct exec $CTID -- bash -c "
sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' /etc/postgresql/15/main/pg_hba.conf
sed -i 's/host    all             all             127.0.0.1\/32            scram-sha-256/host    all             all             127.0.0.1\/32            trust/' /etc/postgresql/15/main/pg_hba.conf
systemctl restart postgresql
"

# 6. Datenbank & Tabellen initialisieren
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/install/init_db.sql'"

# 7. AUTOMATISCHES UPGRADE (Falls Tabellen schon da waren)
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c '
ALTER TABLE tenants RENAME COLUMN unit_id TO apartment_id;
ALTER TABLE meters ADD COLUMN IF NOT EXISTS is_submeter BOOLEAN DEFAULT FALSE;
ALTER TABLE meters ADD COLUMN IF NOT EXISTS parent_meter_id INTEGER;
'\""

# ... [Rest deines Setup-Skripts] ...
