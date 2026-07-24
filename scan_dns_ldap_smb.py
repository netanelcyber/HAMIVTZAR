#!/usr/bin/env python3
"""Deep infrastructure scan: DNS + LDAP + SMB for 657 Israeli domains.

Discovers:
- Active Directory / LDAP servers
- SMB/CIFS shares
- SRV records (Kerberos, LDAP, etc)
- Domain controllers

Usage:
    python3 scan_dns_ldap_smb.py --file israeli_websites_coil_only.txt
"""

import socket
import sys
import argparse
import concurrent.futures
from collections import defaultdict

try:
    import dns.resolver
    import dns.rdatatype
except ImportError:
    print("ERROR: dnspython required: pip install dnspython")
    sys.exit(1)

try:
    from smb.SMBConnection import SMBConnection
    from smb.smb_structs import FILE_OPEN_READONLY
except ImportError:
    SMBConnection = None

# LDAP ports
LDAP_PORT = 389
LDAPS_PORT = 636

# SMB ports
SMB_PORTS = [139, 445]

# SRV records to check
SRV_RECORDS = [
    "_ldap._tcp",
    "_ldap._udp",
    "_kerberos._tcp",
    "_kerberos._udp",
    "_kpasswd._tcp",
    "_kpasswd._udp",
    "_sip._tcp",
    "_sip._udp",
    "_xmpp._tcp",
    "_xmpp._udp",
    "_domain._tcp",
    "_domain._udp",
    "_gc._tcp",
    "_gc._udp",
    "_ntp._udp",
    "_http._tcp",
    "_https._tcp",
    "_smtp._tcp",
    "_submission._tcp",
    "_imap._tcp",
    "_imaps._tcp",
    "_pop3._tcp",
    "_pop3s._tcp",
]

# AD DNS records
AD_DNS_RECORDS = [
    "_msdcs",
    "_sites",
    "_tcp",
]


def dns_lookup(domain, record_type="A"):
    """DNS lookup."""
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 2
        resolver.lifetime = 3

        answers = resolver.resolve(domain, record_type)
        return [str(rdata) for rdata in answers]
    except Exception as e:
        return None


def check_srv_records(domain):
    """Check for SRV records."""
    srv_found = []

    for srv in SRV_RECORDS:
        full_domain = f"{srv}.{domain}"
        results = dns_lookup(full_domain, "SRV")
        if results:
            srv_found.append({"record": srv, "results": results})

    return srv_found if srv_found else None


def check_ad_records(domain):
    """Check for Active Directory records."""
    ad_found = []

    for record in AD_DNS_RECORDS:
        full_domain = f"{record}.{domain}"
        results = dns_lookup(full_domain, "A")
        if results:
            ad_found.append({"record": record, "ips": results})

    return ad_found if ad_found else None


