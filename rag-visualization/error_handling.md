# Error Handling Solutions - Chain-of-Thought & One-Shot Format

This file contains known error patterns and their solutions using Chain-of-Thought reasoning.

**Architect**: Add new solutions following the CoT template below!

---

## 🎯 CoT Template for Error Solutions

```
## Problem: [Brief description]

### Symptoms
- [What you observe]
- [Error messages or behaviors]

### Chain-of-Thought Analysis

UNDERSTAND:
- What is failing? [Description]
- Why might it fail? [Potential causes]

ANALYZE:
- Root cause: [Most likely reason]
- Evidence: [What supports this]

PLAN:
- Approach 1: [First solution to try]
- Approach 2: [Backup solution]
- Approach 3: [Last resort]

### One-Shot Example

[Complete walkthrough showing the solution working]

###Solutions (Priority Order)

[Numbered list of solutions]
```

---

## Problem 1: KEYCODE_MENU doesn't open app launcher

### Symptoms

- Pressing KEYCODE_MENU does nothing
- No response from hard key events
- Custom automotive display doesn't respond to standard Android keys

### Chain-of-Thought Analysis

```
UNDERSTAND:
Q: What is failing?
A: Standard Android KEYCODE_MENU not opening app launcher

Q: Why might it fail?
A: Custom automotive displays often override standard Android behaviors

ANALYZE:
Q: What's the root cause?
A: Automotive OEMs customize system UI, disable standard hard keys

Q: What evidence supports this?
A: Many car displays use custom launcher implementations

PLAN:
Q: What's the best approach?
A: Visual recognition (OCR/Image) - works on ANY system

Q: Why visual first?
A: Zero setup, doesn't depend on system implementation

Q: What's the backup?
A: Intent discovery if visual methods fail (10th attempt)
```

### One-Shot Example: Finding App Launcher

```
TASK: Open app launcher

ATTEMPT 1: OCR Search
---
UNDERSTAND:
- Goal: Find app launcher button
- Context: Main screen, unknown display type

ANALYZE:
- *Capture screenshot*
- *Run OCR*
- Found text: "Home", "Media", "Apps", "HVAC"

OBSERVE: "Apps" text found at (900, 1080)

PLAN:
- This looks like app launcher button
- Use OCR tap on "Apps"

EXECUTE:
Action: ocr_tap("Apps")

VERIFY:
- *Screenshot shows grid of app icons*
- *OCR finds: "Settings", "Browser", "Calendar"*
- ✓ App launcher is open!

RESULT: ✅ Success using OCR (PRIMARY method)
```

**Alternative Attempt if OCR Failed:**

```
ATTEMPT 2: Image Matching
---
UNDERSTAND:
- OCR didn't find "Apps" text
- Launcher might be icon-only

ANALYZE:
- Check reference_icons/app_launcher.png
- Icon exists in library

PLAN:
- Use image matching
- Multi-scale search (80%-120%)

EXECUTE:
Action: image_tap("app_launcher.png")
Result: Found at (905, 1080), confidence 0.92

VERIFY:
- *App grid visible*
- ✓ Success!

RESULT: ✅ Success using Image Matching (SECONDARY method)
```

**Last Resort if Both Failed:**

```
ATTEMPT 10: Intent Discovery
---
UNDERSTAND:
- All visual methods failed (9 attempts)
- Need manual help to discover intent

PLAN:
- Ask architect to tap launcher ONCE
- Capture intent information
- Store for future use

EXECUTE:
1. *Show message to architect*: "Please tap the app launcher button once"
2. *Architect taps launcher*
3. Run: adb shell dumpsys activity activities | findstr "ResumedActivity"
4. Output: "ResumedActivity: com.android.launcher/.LauncherActivity"
5. Store: "App Launcher Intent: com.android.launcher/.LauncherActivity"

FUTURE USE:
Action: adb shell am start -n com.android.launcher/.LauncherActivity
Result: ✅ Launcher opens

LEARN:
- Store in learned_solutions.md
- Never need to ask again!
```

### Solutions (Priority Order)

**1. OCR Search** (PRIMARY - Try First)

```python
# Find text: "Apps", "Launcher", "Applications"
coords = ocr_find("Apps") or ocr_find("Launcher")
if coords:
    tap(coords)
```

_Success Rate: 85%_
_Speed: <500ms_

**2. Image Matching** (SECONDARY)

