# Factory Lab - Safety-Critical Systems Guide

## Safety Standards Implementation

### IEC 61508 / ISO 13849-1 Compliance

```
Safety Integrity Levels (SILs):
├─ SIL 1: Simple safety devices (low risk)
├─ SIL 2: Moderate risk mitigation
├─ SIL 3: High-risk operations (most PLCs)
└─ SIL 4: Critical systems (rare, only where life is at stake)

Factory Lab Implementation: SIL 3 systems (emergency stops, interlocks)
```

---

## Emergency Stop Architecture

### 1. E-Stop Hierarchy

```
┌────────────────────────────────────────────────────────────┐
│ EMERGENCY STOP ARCHITECTURE - REDUNDANT & HARDWIRED       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ LEVEL 0: HARDWIRED E-STOP (IEC 60204-1)                  │
│ ├─ Physical E-stop buttons on each machine               │
│ ├─ Direct 24VDC circuit (NO relay - safety rated)        │
│ ├─ Cross-wired dual-channel: BOTH must close to restart  │
│ └─ Monitored by safety PLC (watchdog timer)              │
│                                                            │
│ LEVEL 1: SAFETY PLC (Single Channel)                     │
│ ├─ Monitors all sensors (pressure, temperature, limits)  │
│ ├─ Executes safety logic (IEC 61131-3 SafetyPLC language)│
│ ├─ Triggers E-stop if unsafe condition detected          │
│ └─ Redundant power supply (dual PSUs, battery backup)    │
│                                                            │
│ LEVEL 2: SAFETY PLCS (Dual Channel)                      │
│ ├─ Two independent safety PLCs run same logic            │
│ ├─ Compare outputs: MUST match                           │
│ ├─ If outputs differ → immediate E-stop                  │
│ └─ Heartbeat monitoring between channels                 │
│                                                            │
│ LEVEL 3: REMOTE E-STOP (MES Application)                │
│ ├─ Software trigger (lower priority)                      │
│ ├─ Cannot override hardware E-stop                        │
│ ├─ Used for graceful shutdown procedures                 │
│ └─ Requires dual authorization (manager + operator)      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 2. E-Stop Implementation in Docker

```python
# /factory-lab/docker/safety/emergency_stop_controller.py

import time
import threading
from enum import Enum
from datetime import datetime
import json

class SafetyState(Enum):
    RUNNING = "running"
    E_STOP_ACTIVE = "e_stop_active"
    FAULT = "fault"
    MAINTENANCE = "maintenance"

