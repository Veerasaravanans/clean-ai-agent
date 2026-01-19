"""
Patch script to fix ai_analyze node in nodes.py
"""

import re

file_path = "backend/langgraph/nodes.py"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the problematic section
old_code = """            # Extract all text elements with OCR
            detected_elements = toolkit.vision.get_all_text(screenshot_path)
            
            return {
                **state,
                "screen_analysis": analysis.summary,
                "detected_elements": [
                    {
                        "text": elem.text,
                        "x": elem.x,
                        "y": elem.y,
                        "confidence": elem.confidence
                    }
                    for elem in detected_elements
                ],"""

new_code = """            # Extract all text elements with OCR (safely)
            try:
                detected_elements = toolkit.vision.get_all_text(screenshot_path) or []
                if not isinstance(detected_elements, list):
                    detected_elements = []
            except Exception as e:
                logger.error(f"❌ OCR extraction error: {e}")
                detected_elements = []
            
            return {
                **state,
                "screen_analysis": analysis.summary,
                "detected_elements": [
                    {
                        "text": getattr(elem, 'text', ''),
                        "x": getattr(elem, 'x', 0),
                        "y": getattr(elem, 'y', 0),
                        "confidence": getattr(elem, 'confidence', 0.0)
                    }
                    for elem in detected_elements
                    if hasattr(elem, 'text')
                ],"""

if old_code in content:
    content = content.replace(old_code, new_code)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Successfully patched ai_analyze node!")
    print("   Fixed: detected_elements handling")
    print("\nNext steps:")
    print("1. Restart server: uvicorn backend.main:app --reload")
    print("2. Test: python test_api.py")
else:
    print("❌ Could not find code to replace")
    print("   Please manually edit backend/langgraph/nodes.py")
    print("   See FIX_LAST_ERROR.md for instructions")