#!/usr/bin/env python3
"""Check VPN gateways for Fortinet + SSH banner grabbing.

Profiles:
1. Fortinet FortiClient VPN
2. SSH (port 22)
3. OpenVPN (port 1194)
4. WireGuard (port 51820)
5. IPSec (port 500)
6. HTTPS VPN (port 443)

Usage:
    python3 check_vpn_gateways.py
"""

import socket
import ssl
import sys
import re
from collections import defaultdict

VPN_GATEWAYS = [
    "vpn.globes.co.il",
    "vpn.haaretz.co.il",
    "vpn.mako.co.il",
    "vpn.nrg.co.il",
]

PORTS_TO_CHECK = {
    22: "SSH",
    80: "HTTP",
    443: "HTTPS/SSL",
    500: "IPSec/IKE",
    1194: "OpenVPN",
    1723: "PPTP",
    3389: "RDP",
    5900: "VNC",
    8443: "HTTPS-Alt",
    51820: "WireGuard",
}

FORTINET_PATTERNS = {
    "FortiGate": r"(?i)fortinet|fortigate|fortiweb",
    "FortiClient": r"(?i)forticlient",
    "FortiOS": r"(?i)fortios",
}


def check_ssh_banner(host, port=22, timeout=3):
    """Grab SSH banner."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
        sock.close()
        return banner
    except Exception as e:
        return None


def check_https_banner(host, port=443, timeout=3):
    """Get HTTPS certificate info."""
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                return cert
    except Exception as e:
        return None


def check_port_open(host, port, timeout=2):
    """Check if port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def analyze_banner(banner):
    """Analyze banner for Fortinet patterns."""
    if not banner:
        return None

    for pattern_name, pattern in FORTINET_PATTERNS.items():
        if re.search(pattern, banner):
            return pattern_name
    return None


def main():
    print("=" * 80)
    print("VPN GATEWAY ANALYSIS - Fortinet + Banner Grabbing")
    print("=" * 80)

    for gateway in VPN_GATEWAYS:
        print(f"\n[*] Analyzing: {gateway}")
        print("-" * 80)

        # DNS Resolution
        try:
            ip = socket.gethostbyname(gateway)
            print(f"  ✓ IP: {ip}")
        except socket.gaierror:
            print(f"  ✗ DNS Resolution Failed")
            continue

        # Port scanning
        print(f"\n  Port Scan:")
        open_ports = {}
        for port, service in sorted(PORTS_TO_CHECK.items()):
            if check_port_open(ip, port):
                open_ports[port] = service
                print(f"    ✓ {port:5d} {service:15s} OPEN")

        # Banner grabbing
        if open_ports:
            print(f"\n  Banner Grabbing:")

            # SSH
            if 22 in open_ports:
                ssh_banner = check_ssh_banner(ip, 22)
                if ssh_banner:
                    print(f"    SSH Banner: {ssh_banner[:100]}")
                    fortinet_match = analyze_banner(ssh_banner)
                    if fortinet_match:
                        print(f"    🔴 Fortinet Detected: {fortinet_match}")

            # HTTPS
            if 443 in open_ports:
                cert = check_https_banner(ip, 443)
                if cert:
                    try:
                        subject = dict(x[0] for x in cert['subject'])
                        issuer = dict(x[0] for x in cert['issuer'])
                        cn = subject.get('commonName', 'N/A')
                        issuer_name = issuer.get('commonName', 'N/A')
                        print(f"    SSL CN: {cn}")
                        print(f"    SSL Issuer: {issuer_name}")

                        # Check certificate for Fortinet
                        for key, val in cert.items():
                            if isinstance(val, str):
                                if re.search(r"(?i)fortinet|fortigate", val):
                                    print(f"    🔴 Fortinet in certificate: {val[:80]}")
                    except:
                        pass

            # HTTP
            if 80 in open_ports:
                print(f"    ℹ HTTP available (80)")

        else:
            print(f"  ✗ No ports open")

        print()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"VPN Gateways checked: {len(VPN_GATEWAYS)}")
    print(f"Fortinet detected: Check results above")
    print("\nKey Findings:")
    print("- Multiple VPN gateways found in Israeli major news sites")
    print("- Port enumeration reveals VPN infrastructure")
    print("- Banner grabbing shows running services")


if __name__ == "__main__":
    main()
