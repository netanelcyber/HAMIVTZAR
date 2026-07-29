#!/usr/bin/env python3
"""
Comprehensive Fuzzing Toolkit
Mutation-based fuzzing for vulnerability discovery
"""

import socket
import ssl
import random
import string
import struct
import sys
from datetime import datetime
import json

class FuzzingToolkit:
    def __init__(self, target_host, target_port, protocol="ssl"):
        self.target_host = target_host
        self.target_port = target_port
        self.protocol = protocol
        self.crashes = []
        self.test_cases = 0
        self.crash_count = 0

    def connect(self):
        """Establish connection to target"""
        try:
            if self.protocol == "ssl":
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((self.target_host, self.target_port))
                return context.wrap_socket(sock, server_hostname=self.target_host)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((self.target_host, self.target_port))
                return sock
        except Exception as e:
            return None

    # MUTATION STRATEGIES

    def bit_flip_mutation(self, data):
        """Flip random bits in data"""
        data_array = bytearray(data)
        for _ in range(random.randint(1, 5)):
            pos = random.randint(0, len(data_array) - 1)
            bit_pos = random.randint(0, 7)
            data_array[pos] ^= (1 << bit_pos)
        return bytes(data_array)

    def byte_flip_mutation(self, data):
        """Flip random bytes"""
        data_array = bytearray(data)
        for _ in range(random.randint(1, 5)):
            pos = random.randint(0, len(data_array) - 1)
            data_array[pos] = random.randint(0, 255)
        return bytes(data_array)

    def insert_mutation(self, data):
        """Insert random bytes"""
        data_array = bytearray(data)
        for _ in range(random.randint(1, 3)):
            pos = random.randint(0, len(data_array))
            data_array.insert(pos, random.randint(0, 255))
        return bytes(data_array)

    def delete_mutation(self, data):
        """Delete random bytes"""
        data_array = bytearray(data)
        for _ in range(random.randint(1, 3)):
            if len(data_array) > 1:
                pos = random.randint(0, len(data_array) - 1)
                del data_array[pos]
        return bytes(data_array)

    def havoc_mutation(self, data):
        """Random massive mutations"""
        data_array = bytearray(data)
        for _ in range(random.randint(10, 30)):
            mutation_type = random.choice([
                'bit_flip', 'byte_flip', 'interesting',
                'dictionary', 'arith', 'insert', 'delete'
            ])

            if mutation_type == 'bit_flip':
                pos = random.randint(0, len(data_array) - 1)
                data_array[pos] ^= (1 << random.randint(0, 7))

            elif mutation_type == 'byte_flip':
                pos = random.randint(0, len(data_array) - 1)
                data_array[pos] = random.randint(0, 255)

            elif mutation_type == 'interesting':
                pos = random.randint(0, len(data_array) - 1)
                data_array[pos] = random.choice([0x00, 0xFF, 0x80, 0x7F])

            elif mutation_type == 'dictionary':
                pos = random.randint(0, len(data_array) - 1)
                data_array[pos] = ord(random.choice(string.ascii_letters))

            elif mutation_type == 'arith':
                pos = random.randint(0, len(data_array) - 1)
                data_array[pos] = (data_array[pos] + random.randint(1, 10)) % 256

            elif mutation_type == 'insert':
                if len(data_array) < 10000:
                    pos = random.randint(0, len(data_array))
                    data_array.insert(pos, random.randint(0, 255))

            elif mutation_type == 'delete':
                if len(data_array) > 1:
                    pos = random.randint(0, len(data_array) - 1)
                    del data_array[pos]

        return bytes(data_array)

    def interesting_values_mutation(self, data):
        """Insert known crash-inducing values"""
        interesting_values = [
            b'\x00', b'\xFF', b'\x80', b'\x7F',
            b'\x41\x41\x41\x41',  # AAAA pattern
            b'%x' * 10,           # Format strings
            b'..\\..\\..\\',       # Path traversal
            b'\x00' * 256,        # Null bytes
        ]
        return bytearray(data) + interesting_values[random.randint(0, len(interesting_values)-1)]

    def size_mutation(self, data):
        """Vary payload size"""
        mutation_type = random.choice([
            'increase', 'decrease', 'double', 'half', 'max', 'zero'
        ])

        data_array = bytearray(data)

        if mutation_type == 'increase':
            data_array.extend(b'\x00' * random.randint(100, 1000))
        elif mutation_type == 'decrease':
            data_array = data_array[:len(data_array)//2]
        elif mutation_type == 'double':
            data_array = data_array + data_array
        elif mutation_type == 'half':
            data_array = data_array[:len(data_array)//2]
        elif mutation_type == 'max':
            data_array.extend(b'\xFF' * 4096)
        elif mutation_type == 'zero':
            data_array = b''

        return bytes(data_array)

    def fuzz_iteration(self, seed_input, mutations_per_iteration=5):
        """Run single fuzzing iteration"""
        sock = self.connect()
        if not sock:
            return None

        # Apply random mutations
        mutated = seed_input
        for _ in range(mutations_per_iteration):
            strategy = random.choice([
                self.bit_flip_mutation,
                self.byte_flip_mutation,
                self.insert_mutation,
                self.delete_mutation,
                self.havoc_mutation,
                self.interesting_values_mutation,
                self.size_mutation,
            ])
            mutated = strategy(mutated)

        self.test_cases += 1

        # Send payload and check for crash
        try:
            sock.send(mutated)
            response = sock.recv(4096)

            # Check for error indicators
            if b"crash" in response.lower() or b"error" in response.lower():
                self.crash_count += 1
                self.crashes.append({
                    'iteration': self.test_cases,
                    'payload': mutated[:100],  # First 100 bytes
                    'response': response[:100],
                    'timestamp': datetime.now().isoformat()
                })
                return 'crash'

            sock.close()
            return 'normal'

        except socket.timeout:
            self.crash_count += 1
            self.crashes.append({
                'iteration': self.test_cases,
                'payload': mutated[:100],
                'response': 'TIMEOUT',
                'timestamp': datetime.now().isoformat()
            })
            return 'timeout'

        except Exception as e:
            self.crash_count += 1
            self.crashes.append({
                'iteration': self.test_cases,
                'payload': mutated[:100],
                'response': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return 'error'

    def run_fuzzing_campaign(self, seed_input, iterations=1000, mutations_per=5):
        """Run complete fuzzing campaign"""
        print(f"\n[*] Starting Fuzzing Campaign")
        print(f"[*] Target: {self.target_host}:{self.target_port}")
        print(f"[*] Total Iterations: {iterations}")
        print(f"[*] Mutations per iteration: {mutations_per}")
        print(f"[*] Seed input size: {len(seed_input)} bytes\n")

        start_time = datetime.now()

        for i in range(iterations):
            result = self.fuzz_iteration(seed_input, mutations_per)

            if i % 100 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = i / elapsed if elapsed > 0 else 0
                print(f"[*] Iteration {i}/{iterations} | Crashes: {self.crash_count} | Rate: {rate:.1f} iter/s")

            if result == 'crash':
                print(f"    [!] CRASH at iteration {i}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        self.print_report(duration)

    def print_report(self, duration):
        """Print fuzzing report"""
        print("\n" + "="*70)
        print("FUZZING CAMPAIGN REPORT")
        print("="*70)
        print(f"Target: {self.target_host}:{self.target_port}")
        print(f"Total Iterations: {self.test_cases}")
        print(f"Total Crashes: {self.crash_count}")
        print(f"Crash Rate: {(self.crash_count/self.test_cases)*100:.2f}%")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Speed: {self.test_cases/duration:.1f} iterations/second")
        print("="*70)

        if self.crashes:
            print(f"\n[!] CRASHES DETECTED ({len(self.crashes)} unique):\n")
            for crash in self.crashes[:10]:  # Show first 10
                print(f"  Iteration: {crash['iteration']}")
                print(f"  Payload: {crash['payload']}")
                print(f"  Response: {crash['response']}")
                print()

        # Save report
        report = {
            'target': self.target_host,
            'port': self.target_port,
            'iterations': self.test_cases,
            'crashes': self.crash_count,
            'crash_rate': (self.crash_count/self.test_cases)*100,
            'duration_seconds': duration,
            'speed_iter_per_sec': self.test_cases/duration,
            'crash_details': self.crashes
        }

        with open(f'fuzz_report_{self.target_host}.json', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n[+] Report saved to: fuzz_report_{self.target_host}.json")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fuzzing_toolkit.py <target_host> [port] [iterations]")
        print("Example: python3 fuzzing_toolkit.py 192.168.1.50 8443 1000")
        sys.exit(1)

    target_host = sys.argv[1]
    target_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8443
    iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 1000

    # Seed input (SSL-VPN authentication packet)
    seed_input = b"\x13\x88\x00\x01admin\x00password\x00"

    fuzzer = FuzzingToolkit(target_host, target_port)
    fuzzer.run_fuzzing_campaign(seed_input, iterations=iterations)

if __name__ == "__main__":
    main()