def check_ldap_open(ip, port=389):
    """Check if LDAP port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False


def check_smb_open(ip, ports=[139, 445]):
    """Check if SMB ports are open."""
    open_ports = []
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                open_ports.append(port)
        except:
            pass
    return open_ports if open_ports else None


def scan_domain(domain):
    """Scan single domain for LDAP/SMB infrastructure."""
    result = {
        "domain": domain,
        "dns_live": False,
        "ip": None,
        "srv_records": None,
        "ad_records": None,
        "ldap_open": False,
        "smb_open": None,
    }

    # DNS resolution
    try:
        ip = socket.gethostbyname(domain)
        result["dns_live"] = True
        result["ip"] = ip
    except socket.gaierror:
        return result

    # Check SRV records
    srv = check_srv_records(domain)
    if srv:
        result["srv_records"] = srv

    # Check AD records
    ad = check_ad_records(domain)
    if ad:
        result["ad_records"] = ad

    # Check LDAP
    if check_ldap_open(result["ip"]):
        result["ldap_open"] = True

    # Check SMB
    smb = check_smb_open(result["ip"])
    if smb:
        result["smb_open"] = smb

    return result


def main():
    parser = argparse.ArgumentParser(description="DNS + LDAP + SMB infrastructure scanner")
    parser.add_argument("--file", required=True, help="File with domains")
    parser.add_argument("--workers", type=int, default=25, help="Concurrent workers")
    parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    # Load domains
    try:
        with open(args.file) as f:
            domains = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Scanning {len(domains)} domains for DNS/LDAP/SMB infrastructure...", file=sys.stderr)

    results = []
    infrastructure_found = defaultdict(list)

    # Scan all domains
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for i, result in enumerate(executor.map(scan_domain, domains), 1):
            results.append(result)

            # Track infrastructure
            if result["dns_live"]:
                if result["srv_records"]:
                    infrastructure_found["srv_records"].append(result["domain"])
                if result["ad_records"]:
                    infrastructure_found["ad_records"].append(result["domain"])
                if result["ldap_open"]:
                    infrastructure_found["ldap_open"].append(result["domain"])
                if result["smb_open"]:
                    infrastructure_found["smb_open"].append(result["domain"])

            if i % 50 == 0:
                print(f"[*] [{i}/{len(domains)}] scanned...", file=sys.stderr)

    # Summary
    print("\n" + "=" * 80, file=sys.stderr)
    print("INFRASTRUCTURE DISCOVERY RESULTS", file=sys.stderr)
    print("=" * 80, file=sys.stderr)

    live_count = sum(1 for r in results if r["dns_live"])
    print(f"Total domains: {len(domains)}", file=sys.stderr)
    print(f"DNS live: {live_count}", file=sys.stderr)
    print(f"\nInfrastructure Found:", file=sys.stderr)
    print(f"  SRV Records (AD/LDAP): {len(infrastructure_found['srv_records'])}", file=sys.stderr)
    print(f"  AD DNS Records: {len(infrastructure_found['ad_records'])}", file=sys.stderr)
    print(f"  LDAP Open (389): {len(infrastructure_found['ldap_open'])}", file=sys.stderr)
    print(f"  SMB Open (139/445): {len(infrastructure_found['smb_open'])}", file=sys.stderr)

    # Print detailed results
    if args.json:
        import json
        print(json.dumps(results, indent=2))
    else:
        print("\n" + "=" * 80, file=sys.stderr)
        print("DETAILED FINDINGS", file=sys.stderr)
        print("=" * 80, file=sys.stderr)

        if infrastructure_found["srv_records"]:
            print("\n🔴 Domains with SRV Records (Active Directory/LDAP):", file=sys.stderr)
            for domain in sorted(infrastructure_found["srv_records"]):
                for r in results:
                    if r["domain"] == domain:
                        print(f"\n  {domain} ({r['ip']})", file=sys.stderr)
                        for srv in r["srv_records"]:
                            print(f"    - {srv['record']}: {srv['results'][0]}", file=sys.stderr)

        if infrastructure_found["ldap_open"]:
            print("\n🔴 Domains with LDAP Port Open (389):", file=sys.stderr)
            for domain in sorted(infrastructure_found["ldap_open"]):
                for r in results:
                    if r["domain"] == domain:
                        print(f"  {domain} ({r['ip']})", file=sys.stderr)

        if infrastructure_found["smb_open"]:
            print("\n🔴 Domains with SMB Ports Open (139/445):", file=sys.stderr)
            for domain in sorted(infrastructure_found["smb_open"]):
                for r in results:
                    if r["domain"] == domain:
                        ports = ",".join(map(str, r["smb_open"]))
                        print(f"  {domain} ({r['ip']}) ports: {ports}", file=sys.stderr)

        # Export CSV format
        print("\n" + "=" * 80, file=sys.stderr)
        print("CSV EXPORT:", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print("domain,ip,dns_live,srv_records,ad_records,ldap_open,smb_open")
        for r in results:
            if r["dns_live"]:
                srv = "yes" if r["srv_records"] else "no"
                ad = "yes" if r["ad_records"] else "no"
                ldap = "yes" if r["ldap_open"] else "no"
                smb = "yes" if r["smb_open"] else "no"
                print(f"{r['domain']},{r['ip']},{r['dns_live']},{srv},{ad},{ldap},{smb}")


if __name__ == "__main__":
    main()