```python
# Load reference icon
coords = image_find("app_launcher.png", confidence=0.85)
if coords:
    tap(coords)
```

_Success Rate: 90%_
_Speed: <300ms_

**3. Vision AI** (BACKUP)

```python
# Ask moondream2
description = vision_ai_query("Where is the app launcher icon?")
coords = estimate_from_description(description)
tap(coords)
```

_Success Rate: 70%_
_Speed: ~2s_

**4. Intent Discovery** (LAST RESORT - Attempt 10)

```python
# Manual intervention required
ask_architect("Please tap app launcher once")
intent = capture_intent()
save_to_learned_solutions(intent)

# Future: Use intent directly
launch_via_intent(intent)
```

---

## Problem 2: Button not responding to tap

### Symptoms

- Tap action completes successfully
- No visual change on screen
- Button doesn't activate

### Chain-of-Thought Analysis

```
UNDERSTAND:
Q: What's happening?
A: Tap command execution but no effect

Q: What could cause this?
A: Multiple possibilities:
   - Button is disabled/greyed out
   - Overlay blocking touch
   - Coordinates slightly off
   - Button needs different gesture (long press/double tap)
   - Touch latency/timing issue

ANALYZE:
Q: How do I identify the cause?
A: Try solutions in order of likelihood

PLAN:
Priority 1: Re-detect coordinates (stale coordinates)
Priority 2: Try double-tap (some buttons need it)
Priority 3: Try long-press (activation method)
Priority 4: Check for overlays (blocking layer)
Priority 5: Add delays (timing issue)
```

### One-Shot Example: Unresponsive AC Button

```
TASK: Tap AC button (not responding)

ATTEMPT 1: Verify Coordinates
---
UNDERSTAND:
- Tapped AC at previous coords (540, 300)
- No response

ANALYZE:
- UI might have shifted
- Coordinates could be stale

PLAN:
- Re-run OCR to get fresh coordinates
- Use ocr_tap instead of cached coords

EXECUTE:
Action: ocr_tap("AC")  # Fresh detection
Result: Found "AC" at (545, 305) - slightly different!

VERIFY:
- *AC button lights up blue*
- *Shows "ON" state*
- ✓ Success!

LEARN:
Observation: Coordinates were off by 5 pixels
Lesson: Always re-detect if tap fails - UI might have shifted
```

**Alternative: Double-Tap Needed**

```
ATTEMPT 2: Try Double-Tap
---
UNDERSTAND:
- Single tap failed
- Some buttons (like PACCAR Media) need double-tap

ANALYZE:
- This might be similar behavior
- Worth trying double-tap

PLAN:
- Use double_tap on same coordinates

EXECUTE:Action: double_tap(540, 300, delay=50)

VERIFY:
- *Button activates*
- ✓ Success!

LEARN:
Observation: Button required double-tap activation
Lesson: If single tap fails, try double-tap before other methods
```

**Alternative: Long Press Required**

```
ATTEMPT 3: Try Long Press
---
UNDERSTAND:
- Single and double tap failed
- Some buttons activate on long press

PLAN:
- Long press for 1 second

EXECUTE:
Action: long_press(540, 300, duration=1000)

VERIFY:
- *Button shows context menu*
- or *Button activates*
- ✓ Success!

LEARN:
Observation: Button was long-press activated
Lesson: Some buttons use long-press for primary action
```

### Solutions (Priority Order)

**1. Fresh Coordinate Detection**

```python
# Re-run OCR for current coordinates
coords = ocr_tap("Button Text")  # Don't use cached coords
```

**2. Add Delays**

```python
# UI might not be ready
time.sleep(0.2)  # Wait before tap
tap(x, y)
time.sleep(0.2)  # Wait after tap
```

**3. Try Double-Tap**

```python
double_tap(x, y, delay=50)
# Some buttons need double activation
```

**4. Try Long Press**

```python
long_press(x, y, duration=1000)
# Alternative activation method
```

**5. Check for Overlays**

```python
# Use vision to detect dialogs
has_dialog = vision_ai_query("Is there a dialog or popup visible?")
if has_dialog:
    dismiss_overlay()
    retry_tap()
```

**6. Verify Button State**

```python
# Check if button is disabled
is_enabled = vision_ai_query("Is this button enabled or greyed out?")
if not is_enabled:
    report_error("Button is disabled")
```

---

## Problem 3: Text found by OCR but tap doesn't work

### Symptoms

- OCR successfully detects text
- Coordinates returned
- Tap at coordinates has no effect

