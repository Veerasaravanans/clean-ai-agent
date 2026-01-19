# HVAC Component Knowledge

Comprehensive knowledge for testing HVAC (Climate Control) systems in automotive displays.

---

## CRITICAL: HVAC Display Type Detection

Always detect which type before proceeding!

### Type 1: Always-Visible Controls (Most Common)

**Characteristics**:

- AC, Auto, Temperature, Fan controls ALWAYS visible on main screen
- NO separate HVAC app icon
- Controls are permanent UI elements
- Usually integrated into main dashboard

**Detection**:

```python
# Capture main screen
screenshot = capture_screenshot()

# Run OCR to find HVAC-related text
hvac_texts = ["AC", "Auto", "Temperature", "Fan", "Climate"]
found = any(ocr_find(text) for text in hvac_texts)

if found:
    # Type 1: Direct interaction
    type = "always_visible"
```

**Strategy**:

- Use `ocr_tap()` or `image_tap()` DIRECTLY on main screen
- NO app opening gesture needed
- Faster testing (no navigation overhead)

---

### Type 2: App-Based HVAC (Some Systems)

**Characteristics**:

- Dedicated HVAC/Climate app icon
- Tap icon to open full HVAC control screen
- Controls only available after opening app

**Detection**:

```python
# Look for HVAC app icon
icon_found = ocr_find("HVAC") or ocr_find("Climate") or image_find("hvac_icon.png")

if icon_found and not_already_in_hvac_app:
    # Type 2: App-based
    type = "app_based"
```

**Strategy**:

1. Find HVAC icon (OCR "HVAC"/"Climate" or image match)
2. Tap to open app
3. Then interact with controls

---

## UI Layout Variations

### Temperature Controls

**Common Locations**:

- Left/Right sides (dual-zone: driver/passenger)
- Center (single-zone)
- Top/Bottom

**Common Formats**:

- Numeric display: "72°F", "22°C"
- Slider with indicator
- Plus/Minus buttons

**Finding**:

```python
# Try OCR for temperature value
temp_coords = ocr_tap("72") or ocr_tap("Temperature")

# Or find +/- buttons
plus_coords = ocr_tap("+") or image_tap("temp_up.png")
minus_coords = ocr_tap("-") or image_tap("temp_down.png")
```

---

### Fan Speed Controls

**Layout**: Can be **horizontal OR vertical** slider

- Horizontal: Left-right swipe
- Vertical: Up-down swipe
- **Always check screen first!**

**Levels**: Usually 1-7, some systems 1-10

**Finding**:

```python
# OCR for fan indicator
fan_coords = ocr_find("Fan") or ocr_find("Fan Speed")

# Or look for fan icon
fan_icon = image_find("fan_icon.png")

# Detect orientation from visual analysis
if slider_is_horizontal:
    # Swipe right to increase
    swipe('right', distance=100)
else:
    # Swipe up to increase
    swipe('up', distance=100)
```

**Adjustment**:

- May require longer swipe duration (800ms)
- Some systems need multiple small swipes vs one long swipe

---

### AC Button

**Appearance**:

- Snowflake icon ❄️
- "AC" text
- May light up blue/green when active

**Finding**:

```python
# Priority 1: OCR
ac_coords = ocr_tap("AC")

# Priority 2: Image match
if not ac_coords:
    ac_coords = image_tap("ac_button.png")

# Priority 3: Look for snowflake
if not ac_coords:
    # Vision AI: "Find snowflake icon"
```

**Verification**:

- Check if button changes color/state after tap
- Some displays show "AC ON/OFF" text

---

### Auto Mode Button

**Appearance**:

- "AUTO" text
- "A" icon
- Circle with "AUTO" inside

**Behavior**:

- May override manual temperature/fan settings (not always!)
- Some systems: Auto mode is advisory only
- **Check visually** after activation

**Finding**:

```python
auto_coords = ocr_tap("AUTO") or ocr_tap("Auto") or image_tap("auto_button.png")
```

---

### Mode Buttons (Air Distribution)

**Icons**:

- Face (person head icon)
- Feet (shoes/feet icon)
- Face+Feet (combined icon)
- Defrost (windshield with wavy lines)

**Finding**:

```python
# Use image matching for mode icons
face_mode = image_tap("mode_face.png")
feet_mode = image_tap("mode_feet.png")
defrost_mode = image_tap("mode_defrost.png")

# Or try OCR if text labels exist
mode = ocr_tap("Face") or ocr_tap("Feet")
```

---

## Value Ranges

### Temperature

- Fahrenheit: 65°F - 85°F (typical range)
- Celsius: 16°C - 30°C
- Some systems: 60°F - 90°F

### Fan Speed

- Common: 1-7 levels
- Some systems: 1-10 levels
- Auto mode:often hidden/max level

---

## Common Issues & Solutions

### Issue: Temperature change not reflecting

**Cause**: UI update delay (2-3 seconds)

**Solution**:

```python
# Tap temperature up
ocr_tap("+")

# Wait for UI update
time.sleep(3)

# Verify change
verify_screen_state("Temperature increased")
```

---

### Issue: Fan slider not responding

**Cause**: Too fast swipe or wrong duration

**Solution**:

```python
# Use slower, longer swipe
swipe('right', distance=150, speed='slow', duration=800)

# Or multiple small swipes
for i in range(3):
    swipe('right', distance=50, duration=300)
    time.sleep(0.5)
```

---

### Issue: Auto mode doesn't override settings

**This is NORMAL** in many systems:

- Auto mode is optional/advisory
- Manual settings may take precedence
- Behavior varies by car manufacturer

**Solution**:

- Don't assume auto overrides
- Verify actual behavior visually
- Test both scenarios

---

## Reference Icons

Add these to `reference_icons/component_icons/`:

Essential:

- `ac_button.png` - AC/Snowflake icon
- `auto_button.png` - Auto mode button
- `fan_up.png` - Fan increase
- `fan_down.png` - Fan decrease
- `temp_up.png` - Temperature increase
- `temp_down.png` - Temperature decrease

Optional:

- `mode_face.png` - Face mode icon
- `mode_feet.png` - Feet mode icon
- `mode_defrost.png` - Defrost icon
- `recirculation.png` - Air recirculation icon

---

## Example Test Flows

### Increase Temperature

```python
# Detect HVAC type
if hvac_type_1_always_visible():
    # Direct interaction
    coords = ocr_tap("+") or ocr_tap("Temperature Up")
else:
    # Open HVAC app first
    ocr_tap("HVAC") or ocr_tap("Climate")
    time.sleep(1)
    coords = ocr_tap("+")

# Verify
time.sleep(2)
verify_temperature_increased()
```

### Turn On AC

```python
ac_coords = ocr_tap("AC") or image_tap("ac_button.png")

if ac_coords:
    tap(ac_coords)
    time.sleep(1)
    verify_ac_indicator_on()
```

---

**Remember**: Always use OCR/image matching FIRST. Adapt to what you see on screen!
