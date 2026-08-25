# MedicineApp Mobile — Flutter Android Client

A production-ready Flutter mobile application for intelligent prescription scanning, on-device text recognition, AI-assisted medication review, drug interaction safety warnings, and exact dose reminder scheduling.

---

## 1. System Architecture & End-to-End Workflow

### Edge-Cloud Hybrid Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Flutter Mobile App (Client)                       │
│                                                                             │
│  [1. ML Kit Document Scanner] ───> Auto-edge detection, crop & perspective  │
│                 │                                                           │
│  [2. On-Device Latin OCR]     ───> Line & Bounding Box extraction (offline) │
│                 │                                                           │
│  [3. Multipart HTTP Upload]   ───> POST /api/scan (clean image + OCR JSON)  │
└─────────────────┬───────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Backend Services (Node.js & FastAPI)                  │
│                                                                             │
│  [PhoBERT NER Classifier]     ───> Semantic entity tagging (DRUG / OTHER)   │
│                 │                                                           │
│  [Vietnamese Drug DB Search]  ───> Fuzzy match against 9,284 VN drugs       │
└─────────────────┬───────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Mobile Review & Medication Management                 │
│                                                                             │
│  [4. Review & Safety Screen]  ───> Confidence chips & Drug interaction check│
│  [5. Plan Schedule & Alarms]  ───> Exact local alarms (AlarmManager/Notify) │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Feature Overview
- **Intelligent Document Scanner**: Native Android bridge to Google Play Services ML Kit Document Scanner (`GmsDocumentScannerOptions.SCANNER_MODE_FULL`) with auto edge-detection, perspective warp, and shadow removal.
- **Edge Text Recognition**: Ultra-fast on-device OCR via `google_mlkit_text_recognition` Latin script, minimizing upload latency and backend bandwidth.
- **State Management & DI**: Clean Architecture powered by `flutter_riverpod` (v3.3.1) with strictly separated domain entities, repositories, and state notifiers.
- **Declarative Navigation**: `go_router` (v17.1.0) with tri-state authentication guards (`/boot`, `/login`, `/home`) and secure token storage via `flutter_secure_storage`.
- **Clinical Safety Warnings**: Real-time cross-medication interaction analysis querying backend safety matrices (`/api/drug-interactions/check-by-drugs`).
- **Resilient Medication Reminders**: Exact scheduled alarms via `flutter_local_notifications` and `timezone`, maintaining active schedules across device restarts (`BOOT_COMPLETED` receiver) with rolling 3-day window scheduling.

---

## 2. Prerequisites & Development Environment

| Requirement | Supported Version | Notes |
|-------------|-------------------|-------|
| **Flutter SDK** | `3.38.x` (Dart `3.10.x`) | Tested on Flutter 3.38.5 stable |
| **Android SDK** | `API 34` / `API 35` | `minSdk: 21`, `compileSdk: 35`, `targetSdk: 34` |
| **Java JDK** | `OpenJDK 17` or `OpenJDK 21` | Compatible with Gradle JVM target Java 17 |
| **Gradle** | `8.14` (AGP `8.11.1`) | Auto-managed via Gradle Wrapper (`gradlew`) |
| **Google Play Services** | `v16.0.0+` | Required on emulator/device for ML Kit Document Scanner |

---

## 3. Configuration & Environment Variables

Copy the example environment file into `.env` inside the `mobile/` directory:

```bash
cp .env.example .env
```

### Configuration Matrix for `API_BASE_URL`

| Environment / Device | `API_BASE_URL` | Setup Command / Details |
|----------------------|----------------|--------------------------|
| **Android Emulator (AVD)** | `http://10.0.2.2:3001/api` | Default loopback alias pointing to PC host port 3001 (`dev.sh`) |
| **Android Emulator (Docker)** | `http://10.0.2.2:3000/api` | Pointing to PC host port 3000 (`docker compose up`) |
| **Physical Device (USB Debugging)** | `http://127.0.0.1:3001/api` | Run: `adb reverse tcp:3001 tcp:3001` (Recommended) |
| **Physical Device (Local Wi-Fi)** | `http://192.168.1.x:3001/api` | Replace with PC host LAN IP; devices must share Wi-Fi subnet |
| **Desktop / Linux / Web** | `http://127.0.0.1:3001/api` | Direct localhost loopback |
| **Production / Cloud Server** | `https://api.yourdomain.com/api` | HTTPS production endpoint |

*Note*: After modifying `.env`, perform a full hot restart (`R`) or re-launch `flutter run` because `.env` is loaded through Flutter's asset bundle at boot.

---

## 4. Step-by-Step Build & Run Guide

### 4.1 Install Flutter Dependencies
```bash
flutter pub get
```