### Chain-of-Thought Reasoning

```
TASK: Tap "Settings" text (OCR found it but tap failed)

UNDERSTAND:
- OCR found "Settings" with bounding box: [100, 200, 200, 250]
- Calculated center: (150, 225)
- Tap at (150, 225) did nothing

ANALYZE:
Q: Why might this fail?
A: Possible reasons:
   1. Text is part of larger button (center might not be tappable)
   2. Multiple "Settings" on screen (tapped wrong one)
   3. Text is label, not button
   4. Bounding box calculation off

PLAN:
Approach 1: Try different points in bounding box
Approach 2: Find the correct "Settings" instance
Approach 3: Find associated button/icon nearby

EXECUTE Approach 1:
- OCR gave bbox: [100, 200, 200, 250]
- Tried center (150, 225) - failed
- Try top-left (100, 200) - failed
- Try bottom-right (200, 250) - failed
- Try slightly right of center (170, 225) - SUCCESS!

LEARN:
- Button active area might not align with text center
- Try multiple points within detected region
```

### One-Shot Example

```
PROBLEM: "AC" found by OCR but tap ineffective

STEP 1: Analyze Detection
---
- OCR result: Text "AC", bbox [530, 290, 550, 310]
- Calculated center: (540, 300)
- Tap result: No response

STEP 2: Try Alternative Points
---
# Top of text
tap(540, 292)  # Failed

# Bottom of text
tap(540, 308)  # Failed

# Slightly right
tap(548, 300)  # SUCCESS!

CONCLUSION:
- Active button area was slightly right of text
- Text rendering vs touch target mismatch

SOLUTION:
Try offsets from detected center:
- Center ± 5-10 pixels in X
- Center ± 5-10 pixels in Y
```

### Solutions (Priority Order)

**1. Try Multiple Points in Bounding Box**

```python
bbox = ocr_find_bbox("Text")
points_to_try = [
    (bbox.center_x, bbox.center_y),  # Center
    (bbox.left + 10, bbox.center_y),  # Left edge
    (bbox.right - 10, bbox.center_y),  # Right edge
    (bbox.center_x, bbox.top + 10),  # Top
    (bbox.center_x, bbox.bottom - 10)  # Bottom
]

for x, y in points_to_try:
    tap(x, y)
    if verify_success():
        break
```

**2. Find Correct Instance (If Multiple Matches)**

```python
# OCR might find multiple "Settings"
all_matches = ocr_find_all("Settings")

# Choose based on position
top_right = find_by_position(all_matches, "top-right")
tap(top_right.center)
```

**3. Look for Associated Icon**

```python
# Text might be label, icon is the button
text_coords = ocr_find("Settings")

# Search for icon near text
icon = image_find_near("settings_gear.png", near=text_coords, radius=50)
tap(icon)
```

**4. Use Case-Insensitive Match**

```python
# Try different casings
coords = ocr_find("Settings") or \
         ocr_find("SETTINGS") or \
         ocr_find("settings")
```

---

## Problem 4: HVAC controls not found

### One-Shot Example: Type Detection

```
TASK: Find and tap AC button

STEP 1: UNDERSTAND
---
Q: Where might HVAC controls be?
A: Two possibilities:
   - Type 1: Always visible on main screen
   - Type 2: Inside HVAC app

STEP 2: ANALYZE - Detect Type
---
Action: capture_screenshot()
Action: ocr_detect_all()

Found on main screen: "AC", "72°F", "Auto", "Fan Speed"

CONCLUSION: Type 1 (Always-Visible Controls)

STEP 3: PLAN
---
- No need to open app
- Use OCR directly on main screen

STEP 4: EXECUTE
---
Action: ocr_tap("AC")
Result: Found at (540, 300)
        Tapped successfully
        AC activated ✓

SUCCESS PATH: Detect type → Direct tap
```

**Alternative: Type 2 (App-Based)**

```
STEP 2: ANALYZE - Detect Type
---
Action: capture_screenshot()
Action: ocr_detect_all()

Found on main screen: "Home", "Media", "Apps"
NOT found: Any HVAC controls

Found: HVAC icon via image_match

CONCLUSION: Type 2 (App-Based)

STEP 3: PLAN
---
- Must open HVAC app first
- Then access controls

STEP 4: EXECUTE
---
Action: image_tap("hvac_icon.png")
Wait: 1 second for app to open
Action: ocr_tap("AC")
Result: AC activated ✓

SUCCESS PATH: Open app → Then tap control
```