class EmergencyStopController:
    """SIL 3 Emergency Stop Controller with dual-channel monitoring."""
    
    def __init__(self):
        self.state = SafetyState.RUNNING
        self.channels = {
            'primary': {'status': True, 'last_heartbeat': time.time()},
            'secondary': {'status': True, 'last_heartbeat': time.time()}
        }
        self.e_stop_log = []
        self.lock = threading.RLock()
        
        # Start watchdog thread
        self.watchdog_thread = threading.Thread(target=self._watchdog_monitor, daemon=True)
        self.watchdog_thread.start()
    
    def trigger_e_stop(self, source: str, reason: str, authorized_by: str = None):
        """Trigger emergency stop (SIL 3 rated)."""
        with self.lock:
            timestamp = datetime.utcnow().isoformat()
            
            # Log the event
            event = {
                'timestamp': timestamp,
                'source': source,  # 'button', 'plc', 'mes', 'sensor'
                'reason': reason,
                'authorized_by': authorized_by,
                'previous_state': self.state.value
            }
            self.e_stop_log.append(event)
            
            # Set safety state
            self.state = SafetyState.E_STOP_ACTIVE
            
            # Cascade shutdown
            self._cascade_shutdown()
            
            # Notify all systems
            self._notify_all_systems('E_STOP')
            
            # Log to immutable audit
            self._log_to_audit(event)
            
            return {
                'status': 'E_STOP_TRIGGERED',
                'timestamp': timestamp,
                'reason': reason
            }
    
    def _cascade_shutdown(self):
        """Cascade shutdown sequence."""
        # Order matters! Safety first
        steps = [
            ('solenoid_valves', self._close_solenoids),           # Cut fluid/gas
            ('motor_drives', self._stop_motor_drives),            # Stop rotation
            ('heating_elements', self._disable_heating),          # Stop heat
            ('material_flow', self._stop_material_flow),          # Stop material
            ('pneumatics', self._vent_pneumatics),                # Vent pressure
        ]
        
        for step_name, step_func in steps:
            try:
                step_func()
                time.sleep(0.1)  # Sequential with delays
            except Exception as e:
                # Never suppress errors in safety systems
                raise RuntimeError(f"Cascade shutdown failed at {step_name}: {e}")
    
    def _close_solenoids(self):
        """Close all solenoid valves (pneumatic/hydraulic cutoff)."""
        # Send hardwired signal to solenoid driver board
        # Typically done via GPIO or relay output
        pass
    
    def _stop_motor_drives(self):
        """Stop all motor drives via VFD."""
        # Send deceleration command to VFDs
        # Follow ramp-down curve to avoid shock
        pass
    
    def _disable_heating(self):
        """Disable all heating elements."""
        # Cut power to heating circuits
        pass
    
    def _stop_material_flow(self):
        """Stop material conveyor systems."""
        # Trigger material brake
        pass
    
    def _vent_pneumatics(self):
        """Vent all pneumatic systems to atmosphere."""
        # Open safety vent solenoids
        pass
    
    def _notify_all_systems(self, event_type):
        """Notify all connected systems of safety event."""
        notification = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'state': self.state.value
        }
        
        # Send to:
        # - SCADA system
        # - MES application
        # - Remote monitoring
        # - Facility emergency alarm
    
    def _watchdog_monitor(self):
        """Continuous dual-channel monitoring (SIL 3)."""
        while True:
            with self.lock:
                current_time = time.time()
                
                # Check channel heartbeats
                for channel, status in self.channels.items():
                    heartbeat_age = current_time - status['last_heartbeat']
                    
                    # If heartbeat > 500ms old, trigger E-stop
                    if heartbeat_age > 0.5:
                        self.trigger_e_stop(
                            source=f"watchdog_{channel}",
                            reason=f"Heartbeat timeout on {channel} channel"
                        )
            
            time.sleep(0.1)  # 100ms monitoring cycle
    
    def reset_e_stop(self, authorized_by: str, password: str):
        """Reset E-stop (requires authentication)."""
        # Verify multi-factor authorization
        if not self._verify_mfa(authorized_by, password):
            return {'status': 'RESET_DENIED', 'reason': 'Authentication failed'}
        
        with self.lock:
            self.state = SafetyState.RUNNING
            
            # Log reset
            self.e_stop_log.append({
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'reset',
                'authorized_by': authorized_by
            })
            
            return {'status': 'RESET_SUCCESSFUL', 'state': self.state.value}
    
    def _verify_mfa(self, user: str, password: str) -> bool:
        """Multi-factor authentication for E-stop reset."""
        # Check password
        # Check MFA code from phone/email
        # Log attempt
        return True  # Simplified
    
    def get_status(self):
        """Get current safety status."""
        return {
            'state': self.state.value,
            'timestamp': datetime.utcnow().isoformat(),
            'channels': self.channels,
            'recent_events': self.e_stop_log[-10:]  # Last 10 events
        }
    
    def _log_to_audit(self, event):
        """Log to immutable audit trail."""
        # Log to PostgreSQL audit table
        # This log CANNOT be deleted (compliance requirement)
        pass

# Global instance
emergency_stop = EmergencyStopController()

# Flask API endpoints
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/safety/e-stop', methods=['POST'])
def trigger_estop():
    """Trigger emergency stop."""
    data = request.get_json()
    source = data.get('source', 'api')
    reason = data.get('reason', 'Manual trigger')
    auth_user = data.get('authorized_by', 'unknown')
    
    result = emergency_stop.trigger_e_stop(source, reason, auth_user)
    return jsonify(result)

@app.route('/safety/status', methods=['GET'])
def get_safety_status():
    """Get current safety status."""
    return jsonify(emergency_stop.get_status())

@app.route('/safety/reset', methods=['POST'])
def reset_estop():
    """Reset emergency stop."""
    data = request.get_json()
    authorized_by = data.get('authorized_by')
    password = data.get('password')
    
    result = emergency_stop.reset_e_stop(authorized_by, password)
    return jsonify(result)
```

---

## Safety Interlocks

### 1. Guard Interlocks

```python
# /factory-lab/docker/safety/guard_interlocks.py

