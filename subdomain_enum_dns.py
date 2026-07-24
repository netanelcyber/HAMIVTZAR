#!/usr/bin/env python3
"""DNS-based subdomain enumeration for Israeli websites.

Performs DNS lookups for common subdomains to discover hidden hosts.

Usage:
    python3 subdomain_enum_dns.py --domain ynet.co.il
    python3 subdomain_enum_dns.py --file domains.txt --workers 20
"""

import sys
import socket
import argparse
import concurrent.futures
from collections import defaultdict

# Common subdomains to check
COMMON_SUBDOMAINS = [
    "www",
    "mail",
    "smtp",
    "pop",
    "imap",
    "ftp",
    "sftp",
    "ssh",
    "telnet",
    "dns",
    "ns1",
    "ns2",
    "ns3",
    "admin",
    "administrator",
    "root",
    "test",
    "staging",
    "dev",
    "development",
    "prod",
    "production",
    "api",
    "api-test",
    "api-dev",
    "api-staging",
    "app",
    "applications",
    "blog",
    "cms",
    "content",
    "cp",
    "cpanel",
    "webhook",
    "webhook-test",
    "cdn",
    "cdn-test",
    "cache",
    "proxy",
    "vpn",
    "vpn-test",
    "waf",
    "firewall",
    "lb",
    "load",
    "load-balancer",
    "backup",
    "bak",
    "backups",
    "database",
    "db",
    "db-test",
    "db-dev",
    "redis",
    "cache-server",
    "elasticsearch",
    "kibana",
    "grafana",
    "prometheus",
    "metrics",
    "monitoring",
    "logs",
    "logging",
    "syslog",
    "siem",
    "security",
    "ids",
    "ips",
    "dga",
    "gateway",
    "vpn-gateway",
    "bastion",
    "jump",
    "jumphost",
    "edge",
    "edge-server",
    "mirror",
    "mirrors",
    "download",
    "downloads",
    "upload",
    "uploads",
    "files",
    "share",
    "sharing",
    "storage",
    "s3",
    "cloud",
    "azure",
    "aws",
    "gcp",
    "docker",
    "kubernetes",
    "k8s",
    "registry",
    "repo",
    "repository",
    "git",
    "github",
    "gitlab",
    "bitbucket",
    "jenkins",
    "ci",
    "cd",
    "ci-cd",
    "build",
    "deploy",
    "deployment",
    "test",
    "testing",
    "qa",
    "quality-assurance",
    "stage",
    "staging-api",
    "dev-api",
    "test-api",
    "v1",
    "v2",
    "v3",
    "api-v1",
    "api-v2",
    "api-v3",
    "rest",
    "graphql",
    "soap",
    "websocket",
    "ws",
    "wss",
    "socket",
    "mqtt",
    "amqp",
    "kafka",
    "queue",
    "mq",
    "message",
    "messaging",
    "mail-server",
    "exchange",
    "lync",
    "sharepoint",
    "teams",
    "slack",
    "discord",
    "telegram",
    "chat",
    "messaging-service",
    "notification",
    "notifications",
    "push",
    "push-notifications",
    "sms",
    "twilio",
    "sendgrid",
    "mailgun",
    "ses",
    "email",
    "auth",
    "oauth",
    "saml",
    "ldap",
    "sso",
    "single-sign-on",
    "2fa",
    "mfa",
    "multi-factor",
    "otp",
    "totp",
    "session",
    "sessions",
    "cookie",
    "cookies",
    "token",
    "tokens",
    "jwt",
    "bearer",
    "passport",
    "auth0",
    "cognito",
    "keycloak",
    "vault",
    "secrets",
    "secret-manager",
    "certificate",
    "certificates",
    "ca",
    "pki",
    "acme",
    "letsencrypt",
    "ssl",
    "tls",
    "https",
    "http2",
    "http3",
    "quic",
    "spdy",
    "compression",
    "gzip",
    "brotli",
    "performance",
    "perf",
    "analytics",
    "reporting",
    "reports",
    "dashboard",
    "dashboards",
    "bi",
    "business-intelligence",
    "data",
    "data-warehouse",
    "etl",
    "ml",
    "machine-learning",
    "ai",
    "artificial-intelligence",
    "nlp",
    "cv",
    "computer-vision",
    "deep-learning",
    "torch",
    "tensorflow",
    "pytorch",
    "model",
    "models",
    "inference",
    "training",
    "experiment",
    "experiments",
    "notebook",
    "notebooks",
    "jupyter",
    "lab",
    "research",
    "science",
    "innovation",
    "incubator",
    "startup",
    "accelerator",
]


def resolve_subdomain(subdomain, domain):
    """Try to resolve a subdomain."""
    full_domain = f"{subdomain}.{domain}"
    try:
        ip = socket.gethostbyname(full_domain)
        return {"subdomain": subdomain, "domain": domain, "full": full_domain, "ip": ip, "found": True}
    except (socket.gaierror, socket.timeout):
        return {"subdomain": subdomain, "domain": domain, "full": full_domain, "found": False}


def enumerate_domain(domain, workers=10):
    """Enumerate subdomains for a single domain."""
    found = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(resolve_subdomain, sub, domain) for sub in COMMON_SUBDOMAINS]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result["found"]:
                found.append(result)

    return found


def main():
    parser = argparse.ArgumentParser(description="DNS-based subdomain enumeration")
    parser.add_argument("--domain", help="Single domain to enumerate")
    parser.add_argument("--file", help="File with domains (one per line)")
    parser.add_argument("--workers", type=int, default=20, help="Concurrent DNS workers")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    domains = []
    if args.domain:
        domains = [args.domain]
    elif args.file:
        try:
            with open(args.file) as f:
                domains = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"ERROR: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    all_results = defaultdict(list)

    for domain in domains:
        print(f"[*] Enumerating subdomains for {domain}...", file=sys.stderr)
        found = enumerate_domain(domain.strip(), workers=args.workers)
        all_results[domain] = found
        print(f"[*] Found {len(found)} subdomains for {domain}", file=sys.stderr)

    # Print results
    if args.json:
        import json
        print(json.dumps(dict(all_results), indent=2))
    else:
        total_found = 0
        for domain in domains:
            found = all_results[domain]
            if found:
                print(f"\n{'=' * 80}")
                print(f"Subdomains for: {domain}")
                print(f"{'=' * 80}")
                for result in sorted(found, key=lambda x: x["subdomain"]):
                    print(f"  {result['full']:40s} {result['ip']}")
                    total_found += 1

        print(f"\n{'=' * 80}")
        print(f"Total subdomains found: {total_found}")
        print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
