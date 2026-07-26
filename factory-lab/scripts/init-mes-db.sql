-- Manufacturing Execution System Database Schema
-- Simulates a realistic factory production system

-- ========== PRODUCTION LINES ==========
CREATE TABLE production_lines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    location VARCHAR(100),
    line_type VARCHAR(50),
    capacity_per_hour INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active'
);

-- ========== EQUIPMENT ==========
CREATE TABLE equipment (
    id SERIAL PRIMARY KEY,
    production_line_id INTEGER REFERENCES production_lines(id),
    name VARCHAR(100) NOT NULL,
    serial_number VARCHAR(50) UNIQUE,
    equipment_type VARCHAR(50),
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    installation_date DATE,
    last_maintenance DATE,
    maintenance_interval_days INTEGER,
    status VARCHAR(20) DEFAULT 'operational',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== PRODUCTION ORDERS ==========
CREATE TABLE production_orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    customer VARCHAR(150),
    product_code VARCHAR(50),
    quantity INTEGER,
    start_date TIMESTAMP,
    expected_completion TIMESTAMP,
    actual_completion TIMESTAMP,
    status VARCHAR(20) DEFAULT 'planned',
    priority VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
);

-- ========== PRODUCTION_BATCHES ==========
CREATE TABLE production_batches (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES production_orders(id),
    production_line_id INTEGER REFERENCES production_lines(id),
    batch_number VARCHAR(50) UNIQUE NOT NULL,
    batch_size INTEGER,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',
    operator_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== QUALITY INSPECTIONS ==========
CREATE TABLE quality_inspections (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER REFERENCES production_batches(id),
    inspection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    inspector_id VARCHAR(100),
    sample_size INTEGER,
    defects_found INTEGER,
    inspection_result VARCHAR(20),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== MAINTENANCE RECORDS ==========
CREATE TABLE maintenance_records (
    id SERIAL PRIMARY KEY,
    equipment_id INTEGER REFERENCES equipment(id),
    maintenance_type VARCHAR(50),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    technician_id VARCHAR(100),
    hours_spent DECIMAL(5,2),
    parts_replaced TEXT,
    status VARCHAR(20) DEFAULT 'completed',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== PRODUCTION METRICS ==========
CREATE TABLE production_metrics (
    id SERIAL PRIMARY KEY,
    production_line_id INTEGER REFERENCES production_lines(id),
    measurement_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    units_produced INTEGER,
    downtime_minutes INTEGER,
    efficiency_percent DECIMAL(5,2),
    defect_rate DECIMAL(5,2),
    temperature DECIMAL(5,1),
    pressure DECIMAL(7,2),
    power_consumption DECIMAL(8,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== INVENTORY ==========
CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    product_code VARCHAR(50) NOT NULL,
    product_name VARCHAR(150),
    quantity_on_hand INTEGER,
    quantity_reserved INTEGER,
    reorder_point INTEGER,
    supplier VARCHAR(150),
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location VARCHAR(100),
    UNIQUE(product_code)
);

-- ========== USERS/OPERATORS ==========
CREATE TABLE operators (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(100),
    department VARCHAR(50),
    role VARCHAR(50),
    certification_level VARCHAR(50),
    certification_expires DATE,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== ALERTS/INCIDENTS ==========
CREATE TABLE incidents (
    id SERIAL PRIMARY KEY,
    incident_type VARCHAR(50),
    severity VARCHAR(20),
    description TEXT,
    equipment_id INTEGER REFERENCES equipment(id),
    reported_by VARCHAR(100),
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'open',
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    resolution_notes TEXT
);

-- ========== SHIFT LOGS ==========
CREATE TABLE shift_logs (
    id SERIAL PRIMARY KEY,
    shift_date DATE,
    shift_number INTEGER,
    supervisor_id VARCHAR(100),
    notes TEXT,
    production_line_id INTEGER REFERENCES production_lines(id),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========== INITIAL DATA ==========

-- Production Lines
INSERT INTO production_lines (name, location, line_type, capacity_per_hour) VALUES
('Assembly Line A', 'Building A, Floor 1', 'assembly', 150),
('Assembly Line B', 'Building A, Floor 1', 'assembly', 150),
('Packaging Line 1', 'Building A, Floor 2', 'packaging', 200),
('Welding Station', 'Building B', 'welding', 80),
('Testing Lab', 'Building B', 'testing', 50);

-- Equipment
INSERT INTO equipment (production_line_id, name, serial_number, equipment_type, manufacturer, model, installation_date, last_maintenance, maintenance_interval_days, status) VALUES
(1, 'Conveyor Belt A1', 'CB-2020-001', 'conveyor', 'TechFlow', 'TF-3000', '2020-01-15', '2024-07-01', 30, 'operational'),
(1, 'Robot Arm A1', 'RA-2021-001', 'robot', 'ABB', 'IRB 6700', '2021-03-20', '2024-06-15', 45, 'operational'),
(2, 'Conveyor Belt B1', 'CB-2020-002', 'conveyor', 'TechFlow', 'TF-3000', '2020-02-10', '2024-07-05', 30, 'operational'),
(2, 'Robot Arm B1', 'RA-2021-002', 'robot', 'ABB', 'IRB 6700', '2021-04-15', '2024-06-20', 45, 'operational'),
(3, 'Packaging Machine 1', 'PM-2022-001', 'packaging', 'Bosch', 'Bosch KGX', '2022-05-01', '2024-06-30', 30, 'operational'),
(4, 'Welding Machine', 'WM-2019-001', 'welding', 'KUKA', 'KR CYBERTECH', '2019-11-01', '2024-05-30', 60, 'operational'),
(5, 'Test Equipment 1', 'TE-2023-001', 'testing', 'Flextronics', 'FX-AUTO', '2023-01-15', '2024-07-10', 30, 'operational');

-- Operators
INSERT INTO operators (username, full_name, department, role, certification_level, certification_expires, active) VALUES
('john.smith', 'John Smith', 'Production', 'Line Operator', 'Level 3', '2025-06-30', true),
('sarah.johnson', 'Sarah Johnson', 'Production', 'Line Lead', 'Level 4', '2026-12-31', true),
('michael.brown', 'Michael Brown', 'Maintenance', 'Technician', 'Level 3', '2025-03-15', true),
('emily.davis', 'Emily Davis', 'Quality Assurance', 'Inspector', 'Level 2', '2024-11-30', true),
('david.wilson', 'David Wilson', 'Operations', 'Supervisor', 'Level 4', '2026-09-30', true);

-- Sample Production Order
INSERT INTO production_orders (order_number, customer, product_code, quantity, start_date, expected_completion, status, priority, created_by) VALUES
('PO-2024-001', 'Global Industries Inc.', 'PROD-A-123', 5000, '2024-07-15', '2024-07-25', 'in_progress', 'high', 'david.wilson'),
('PO-2024-002', 'Tech Solutions Ltd.', 'PROD-B-456', 3000, '2024-07-16', '2024-07-28', 'planned', 'medium', 'david.wilson'),
('PO-2024-003', 'Manufacturing Co.', 'PROD-A-789', 2500, '2024-07-10', '2024-07-20', 'completed', 'high', 'david.wilson');

-- Sample Inventory
INSERT INTO inventory (product_code, product_name, quantity_on_hand, quantity_reserved, reorder_point, supplier, location) VALUES
('PROD-A-123', 'Component A Type 1', 450, 200, 100, 'SupplierX Inc.', 'Warehouse A'),
('PROD-B-456', 'Component B Type 2', 320, 150, 75, 'SupplierY Ltd.', 'Warehouse B'),
('PROD-A-789', 'Component A Type 3', 100, 50, 100, 'SupplierZ Corp.', 'Warehouse A'),
('RAW-001', 'Raw Material 1', 1000, 0, 500, 'RawMat Suppliers', 'Warehouse C'),
('RAW-002', 'Raw Material 2', 750, 200, 400, 'RawMat Suppliers', 'Warehouse C');

-- Create Indexes
CREATE INDEX idx_production_lines_status ON production_lines(status);
CREATE INDEX idx_equipment_line ON equipment(production_line_id);
CREATE INDEX idx_equipment_status ON equipment(status);
CREATE INDEX idx_orders_status ON production_orders(status);
CREATE INDEX idx_batches_line ON production_batches(production_line_id);
CREATE INDEX idx_batches_order ON production_batches(order_id);
CREATE INDEX idx_maintenance_equipment ON maintenance_records(equipment_id);
CREATE INDEX idx_metrics_line ON production_metrics(production_line_id);
CREATE INDEX idx_metrics_time ON production_metrics(measurement_time);
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_shift_logs_date ON shift_logs(shift_date);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO mes_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mes_admin;
