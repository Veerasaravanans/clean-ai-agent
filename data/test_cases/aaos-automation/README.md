# AAOS Car Display UI Automation Framework

A comprehensive Java-based UI automation framework for Android Automotive OS (AAOS) car display testing using Appium and TestNG.

## 📋 Table of Contents
- [Overview](#overview)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Running Tests](#running-tests)
- [Test Cases](#test-cases)
- [Configuration](#configuration)
- [Reporting](#reporting)

## 🎯 Overview

This automation framework is designed for testing AAOS car display UI components including:
- App Launcher navigation
- Settings menu navigation (Bluetooth, Network, Notifications, Sound, Display)
- Application launches (Spotify, Phone, SMS)
- Touch gestures (tap, swipe, long press, drag and drop)
- SSIM-based image verification

## 📁 Project Structure

```
aaos-automation/
├── pom.xml                          # Maven configuration
├── testng.xml                       # TestNG suite configuration
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/aaos/automation/
│   │   │       ├── base/            # Base test classes
│   │   │       ├── config/          # Configuration management
│   │   │       ├── driver/          # WebDriver management
│   │   │       ├── listeners/       # TestNG listeners
│   │   │       ├── pages/           # Page Object classes
│   │   │       ├── reporting/       # Extent Reports
│   │   │       ├── utils/           # Utility classes
│   │   │       └── verification/    # Verification utilities
│   │   └── resources/
│   │       ├── config.properties    # Configuration file
│   │       └── log4j2.xml          # Logging configuration
│   └── test/
│       └── java/
│           └── com/aaos/automation/tests/
│               ├── NAID_NEW_001_*.java   # Navigation tests
│               ├── NAID_NEW_002_*.java   # Spotify tests
│               ├── NAID_NEW_003_*.java   # Settings tests
│               └── ...                    # More test classes
├── screenshots/                     # Test screenshots
├── reports/                         # HTML test reports
├── logs/                           # Log files
└── reference_images/               # Reference images for SSIM verification
```

## ✅ Prerequisites

1. **Java JDK 11 or higher**
   ```bash
   java -version
   ```

2. **Maven 3.6+**
   ```bash
   mvn -version
   ```

3. **Appium Server 2.x**
   ```bash
   npm install -g appium
   appium driver install uiautomator2
   ```

4. **Android SDK with AAOS emulator or device**
   - Android Studio with AAOS system image
   - Or physical AAOS device

5. **ADB (Android Debug Bridge)**
   ```bash
   adb devices
   ```

## 🚀 Setup Instructions

### 1. Clone/Download the Project
```bash
cd aaos-automation
```

### 2. Configure Device Settings
Edit `src/main/resources/config.properties`:
```properties
device.name=AAOS_Emulator
device.platform.version=13
device.udid=emulator-5554
appium.server.url=http://127.0.0.1:4723
```

### 3. Install Dependencies
```bash
mvn clean install -DskipTests
```

### 4. Start Appium Server
```bash
appium --base-path /wd/hub
```

### 5. Start AAOS Emulator/Connect Device
```bash
# For emulator
emulator -avd AAOS_Emulator

# For device
adb connect <device-ip>:5555
```

## 🏃 Running Tests

### Run All Tests
```bash
mvn clean test
```

### Run Specific Test Suite
```bash
mvn test -DsuiteXmlFile=testng.xml
```

### Run Specific Test Class
```bash
mvn test -Dtest=NAID_NEW_001_NavigationAppLauncherToBluetoothTest
```

### Run Tests with Parallel Execution
```bash
mvn test -Dparallel=methods -DthreadCount=2
```

## 📝 Test Cases

| Test ID | Description | Component |
|---------|-------------|-----------|
| NAID-NEW-001 | Navigation: App Launcher to Settings Bluetooth | Bluetooth |
| NAID-NEW-002 | Navigation: Spotify Launch and Return Home | Navigation |
| NAID-NEW-003 | Navigation: App Launcher to Settings Notifications | Settings |
| NAID-NEW-004 | Application Launch: Spotify | General |
| NAID-NEW-005 | Application Launch: Phone | Phone |
| NAID-NEW-006 | Application Launch: SMS | General |
| NAID-NEW-007 | Navigation: Settings Multiple Menu Navigation | Settings |
| NAID-NEW-008 | Drag and Drop | General |
| NAID-NEW-009 | Swipe | General |
| NAID-NEW-010 | RAW ADB - Double Tap | General |

## ⚙️ Configuration

### config.properties
```properties
# Device Configuration
device.name=AAOS_Emulator
device.platform.name=Android
device.platform.version=13
device.automation.name=UiAutomator2
device.udid=emulator-5554

# Appium Server
appium.server.url=http://127.0.0.1:4723
appium.server.timeout=60

# Display Configuration (Car Display Resolution)
display.width=1408
display.height=792

# Test Configuration
test.implicit.wait=10
test.explicit.wait=30
test.retry.count=3

# Verification
verification.ssim.default.threshold=0.85
```

## 📊 Reporting

### Extent Reports
After test execution, HTML reports are generated in `./reports/` directory:
- `AAOS_UI_Test_Report_YYYYMMDD_HHMMSS.html`

### Screenshots
- Captured on test failure automatically
- Located in `./screenshots/` directory

### Logs
- Logs are stored in `./logs/aaos-automation.log`
- Console output shows real-time test execution

## 🔧 Key Classes

### Page Objects
- `HomePage` - Home screen interactions
- `AppLauncherPage` - App drawer/launcher
- `SettingsPage` - Settings application
- `BluetoothSettingsPage` - Bluetooth settings
- `SpotifyPage` - Spotify application
- `PhonePage` - Phone dialer
- `SmsPage` - SMS/Messaging

### Utilities
- `GestureUtils` - Touch gestures (tap, swipe, drag)
- `WaitUtils` - Explicit waits
- `ScreenshotUtils` - Screenshot capture
- `ImageUtils` - SSIM calculation
- `VerificationUtils` - Image verification

## 🎨 Gesture Examples

```java
// Tap at coordinates
gestureUtils.tap(730, 380);

// Double tap
gestureUtils.doubleTap(730, 380);

// Long press
gestureUtils.longPress(630, 740, 2000);

// Swipe
gestureUtils.swipe(100, 396, 1308, 396, GestureUtils.MEDIUM_SWIPE);

// Drag and drop
gestureUtils.dragAndDrop(startX, startY, endX, endY);
```

## 📱 SSIM Verification

```java
// Full screen verification
verificationUtils.verifyBySSIM("reference_image", 0.85);

// Region verification
verificationUtils.verifyRegionBySSIM("bluetooth_cropped", 0.85, 550, 80, 858, 340);
```

## ⚠️ Troubleshooting

1. **Appium connection failed**
   - Ensure Appium server is running
   - Check device/emulator is connected: `adb devices`

2. **Element not found**
   - Increase implicit/explicit wait times
   - Use UIAutomator Viewer to inspect elements

3. **Screenshot failures**
   - Check write permissions for screenshots directory
   - Verify device screen is unlocked

## 📄 License

This project is for internal testing purposes.

---

Generated from test case spreadsheet: `NAID_updated_with_cleanup.csv`
