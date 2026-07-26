#!/usr/bin/env python3
"""SCADA System Simulator - Modbus server with Flask API."""

import os
import threading
import time
import random
from datetime import datetime
from flask import Flask, jsonify
from pymodbus.server.sync import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataStore
from pymodbus.datastore import ModbusSparseDataStore
from pymodbus.datastore import ModbusSlaveContext
from pymodbus.datastore import ModbusServerContext

app = Flask(__name__)

# Global state for simulated factory data
factory_state = {
    'production_lines': {
        'line_1': {'running': True, 'speed': 95, 'temp': 72, 'pressure': 30},
        'line_2': {'running': True, 'speed': 88, 'temp': 71, 'pressure': 28},
        'line_3': {'running': True, 'speed': 92, 'temp': 73, 'pressure': 31},
        'line_4': {'running': False, 'speed': 0, 'temp': 68, 'pressure': 0},
        'line_5': {'running': True, 'speed': 85, 'temp': 70, 'pressure': 29},
    },
    'plcs': {},
    'sensors': {},
    'alarms': [],
    'last_update': datetime.now().isoformat()
}

def initialize_modbus_datastore():
    """Initialize Modbus data store with simulated factory data."""
    store = ModbusSlaveContext(
        di=ModbusSparseDataStore(),
        co=ModbusSparseDataStore(),
        hr=ModbusSparseDataStore(),
        ir=ModbusSparseDataStore()
    )

    # Map production line states to registers (Holding Registers)
    register_offset = 0
    for line_id, (line_name, line_data) in enumerate(factory_state['production_lines'].items()):
        base_addr = register_offset + (line_id * 10)
        store.store[3][base_addr + 0] = 1 if line_data['running'] else 0  # Status
        store.store[3][base_addr + 1] = int(line_data['speed'] * 100)      # Speed (scaled)
        store.store[3][base_addr + 2] = int(line_data['temp'] * 10)        # Temp (scaled)
        store.store[3][base_addr + 3] = int(line_data['pressure'] * 100)   # Pressure (scaled)

    return ModbusServerContext({'*': store}, single=False)

def simulate_factory_dynamics():
    """Simulate realistic factory dynamics."""
    while True:
        try:
            time.sleep(5)

            # Update production line states
            for line_name, line_data in factory_state['production_lines'].items():
                if line_data['running']:
                    # Add some variance
                    line_data['speed'] += random.uniform(-2, 3)
                    line_data['speed'] = max(0, min(100, line_data['speed']))

                    line_data['temp'] += random.uniform(-1, 1)
                    line_data['pressure'] += random.uniform(-0.5, 0.5)

                    # Simulate occasional downtime
                    if random.random() < 0.02:  # 2% chance per cycle
                        line_data['running'] = False
                        factory_state['alarms'].append({
                            'line': line_name,
                            'timestamp': datetime.now().isoformat(),
                            'message': f'{line_name} stopped unexpectedly'
                        })
                else:
                    # Simulate recovery
                    if random.random() < 0.05:  # 5% chance per cycle
                        line_data['running'] = True
                        line_data['speed'] = 0
                        factory_state['alarms'].append({
                            'line': line_name,
                            'timestamp': datetime.now().isoformat(),
                            'message': f'{line_name} restarted'
                        })

            # Keep only last 100 alarms
            factory_state['alarms'] = factory_state['alarms'][-100:]
            factory_state['last_update'] = datetime.now().isoformat()

        except Exception as e:
            print(f"Error in simulation: {e}")

# REST API Endpoints
@app.route('/scada/health', methods=['GET'])
def health():
    return jsonify({'status': 'online', 'timestamp': datetime.now().isoformat()})

@app.route('/scada/status', methods=['GET'])
def get_status():
    return jsonify(factory_state)

@app.route('/scada/lines', methods=['GET'])
def get_lines():
    return jsonify({
        'lines': factory_state['production_lines'],
        'timestamp': factory_state['last_update']
    })

@app.route('/scada/lines/<line_name>', methods=['GET'])
def get_line(line_name):
    if line_name not in factory_state['production_lines']:
        return jsonify({'error': 'Not found'}), 404

    return jsonify({
        'name': line_name,
        'data': factory_state['production_lines'][line_name],
        'timestamp': factory_state['last_update']
    })

@app.route('/scada/alarms', methods=['GET'])
def get_alarms():
    return jsonify({
        'alarms': factory_state['alarms'][-50:],  # Last 50
        'total': len(factory_state['alarms'])
    })

@app.route('/scada/lines/<line_name>/control', methods=['POST'])
def control_line(line_name):
    """Control production line (start/stop)."""
    if line_name not in factory_state['production_lines']:
        return jsonify({'error': 'Not found'}), 404

    data = request.get_json()
    action = data.get('action', 'status')

    if action == 'start':
        factory_state['production_lines'][line_name]['running'] = True
        return jsonify({'status': 'started', 'line': line_name})
    elif action == 'stop':
        factory_state['production_lines'][line_name]['running'] = False
        return jsonify({'status': 'stopped', 'line': line_name})
    else:
        return jsonify({'error': 'Invalid action'}), 400

@app.route('/scada/metrics', methods=['GET'])
def get_metrics():
    """Get aggregate metrics."""
    running_count = sum(1 for line in factory_state['production_lines'].values() if line['running'])
    total_lines = len(factory_state['production_lines'])
    avg_speed = sum(line['speed'] for line in factory_state['production_lines'].values()) / total_lines
    avg_temp = sum(line['temp'] for line in factory_state['production_lines'].values()) / total_lines

    return jsonify({
        'production_lines': {
            'total': total_lines,
            'running': running_count,
            'availability': (running_count / total_lines * 100) if total_lines > 0 else 0
        },
        'average_speed_percent': round(avg_speed, 2),
        'average_temperature_c': round(avg_temp, 2),
        'recent_alarms': len(factory_state['alarms'][-10:])
    })

def run_modbus_server():
    """Run Modbus server in separate thread."""
    try:
        context = initialize_modbus_datastore()
        identity = ModbusDeviceIdentification(
            info_name='Factory SCADA System',
            info_code='FA0001',
            info_text='Industrial SCADA Simulator'
        )
        StartTcpServer(context, identity=identity, address=('0.0.0.0', 502))
    except Exception as e:
        print(f"Modbus server error: {e}")

if __name__ == '__main__':
    # Start Modbus server in background
    modbus_thread = threading.Thread(target=run_modbus_server, daemon=True)
    modbus_thread.start()

    # Start simulation
    sim_thread = threading.Thread(target=simulate_factory_dynamics, daemon=True)
    sim_thread.start()

    # Run Flask app
    app.run(host='0.0.0.0', port=8001, debug=False)
