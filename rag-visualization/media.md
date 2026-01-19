# Media Component Knowledge

Comprehensive knowledge for testing Media/Audio systems in automotive displays.

---

## CRITICAL: Media Source Access Variations

Different car systems have DIFFERENT ways to access media sources!

### PACCAR System Style (NO Source Button)

**Characteristics**:

- NO visible "Source" button
- NO visible FM/AM/BT buttons initially
- Media icon in navigation/task bar

**Access Method**:

```python
# Find Media icon in taskbar
media_coords = ocr_find("Media")

# DOUBLE TAP (not single tap!)
double_tap(media_coords[0], media_coords[1], delay=50)

# First tap: Opens media player (shows current station/track)
# Second tap (within 1s): Opens source selection menu

# Wait for menu
time.sleep(1)

# Now can see and tap: FM, AM, SiriusXM, Bluetooth, etc.
source_coords = ocr_tap("FM") or ocr_tap("AM")
```

**Key Points**:

- Must use `double_tap()`, not `tap()`
- Delay between taps: 50ms (default)
- If too slow (>1s), just opens media player twice

---

### Standard System Style (Has Source Button)

**Characteristics**:

- Visible "Source" button OR
- Visible direct source buttons (FM, AM, BT buttons)

**Access Method**:

```python
# Look for Source button
source_btn = ocr_find("Source")

if source_btn:
    tap(source_btn)
    time.sleep(1)
    # Then select from menu
    ocr_tap("FM")
else:
    # Or direct source buttons
    ocr_tap("FM") or ocr_tap("AM") or ocr_tap("Bluetooth")
```

---

### Hybrid System Style

**Characteristics**:

- Has both Source button AND direct buttons
- Source button opens detailed menu
- Direct buttons for quick access

**Strategy**: Try direct buttons first (faster), fall back to Source button

---

## Detection Strategy

```python
def find_media_source_access():
    # 1. Look for direct source buttons via OCR
    if ocr_find("FM") or ocr_find("AM") or ocr_find("Bluetooth"):
        return "direct_buttons"

    # 2. Look for Source button
    if ocr_find("Source"):
        return "source_button"

    # 3. Assume PACCAR-style (double-tap needed)
    if ocr_find("Media") or image_find("media_icon.png"):
        return "double_tap_required"

    # 4. Ask architect
    return "unknown"
```

---

## UI Layout Variations

### Source Selection

**Types**:

- Dropdown menu
- Tab interface
- Grid of icons
- List view

**Sources**:

- FM Radio (87.5 - 108.0 MHz)
- AM Radio (530 - 1710 kHz)
- Weather Band (162.400 - 162.550 MHz, 7 channels)
- SiriusXM (channel-based, requires subscription)
- Bluetooth Audio (from paired device)
- USB Media
- Auxiliary Input

---

### Station/Track Display

**Location**: Usually center or top of screen

**Information Shown**:

- Current station frequency (FM/AM)
- Station name (RDS if available)
- Song/artist (Bluetooth, SiriusXM)
- Album art (some systems)

**Finding**:

```python
# OCR for frequency
station = ocr_find_pattern(r"\d{2,3}\.\d")  # e.g., "98.5"

# Or station name
station_name = ocr_find("KEXP") or ocr_find("NPR")
```

---

### Control Buttons

**Common Controls**:

- **Seek**: Forward/Backward (skip stations)
- **Tune**: Fine-tune frequency (±0.1 MHz)
- **Previous/Next**: For playlists/presets
- **Play/Pause**: For Bluetooth/USB
- **Favorites/Presets**: Saved stations (1-6 typically)

**Finding**:

```python
# OCR for button labels
seek_fwd = ocr_tap("Seek") or ocr_tap("▶") or image_tap("seek_forward.png")
play_pause = ocr_tap("Play") or ocr_tap("▶▮▮") or image_tap("play_button.png")

# Favorites (numeric)
preset_1 = ocr_tap("1") or ocr_tap("Preset 1")
```

---

### Volume Control

**Types**:

- Side slider (most common)
- Buttons (+/-)
- Rotary dial (physical, may not be testable via ADB)
- Gesture-based swipe

**Range**: Usually 0-40 (varies by system)

**Finding**:

