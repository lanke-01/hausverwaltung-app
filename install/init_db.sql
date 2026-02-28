-- init_db.sql
DROP TABLE IF EXISTS meter_readings CASCADE;
DROP TABLE IF EXISTS meters CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
DROP TABLE IF EXISTS apartments CASCADE;
DROP TABLE IF EXISTS landlord_settings CASCADE;
DROP TABLE IF EXISTS expenses CASCADE;

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

CREATE TABLE apartments (
    id SERIAL PRIMARY KEY,
    unit_name VARCHAR(255),
    area NUMERIC(10,2), -- Vereinheitlicht auf 'area'
    base_rent NUMERIC(10,2)
);

CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    apartment_id INTEGER REFERENCES apartments(id), -- Vereinheitlicht auf 'apartment_id'
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    move_in DATE,
    move_out DATE,
    occupants INTEGER DEFAULT 1,
    monthly_prepayment NUMERIC(10,2) DEFAULT 0
);

CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    expense_type VARCHAR(255),
    amount NUMERIC(10,2),
    expense_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE meters (
    id SERIAL PRIMARY KEY,
    apartment_id INTEGER REFERENCES apartments(id),
    meter_type VARCHAR(50),
    meter_number VARCHAR(100),
    is_submeter BOOLEAN DEFAULT FALSE, -- Wallbox Unterstützung
    parent_meter_id INTEGER             -- Verknüpfung zu Hauptzähler
);

CREATE TABLE meter_readings (
    id SERIAL PRIMARY KEY,
    meter_id INTEGER REFERENCES meters(id),
    reading_date DATE DEFAULT CURRENT_DATE,
    reading_value NUMERIC(15,3)
);

-- Erweiterung für die automatische Zuordnung
CREATE TABLE IF NOT EXISTS tenant_keywords (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    keyword VARCHAR(255) UNIQUE NOT NULL
);