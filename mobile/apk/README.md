# Icekey Inventory Android APK

This directory contains a minimal Android WebView wrapper for the Icekey Inventory PWA.

## App details

- Package/application ID: `de.icekey.inventory`
- Min SDK: 24
- Target/compile SDK: 34
- Version code: 21
- Version name: read from the repository `VERSION` file (`2.1.0`)
- Default server URL: configured in `WebViewActivity.DEFAULT_SERVER_URL` and `strings.xml`

## Build prerequisites

Install a JDK 17 and Android SDK/build tools. Set `JAVA_HOME` if it is not auto-detected by `build.sh`.

## Build

```bash
cd mobile/apk
./scripts/sync-version.sh
./gradlew assembleRelease
```

Or build and copy/sign the APK for web download:

```bash
cd mobile/apk
./build.sh
```

`build.sh` runs `assembleRelease`, signs with a generated debug keystore when `apksigner` is available, and writes:

```text
mobile/static/mobile/icekey-inventory.apk
```

## Server URL

The app reads the server URL from Android shared preferences. The default is the local Icekey Inventory PWA dashboard URL. `SettingsActivity` can update the URL on device; values are normalized to include a scheme and trailing slash.
