-- init_db.sql
-- Bestehende Tabellen löschen (Vorsicht: Nur bei Neuinstallation!)
DROP TABLE IF EXISTS meter_readings CASCADE;
DROP TABLE IF EXISTS meters CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
DROP TABLE IF EXISTS apartments CASCADE;
DROP TABLE IF EXISTS landlord_settings CASCADE;
DROP TABLE IF EXISTS operating_expenses CASCADE;
DROP TABLE IF EXISTS tenant_keywords CASCADE;

-- 1. Vermieter-Einstellungen
CREATE TABLE landlord_settings (
    id SERIAL PRIMARY KEY, 
    name VARCHAR(255), 
    street VARCHAR(255), 
    city VARCHAR(255), 
    iban VARCHAR(50), 
    bank_name VARCHAR(255),
    total_area NUMERIC(10,2) DEFAULT 0,
    total_occupants INTEGER DEFAULT 0,
    total_units INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Wohnungen
CREATE TABLE apartments (
    id SERIAL PRIMARY KEY,
    unit_name VARCHAR(255),
    area NUMERIC(10,2),
    base_rent NUMERIC(10,2)
);

-- 3. Mieter
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    apartment_id INTEGER REFERENCES apartments(id),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    move_in DATE,
    move_out DATE,
    occupants INTEGER DEFAULT 1,
    monthly_prepayment NUMERIC(10,2) DEFAULT 0
);

-- 4. Betriebskosten (Wichtig: Name ist jetzt operating_expenses)
CREATE TABLE operating_expenses (
    id SERIAL PRIMARY KEY,
    expense_type VARCHAR(255),
    amount NUMERIC(12,2),
    distribution_key VARCHAR(50), -- z.B. 'area', 'person', 'unit', 'direct'
    expense_year INTEGER,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE SET NULL,
    expense_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. Zahlungen
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    amount NUMERIC(10,2),
    payment_date DATE DEFAULT CURRENT_DATE,
    payment_type VARCHAR(50),
    note TEXT
);

-- 6. Zähler (für Strom, Wasser, Wallbox)
CREATE TABLE meters (
    id SERIAL PRIMARY KEY,
    apartment_id INTEGER REFERENCES apartments(id),
    meter_type VARCHAR(50),
    meter_number VARCHAR(100),
    is_submeter BOOLEAN DEFAULT FALSE,
    parent_meter_id INTEGER -- ID des Hauptzählers für Wallbox-Differenz
);

-- 7. Ablesewerte
CREATE TABLE meter_readings (
    id SERIAL PRIMARY KEY,
    meter_id INTEGER REFERENCES meters(id) ON DELETE CASCADE,
    reading_date DATE DEFAULT CURRENT_DATE,
    reading_value NUMERIC(12,2)
);

-- 8. NEU: Keywords für automatische CSV-Zuweisung
CREATE TABLE tenant_keywords (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    keyword VARCHAR(255) UNIQUE NOT NULL
);

-- Standard-Einstellungen einfügen
INSERT INTO landlord_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;