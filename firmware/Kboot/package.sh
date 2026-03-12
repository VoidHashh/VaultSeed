#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
PREBUILT_DIR="${SCRIPT_DIR}/prebuilt"

require_file() {
    local path="$1"
    if [ ! -f "${path}" ]; then
        echo "ERROR: required file not found: ${path}" >&2
        exit 1
    fi
}

cd "${BUILD_DIR}"

require_file firmware.bin
require_file config.bin

if [ ! -f "${PREBUILT_DIR}/bootloader_lo.bin" ] || [ ! -f "${PREBUILT_DIR}/bootloader_hi.bin" ]; then
    echo "Prebuilt Kboot bootloaders not found in ${PREBUILT_DIR}; falling back to BUILD.sh" >&2
    /bin/bash "${BUILD_DIR}/BUILD.sh"
    require_file kboot.kfpkg
    exit 0
fi

cp -f "${PREBUILT_DIR}/bootloader_lo.bin" .
cp -f "${PREBUILT_DIR}/bootloader_hi.bin" .
rm -f flash-list.json kboot.kfpkg

cat > flash-list.json <<'EOF'
{
    "version": "0.1.1",
    "files": [
        {
            "address": 0,
            "bin": "bootloader_lo.bin",
            "sha256Prefix": true
        },
        {
            "address": 4096,
            "bin": "bootloader_hi.bin",
            "sha256Prefix": true
        },
        {
            "address": 16384,
            "bin": "config.bin",
            "sha256Prefix": false
        },
        {
            "address": 20480,
            "bin": "config.bin",
            "sha256Prefix": false
        },
        {
            "address": 524288,
            "bin": "firmware.bin",
            "sha256Prefix": true
        }
    ]
}
EOF

# Fix timestamps and permissions so the resulting package is deterministic.
touch -t 200901031815 flash-list.json bootloader_lo.bin bootloader_hi.bin config.bin firmware.bin
chmod 0644 flash-list.json bootloader_lo.bin bootloader_hi.bin config.bin firmware.bin
zip -q -9 kboot.kfpkg flash-list.json bootloader_lo.bin bootloader_hi.bin config.bin firmware.bin
rm -f flash-list.json bootloader_lo.bin bootloader_hi.bin
