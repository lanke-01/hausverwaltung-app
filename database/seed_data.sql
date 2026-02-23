-- Standard-Kostenarten nach Betriebskostenverordnung (BetrKV)
INSERT INTO cost_types (name, distribution_key) VALUES 
('Grundsteuer', 'square_meters'),
('Wasserversorgung', 'consumption'),
('Entwässerung', 'consumption'),
('Aufzug', 'square_meters'),
('Straßenreinigung', 'square_meters'),
('Müllabfuhr', 'unit'),
('Gebäudereinigung', 'square_meters'),
('Gartenpflege', 'square_meters'),
('Beleuchtung (Allgemeinstrom)', 'square_meters'),
('Schornsteinreinigung', 'unit'),
('Sach- und Haftpflichtversicherung', 'square_meters'),
('Hauswart / Hausmeister', 'square_meters'),
('Gemeinschaftsantenne / Kabelanschluss', 'unit'),
('Wascheinrichtungen', 'unit');

-- Beispiel-Objekt für den ersten Start
INSERT INTO properties (name, address) VALUES 
('Musterhaus Allee', 'Beispielstraße 42, 12345 Musterstadt');

-- Beispiel-Einheiten für das Objekt (ID 1)
INSERT INTO units (property_id, unit_number, square_meters) VALUES 
(1, 'EG Links', 65.00),
(1, 'EG Rechts', 80.00),
(1, 'OG Links', 75.50);

-- Ein Test-Mieter, damit man sofort sieht, wie es aussieht
INSERT INTO tenants (unit_id, first_name, last_name, start_date, monthly_prepayment, balance) 
VALUES (1, 'Erika', 'Mustermann', '2026-01-01', 200.00, 0.00);