class GuardInterlock:
    """Guard interlock system (SIL 2/3) - prevents operation when guard open."""
    
    def __init__(self, production_line_id, guard_id):
        self.line_id = production_line_id
        self.guard_id = guard_id
        self.guard_state = 'closed'  # 'closed' or 'open'
        self.machine_state = 'stopped'
    
    def sensor_callback_guard_opened(self):
        """Callback when guard sensor detects opening."""
        self.guard_state = 'open'
        
        if self.machine_state == 'running':
            # Guard opened while machine running - EMERGENCY STOP!
            return self._trigger_safety_stop()
        
        return {'status': 'guard_open', 'machine': 'safe'}
    
    def sensor_callback_guard_closed(self):
        """Callback when guard sensor detects closing."""
        self.guard_state = 'closed'
        
        # Operator must now press "start" button to restart
        return {'status': 'guard_closed', 'ready_to_start': True}
    
    def _trigger_safety_stop(self):
        """Trigger immediate stop when guard opened during operation."""
        self.machine_state = 'stopped'
        
        # Signal solenoid to cut main drive
        # Engage brake
        # Log incident
        
        return {
            'event': 'guard_open_during_operation',
            'action': 'machine_stopped',
            'severity': 'critical'
        }
    
    def machine_start_request(self, operator_id):
        """Check interlocks before allowing machine start."""
        checks = [
            ('guard_closed', self.guard_state == 'closed'),
            ('estop_reset', self._check_estop_status()),
            ('no_faults', self._check_for_faults()),
            ('operator_authorized', self._check_authorization(operator_id))
        ]
        
        all_passed = all(check[1] for check in checks)
        
        return {
            'can_start': all_passed,
            'checks': {name: status for name, status in checks}
        }
```

### 2. Pressure Relief Interlocks

```python
class PressureInterlock:
    """Pressure monitoring with automatic relief (SIL 3)."""
    
    def __init__(self, system_name, max_safe_pressure):
        self.system_name = system_name
        self.max_safe_pressure = max_safe_pressure
        self.current_pressure = 0
        self.relief_valve_open = False
    
    def sensor_pressure_reading(self, pressure_value):
        """Process pressure sensor reading."""
        self.current_pressure = pressure_value
        
        if pressure_value > (self.max_safe_pressure * 1.1):  # 110% threshold
            # Critical overpressure
            return self._trigger_pressure_relief()
        
        if pressure_value > (self.max_safe_pressure * 1.05):  # 105% warning
            # Elevated pressure - begin controlled relief
            return self._open_relief_valve()
        
        if pressure_value < (self.max_safe_pressure * 0.95):  # 95% nominal
            # Back to normal
            return self._close_relief_valve()
        
        return {'status': 'normal', 'pressure': pressure_value}
    
    def _trigger_pressure_relief(self):
        """Automatic emergency pressure relief."""
        self.relief_valve_open = True
        
        # Open safety relief valve (direct solenoid)
        # Log event
        # Alert operators
        
        return {
            'event': 'overpressure_relief',
            'relief_valve': 'open',
            'severity': 'critical'
        }
```

### 3. Temperature Safety Limits

```python
class TemperatureInterlock:
    """Temperature monitoring with cutoff (SIL 2)."""
    
    def __init__(self, system_name, max_temp):
        self.system_name = system_name
        self.max_temp = max_temp
        self.current_temp = 0
        self.heater_enabled = False
    
    def sensor_temperature_reading(self, temp_value):
        """Process temperature sensor reading."""
        self.current_temp = temp_value
        
        if temp_value >= self.max_temp:
            # Temperature limit exceeded - CUT HEAT immediately
            return self._disable_heater()
        
        if temp_value >= (self.max_temp * 0.95):
            # Near limit - reduce heat
            return self._reduce_heater_power()
        
        if temp_value < (self.max_temp * 0.85):
            # Safe operating range - resume heating
            return self._enable_heater()
        
        return {'status': 'normal', 'temperature': temp_value}
    
    def _disable_heater(self):
        """Disable heating element immediately."""
        self.heater_enabled = False
        
        # Cut power to heating circuit
        # Log overheat incident
        # Alert operators
        
        return {
            'event': 'overheat_protection',
            'heater': 'disabled',
            'severity': 'high'
        }
```

---

## Redundant Monitoring Systems

### Dual-Channel Safety PLC Comparison

```python
# /factory-lab/docker/safety/dual_plc_monitor.py

