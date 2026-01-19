# Custom ADB Commands

Special ADB commands and tricks for automotive testing.

---

## Finding Package/Activity Information

### Get Current Activity (ResumedActivity)

```bash
adb shell dumpsys activity activities | findstr "ResumedActivity"
```

**Use**: To find which app/activity is currently actioned

### Get All Running Activities

```bash
adb shell dumpsys activity activities
```

### Launch Specific App

```bash
adb shell am start -n com.package.name/com.package.ActivityName
```

---

## Screen Information

### Get Screen Resolution

```bash
adb shell wm size
```

### Get Screen Density

```bash
adb shell wm density
```

---

## Input Methods

### Send Text (Special Characters)

```bash
adb shell input text "Hello%sWorld"
```

**Note**: %s = space, escape special chars with \\

### Send Key Events

```bash
adb shell input keyevent KEYCODE_HOME
adb shell input keyevent KEYCODE_BACK
adb shell input keyevent KEYCODE_MENU
```

### Common Keycodes

- KEYCODE_HOME = 3
- KEYCODE_BACK = 4
- KEYCODE_MENU = 82
- KEYCODE_VOLUME_UP = 24
- KEYCODE_VOLUME_DOWN = 25

---

## App Management

### List Installed Packages

```bash
adb shell pm list packages
```

### Clear App Data

```bash
adb shell pm clear com.package.name
```

### Force Stop App

```bash
adb shell am force-stop com.package.name
```

---

## System Information

### Get Android Version

```bash
adb shell getprop ro.build.version.release
```

### Get Device Model

```bash
adb shell getprop ro.product.model
```

---

## Debugging

### Capture Logcat

```bash
adb logcat -d > logcat.txt
```

### Monitor Touch Events

```bash
adb shell getevent
```

---

**Note**: These commands can be executed via the agent or manually for debugging.
