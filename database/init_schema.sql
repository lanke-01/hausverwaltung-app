-- Erweitertes Schema für Hausverwaltung

-- 1. Objekte & 2. Einheiten (wie gehabt)
CREATE TABLE properties (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL
);

CREATE TABLE units (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
    unit_number VARCHAR(50),
    square_meters DECIMAL(10, 2) NOT NULL
);

-- 3. Mieter mit Mahnwesen und Rücks
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    unit_id INTEGER REFERENCES units(id),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    start_date DATE NOT NULL,
    end_date DATE,
    monthly_prepayment DECIMAL(10, 2),
    balance DECIMAL(10, 2) DEFAULT 0.00,       -- Positiv = Guthaben, Negativ = Rückstand
    reminder_count INTEGER DEFAULT 0           -- Anzahl der Mahnungen
);

-- 4. Zählerstände (für Verbrauchsabrechnung)
CREATE TABLE meter_readings (
    id SERIAL PRIMARY KEY,
    unit_id INTEGER REFERENCES units(id),
    meter_type VARCHAR(50),                   -- z.B. 'Kaltwasser', 'Warmwasser', 'Heizung'
    reading_value DECIMAL(15, 3) NOT NULL,
    reading_date DATE NOT NULL
);

-- 5. Kostenarten & 6. Ausgaben (wie gehabt)
CREATE TABLE cost_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    distribution_key VARCHAR(50) 
);

CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id),
    cost_type_id INTEGER REFERENCES cost_types(id),
    amount DECIMAL(10, 2) NOT NULL,
    billing_period_start DATE,
    billing_period_end DATE
);