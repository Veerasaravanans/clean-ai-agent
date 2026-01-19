# Navigation Component Knowledge

Comprehensive knowledge for testing Navigation/Maps systems in automotive displays.

---

## Common Entry Points

### Opening Navigation

**Methods** (try in order):

1. **Direct Icon Tap**:
   - OCR: "Navigation", "Maps", "Nav"
   - Image: `navigation_icon.png`
2. **App Launcher**:

   - Open app drawer
   - Find Navigation app
   - Tap to launch

3. **Home Screen**:
   - Some systems have Navigation widget on home

```python
# Try direct
nav_coords = ocr_tap("Navigation") or ocr_tap("Maps") or image_tap("navigation_icon.png")

if not nav_coords:
    # Try app launcher
    open_app_launcher()
    ocr_tap("Navigation")
```

---

## Main UI Elements

### Search/Destination Input

**Location**: Usually top of screen

**Types**:

- Text input field
- Voice input button (microphone icon)
- Recent destinations list
- Favorites/Home/Work shortcuts

**Finding**:

```python
# Input field
search_field = ocr_find("Search") or ocr_find("Enter destination") or image_find("search_bar.png")

tap(search_field)
time.sleep(0.5)

# Type destination
input_text("123%sMain%sStreet")  # %s = space in ADB

# Or voice input
voice_btn = ocr_tap("Voice") or image_tap("mic_icon.png")
```

---

### Map View

**Elements**:

- Current location indicator (blue dot)
- Zoom controls (+/-)
- Compass/North indicator
- Scale indicator
- Traffic overlay (if available)

**Interactions**:

- **Pan**: Swipe in any direction
- **Zoom In**: Pinch out (or + button)
- **Zoom Out**: Pinch in (or - button)
- **Rotate**: Two-finger rotation (may not work via ADB)

```python
# Zoom in via button
zoom_in = ocr_tap("+") or image_tap("zoom_in.png")

# Pan map
swipe('left', distance=200)  # Pan right
swipe('up', distance=200)    # Pan down
```

---

### Route Controls

**During Navigation**:

- Turn-by-turn directions
- Next maneuver preview
- Distance to destination
- Estimated time of arrival (ETA)
- Recalculate route
- Alternative routes
- End navigation

**Finding**:

```python
# End navigation
end_btn = ocr_tap("End") or ocr_tap("Stop") or ocr_tap("Cancel Navigation")

# Alternative routes
alt_routes = ocr_tap("Alternative") or ocr_tap("Options")

# Recalculate
recalc = ocr_tap("Recalculate") or image_tap("recalculate_icon.png")
```

---

### POI (Points of Interest)

**Categories**:

- Gas stations
- Restaurants
- Parking
- Hotels
- Charging stations (electric vehicles)

**Search**:

```python
# Search for category
search_poi("Gas Station") or search_poi("Restaurant")

# Or use category buttons
poi_btn = ocr_tap("Gas") or ocr_tap("Food") or image_tap("poi_gas.png")
```

---

## Common Test Flows

### Search for Destination

```python
# 1. Open Navigation
ocr_tap("Navigation") or image_tap("navigation_icon.png")
time.sleep(2)

# 2. Tap search field
search = ocr_tap("Search") or ocr_find("destination")
tap(search)
time.sleep(0.5)

# 3. Type address
input_text("Seattle")
time.sleep(1)

# 4. Press Enter or tap first suggestion
press_key("KEYCODE_ENTER")
# OR
ocr_tap("Seattle, WA")

time.sleep(2)

# 5. Start navigation
start_btn = ocr_tap("Start") or ocr_tap("Go") or ocr_tap("Navigate")

# 6. Verify navigation started
verify_screen_contains("Turn") or verify_screen_contains("miles") or verify_screen_contains("ETA")
```

---

### Use Recent/Favorites

```python
# 1. Open Navigation
ocr_tap("Navigation")
time.sleep(2)

# 2. Look for Recents or Favorites tab
recents = ocr_tap("Recent") or ocr_tap("Favorites") or image_tap("star_icon.png")
time.sleep(1)

# 3. Tap saved location
ocr_tap("Home") or ocr_tap("Work") or ocr_tap("First saved location")

# 4. Start navigation
ocr_tap("Start") or ocr_tap("Go")
```