### Decision Tree

```
START

OCR on main screen
   ↓
Found HVAC terms? (AC, Temp, Fan, Auto)
   ↓
YES → Type 1: Direct interaction
│     Action: ocr_tap(control_name)
│     ✓ Done
   ↓
NO → Type 2: Look for HVAC app
│    ↓
│    Found HVAC icon? (OCR/Image)
│    ↓
│    YES → Open app first
│    │      Action: tap(hvac_icon)
│    │      Wait: 1 sec
│    │      Action: ocr_tap(control_name)
│    │      ✓ Done
│    ↓
│    NO → Error: HVAC not accessible
│          Action: Ask architect
```

---

## Problem 5: Media source selection not opening (PACCAR)

### Complete CoT Example

```
OBJECTIVE: Select FM radio in PACCAR Media system

=== ATTEMPT 1: Standard Approach ===

UNDERSTAND:
- Goal: Switch to FM radio
- System: PACCAR Media (special handling)

ANALYZE:
- Current screen: Main dashboard
- Media icon visible in taskbar

PLAN:
- Approach: Tap Media icon
- Expectation: Opens Media app

EXECUTE:
- Action: ocr_tap("Media")
- Result: Media player opens, shows current station

VERIFY:
- ✓ Media opened
- ❌ But no source selection menu
- Current source shows: "SiriusXM Channel 15"
- Need to access FM

OBSERVE:
- Single tap opened player, not source menu
- This matches PACCAR behavior in knowledge base!

=== ATTEMPT 2: PACCAR Double-Tap ===

UNDERSTAND:
- PACCAR requires DOUBLE-TAP for source menu
- Knowledge base: "Double tap within 1 second"

PLAN:
- Action: Double-tap Media icon in the navigation bar
- Wait: For source menu to appear

EXECUTE:
- Action: double_tap(800, 1080, delay=50)
  # 50ms delay between taps
- Wait: 1 second

VERIFY:
- *Capture screenshot*
- *Run OCR*
- Found: "FM", "AM", "SiriusXM", "Bluetooth"
- ✓ Source menu is open!

CONTINUE:
- Action: ocr_tap("FM")
- Result: FM radio activates
- Verify: Shows "FM 98.5"

SUCCESS:
- ✓ FM radio selected
- Method: PACCAR double-tap + OCR

LEARN:
- PACCAR Media: Always use double_tap for source menu
- Single tap = Player view
- Double tap = Source selection
- Store this pattern for future PACCAR tests
```

### Solutions

**1. PACCAR System (Double-Tap)**

```python
# Find Media icon
media_coords = ocr_find("Media") or image_find("media_icon.png")

# Double-tap for source menu
double_tap(media_coords[0], media_coords[1], delay=50)
time.sleep(1)

# Now select source
ocr_tap("FM")
```

**2. Standard System (Source Button)**

```python
# Single tap opens player
ocr_tap("Media")
time.sleep(1)

# Look for Source button
ocr_tap("Source") or ocr_tap("FM") or ocr_tap("AM")
```

**3. Detection Logic**

```python
# Try PACCAR method first
double_tap_on_media()
wait(1)

if source_menu_visible():
    # PACCAR system
    use_double_tap_pattern()
else:
    # Standard system
    look_for_source_button()
```

---

## 📝 Adding New Solutions Template

```markdown
## Problem: [Name]

### Symptoms

- [What you observe]
- [Error indicators]

### Chain-of-Thought Analysis

\`\`\`
UNDERSTAND:

- What fails: [Description]
- Potential causes: [List]

ANALYZE:

- Root cause: [Most likely]
- Evidence: [Supporting facts]

PLAN:

- Approach 1: [First try]
- Approach 2: [Backup]
- Approach 3: [Last resort]
  \`\`\`

### One-Shot Example

\`\`\`
[Complete walkthrough with UNDERSTAND → ANALYZE → PLAN → EXECUTE → VERIFY → LEARN]
\`\`\`

### Solutions (Priority Order)

**1. [Primary Solution]**
\`\`\`python
[Code example]
\`\`\`

**2. [Backup Solution]**
\`\`\`python
[Code example]
\`\`\`
```

---

**Remember**: Every error is a learning opportunity. Use Chain-of-Thought to understand WHY something failed, then systematically try solutions!

_CoT Error Handling v1.0 - Created by Veera Saravanan_
