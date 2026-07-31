#!/bin/bash
# Build 0167 Testing Framework - Quick Start Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
TARGET_IP=${1:-192.168.1.100}
TARGET_PORT=${2:-443}
BINARY_0030=${3:-}
BINARY_0167=${4:-}

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}FortiOS 8.0.0 Build 0167 Testing${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Target: $TARGET_IP:$TARGET_PORT"
echo "Timestamp: $(date)"
echo ""

# Create reports directory
mkdir -p reports
mkdir -p logs

# Phase 1: Binary Analysis (if binaries provided)
if [ ! -z "$BINARY_0030" ] && [ ! -z "$BINARY_0167" ]; then
    echo -e "${YELLOW}[Phase 1] Running Binary Comparison${NC}"

    if [ ! -f "$BINARY_0030" ]; then
        echo -e "${RED}ERROR: Binary 0030 not found at $BINARY_0030${NC}"
        exit 1
    fi

    if [ ! -f "$BINARY_0167" ]; then
        echo -e "${RED}ERROR: Binary 0167 not found at $BINARY_0167${NC}"
        exit 1
    fi

    python3 binary_comparison_tool.py "$BINARY_0030" "$BINARY_0167" \
        > logs/binary_comparison.log 2>&1

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Binary comparison complete${NC}"
        echo "Results: binary_comparison_results.json"
    else
        echo -e "${RED}✗ Binary comparison failed${NC}"
        cat logs/binary_comparison.log
    fi
    echo ""
fi

# Phase 2: Main Exploitation Testing
echo -e "${YELLOW}[Phase 2] Running Exploitation Tests${NC}"
python3 test_build_0167.py $TARGET_IP $TARGET_PORT \
    > logs/exploitation_tests.log 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Exploitation testing complete${NC}"
    RESULTS_FILE=$(ls -t reports/build_0167_test_results_*.json | head -1)
    echo "Results: $RESULTS_FILE"
else
    echo -e "${RED}✗ Exploitation testing failed${NC}"
    cat logs/exploitation_tests.log
fi
echo ""

# Phase 3: Run Exploitation Chains
echo -e "${YELLOW}[Phase 3] Running Exploitation Chains${NC}"
python3 exploit_automation.py $TARGET_IP $TARGET_PORT \
    > logs/exploitation_chains.log 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Exploitation chains complete${NC}"
    CHAINS_FILE=$(ls -t exploitation_results_0167_*.json | head -1)
    echo "Results: $CHAINS_FILE"
else
    echo -e "${RED}✗ Exploitation chains failed${NC}"
    cat logs/exploitation_chains.log
fi
echo ""

# Phase 4: Generate Summary
echo -e "${YELLOW}[Phase 4] Generating Summary Report${NC}"

echo "===========================================================" > reports/TEST_SUMMARY.txt
echo "FortiOS 8.0.0 Build 0167 Testing Summary" >> reports/TEST_SUMMARY.txt
echo "===========================================================" >> reports/TEST_SUMMARY.txt
echo "Test Date: $(date)" >> reports/TEST_SUMMARY.txt
echo "Target: $TARGET_IP:$TARGET_PORT" >> reports/TEST_SUMMARY.txt
echo "" >> reports/TEST_SUMMARY.txt
echo "Files Generated:" >> reports/TEST_SUMMARY.txt
echo "- $RESULTS_FILE" >> reports/TEST_SUMMARY.txt
echo "- $CHAINS_FILE" >> reports/TEST_SUMMARY.txt
echo "- binary_comparison_results.json (if binary analysis ran)" >> reports/TEST_SUMMARY.txt
echo "" >> reports/TEST_SUMMARY.txt
echo "Logs:" >> reports/TEST_SUMMARY.txt
ls -lh logs/ >> reports/TEST_SUMMARY.txt
echo "" >> reports/TEST_SUMMARY.txt
echo "===========================================================" >> reports/TEST_SUMMARY.txt

cat reports/TEST_SUMMARY.txt

# Final status
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Testing Framework Complete${NC}"
echo -e "${GREEN}================================${NC}"
echo "Check the following for results:"
echo "  - reports/: All test results"
echo "  - logs/: Detailed execution logs"
echo ""
echo "To analyze results:"
echo "  cat reports/build_0167_test_results_*.json | jq ."
echo "  cat reports/binary_comparison_results.json | jq ."
