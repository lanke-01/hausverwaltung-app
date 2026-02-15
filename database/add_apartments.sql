-- 1. Tabelle für Wohnungen erstellen
CREATE TABLE apartments (
    id SERIAL PRIMARY KEY,
    unit_name VARCHAR(50) NOT NULL, -- z.B. "EG links"
    size_sqm DECIMAL(5,2),           -- Quadratmeter
    base_rent DECIMAL(10,2)          -- Kaltmiete
);

-- 2. Den Mietern eine Wohnungs-ID hinzufügen
ALTER TABLE tenants ADD COLUMN apartment_id INTEGER REFERENCES apartments(id);

-- 3. Beispiel-Wohnung anlegen
INSERT INTO apartments (unit_name, size_sqm, base_rent) 
VALUES ('EG links', 65.50, 550.00);

-- 4. Erika der Wohnung zuordnen
UPDATE tenants SET apartment_id = 1 WHERE last_name = 'Mustermann';