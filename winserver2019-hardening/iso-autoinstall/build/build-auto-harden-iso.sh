#!/usr/bin/env bash
#
# Injects the Windows Server 2019 auto-hardening files into a source ISO
# and repacks a new bootable ISO, using 7z + xorriso (no Windows/ADK
# required). Prefer Build-AutoHardenIso.ps1 (oscdimg) when a Windows host
# is available - that's Microsoft's officially supported tool. Boot-test
# the ISO this script produces in a VM before using it on real hardware.
#
# Usage:
#   ./build-auto-harden-iso.sh --source WS2019.iso --output WS2019-autoharden.iso [--with-answer-file] [--skip Id1,Id2]

set -euo pipefail

SOURCE_ISO=""
OUTPUT_ISO=""
WITH_ANSWER_FILE=0
SKIP_IDS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --source) SOURCE_ISO="$2"; shift 2 ;;
        --output) OUTPUT_ISO="$2"; shift 2 ;;
        --with-answer-file) WITH_ANSWER_FILE=1; shift ;;
        --skip) SKIP_IDS="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$SOURCE_ISO" || -z "$OUTPUT_ISO" ]]; then
    echo "Usage: $0 --source <in.iso> --output <out.iso> [--with-answer-file] [--skip Id1,Id2]" >&2
    exit 1
fi
if [[ ! -f "$SOURCE_ISO" ]]; then
    echo "Source ISO not found: $SOURCE_ISO" >&2
    exit 1
fi
for tool in 7z xorriso; do
    command -v "$tool" >/dev/null 2>&1 || { echo "Missing required tool: $tool (install p7zip-full and xorriso)" >&2; exit 1; }
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO_AUTOINSTALL_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$ISO_AUTOINSTALL_DIR")"
SCRIPTS_DIR="$REPO_ROOT/scripts"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

EXTRACT_DIR="$WORKDIR/extracted"
mkdir -p "$EXTRACT_DIR"

echo "Extracting $SOURCE_ISO ..."
7z x "$SOURCE_ISO" -o"$EXTRACT_DIR" -y >/dev/null

BOOT_IMG_BIOS="$EXTRACT_DIR/[BOOT]/1-Boot-NoEmul.img"
BOOT_IMG_UEFI="$EXTRACT_DIR/[BOOT]/2-Boot-NoEmul.img"
if [[ ! -f "$BOOT_IMG_BIOS" || ! -f "$BOOT_IMG_UEFI" ]]; then
    echo "Couldn't find both El Torito boot images under '[BOOT]/' after extraction -" \
         "is this a standard hybrid BIOS+UEFI Server 2019 ISO?" >&2
    exit 1
fi

OEM_SCRIPTS_DIR="$EXTRACT_DIR/sources/\$OEM\$/\$\$/Setup/Scripts"
HARDENING_DEST_DIR="$OEM_SCRIPTS_DIR/hardening"
mkdir -p "$HARDENING_DEST_DIR"

cp "$SCRIPTS_DIR/Harden-WinServer2019.ps1" "$HARDENING_DEST_DIR/"
cp "$SCRIPTS_DIR/Audit-WinServer2019.ps1" "$HARDENING_DEST_DIR/"

SETUP_COMPLETE_SRC="$ISO_AUTOINSTALL_DIR/oem/\$OEM\$/\$\$/Setup/Scripts/SetupComplete.cmd"
SETUP_COMPLETE_DEST="$OEM_SCRIPTS_DIR/SetupComplete.cmd"
cp "$SETUP_COMPLETE_SRC" "$SETUP_COMPLETE_DEST"
if [[ -n "$SKIP_IDS" ]]; then
    # Insert "-Skip Id1,Id2" right after the Harden-WinServer2019.ps1 -Apply call.
    sed -i "s/\(Harden-WinServer2019\.ps1\" -Apply\)/\1 -Skip $SKIP_IDS/" "$SETUP_COMPLETE_DEST"
fi
# CRLF line endings for the batch file (Windows cmd.exe is picky about this).
sed -i 's/$/\r/' "$SETUP_COMPLETE_DEST"

if [[ "$WITH_ANSWER_FILE" -eq 1 ]]; then
    echo "Including autounattend.xml at ISO root (unattended install, WIPES Disk 0)."
    cp "$ISO_AUTOINSTALL_DIR/autounattend.xml" "$EXTRACT_DIR/autounattend.xml"
fi

echo "Building $OUTPUT_ISO with xorriso ..."
xorriso -as mkisofs \
    -iso-level 3 -udf -allow-limited-size \
    -volid "WS2019_AUTOHARDEN" \
    -b "[BOOT]/1-Boot-NoEmul.img" -no-emul-boot -boot-load-size 4 -boot-info-table \
    -eltorito-alt-boot \
    -e "[BOOT]/2-Boot-NoEmul.img" -no-emul-boot \
    -isohybrid-gpt-basdat \
    -o "$OUTPUT_ISO" \
    "$EXTRACT_DIR"

echo "Done: $OUTPUT_ISO"
