DROP TABLE IF EXISTS meter_readings CASCADE;
DROP TABLE IF EXISTS meters CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
DROP TABLE IF EXISTS apartments CASCADE;
DROP TABLE IF EXISTS landlord_settings CASCADE;

CREATE TABLE landlord_settings (
    id SERIAL PRIMARY KEY, 
    name VARCHAR(255), 
    street VARCHAR(255), 
    city VARCHAR(255), 
    iban VARCHAR(50), 
    bank_name VARCHAR(255),
    updated_at TIMESTAMP DEFAULT NOW() -- DIESES FELD FEHLTE!
);

CREATE TABLE apartments (
    id SERIAL PRIMARY KEY,
    unit_name VARCHAR(255),
    size_sqm NUMERIC(10,2),
    base_rent NUMERIC(10,2),
    service_charge_propayment NUMERIC(10,2)
);

CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    apartment_id INTEGER REFERENCES apartments(id),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    moved_in DATE,
    moved_out DATE,
    occupants INTEGER DEFAULT 1, -- DIESE ZEILE FEHLTE!
    phone VARCHAR(50),
    email VARCHAR(255)
);

CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    amount NUMERIC(10,2),
    period_month INTEGER,
    period_year INTEGER,
    payment_date DATE
);

CREATE TABLE meters (
    id SERIAL PRIMARY KEY,
    apartment_id INTEGER REFERENCES apartments(id),
    meter_type VARCHAR(50),
    meter_number VARCHAR(100),
    unit VARCHAR(20) DEFAULT 'kWh'
);

CREATE TABLE meter_readings (
    id SERIAL PRIMARY KEY,
    meter_id INTEGER REFERENCES meters(id),
    reading_date DATE,
    reading_value NUMERIC(15,3),
    comment TEXT
);