### 4.2 Run in Debug Mode (Connected Device or Emulator)
```bash
flutter run
```

### 4.3 Build Debug APK
```bash
flutter build apk --debug
```
*Output Artifact*: `build/app/outputs/flutter-apk/app-debug.apk`

### 4.4 Build Release APK
```bash
flutter build apk --release
```
*Output Artifact*: `build/app/outputs/flutter-apk/app-release.apk`

### 4.5 Install Release APK to Device via ADB
```bash
adb install -r build/app/outputs/flutter-apk/app-release.apk
```

---

## 5. Android Permissions & Manifest Breakdown

Declared in `mobile/android/app/src/main/AndroidManifest.xml`:

| Permission / Attribute | Purpose & Operational Rationale |
|------------------------|---------------------------------|
| `android.permission.INTERNET` | Communicates with the Node.js API server and FastAPI AI proxy. |
| `android.permission.CAMERA` | Camera capture and live camera viewfinder fallback when scanner unavailable. |
| `android.permission.RECEIVE_BOOT_COMPLETED` | Wakes notification boot receivers on device startup to re-register pending medication alarms. |
| `android.permission.SCHEDULE_EXACT_ALARM` | Permits precise timing for dose alarms on Android 12+ (API 31+). |
| `android.permission.USE_EXACT_ALARM` | Pre-granted exact alarm scheduling on Android 13+ (API 33+) for reminder apps. |
| `android.permission.POST_NOTIFICATIONS` | Runtime notification permission required on Android 13+. |
| `android:usesCleartextTraffic="true"` | Allows unencrypted HTTP communication with local development servers (`10.0.2.2`, `127.0.0.1`, LAN IPs). |

### Background Alarm Receivers
- `com.dexterous.flutterlocalnotifications.ScheduledNotificationReceiver` — Fires exact scheduled medication alarms.
- `com.dexterous.flutterlocalnotifications.ScheduledNotificationBootReceiver` — Listens for `BOOT_COMPLETED` and `MY_PACKAGE_REPLACED` to restore alarm schedules.

---

## 6. Testing & Quality Assurance

### 6.1 Unit & Widget Test Suite (39 Tests)
Execute the complete Flutter test suite:
```bash
flutter test
```
*Expected Output*: `All tests passed!` (39/39 passed, 0 failures).

Coverage highlights:
- **`document_scanner_test.dart`**: Locked platform channel wire contracts, native cache mappings, error handling, and memory/cache lease cleanup.
- **`prescription_image_acquirer_test.dart`**: Scanner fallback mechanics, cancellation handling, and payload invariant checks.
- **`plan_interaction_checker_test.dart`**: Drug deduplication, multi-drug safety checks, and severity level mapping.
- **`lookup_screen_golden_test.dart`**: Pixel-perfect golden widget regression tests for drug interaction and active ingredient catalogs.
- **`home_screen_test.dart`**: Vietnamese locale formatting (`vi_VN`) and responsive quick actions.

### 6.2 Static Analysis
Run static analysis to confirm zero errors, zero warnings, and zero lints:
```bash
flutter analyze
```
*Expected Output*: `No issues found!`

---

## 7. Troubleshooting Common Issues

### 1. `Cleartext HTTP traffic not permitted`
- **Cause**: Android 9+ (API 28+) disables unencrypted HTTP communication by default.
- **Resolution**: Confirm `android:usesCleartextTraffic="true"` is present inside `<application>` in `mobile/android/app/src/main/AndroidManifest.xml`.

### 2. Physical Device Fails to Connect to `http://127.0.0.1:3001`
- **Cause**: On a physical phone, `127.0.0.1` refers to the mobile phone itself, not your development PC.
- **Resolution**: Forward the port over USB by running:
  ```bash
  adb reverse tcp:3001 tcp:3001
  ```
  Alternatively, update `API_BASE_URL` in `.env` to your PC's local Wi-Fi IP (e.g. `http://192.168.1.50:3001/api`).

### 3. `google_play_services_unavailable` on Emulator
- **Cause**: The Android emulator was created without Google Play Services support.
- **Resolution**: In Android Studio AVD Manager, create an emulator with the **Google Play** logo next to the target image (e.g. `Pixel 7 - API 34 with Google Play`).

### 4. Exact Medication Alarms Not Triggering on Android 12+ / 14+
- **Cause**: Aggressive OEM battery saving or revoked exact alarm permissions.
- **Resolution**: Navigate to **Settings -> Apps -> Special app access -> Alarms & reminders -> Uống thuốc** and enable **Allow setting alarms**. The app also includes an automatic fallback to `AndroidScheduleMode.inexactAllowWhileIdle` if permission is revoked.
