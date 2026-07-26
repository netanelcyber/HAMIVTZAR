#!/usr/bin/env python3
"""Generate 50 factory employees with realistic data for AD setup."""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict

DEPARTMENTS = [
    "Production",
    "Maintenance",
    "Quality Assurance",
    "Logistics",
    "Operations",
    "Engineering",
    "IT Support",
    "Management"
]

ROLES = {
    "Production": ["Operator", "Line Lead", "Team Lead", "Production Manager"],
    "Maintenance": ["Technician", "Electrician", "Mechanical Tech", "Maintenance Lead"],
    "Quality Assurance": ["Inspector", "QA Analyst", "Quality Engineer", "QA Manager"],
    "Logistics": ["Warehouse Worker", "Forklift Operator", "Shipping Clerk", "Logistics Manager"],
    "Operations": ["Shift Supervisor", "Planning Analyst", "Operations Coordinator", "Operations Manager"],
    "Engineering": ["Process Engineer", "Manufacturing Engineer", "Design Engineer", "Engineering Manager"],
    "IT Support": ["IT Technician", "IT Support Specialist", "System Administrator", "IT Manager"],
    "Management": ["Plant Manager", "Director", "Supervisor", "Coordinator"]
}

NAMES = {
    "first": [
        "John", "Sarah", "Michael", "Jennifer", "David", "Emily", "Robert", "Jessica",
        "James", "Lisa", "William", "Mary", "Richard", "Patricia", "Joseph", "Linda",
        "Thomas", "Barbara", "Christopher", "Elizabeth", "Daniel", "Susan", "Matthew", "Karen",
        "Mark", "Nancy", "Donald", "Lisa", "Steven", "Betty", "Paul", "Margaret",
        "Andrew", "Sandra", "Joshua", "Ashley", "Kenneth", "Kimberly", "Kevin", "Donna",
        "Brian", "Carol", "George", "Michelle", "Edward", "Dorothy", "Ronald", "Melissa",
        "Anthony", "Deborah", "Frank", "Stephanie"
    ],
    "last": [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
        "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker"
    ]
}

def generate_username(first: str, last: str, number: int) -> str:
    """Generate username from name."""
    base = f"{first.lower()}.{last.lower()}"
    if number > 1:
        base += str(number)
    return base

def generate_employees(count: int = 50) -> List[Dict]:
    """Generate employee data."""
    employees = []
    used_names = set()

    for i in range(count):
        # Generate unique name
        while True:
            first = random.choice(NAMES["first"])
            last = random.choice(NAMES["last"])
            name = f"{first} {last}"
            if name not in used_names:
                used_names.add(name)
                break

        # Assign department and role
        dept = random.choice(DEPARTMENTS)
        role = random.choice(ROLES[dept])

        # Generate username
        username = generate_username(first, last, 1)
        counter = 2
        while any(e["username"] == username for e in employees):
            username = generate_username(first, last, counter)
            counter += 1

        # Generate email
        email = f"{username}@factory.local"

        # Generate employee ID
        emp_id = f"EMP{1000 + i}"

        # Random start date (within last 5 years)
        days_ago = random.randint(1, 1825)
        start_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

        # Generate password (will be hashed in AD setup)
        password = f"FactoryP@ss{random.randint(100, 999)}"

        # Determine office/location
        locations = ["Building A", "Building B", "Warehouse", "Admin Block"]
        location = random.choice(locations)

        employees.append({
            "id": emp_id,
            "first_name": first,
            "last_name": last,
            "full_name": name,
            "username": username,
            "email": email,
            "department": dept,
            "role": role,
            "password": password,
            "start_date": start_date,
            "location": location,
            "phone": f"+1-555-{random.randint(100, 999):03d}-{random.randint(1000, 9999):04d}",
            "manager": random.choice([True, False]) if dept in ["Management", "Engineering"] else False,
            "contractor": random.choice([True, False]) if random.random() < 0.1 else False
        })

    return employees

def generate_ldif(employees: List[Dict]) -> str:
    """Generate LDIF format for AD import."""
    ldif = """dn: dc=factory,dc=local
objectClass: top
objectClass: dcObject
objectClass: organization
o: Factory Inc.
dc: factory

dn: cn=Users,dc=factory,dc=local
objectClass: top
objectClass: container
cn: Users

"""

    # Organization Units
    ous = {}
    for emp in employees:
        dept = emp["department"].replace(" ", "")
        if dept not in ous:
            ous[dept] = True

    for ou in ous:
        ldif += f"""dn: ou={ou},dc=factory,dc=local
objectClass: top
objectClass: organizationalUnit
ou: {ou}

"""

    # Users
    for emp in employees:
        dept = emp["department"].replace(" ", "")
        ldif += f"""dn: cn={emp['full_name']},ou={dept},dc=factory,dc=local
objectClass: top
objectClass: person
objectClass: organizationalPerson
objectClass: user
cn: {emp['full_name']}
sn: {emp['last_name']}
givenName: {emp['first_name']}
displayName: {emp['full_name']}
mail: {emp['email']}
userPrincipalName: {emp['username']}@factory.local
sAMAccountName: {emp['username']}
employeeID: {emp['id']}
title: {emp['role']}
department: {emp['department']}
physicalDeliveryOfficeName: {emp['location']}
telephoneNumber: {emp['phone']}
userAccountControl: 512
accountExpires: 9223372036854775807

"""

    return ldif

def generate_samba_script(employees: List[Dict]) -> str:
    """Generate Samba setup script."""
    script = "#!/bin/bash\n"
    script += "# Auto-generated Samba user setup script\n\n"

    script += """set -e

# Enable user accounts
samba-tool user enable Administrator 2>/dev/null || true

"""

    for emp in employees:
        script += f"""# Create user: {emp['full_name']}
samba-tool user create {emp['username']} '{emp['password']}' \\
  --mail-address='{emp['email']}' \\
  --given-name='{emp['first_name']}' \\
  --surname='{emp['last_name']}' \\
  --job-title='{emp['role']}' \\
  --department='{emp['department']}' \\
  --office='{emp['location']}' \\
  2>/dev/null || true

"""

    script += "\n# Set group memberships\n"

    # Add department-based group memberships
    depts_handled = set()
    for emp in employees:
        dept = emp["department"]
        if dept not in depts_handled:
            script += f"samba-tool group add {dept.replace(' ', '_')} 2>/dev/null || true\n"
            depts_handled.add(dept)

    script += "\n"

    # Add users to groups
    for emp in employees:
        group = emp["department"].replace(" ", "_")
        script += f"samba-tool group addmembers {group} {emp['username']} 2>/dev/null || true\n"

    return script

if __name__ == "__main__":
    employees = generate_employees(50)

    # Save as JSON
    with open("factory_employees.json", "w") as f:
        json.dump(employees, f, indent=2)

    # Generate LDIF
    ldif = generate_ldif(employees)
    with open("factory_users.ldif", "w") as f:
        f.write(ldif)

    # Generate Samba setup script
    samba_script = generate_samba_script(employees)
    with open("setup-samba-users.sh", "w") as f:
        f.write(samba_script)

    print(f"✓ Generated {len(employees)} employees")
    print("  - factory_employees.json")
    print("  - factory_users.ldif")
    print("  - setup-samba-users.sh")
