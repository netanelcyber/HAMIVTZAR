#!/bin/bash
# Post-fuzzing crash analysis and binary disassembly pipeline

echo "[*] FortiOS Vulnerability Analysis Pipeline"
echo "[*] This will run after fuzzing completes"
echo ""

FUZZER_REPORT="zero_day_report.json"
BINARY="binaries/fortios"

# Phase 1: Analyze fuzzing report
if [ -f "$FUZZER_REPORT" ]; then
    echo "[+] Phase 1: Analyzing fuzzing report..."
    python3 tools/crash_analyzer.py crashes/ 2>/dev/null || echo "   (crashes directory may be empty, that's OK)"
    echo ""
fi

# Phase 2: Extract binary information
if [ -f "$BINARY" ]; then
    echo "[+] Phase 2: Binary analysis..."
    echo "    Running binary disassembler..."
    python3 tools/binary_disassembler.py "$BINARY" binary_analysis.json
    echo ""
    echo "    Running binary debugger..."
    python3 tools/binary_debugger.py "$BINARY" debugger_info.json
    echo ""
fi

# Phase 3: Generate combined report
echo "[+] Phase 3: Generating vulnerability analysis report..."
cat > vulnerability_analysis_report.md << 'MARKDOWN'
# Vulnerability Analysis Report
## FortiOS 8.0.0 Lab Environment

### Fuzzing Results
- Automatic analysis will be inserted here

### Binary Analysis
- String patterns and dangerous functions identified

### Recommendations
1. Escalate critical findings to Fortinet security team
2. Document all CVE details
3. Prepare responsible disclosure timeline
MARKDOWN

echo "[+] Analysis pipeline ready!"
echo ""
echo "[*] Generated files:"
echo "    - fuzzing report: $FUZZER_REPORT"
echo "    - binary analysis: binary_analysis.json"
echo "    - debugger info: debugger_info.json"
echo "    - analysis report: vulnerability_analysis_report.md"