---

### Pan and Zoom Map

```python
# 1. Ensure in map view (not navigation)
if in_navigation_mode():
    end_navigation()

time.sleep(1)

# 2. Zoom in
zoom_in_btn = ocr_tap("+") or image_tap("zoom_in.png")
time.sleep(0.5)

# 3. Zoom out
zoom_out_btn = ocr_tap("-") or image_tap("zoom_out.png")
time.sleep(0.5)

# 4.Pan left
swipe('left', distance=200)
time.sleep(0.5)

# 5. Pan up
swipe('up', distance=200)
```

---

## Common Issues

### Issue: Search field not responding

**Cause**: Keyboard not appearing

**Solution**:

```python
# Tap search field again
tap(search_coords)
time.sleep(1)

# If still no keyboard, try pressing key to focus
press_key("KEYCODE_DPAD_DOWN")
time.sleep(0.5)

# Then type
input_text("destination")
```

---

### Issue: Cannot find "Start" button

**Cause**: Button might say "Go", "Navigate Name", "Drive"

**Solution**:

```python
# Try variations
start = (ocr_find("Start") or
         ocr_find("Go") or
         ocr_find("Navigate") or
         ocr_find("Drive") or
         image_find("start_icon.png"))
```

---

### Issue: Navigation won't end

**Cause**: Button location varies

**Solution**:

```python
# Try multiple methods
end = (ocr_tap("End") or
       ocr_tap("Stop") or
       ocr_tap("Cancel") or
       ocr_tap("x") or
       image_tap("close_icon.png"))

# Or use BACK key
if not end:
    press_key("KEYCODE_BACK")
```

---

### Issue: Map won't pan/zoom

**Cause**: Touch gestures may not work during navigation

**Solution**:

- End navigation first
- Then pan/zoom
- Or use +/- buttons instead of gestures

---

## Platform-Specific Notes

### Google Maps

- Blue circle = current location
- Search at top
- Menu (≡) at top-left usually

### Apple CarPlay / Maps

- Different UI patterns
- May need different approach
- Check with vision AI first

### Built-in OEM Navigation

- Varies widely by manufacturer
- Always use OCR/vision to adapt
- No assumptions about layout

---

## Reference Icons

Add to `reference_icons/component_icons/`:

Essential:

- `navigation_icon.png` - Navigation app icon
- `search_icon.png` - Search/magnifying glass
- `mic_icon.png` - Voice input
- `zoom_in.png` - Plus/zoom in button
- `zoom_out.png` - Minus/zoom out button

Optional:

- `poi_gas.png` - Gas station POI icon
- `poi_food.png` - Restaurant POI icon
- `poi_parking.png` - Parking POI icon
- `home_icon.png` - Home destination icon
- `work_icon.png` - Work destination icon
- `recalculate_icon.png` - Recalculate route

---

## Voice Commands (If Supported)

Some systems support voice navigation:

```python
# Activate voice
voice_btn = ocr_tap("Voice") or image_tap("mic_icon.png") or press_key("KEYCODE_VOICE_ASSIST")

time.sleep(0.5)

# System listens...
# (Agent would use STT to send "Navigate to Seattle")

# Verify voice processed
verify_screen_contains("Seattle") or verify_screen_contains("Did you mean")
```

---

## Verification Strategies

### Verify Navigation Started

```python
# Look for turn-by-turn UI elements
indicators = [
    "Turn",
    "mile",
    "feet",
    "ETA",
    "Arrive",
    "Next",
    "maneuver",
    "Continue",
    "Keep"
]

found = any(ocr_find(indicator) for indicator in indicators)

if found:
    navigation_active = True
```

### Verify Destination Accepted

```python
# After searching
verification = (
    ocr_find("Start") or
    ocr_find("Go") or
    ocr_find("Route") or
    screen_shows_destination_card()
)
```

---

**Remember**: Navigation UIs vary significantly. Always use vision/OCR to understand current screen!
