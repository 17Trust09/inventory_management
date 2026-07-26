#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
VERSION_FILE="$ROOT_DIR/VERSION"
BUILD_FILE="$ROOT_DIR/mobile/apk/app/build.gradle"

if [ ! -f "$VERSION_FILE" ]; then
  echo "VERSION file not found at $VERSION_FILE" >&2
  exit 1
fi

VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
if [ -z "$VERSION" ]; then
  echo "VERSION file is empty" >&2
  exit 1
fi

python3 - "$BUILD_FILE" "$VERSION" <<'PY2'
import re
import sys

path, version = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8') as fh:
    text = fh.read()

text = re.sub(r'versionName inventoryVersion|versionName [\'"][^\'"]+[\'"]', 'versionName inventoryVersion', text)

if 'def inventoryVersion' not in text:
    injection = "def versionFile = rootProject.file('../../VERSION')\n" \
                "def inventoryVersion = versionFile.exists() ? versionFile.text.trim() : '%s'\n\n" % version
    text = text.replace('android {', injection + 'android {', 1)

with open(path, 'w', encoding='utf-8') as fh:
    fh.write(text)
PY2

echo "Gradle versionName is sourced from VERSION=$VERSION"