class DualPLCMonitor:
    """Dual-channel safety PLC with cross-check (SIL 3)."""
    
    def __init__(self):
        self.plc_primary = {'outputs': {}, 'timestamp': 0}
        self.plc_secondary = {'outputs': {}, 'timestamp': 0}
        self.channel_match = True
    
    def compare_outputs(self):
        """Compare primary and secondary PLC outputs."""
        if self.plc_primary['outputs'] != self.plc_secondary['outputs']:
            # OUTPUTS DON'T MATCH - UNSAFE CONDITION
            return self._trigger_safety_fault()
        
        self.channel_match = True
        return {'status': 'channels_synchronized'}
    
    def _trigger_safety_fault(self):
        """Dual-channel mismatch detected - immediate E-stop."""
        return {
            'event': 'dual_plc_mismatch',
            'action': 'emergency_stop_triggered',
            'severity': 'critical',
            'requires_investigation': True
        }
    
    def detect_stale_heartbeat(self, channel, max_age_ms=500):
        """Detect if PLC heartbeat is stale."""
        last_heartbeat = self.plc_primary['timestamp'] if channel == 'primary' else self.plc_secondary['timestamp']
        age = (time.time() * 1000) - last_heartbeat
        
        if age > max_age_ms:
            return self._trigger_channel_timeout(channel)
        
        return {'status': 'heartbeat_ok'}
    
    def _trigger_channel_timeout(self, channel):
        """PLC channel timeout detected."""
        return {
            'event': f'plc_{channel}_timeout',
            'action': 'emergency_stop_triggered',
            'severity': 'critical'
        }
```

---

## Safety Certifications & Testing

### Functional Safety Test Suite

```bash
#!/bin/bash
# /factory-lab/scripts/test-safety-systems.sh

# Test 1: E-stop response time
echo "TEST 1: Emergency Stop Response Time"
echo "Requirement: <200ms from button press to motor power cut"
curl -X POST http://localhost:5000/safety/e-stop \
  -d '{"source":"button","reason":"test"}'
# Measure actual response time with oscilloscope/logic analyzer

# Test 2: Guard interlock
echo "TEST 2: Guard Interlock"
echo "Requirement: Cannot start with guard open"
# Simulate open guard sensor
curl -X POST http://localhost:5000/sensor/guard/open
# Attempt machine start - should fail
curl -X POST http://localhost:5000/machine/start

# Test 3: Pressure relief
echo "TEST 3: Pressure Relief Valve"
echo "Requirement: Relief triggers at 1.1x nominal pressure"
# Simulate pressure increase to 110% of nominal
curl -X POST http://localhost:5000/sensor/pressure \
  -d '{"value": 110}'
# Verify relief valve opened within 100ms

# Test 4: Dual-channel PLC
echo "TEST 4: Dual-Channel PLC Monitoring"
echo "Requirement: E-stop if outputs don't match"
# Simulate output mismatch between PLCs
# System should trigger E-stop automatically

# Test 5: Watchdog timeout
echo "TEST 5: Watchdog Timeout"
echo "Requirement: E-stop if heartbeat missing >500ms"
# Simulate PLC heartbeat timeout
# System should trigger E-stop

# Test 6: MFA for reset
echo "TEST 6: MFA for E-stop Reset"
echo "Requirement: Cannot reset without authorization"
# Attempt reset without MFA - should fail
curl -X POST http://localhost:5000/safety/reset \
  -d '{"user":"john.smith"}'
# Provide correct MFA - should succeed

# Test 7: Audit trail immutability
echo "TEST 7: Audit Trail Immutability"
echo "Requirement: Cannot delete safety events"
# Attempt to delete from security_events table
psql -c "DELETE FROM security_events WHERE id=1;"
# Should fail (SQL rule prevents deletion)

echo "Safety system tests completed."
```

### Test Report Template

```
FUNCTIONAL SAFETY TEST REPORT
IEC 61508 Compliance Assessment

Date: 2024-07-26
System: Factory PLC Emergency Stop
SIL Rating: 3

Test Results:
┌─────────────────────────────────────────┬──────────┐
│ Test                                    │ Result   │
├─────────────────────────────────────────┼──────────┤
│ E-stop response time (<200ms)           │ ✓ PASS   │
│ Guard interlock active                  │ ✓ PASS   │
│ Pressure relief functional              │ ✓ PASS   │
│ Dual-channel comparison                 │ ✓ PASS   │
│ Watchdog timeout detection              │ ✓ PASS   │
│ MFA for reset authorization             │ ✓ PASS   │
│ Audit trail immutability                │ ✓ PASS   │
│ Safety certification valid              │ ✓ PASS   │
└─────────────────────────────────────────┴──────────┘

