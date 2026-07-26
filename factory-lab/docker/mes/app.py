#!/usr/bin/env python3
"""Manufacturing Execution System - REST API Server."""

import os
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database Configuration
db_user = os.getenv('DB_USER', 'mes_admin')
db_password = os.getenv('DB_PASSWORD', 'MESp@ssw0rd123!')
db_host = os.getenv('DB_HOST', 'mes-db')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'manufacturing')

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class ProductionLine(db.Model):
    __tablename__ = 'production_lines'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    location = db.Column(db.String(100))
    line_type = db.Column(db.String(50))
    capacity_per_hour = db.Column(db.Integer)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Equipment(db.Model):
    __tablename__ = 'equipment'
    id = db.Column(db.Integer, primary_key=True)
    production_line_id = db.Column(db.Integer, db.ForeignKey('production_lines.id'))
    name = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(50), unique=True)
    equipment_type = db.Column(db.String(50))
    manufacturer = db.Column(db.String(100))
    status = db.Column(db.String(20), default='operational')

class ProductionOrder(db.Model):
    __tablename__ = 'production_orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    customer = db.Column(db.String(150))
    product_code = db.Column(db.String(50))
    quantity = db.Column(db.Integer)
    start_date = db.Column(db.DateTime)
    expected_completion = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='planned')
    priority = db.Column(db.String(20))

class ProductionMetrics(db.Model):
    __tablename__ = 'production_metrics'
    id = db.Column(db.Integer, primary_key=True)
    production_line_id = db.Column(db.Integer, db.ForeignKey('production_lines.id'))
    measurement_time = db.Column(db.DateTime, default=datetime.utcnow)
    units_produced = db.Column(db.Integer)
    downtime_minutes = db.Column(db.Integer)
    efficiency_percent = db.Column(db.Numeric(5, 2))
    defect_rate = db.Column(db.Numeric(5, 2))

# Health check
@app.route('/health', methods=['GET'])
def health():
    try:
        db.session.execute('SELECT 1')
        return jsonify({'status': 'healthy', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Production Lines API
@app.route('/api/v1/production-lines', methods=['GET'])
def get_production_lines():
    lines = ProductionLine.query.all()
    return jsonify([{
        'id': line.id,
        'name': line.name,
        'location': line.location,
        'type': line.line_type,
        'capacity': line.capacity_per_hour,
        'status': line.status
    } for line in lines])

@app.route('/api/v1/production-lines/<int:line_id>', methods=['GET'])
def get_production_line(line_id):
    line = ProductionLine.query.get(line_id)
    if not line:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': line.id,
        'name': line.name,
        'location': line.location,
        'type': line.line_type,
        'capacity': line.capacity_per_hour,
        'status': line.status
    })

# Equipment API
@app.route('/api/v1/equipment', methods=['GET'])
def get_equipment():
    equipment = Equipment.query.all()
    return jsonify([{
        'id': eq.id,
        'name': eq.name,
        'serial': eq.serial_number,
        'type': eq.equipment_type,
        'manufacturer': eq.manufacturer,
        'status': eq.status
    } for eq in equipment])

# Production Orders API
@app.route('/api/v1/orders', methods=['GET'])
def get_orders():
    orders = ProductionOrder.query.all()
    return jsonify([{
        'id': order.id,
        'order_number': order.order_number,
        'customer': order.customer,
        'product_code': order.product_code,
        'quantity': order.quantity,
        'status': order.status,
        'priority': order.priority
    } for order in orders])

@app.route('/api/v1/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = ProductionOrder.query.get(order_id)
    if not order:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': order.id,
        'order_number': order.order_number,
        'customer': order.customer,
        'product_code': order.product_code,
        'quantity': order.quantity,
        'start_date': order.start_date.isoformat() if order.start_date else None,
        'expected_completion': order.expected_completion.isoformat() if order.expected_completion else None,
        'status': order.status,
        'priority': order.priority
    })

# Metrics API
@app.route('/api/v1/metrics', methods=['GET'])
def get_metrics():
    line_id = request.args.get('line_id', type=int)
    query = ProductionMetrics.query
    if line_id:
        query = query.filter_by(production_line_id=line_id)
    metrics = query.order_by(ProductionMetrics.measurement_time.desc()).limit(100).all()

    return jsonify([{
        'id': m.id,
        'line_id': m.production_line_id,
        'timestamp': m.measurement_time.isoformat(),
        'units_produced': m.units_produced,
        'downtime_minutes': m.downtime_minutes,
        'efficiency_percent': float(m.efficiency_percent) if m.efficiency_percent else 0,
        'defect_rate': float(m.defect_rate) if m.defect_rate else 0
    } for m in metrics])

# Dashboard summary
@app.route('/api/v1/dashboard', methods=['GET'])
def get_dashboard():
    total_orders = ProductionOrder.query.count()
    active_orders = ProductionOrder.query.filter_by(status='in_progress').count()
    total_equipment = Equipment.query.count()
    operational_equipment = Equipment.query.filter_by(status='operational').count()

    return jsonify({
        'timestamp': datetime.utcnow().isoformat(),
        'orders': {
            'total': total_orders,
            'active': active_orders
        },
        'equipment': {
            'total': total_equipment,
            'operational': operational_equipment,
            'availability': (operational_equipment / total_equipment * 100) if total_equipment > 0 else 0
        }
    })

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database initialized")
        except Exception as e:
            logger.warning(f"Database already exists or error: {e}")

    port = int(os.getenv('MES_PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
