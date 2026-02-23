#!/bin/bash
# setup_lxc.sh

# ... (Anfang bleibt gleich: CTID Suche, Storage Wahl, Passwort Abfrage) ...

# 5. DATENBANK-AUTHENTIFIZIERUNG FIXEN
echo "--- Datenbank-Berechtigungen (Trust) einrichten ---"
pct exec $CTID -- bash -c "
sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' /etc/postgresql/15/main/pg_hba.conf
sed -i 's/host    all             all             127.0.0.1\/32            scram-sha-256/host    all             all             127.0.0.1\/32            trust/' /etc/postgresql/15/main/pg_hba.conf
systemctl restart postgresql
"

# 6. DATENBANK INITIALISIEREN
pct exec $CTID -- bash -c "su - postgres -c 'psql -c \"CREATE DATABASE hausverwaltung;\"'"
pct exec $CTID -- bash -c "su - postgres -c 'psql -d hausverwaltung -f /opt/hausverwaltung/install/init_db.sql'"

# 7. SCHEMA-UPDATE (Sicherheitshalber falls init_db.sql nicht greift)
pct exec $CTID -- bash -c "su - postgres -c \"psql -d hausverwaltung -c '
ALTER TABLE tenants RENAME COLUMN unit_id TO apartment_id;
ALTER TABLE meters ADD COLUMN IF NOT EXISTS is_submeter BOOLEAN DEFAULT FALSE;
ALTER TABLE meters ADD COLUMN IF NOT EXISTS parent_meter_id INTEGER;
'\""

# 8. RESTART SERVICE
pct exec $CTID -- systemctl restart hausverwaltung.service
echo "Installation abgeschlossen!"