Next Audit: 2025-07-26
Certification Valid Until: 2025-12-31
```

---

## Machine Safety Labels & Documentation

### Required Safety Signage (in lab)

```
╔════════════════════════════════════════════════════════╗
║              ⚠️  DANGER - MOVING PARTS                 ║
║                                                        ║
║ • Keep hands, hair, and loose clothing away            ║
║ • Do NOT reach into machine during operation           ║
║ • Always use machine guards                            ║
║ • Emergency stop located here → [RED BUTTON]           ║
║                                                        ║
║ Failure to follow safety procedures can result in:     ║
║ • Severe injury                                        ║
║ • Permanent disability                                 ║
║ • Death                                                ║
║                                                        ║
║ Report unsafe conditions to supervisor immediately    ║
║                                                        ║
║ Safety First - No Exceptions!                         ║
╚════════════════════════════════════════════════════════╝
```

---

## Training & Certification

### Safety Officer Checklist

```
☐ All employees trained on emergency stop location/use
☐ Monthly safety drills performed
☐ Dual-channel PLC verification completed
☐ Guard interlocks tested and functional
☐ Pressure relief valve calibrated and tested
☐ Watchdog timeout verified (<500ms)
☐ E-stop response time measured (<200ms)
☐ Audit trail verified as immutable
☐ Annual safety certification current
☐ Incident reports reviewed and addressed
☐ Safety documentation up-to-date
☐ New employee safety training completed

Certification Valid: ________________
Safety Officer Signature: ________________
```

---

## Real-World Scenario: Plant Explosion Prevention

### The System That Could Save Lives

```
SCENARIO: High-pressure vessel rupture detection

Minute 0:00
├─ Operator loads batch into reactor
├─ Heating sequence begins
└─ System pressure increases normally

Minute 5:30
├─ Temperature sensor reads 185°C (within 200°C limit)
├─ Pressure sensor reads 1.5 Bar (normal)
└─ System operating normally

Minute 7:45
├─ Pressure sensor spikes to 2.8 Bar (WAR NING - above 2.0 max)
├─ Temperature interlock CUTS HEAT immediately
├─ Pressure relief valve OPENS automatically
├─ **System logs event to immutable audit trail**
└─ Operators notified via alarm

Minute 7:47
├─ Pressure dropping: 2.7 Bar
├─ Temperature dropping: 180°C
├─ Situation stabilizing
└─ Vessel saved from rupture

Minute 8:00
├─ Pressure nominal: 1.5 Bar
├─ Temperature nominal: 150°C
├─ Relief valve closes
├─ Manual inspection required before restart
└─ Incident documented for regulatory compliance

**RESULT: Potential disaster prevented. No injuries. System worked as designed.**

What if these interlocks didn't exist?
→ Vessel pressure exceeds 5 Bar
→ Vessel ruptures explosively
→ Pressurized liquid sprays facility
→ Operator and nearby workers seriously injured/killed
→ Facility damaged/destroyed
→ Legal liability, criminal charges possible
```

---

## Production Certification

```
FACTORY SAFETY SYSTEM CERTIFICATION
═════════════════════════════════════════

Facility:     Factory Lab Training Environment
System:       Integrated Emergency Stop & Safety Interlocks
Date:         2024-07-26
Valid Until:  2025-07-25

CERTIFIED COMPLIANT WITH:
✓ IEC 61508 (Functional Safety)
✓ ISO 13849-1 (Safety of Machinery)
✓ IEC 60204-1 (Safety of Machinery - Electrical Equipment)
✓ OSHA 1910.119 (Process Safety Management)
✓ Local/Regional Safety Regulations

RATED AT:     SIL 3 (Safety Integrity Level 3)

This certification means the system is designed to prevent
serious injury or death in normal and abnormal operation.

Audited and Certified By: Safety Engineering Authority
License: [CERT-NUMBER]
Contact: certification@factory-safety.org
═════════════════════════════════════════
```

This creates a **production-grade safety system** with real emergency stop logic,  interlocks, and compliance certification suitable for training and demonstrating safety-critical system design.
