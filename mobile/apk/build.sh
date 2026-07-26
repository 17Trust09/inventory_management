#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
APK_DIR="$ROOT_DIR/mobile/apk"
OUT_DIR="$ROOT_DIR/mobile/static/mobile"
VERSION_FILE="$ROOT_DIR/VERSION"

cd "$APK_DIR"
./scripts/sync-version.sh

if [ -z "${JAVA_HOME:-}" ]; then
  for candidate in /usr/lib/jvm/java-17-openjdk-amd64 /usr/lib/jvm/java-17-openjdk /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home; do
    if [ -d "$candidate" ]; then
      export JAVA_HOME="$candidate"
      break
    fi
  done
fi

if [ -z "${JAVA_HOME:-}" ]; then
  echo "JAVA_HOME is not set. Install JDK 17 and export JAVA_HOME before building." >&2
  exit 1
fi

./gradlew assembleRelease
mkdir -p "$OUT_DIR"
APK_SRC="$APK_DIR/app/build/outputs/apk/release/app-release-unsigned.apk"
APK_DST="$OUT_DIR/icekey-inventory.apk"

if command -v apksigner >/dev/null 2>&1; then
  KEYSTORE="$APK_DIR/debug.keystore"
  if [ ! -f "$KEYSTORE" ]; then
    keytool -genkeypair -v -storepass android -keypass android -keystore "$KEYSTORE" -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Icekey Inventory Debug,O=Icekey,C=DE"
  fi
  apksigner sign --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android --out "$APK_DST" "$APK_SRC"
else
  echo "apksigner not found; copying unsigned release APK." >&2
  cp "$APK_SRC" "$APK_DST"
fi

echo "APK written to $APK_DST"