```python
# OCR for volume indicator
volume = ocr_find("Volume") or ocr_find_pattern(r"Vol: \d+")

# Or find +/- buttons
vol_up = ocr_tap("+") or image_tap("volume_up.png")
vol_down = ocr_tap("-") or image_tap("volume_down.png")

# Or swipe on volume slider
volume_slider = image_find("volume_slider.png")
if volume_slider:
    # Swipe right to increase
    swipe('right', distance=100, from_point=volume_slider)
```

---

## Media Source Switching Test Flow

### For PACCAR Systems

```python
# 1. Double-tap Media icon
media_icon = ocr_find("Media") or image_find("media_icon.png")
double_tap(media_icon[0], media_icon[1], delay=50)

time.sleep(1)

# 2. Select source
ocr_tap("FM")

time.sleep(2)

# 3. Verify FM radio is active
verify_screen_state("FM radio frequency visible")
```

### For Standard Systems

```python
# 1. Look for direct source button
if ocr_find("FM"):
    ocr_tap("FM")
else:
    # Use Source button
    ocr_tap("Source")
    time.sleep(1)
    ocr_tap("FM")

time.sleep(2)

# 2. Verify
verify_screen_state("FM radio active")
```

---

## Common Issues & Solutions

### Issue: Sources not accessible

**Cause**: Using single tap instead of double tap (PACCAR)

**Solution**:

```python
# Always try double-tap first if unsure
media_coords = ocr_find("Media")
double_tap(media_coords[0], media_coords[1], delay=50)
```

---

### Issue: Station won't change

**Cause**: Wrong button (Seek vs Tune)

**Solution**:

- **Seek**: Jumps to next station with signal
- **Tune**: Changes frequency by 0.1 MHz steps
- For auto-scan: Seek
- For precise frequency: Tune

---

### Issue: Bluetooth source not appearing

**Cause**: No device paired

**Solution**:

- This is expected if no phone paired
- Skip test or pair device first (manual step)
- Or test with FM/AM instead

---

### Issue: Volume gesture not working

**Cause**: System uses physical knob, not touchscreen

**Solution**:

- Check if volume control is physical
- If so, test cannot control volume via ADB
- Use vision to verify volume display only

---

## Reference Icons

Add to `reference_icons/component_icons/`:

Essential:

- `media_icon.png` - Media app icon in taskbar
- `fm_icon.png` - FM radio icon/button
- `am_icon.png` - AM radio icon/button
- `bluetooth_icon.png` - Bluetooth audio icon

Optional:

- `seek_forward.png` - Seek forward button
- `seek_backward.png` - Seek backward button
- `play_button.png` - Play/Pause button
- `volume_up.png` - Volume increase
- `volume_down.png` - Volume decrease
- `preset_buttons.png` - Preset/favorite buttons

---

## Value Ranges

### FM Radio

- Range: 87.5 - 108.0 MHz
- Step: 0.1 MHz (some systems 0.2 MHz)
- Example: 98.5, 101.1, 107.9

### AM Radio

- Range: 530 - 1710 kHz
- Step: 10 kHz
- Example: 720, 1010, 1540

### Weather Band

- 7 fixed frequencies
- 162.400, 162.425, 162.450, 162.475, 162.500, 162.525, 162.550 MHz

### Volume

- Typical: 0-40
- Some systems: 0-30 or 0-60
- Mute: 0 or special mute state

---

## Example Test: Switch to FM and Change Station

```python
# Detect system type
system_type = find_media_source_access()

# Access media sources
if system_type == "double_tap_required":
    media = ocr_find("Media")
    double_tap(media[0], media[1])
    time.sleep(1)
    ocr_tap("FM")
elif system_type == "direct_buttons":
    ocr_tap("FM")
else:
    ocr_tap("Source")
    time.sleep(1)
    ocr_tap("FM")

time.sleep(2)

# Verify FM active
verify_screen_contains("FM") or verify_screen_pattern(r"\d{2,3}\.\d")

# Change station (Seek)
seek_btn = ocr_tap("Seek") or ocr_tap("▶") or image_tap("seek_forward.png")
time.sleep(2)

# Verify station changed
verify_station_different()
```

---

**Remember**: Always detect system type first! PACCAR needs double-tap, others use single tap/buttons.
