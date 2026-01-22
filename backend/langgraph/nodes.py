"""
nodes.py - LangGraph Node Implementations

Part 1: Analysis & Planning Nodes (6 nodes)
Part 2: Execution & Verification Nodes (6 nodes)
Part 3: HITL & Standalone Nodes (3 nodes)

UPDATED: Includes SSIM-based verification and status fix
"""

import logging
from typing import Dict, Any, Optional, Tuple
from backend.services.device_profile_service import get_device_profile_service
from backend.services.verification_image_service import get_verification_image_service
from backend.services.execution_control import get_execution_control
from backend.langgraph.state import AgentState
from backend.models import AgentMode, AgentStatus
from backend.tools import toolkit

logger = logging.getLogger(__name__)


def _check_execution_control(state: AgentState) -> Tuple[bool, Optional[AgentState]]:
    """
    Check execution control flags (stop/pause).

    This should be called at the start of key nodes to allow
    stopping or pausing execution.

    Returns:
        Tuple of (should_continue, stopped_state)
        - If should_continue is True, proceed normally
        - If should_continue is False, return stopped_state
    """
    control = get_execution_control()

    # Check and wait if paused (this blocks until resumed or stopped)
    if not control.check_and_wait():
        # Stop was requested
        logger.info("🛑 Execution stopped by user")
        return False, {
            **state,
            "status": AgentStatus.STOPPED,
            "stop_requested": True,
            "should_continue": False,
            "execution_log": state.get("execution_log", []) + ["Execution stopped by user"]
        }

    return True, None
_reference_cache = {}

def _parse_reference_name_from_target_cached(target_element: str) -> Optional[str]:
    """
    CACHED version of AI reference mapping to reduce API calls.
    
    First checks cache, only calls AI if not cached.
    """
    if not target_element:
        return None
    
    # Check cache first
    cache_key = target_element.lower().strip()
    if cache_key in _reference_cache:
        logger.debug(f"   📦 Cache hit: '{target_element}' → '{_reference_cache[cache_key]}'")
        return _reference_cache[cache_key]
    
    # Not in cache, ask AI
    reference_name = _parse_reference_name_from_target(target_element)
    
    # Store in cache for future use
    if reference_name:
        _reference_cache[cache_key] = reference_name
        logger.debug(f"   💾 Cached: '{target_element}' → '{reference_name}'")
    
    return reference_name

# ═══════════════════════════════════════════════════════════════
# Node 0: Check Resume (Entry Point)
# ═══════════════════════════════════════════════════════════════

def check_resume(state: AgentState) -> AgentState:
    """
    Entry point node - check if resuming from HITL.
    
    This is a passthrough node that just returns state unchanged.
    The actual routing logic is in the conditional edge.
    
    Args:
        state: Current agent state
        
    Returns:
        Unchanged state
    """
    hitl_guidance = state.get("hitl_guidance")
    hitl_coordinates = state.get("hitl_coordinates")
    waiting_for_hitl = state.get("waiting_for_hitl", False)
    
    if waiting_for_hitl and (hitl_guidance or hitl_coordinates):
        logger.info("🔄 Resuming from HITL with guidance")
    else:
        logger.info("▶️ Starting normal workflow")
    
    return state


# ═══════════════════════════════════════════════════════════════
# Node 1: Detect Mode
# ═══════════════════════════════════════════════════════════════

def detect_mode(state: AgentState) -> AgentState:
    """
    Detect agent mode based on state inputs.
    
    Determines if this is:
    - Test execution mode (has test_id)
    - Standalone mode (has standalone_command)
    - Idle mode (neither)
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with current_mode set
    """
    logger.info("🔍 Detecting agent mode...")
    
    if state.get("test_id"):
        mode = AgentMode.TEST_EXECUTION
        logger.info(f"✅ Mode: TEST_EXECUTION (test_id={state['test_id']})")
    elif state.get("standalone_command"):
        mode = AgentMode.STANDALONE
        logger.info(f"✅ Mode: STANDALONE (command={state['standalone_command'][:50]}...)")
    else:
        mode = AgentMode.IDLE
        logger.info("✅ Mode: IDLE")
    
    return {
        **state,
        "current_mode": mode,
        "status": AgentStatus.RUNNING,
        "execution_log": state.get("execution_log", []) + [f"Mode detected: {mode.value}"]
    }


# ═══════════════════════════════════════════════════════════════
# Node 2: RAG Retrieval
# ═══════════════════════════════════════════════════════════════

def rag_retrieval(state: AgentState) -> AgentState:
    """
    Retrieve test case description and steps from RAG.
    
    Uses RAG tool to get:
    - Test description
    - Test steps list
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with test_description and test_steps
        
    Retrieve test case description and steps from RAG.
    
    Automatically refreshes index to pick up new Excel files.
    """
    test_id = state.get("test_id")
    logger.info(f"📚 Retrieving test case: {test_id}")
    
    try:
        # CRITICAL: Refresh index to pick up any new Excel files
        toolkit.rag.refresh_index()
        
        # Get test description from RAG
        test_data = toolkit.rag.get_test_description(test_id)
        
        if test_data:
            description = test_data.get("description", "")
            steps = test_data.get("steps", [])
            
            logger.info(f"✅ Retrieved test: {test_data.get('title', test_id)}")
            logger.info(f"✅ Steps: {len(steps)}")
            
            return {
                **state,
                "test_description": description,
                "test_steps": steps,
                "total_steps": len(steps),
                "execution_log": state.get("execution_log", []) + [
                    f"Test case retrieved: {test_id}",
                    f"Total steps: {len(steps)}"
                ]
            }
        else:
            logger.error(f"❌ Test case not found: {test_id}")
            logger.error("   Please ensure the Excel file containing this test case is in data/test_cases/")
            return {
                **state,
                "test_description": None,
                "test_steps": [],
                "total_steps": 0,
                "status": AgentStatus.FAILURE,
                "should_continue": False,
                "errors": state.get("errors", []) + [
                    f"Test case not found: {test_id}. Ensure Excel file is in data/test_cases/ folder."
                ]
            }
    
    except Exception as e:
        logger.error(f"❌ RAG retrieval error: {e}")
        return {
            **state,
            "test_description": None,
            "test_steps": [],
            "total_steps": 0,
            "status": AgentStatus.FAILURE,
            "should_continue": False,
            "errors": state.get("errors", []) + [f"RAG retrieval error: {e}"]
        }


# ═══════════════════════════════════════════════════════════════
# Node 3: Check Learned Solution
# ═══════════════════════════════════════════════════════════════

def check_learned(state: AgentState) -> AgentState:
    """
    Check if learned solution exists for this test.
    
    Queries RAG for previously successful test execution.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with has_learned_solution and learned_solution
    """
    test_id = state.get("test_id")
    use_learned = state.get("use_learned", True)
    
    logger.info(f"🧠 Checking learned solution: {test_id}")
    
    if not use_learned:
        logger.info("⏭️ Learned solutions disabled")
        return {
            **state,
            "has_learned_solution": False,
            "learned_solution": None
        }
    
    try:
        # Check for learned solution
        solution = toolkit.rag.get_learned_solution(test_id)
        
        if solution:
            logger.info(f"✅ Found learned solution for {test_id}")
            logger.info(f"   Success rate: {solution.get('success_rate', 'N/A')}")
            
            return {
                **state,
                "has_learned_solution": True,
                "learned_solution": solution,
                "execution_log": state.get("execution_log", []) + [
                    f"Learned solution found: {test_id}",
                    f"Success rate: {solution.get('success_rate', 'N/A')}"
                ]
            }
        else:
            logger.info(f"ℹ️ No learned solution for {test_id}")
            return {
                **state,
                "has_learned_solution": False,
                "learned_solution": None
            }
    
    except Exception as e:
        logger.error(f"❌ Check learned error: {e}")
        return {
            **state,
            "has_learned_solution": False,
            "learned_solution": None,
            "errors": state.get("errors", []) + [f"Check learned error: {e}"]
        }


# ═══════════════════════════════════════════════════════════════
# Node 4: Capture Screen
# ═══════════════════════════════════════════════════════════════

def capture_screen(state: AgentState) -> AgentState:
    """
    Capture current device screen.

    Uses screenshot tool to capture device display.

    Args:
        state: Current agent state

    Returns:
        Updated state with current_screenshot path
    """
    # Check for stop/pause
    should_continue, stopped_state = _check_execution_control(state)
    if not should_continue:
        return stopped_state

    logger.info("📸 Capturing screen...")

    try:
        # Capture screenshot
        screenshot_path = toolkit.screenshot.capture()
        
        if screenshot_path:
            logger.info(f"✅ Screenshot captured: {screenshot_path}")
            
            return {
                **state,
                "current_screenshot": screenshot_path,
                "execution_log": state.get("execution_log", []) + [
                    f"Screenshot captured: {screenshot_path}"
                ]
            }
        else:
            logger.error("❌ Screenshot capture failed")
            return {
                **state,
                "current_screenshot": None,
                "errors": state.get("errors", []) + ["Screenshot capture failed"]
            }
    
    except Exception as e:
        logger.error(f"❌ Capture screen error: {e}")
        return {
            **state,
            "current_screenshot": None,
            "errors": state.get("errors", []) + [f"Capture screen error: {e}"]
        }


# ═══════════════════════════════════════════════════════════════
# Node 5: AI Analyze Screen
# ═══════════════════════════════════════════════════════════════

def ai_analyze(state: AgentState) -> AgentState:
    """
    Analyze screen using VIO Cloud AI Vision.

    Uses vision tool to:
    - Describe screen contents
    - Identify interactive elements
    - Determine current app state

    Args:
        state: Current agent state

    Returns:
        Updated state with screen_analysis and detected_elements
    """
    # Check execution control (stop/pause) FIRST
    should_continue, stopped_state = _check_execution_control(state)
    if not should_continue:
        return stopped_state

    screenshot_path = state.get("current_screenshot")
    current_step_desc = ""
    
    # Get current step description if in test mode
    if state.get("current_mode") == AgentMode.TEST_EXECUTION:
        steps = state.get("test_steps", [])
        current_idx = state.get("current_step", 0)
        if steps and current_idx < len(steps):
            current_step_desc = steps[current_idx]
    elif state.get("current_mode") == AgentMode.STANDALONE:
        current_step_desc = state.get("standalone_command", "")
    
    logger.info("🔍 Analyzing screen with AI Vision...")
    logger.info(f"   Context: {str(current_step_desc)[:100] if current_step_desc else 'General analysis'}")
    
    if not screenshot_path:
        logger.error("❌ No screenshot available for analysis")
        return {
            **state,
            "errors": state.get("errors", []) + ["No screenshot for AI analysis"]
        }
    
    try:
        # Analyze with AI Vision
        question = f"Analyze this Android Automotive screen. Current goal: {current_step_desc}. List all visible buttons, text, and interactive elements."
        
        analysis = toolkit.vision.analyze_screen_with_ai(screenshot_path, question)
        
        if analysis and analysis.summary:
            logger.info(f"✅ AI Analysis complete")
            logger.debug(f"   Summary: {analysis.summary[:200]}")
            
            # Extract all text elements with OCR (safely)
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
                        "text": elem.text,
                        "x": elem.x,
                        "y": elem.y,
                        "confidence": elem.confidence
                    }
                    for elem in detected_elements
                    if hasattr(elem, 'text')
                ],
                "execution_log": state.get("execution_log", []) + [
                    "AI screen analysis complete",
                    f"Detected {len(detected_elements)} text elements"
                ]
            }
        else:
            logger.warning("⚠️ AI analysis returned empty result")
            return {
                **state,
                "screen_analysis": "Analysis failed",
                "detected_elements": []
            }
    
    except Exception as e:
        logger.error(f"❌ AI analyze error: {e}")
        return {
            **state,
            "screen_analysis": None,
            "detected_elements": [],
            "errors": state.get("errors", []) + [f"AI analyze error: {e}"]
        }


# ═══════════════════════════════════════════════════════════════
# Node 6: Plan Action - FULLY AI-DRIVEN (NO HARDCODED LOGIC)
# ═══════════════════════════════════════════════════════════════

def plan_action(state: AgentState) -> AgentState:
    """
    Plan next action - FULLY AI-DRIVEN (ZERO HARDCODING).

    Uses AI for:
    1. Target extraction from goal
    2. Action type determination
    3. Navigation decisions

    NO hardcoded word lists.
    NO assumptions about filler words or action words.
    Completely dynamic.
    """
    # Check execution control (stop/pause) FIRST
    should_continue, stopped_state = _check_execution_control(state)
    if not should_continue:
        return stopped_state

    screen_analysis = state.get("screen_analysis", "")
    detected_elements = state.get("detected_elements", [])
    screenshot_path = state.get("current_screenshot")
    
    # Get current goal
    goal = ""
    current_idx = state.get("current_step", 0)
    steps = state.get("test_steps", [])
    
    if state.get("current_mode") == AgentMode.TEST_EXECUTION:
        if steps and current_idx < len(steps):
            goal = steps[current_idx]
    elif state.get("current_mode") == AgentMode.STANDALONE:
        if steps and current_idx < len(steps):
            goal = steps[current_idx]
        else:
            goal = state.get("standalone_command", "")
    
    logger.info("🎯 Planning action...")
    logger.info(f"   Goal: {goal}")
    
    if not goal:
        logger.error("❌ No goal defined")
        return {
            **state,
            "errors": state.get("errors", []) + ["No goal"]
        }
    
    try:
        from backend.config import settings
        import requests
        import json
        import re
        
        # STEP 1: Ask AI to extract target element name
        logger.info("🤖 Asking AI to extract target element name...")
        
        extraction_prompt = f"""
Extract the target element/app name from this goal:

GOAL: {goal}

Return ONLY the element/app name (1-2 words maximum).

Examples:
- "Tap Settings app in drawer" → "Settings"
- "Click HVAC icon" → "HVAC"
- "Press Bluetooth option in menu" → "Bluetooth"
- "Open Media player" → "Media"
- "Select the Phone app" → "Phone"

Respond with just the name, nothing else.
"""
        
        payload = {
            "username": settings.vio_username,
            "token": settings.vio_api_token,
            "type": "QUESTION",
            "payload": extraction_prompt,
            "vio_model": "Default",
            "ai_model": settings.vio_primary_model,
            "knowledge": False,
            "webSearch": False,
            "reason": False
        }
        
        response = requests.post(
            f"{settings.vio_base_url}/message",
            json=payload,
            verify=settings.vio_verify_ssl,
            timeout=settings.vio_timeout
        )
        
        response.raise_for_status()
        result = response.json()
        extracted_target = result.get('message', result.get('response', goal)).strip()
        
        # Clean AI response (remove quotes, extra text)
        extracted_target = extracted_target.replace('"', '').replace("'", '').strip()
        # Take first line if multi-line
        extracted_target = extracted_target.split('\n')[0].strip()
        # Remove "The answer is:" or similar prefixes
        if ':' in extracted_target:
            extracted_target = extracted_target.split(':')[-1].strip()
        
        # Limit to 2 words max
        words = extracted_target.split()
        if len(words) > 2:
            extracted_target = ' '.join(words[:2])
        
        logger.info(f"✅ AI extracted target: '{extracted_target}'")
        
        # STEP 2: Try to find element with vision tool
        logger.info(f"🔍 Trying vision tool (searches entire screen)")
        
        try:
            coords_result = toolkit.vision.find_element_with_ai(screenshot_path, extracted_target)
            
            if coords_result:
                coords = (coords_result.x, coords_result.y)
                logger.info(f"✅ Found '{extracted_target}' at {coords}")
                
                return {
                    **state,
                    "planned_action": f"tap {extracted_target}",
                    "action_type": "tap",
                    "target_element": extracted_target,
                    "target_coordinates": coords,
                    "action_parameters": {"reasoning": "Found via vision tool"},
                    "execution_log": state.get("execution_log", []) + [
                        f"AI extracted: {extracted_target}",
                        f"Vision found: {coords}"
                    ]
                }
            else:
                logger.warning(f"⚠️ Vision tool couldn't find '{extracted_target}'")
                logger.info("   Asking AI for action plan...")
                # Fall through to full AI planning
        
        except Exception as e:
            logger.error(f"❌ Vision tool error: {e}")
            # Fall through to full AI planning
        
        # STEP 3: Full AI planning (when vision fails or for non-tap actions)
        logger.info("🤖 Asking AI to plan action...")
        
        planning_prompt = f"""
Analyze this Android Automotive screen and determine the action.

GOAL: {goal}

SCREEN ANALYSIS:
{screen_analysis}

DETECTED ELEMENTS:
{", ".join([elem.get("text", "") if isinstance(elem, dict) else str(elem) for elem in detected_elements]) if detected_elements else "No text elements"}

Determine the appropriate action.

IMPORTANT:
- If element is visible on current screen, use "tap" action
- Only use "press_key" or navigation if element genuinely not visible
- Don't make assumptions about element locations

Respond with JSON:
{{
    "action_type": "tap|swipe|input_text|press_key",
    "target_element": "element to interact with (just the name, 1-2 words)",
    "reasoning": "brief explanation"
}}
"""
        
        payload = {
            "username": settings.vio_username,
            "token": settings.vio_api_token,
            "type": "QUESTION",
            "payload": planning_prompt,
            "vio_model": "Default",
            "ai_model": settings.vio_primary_model,
            "knowledge": False,
            "webSearch": False,
            "reason": False
        }
        
        response = requests.post(
            f"{settings.vio_base_url}/message",
            json=payload,
            verify=settings.vio_verify_ssl,
            timeout=settings.vio_timeout
        )
        
        response.raise_for_status()
        result = response.json()
        message = result.get('message', result.get('response', str(result)))
        
        # Parse JSON
        json_match = re.search(r'\{[^{}]*"action_type"[^{}]*\}', message, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{.*?\}', message, re.DOTALL)
        
        if json_match:
            plan = json.loads(json_match.group())
            
            action_type = plan.get('action_type', 'tap')
            target_element = plan.get('target_element', extracted_target)
            reasoning = plan.get('reasoning', 'AI planned')
            
            logger.info(f"✅ AI planned: {action_type}")
            logger.info(f"   Target: {target_element}")
            logger.info(f"   Reasoning: {reasoning}")
            
            # Find coordinates for tap actions
            coordinates = None
            if action_type in ['tap', 'double_tap', 'long_press']:
                try:
                    coords = toolkit.vision.find_element_with_ai(screenshot_path, target_element)
                    if coords:
                        coordinates = (coords.x, coords.y)
                        logger.info(f"   Coordinates: {coordinates}")
                except Exception as e:
                    logger.error(f"   Coordinate search failed: {e}")
            
            return {
                **state,
                "planned_action": f"{action_type} on {target_element}",
                "action_type": action_type,
                "target_element": target_element,
                "target_coordinates": coordinates,
                "action_parameters": {"reasoning": reasoning},
                "execution_log": state.get("execution_log", []) + [
                    f"Action: {action_type}",
                    f"Target: {target_element}",
                    f"Coords: {coordinates}"
                ]
            }
        
        # STEP 4: Fallback - use extracted target
        logger.warning("⚠️ JSON parse failed - using extracted target")
        
        fallback_coords = None
        if screenshot_path and extracted_target:
            try:
                coords = toolkit.vision.find_element_with_ai(screenshot_path, extracted_target)
                if coords:
                    fallback_coords = (coords.x, coords.y)
                    logger.info(f"✅ Fallback found: {fallback_coords}")
            except Exception as e:
                logger.error(f"Fallback failed: {e}")
        
        return {
            **state,
            "planned_action": f"tap {extracted_target}",
            "action_type": "tap",
            "target_element": extracted_target,
            "target_coordinates": fallback_coords,
            "action_parameters": {"reasoning": "Fallback with AI-extracted target"},
            "execution_log": state.get("execution_log", []) + [
                f"Fallback: tap {extracted_target}",
                f"Coords: {fallback_coords}"
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Plan action error: {e}")
        return {
            **state,
            "planned_action": None,
            "errors": state.get("errors", []) + [f"Plan action error: {e}"]
        }

# ═══════════════════════════════════════════════════════════════
# PART 2: EXECUTION & VERIFICATION NODES
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# Node 7: Direct Execute
# ═══════════════════════════════════════════════════════════════

def direct_execute(state: AgentState) -> AgentState:
    """
    Execute action from learned solution.

    Captures screenshot BEFORE action for verification comparison.
    """
    # Check for stop/pause before execution
    should_continue, stopped_state = _check_execution_control(state)
    if not should_continue:
        return stopped_state

    current_step = state.get("current_step", 0)
    learned_solution = state.get("learned_solution", {})
    learned_steps = learned_solution.get("steps", [])

    logger.info(f"⚡ Direct execute step {current_step}")
    
    # ═══════════════════════════════════════════════════════════
    # CRITICAL: Capture screenshot BEFORE action for verification
    # ═══════════════════════════════════════════════════════════
    before_screenshot = state.get("current_screenshot")
    if not before_screenshot:
        try:
            before_screenshot = toolkit.screenshot.capture()
            logger.info(f"   📸 Captured before screenshot for verification")
        except Exception as e:
            logger.warning(f"   ⚠️ Could not capture before screenshot: {e}")
    
    # Find the learned step for current step - EXACT MATCH ONLY
    learned_step = None
    for step in learned_steps:
        step_num = step.get("step")
        if step_num == current_step:
            learned_step = step
            break
    
    if not learned_step:
        logger.warning(f"⚠️ No learned step data for step {current_step}")
        return {
            **state,
            "current_screenshot": before_screenshot,  # Preserve screenshot
            "use_learned": False,
            "execution_log": state.get("execution_log", []) + [
                f"No learned data for step {current_step}, using AI for this step"
            ]
        }
    
    action_type = learned_step.get("action")
    target_element = learned_step.get("target_element")
    input_text = learned_step.get("input_text")
    
    logger.info(f"   Action: {action_type}")
    logger.info(f"   Target: {target_element}")
    
    # Handle press key actions (no coordinates needed)
    if action_type and action_type.startswith("press_"):
        try:
            key_name = action_type.replace("press_", "")
            result = toolkit.adb.press_key(key_name)
            
            logger.info(f"   ✅ Press {key_name}: {'Success' if result.success else 'Failed'}")
            
            return {
                **state,
                "current_screenshot": before_screenshot,  # For verification comparison
                "last_action_result": result,
                "action_success": result.success,
                "planned_action": action_type,
                "action_type": action_type,
                "target_element": target_element,
                "use_learned": True,
                "execution_log": state.get("execution_log", []) + [
                    f"Direct execute: {action_type} - {'Success' if result.success else 'Failed'}"
                ]
            }
        except Exception as e:
            logger.error(f"❌ Direct press error: {e}")
    
    # For actions needing coordinates
    coordinates = None
    
    # Priority 1: Device profile (dynamically learned)
    if target_element:
        try:
            from backend.tools import DeviceCoordinateTool
            coord_tool = DeviceCoordinateTool()
            profile_coords = coord_tool.get_coordinate(target_element)
            
            if profile_coords:
                coordinates = profile_coords
                logger.info(f"   📍 Using stored coordinates: {coordinates}")
        except Exception as e:
            logger.debug(f"Device profile lookup: {e}")
    
    # Priority 2: Stored coordinates in learned step
    if not coordinates:
        stored_coords = learned_step.get("coordinates")
        if stored_coords:
            if isinstance(stored_coords, (list, tuple)) and len(stored_coords) >= 2:
                coordinates = (stored_coords[0], stored_coords[1])
            elif isinstance(stored_coords, dict):
                coordinates = (stored_coords.get("x"), stored_coords.get("y"))
            
            if coordinates and coordinates[0] is not None:
                logger.info(f"   📍 Using stored coordinates: {coordinates}")
    
    # Execute tap action
    if action_type == "tap" and coordinates:
        try:
            x, y = int(coordinates[0]), int(coordinates[1])
            result = toolkit.adb.tap(x, y)
            
            logger.info(f"   ✅ Tap at ({x}, {y}): {'Success' if result.success else 'Failed'}")
            
            return {
                **state,
                "current_screenshot": before_screenshot,  # For verification comparison
                "last_action_result": result,
                "action_success": result.success,
                "planned_action": "tap",
                "action_type": "tap",
                "target_element": target_element,
                "target_coordinates": {"x": x, "y": y, "source": "learned"},
                "use_learned": True,
                "execution_log": state.get("execution_log", []) + [
                    f"Direct execute: tap at ({x}, {y}) on '{target_element}'"
                ]
            }
        except Exception as e:
            logger.error(f"❌ Direct tap error: {e}")
    
    # Execute input_text action
    elif action_type == "input_text" and input_text:
        try:
            result = toolkit.adb.input_text(input_text)
            
            logger.info(f"   ✅ Input text: {'Success' if result.success else 'Failed'}")
            
            return {
                **state,
                "current_screenshot": before_screenshot,
                "last_action_result": result,
                "action_success": result.success,
                "planned_action": "input_text",
                "action_type": "input_text",
                "action_parameters": {"text": input_text},
                "use_learned": True,
                "execution_log": state.get("execution_log", []) + [
                    f"Direct execute: input_text"
                ]
            }
        except Exception as e:
            logger.error(f"❌ Direct input error: {e}")
    
    # Execute swipe action
    elif action_type == "swipe" and coordinates:
        try:
            x, y = int(coordinates[0]), int(coordinates[1])
            result = toolkit.adb.swipe(
                start_x=x,
                start_y=y,
                end_x=x,
                end_y=y - 200,
                duration=300
            )
            
            return {
                **state,
                "current_screenshot": before_screenshot,
                "last_action_result": result,
                "action_success": result.success,
                "planned_action": "swipe",
                "action_type": "swipe",
                "use_learned": True,
                "execution_log": state.get("execution_log", []) + [
                    f"Direct execute: swipe"
                ]
            }
        except Exception as e:
            logger.error(f"❌ Direct swipe error: {e}")
    
    # Fall back to AI for this step only
    logger.warning(f"⚠️ Cannot direct execute step {current_step}, using AI for this step")
    
    return {
        **state,
        "current_screenshot": before_screenshot,
        "use_learned": False,
        "execution_log": state.get("execution_log", []) + [
            f"Step {current_step}: using AI detection (missing coordinates)"
        ]
    }


# ═══════════════════════════════════════════════════════════════
# Node 8: Execute ADB Action
# ═══════════════════════════════════════════════════════════════

def execute_adb(state: AgentState) -> AgentState:
    """
    Execute ADB action - FULLY AI-DRIVEN.

    NO hardcoded keyword checks.
    Just trust the action_type that was determined by AI.
    """
    # Check for stop/pause before execution
    should_continue, stopped_state = _check_execution_control(state)
    if not should_continue:
        return stopped_state

    action_type = state.get("action_type")
    target_element = state.get("target_element")
    coordinates = state.get("target_coordinates")
    parameters = state.get("action_parameters", {})

    logger.info(f"⚡ Executing: {action_type}")
    logger.info(f"   Target: {target_element}")
    logger.info(f"   Coords: {coordinates}")
    
    try:
        result = None
        
        # Extract coordinates if needed (handle both dict and tuple)
        def get_coords(coords):
            if isinstance(coords, dict):
                return coords.get("x"), coords.get("y")
            elif isinstance(coords, (list, tuple)) and len(coords) >= 2:
                return coords[0], coords[1]
            return None, None
        
        # ═══════════════════════════════════════════════════════════
        # FULLY DYNAMIC: Trust the action_type directly
        # ═══════════════════════════════════════════════════════════
        
        if action_type == "tap":
            if coordinates:
                x, y = get_coords(coordinates)
                if x is not None and y is not None:
                    result = toolkit.tap(x, y)
                else:
                    return {
                        **state,
                        "action_success": False,
                        "errors": state.get("errors", []) + ["Invalid coordinates"]
                    }
            else:
                return {
                    **state,
                    "action_success": False,
                    "errors": state.get("errors", []) + ["No coordinates for tap"]
                }
        
        elif action_type == "double_tap":
            if coordinates:
                x, y = get_coords(coordinates)
                if x is not None and y is not None:
                    result = toolkit.double_tap(x, y)
            else:
                return {
                    **state,
                    "action_success": False,
                    "errors": state.get("errors", []) + ["No coordinates"]
                }
        
        elif action_type == "long_press":
            if coordinates:
                x, y = get_coords(coordinates)
                if x is not None and y is not None:
                    duration_ms = parameters.get("duration_ms", 1000)
                    result = toolkit.long_press(x, y, duration_ms)
            else:
                return {
                    **state,
                    "action_success": False,
                    "errors": state.get("errors", []) + ["No coordinates"]
                }
        
        # ═══════════════════════════════════════════════════════════
        # CRITICAL: Trust action_type directly (NO KEYWORD CHECKS)
        # ═══════════════════════════════════════════════════════════
        
        elif action_type == "press_home":
            logger.info("🏠 Pressing HOME (AI determined)")
            result = toolkit.press_home()
        
        elif action_type == "press_back":
            logger.info("🔙 Pressing BACK (AI determined)")
            result = toolkit.press_back()
        
        elif action_type == "press_enter":
            logger.info("↩️ Pressing ENTER (AI determined)")
            result = toolkit.press_enter()
        
        # ═══════════════════════════════════════════════════════════
        # Generic press_key: Use AI to determine which key
        # ═══════════════════════════════════════════════════════════
        
        elif action_type == "press_key":
            # Ask AI which key to press based on target_element
            logger.info(f"🤖 Using AI to determine key for: {target_element}")
            
            from backend.config import settings
            import requests
            import json
            import re
            
            key_prompt = f"""
Given target element: "{target_element}"

Which Android key should be pressed?

Respond with ONE of: HOME, BACK, ENTER, MENU, RECENT_APPS

Just the key name, nothing else.
"""
            
            try:
                payload = {
                    "username": settings.vio_username,
                    "token": settings.vio_api_token,
                    "type": "QUESTION",
                    "payload": key_prompt,
                    "vio_model": "Default",
                    "ai_model": settings.vio_primary_model,
                    "knowledge": False,
                    "webSearch": False,
                    "reason": False
                }
                
                response = requests.post(
                    f"{settings.vio_base_url}/message",
                    json=payload,
                    verify=settings.vio_verify_ssl,
                    timeout=settings.vio_timeout
                )
                
                response.raise_for_status()
                ai_result = response.json()
                key_name = ai_result.get('message', ai_result.get('response', 'BACK')).strip().upper()
                
                # Remove any extra text
                key_name = re.sub(r'[^A-Z_]', '', key_name)
                
                logger.info(f"🤖 AI determined key: {key_name}")
                
                # Execute based on AI decision
                if 'HOME' in key_name:
                    result = toolkit.press_home()
                elif 'BACK' in key_name:
                    result = toolkit.press_back()
                elif 'ENTER' in key_name:
                    result = toolkit.press_enter()
                elif 'MENU' in key_name:
                    result = toolkit.adb.press_key("menu")
                elif 'RECENT' in key_name:
                    result = toolkit.adb.press_key("recent_apps")
                else:
                    # Default to back if AI response unclear
                    logger.warning(f"⚠️ Unclear AI response, defaulting to BACK")
                    result = toolkit.press_back()
            
            except Exception as e:
                logger.error(f"❌ AI key determination failed: {e}")
                # Fallback to back
                result = toolkit.press_back()
        
        elif action_type == "swipe":
            # Auto-generate swipe coordinates based on screen size
            try:
                from backend.tools.adb_tool import ADBTool
                adb = ADBTool()
                screen_size = adb.get_screen_dimensions()
                screen_width, screen_height = screen_size if screen_size else (1408, 792)
            except:
                screen_width, screen_height = 1408, 792
            
            retry_count = state.get("retry_count", 0)
            swipe_attempt = retry_count % 4
            
            # Cycle through directions
            directions = [
                ("RIGHT", (int(screen_width * 0.2), int(screen_height * 0.5), int(screen_width * 0.8), int(screen_height * 0.5))),
                ("LEFT", (int(screen_width * 0.8), int(screen_height * 0.5), int(screen_width * 0.2), int(screen_height * 0.5))),
                ("DOWN", (int(screen_width * 0.5), int(screen_height * 0.2), int(screen_width * 0.5), int(screen_height * 0.8))),
                ("UP", (int(screen_width * 0.5), int(screen_height * 0.8), int(screen_width * 0.5), int(screen_height * 0.2)))
            ]
            
            direction, (start_x, start_y, end_x, end_y) = directions[swipe_attempt]
            
            logger.info(f"📱 Swipe {direction}: ({start_x},{start_y}) → ({end_x},{end_y})")
            result = toolkit.swipe(start_x, start_y, end_x, end_y)
        
        elif action_type == "swipe_up":
            result = toolkit.swipe_up(parameters.get("distance", 500))
        
        elif action_type == "swipe_down":
            result = toolkit.swipe_down(parameters.get("distance", 500))
        
        elif action_type == "input_text":
            text = parameters.get("text", "")
            if text:
                result = toolkit.input_text(text)
            else:
                return {
                    **state,
                    "action_success": False,
                    "errors": state.get("errors", []) + ["No text for input"]
                }
        
        elif action_type == "verify":
            return {
                **state,
                "action_success": True,
                "last_action_result": {"action": "verify", "success": True}
            }
        
        else:
            logger.warning(f"⚠️ Unknown action type: {action_type}")
            return {
                **state,
                "action_success": False,
                "errors": state.get("errors", []) + [f"Unknown action: {action_type}"]
            }
        
        success = result.success if result else False
        
        logger.info(f"{'✅' if success else '❌'} {action_type}: {'Success' if success else 'Failed'}")
        
        return {
            **state,
            "last_action_result": {
                "action": action_type,
                "target": target_element,
                "coordinates": coordinates,
                "success": success,
                "output": result.output if result else None,
                "error": result.error if result else None
            },
            "action_success": success,
            "execution_log": state.get("execution_log", []) + [
                f"Executed: {action_type} - {'Success' if success else 'Failed'}"
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Execute ADB error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            **state,
            "action_success": False,
            "last_action_result": {"error": str(e)},
            "errors": state.get("errors", []) + [f"Execute error: {e}"]
        }


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS FOR SSIM VERIFICATION
# ═══════════════════════════════════════════════════════════════

def _get_reference_image_name(state: AgentState) -> Optional[str]:
    """
    Get reference image name for current test step.
    
    FULLY DYNAMIC: Uses AI to determine expected reference image based on
    the target element that was just tapped.
    
    Priority:
    1. AI determines reference from target_element (DYNAMIC)
    2. Explicit reference_image in step metadata (if configured)
    3. AI determines reference from step description (FALLBACK)
    
    Returns:
        Reference image name or None if not applicable
    """
    # PRIORITY 1: AI determines from target element (what we just tapped)
    target_element = state.get("target_element", "")
    
    if target_element:
        logger.debug(f"🎯 Target element: '{target_element}'")
        
        # Ask AI to determine expected reference image
        reference_name = _parse_reference_name_from_target(target_element)
        
        if reference_name:
            logger.info(f"📸 AI mapped '{target_element}' → '{reference_name}'")
            return reference_name
        else:
            logger.warning(f"⚠️ AI could not map target '{target_element}'")
    
    # PRIORITY 2: Explicit reference image in step metadata (if configured)
    current_step = state.get("current_step", 0)
    steps = state.get("test_steps", [])
    
    if current_step < len(steps):
        step_info = steps[current_step]
        
        if isinstance(step_info, dict) and "reference_image" in step_info:
            reference_name = step_info["reference_image"]
            logger.info(f"📸 Explicit reference from metadata: '{reference_name}'")
            return reference_name
    
    # PRIORITY 3: AI determines from step description (FALLBACK)
    if current_step < len(steps):
        step_info = steps[current_step]
        step_text = step_info if isinstance(step_info, str) else step_info.get("description", "")
        
        if step_text:
            logger.debug(f"📝 Falling back to step description: '{step_text}'")
            
            # Ask AI to determine reference from step description
            reference_name = _parse_reference_name_from_target(step_text)
            
            if reference_name:
                logger.info(f"📸 AI mapped from description → '{reference_name}'")
                return reference_name
    
    # No reference image could be determined
    logger.warning(f"⚠️ No reference image found (will use pixel/AI verification)")
    return None


def _parse_reference_name_from_step(step_description: str) -> Optional[str]:
    """
    Parse reference image name from step description.
    
    Examples:
        "Open app launcher" -> "app_launcher_opened"
        "Navigate to Settings" -> "settings_opened"
        "Click Bluetooth option" -> "bluetooth_opened"
    
    Returns:
        Suggested reference image name
    """
    desc_lower = step_description.lower()
    
    # Common patterns
    patterns = {
        'app launcher': 'app_launcher_opened',
        'settings': 'settings_opened',
        'bluetooth': 'bluetooth_opened',
        'notifications': 'notifications_opened',
        'display': 'display_opened',
        'sound': 'sound_opened',
        'network': 'network_opened',
        'media': 'media_opened',
        'phone': 'phone_opened',
        'hvac': 'hvac_opened',
        'climate': 'climate_opened'
    }
    
    # Check for matches
    for keyword, reference_name in patterns.items():
        if keyword in desc_lower:
            return reference_name
    
    # Default: None (no automatic detection)
    return None

def _parse_reference_name_from_target(target_element: str) -> Optional[str]:
    """
    FULLY DYNAMIC: Ask AI to determine expected reference image name.
    
    NO hardcoded patterns - AI analyzes the target element and determines
    what screen state we should expect after tapping it.
    
    Examples:
        AI Input: "app launcher"
        AI Output: "app_launcher_opened"
        
        AI Input: "Settings"
        AI Output: "settings_opened"
        
        AI Input: "Bluetooth toggle"
        AI Output: "bluetooth_opened"
    
    Args:
        target_element: The element that was just tapped/interacted with
        
    Returns:
        Expected reference image name determined by AI
    """
    if not target_element:
        return None
    
    try:
        from backend.config import settings
        import requests
        import re
        
        logger.debug(f"🤖 Asking AI to determine reference image for '{target_element}'")
        
        # Ask AI to determine the expected reference image name
        ai_prompt = f"""
Given that a user just tapped on "{target_element}" in an Android Automotive UI, what screen state should we expect?

Respond with ONLY the reference image name in this format: <element_name>_opened

Rules:
- Use lowercase with underscores
- End with "_opened"
- Be concise (2-3 words max)
- Examples:
  * Tapped "app launcher" → "app_launcher_opened"
  * Tapped "Settings" → "settings_opened"
  * Tapped "Bluetooth" → "bluetooth_opened"
  * Tapped "Media player" → "media_opened"
  * Tapped "HVAC controls" → "hvac_opened"

Target tapped: "{target_element}"
Expected reference image name:"""

        payload = {
            "username": settings.vio_username,
            "token": settings.vio_api_token,
            "type": "QUESTION",
            "payload": ai_prompt,
            "vio_model": "Default",
            "ai_model": settings.vio_primary_model,
            "knowledge": False,
            "webSearch": False,
            "reason": False
        }
        
        response = requests.post(
            f"{settings.vio_base_url}/message",
            json=payload,
            verify=settings.vio_verify_ssl,
            timeout=settings.vio_timeout
        )
        
        response.raise_for_status()
        result = response.json()
        ai_response = result.get('message', result.get('response', '')).strip()
        
        # Clean AI response
        ai_response = ai_response.replace('"', '').replace("'", '').strip()
        # Take first line if multi-line
        ai_response = ai_response.split('\n')[0].strip()
        # Remove common prefixes
        ai_response = re.sub(r'^(the answer is|expected reference image name|reference image):\s*', '', ai_response, flags=re.IGNORECASE).strip()
        
        # Validate format (should end with _opened and be lowercase with underscores)
        if ai_response and '_opened' in ai_response.lower():
            # Ensure proper format
            reference_name = ai_response.lower().replace(' ', '_')
            
            if not reference_name.endswith('_opened'):
                reference_name = reference_name + '_opened'
            
            logger.info(f"   🤖 AI determined reference: '{reference_name}'")
            return reference_name
        else:
            logger.warning(f"   ⚠️ AI response invalid format: '{ai_response}'")
            return None
    
    except Exception as e:
        logger.error(f"❌ AI reference mapping error: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# Node 9: Verify Result (WITH SSIM AS PRIMARY)
# ═══════════════════════════════════════════════════════════════

def verify_result(state: AgentState) -> AgentState:
    """
    Verify action result using COMPREHENSIVE VERIFICATION.

    PRIORITY:
    1. SSIM verification (PRIMARY - must pass to continue)
    2. Pixel change (SECONDARY - informational only)
    3. AI verification (SECONDARY - informational only)

    Also saves coordinates to device profile if from new AI detection.
    """
    # Check execution control (stop/pause) FIRST
    should_continue, stopped_state = _check_execution_control(state)
    if not should_continue:
        return stopped_state

    before_screenshot = state.get("current_screenshot")
    action_type = state.get("action_type")
    target_element = state.get("target_element", "")
    
    # Track if we're using learned solution
    using_learned = state.get("use_learned", False)
    
    logger.info("🔍 Verifying action result...")
    
    try:
        import time
        
        # Wait for UI to update
        time.sleep(1)
        
        # Capture new screenshot
        after_screenshot = toolkit.screenshot.capture()
        
        if not after_screenshot:
            logger.error("❌ Failed to capture verification screenshot")
            return {
                **state,
                "verification_result": {"verified": False, "reason": "Screenshot failed"},
                "errors": state.get("errors", []) + ["Verification screenshot failed"]
            }
        
        # Get reference image name for SSIM verification
        reference_image_name = _get_reference_image_name(state)

        # Get step information for verification tracking
        current_step = state.get("current_step", 0)
        test_id = state.get("test_id")
        test_steps = state.get("test_steps", [])
        step_description = ""
        if current_step < len(test_steps):
            step_description = test_steps[current_step]

        # ═════════════════════════════════════════════════════════
        # COMPREHENSIVE VERIFICATION (SSIM PRIMARY)
        # ═════════════════════════════════════════════════════════

        from backend.tools.verification_tool import VerificationTool
        verification_tool = VerificationTool()

        # Perform comprehensive verification with SSIM
        verification_result = verification_tool.comprehensive_verification(
            before_screenshot=before_screenshot,
            after_screenshot=after_screenshot,
            reference_image_name=reference_image_name,
            ssim_threshold=0.85,  # Configurable threshold
            test_id=test_id,
            step_number=current_step + 1,  # Convert to 1-based for display
            step_description=step_description
        )
        
        # Log results
        logger.info("=" * 60)
        logger.info("📊 VERIFICATION RESULTS")
        logger.info("=" * 60)
        
        # PRIMARY: SSIM Verification
        ssim_result = verification_result.get('ssim_verification')
        overall_passed = verification_result.get('overall_passed', False)
        
        if ssim_result:
            if ssim_result['passed']:
                logger.info(f"✅ PRIMARY (SSIM): PASSED - Similarity: {ssim_result['similarity']:.4f}")
            else:
                if ssim_result['reference_found']:
                    logger.error(f"❌ PRIMARY (SSIM): FAILED - Similarity: {ssim_result['similarity']:.4f} < {ssim_result['threshold']}")
                else:
                    logger.warning(f"⚠️ PRIMARY (SSIM): NO REFERENCE IMAGE - '{reference_image_name}'")
                    # If no reference image, fall back to pixel change for pass/fail
                    pixel_result = verification_result.get('pixel_verification')
                    if pixel_result and pixel_result['changed']:
                        logger.info(f"✅ FALLBACK: Screen changed {pixel_result['change_percentage']:.2f}%")
                        overall_passed = True
        
        # SECONDARY: Pixel Change (Informational)
        pixel_result = verification_result.get('pixel_verification')
        if pixel_result:
            logger.info(f"📊 SECONDARY (Pixel Change): {pixel_result['change_percentage']:.2f}% changed")
        
        # SECONDARY: AI Verification (Informational)
        ai_result = verification_result.get('ai_verification')
        if ai_result:
            logger.info(f"🤖 SECONDARY (AI Vision): {ai_result.get('reasoning', 'N/A')}")
        
        logger.info("=" * 60)
        
        # Update state based on PRIMARY verification
        if overall_passed:
            logger.info("✅ Verification PASSED - Proceeding to next step")
        else:
            logger.error("❌ Verification FAILED - Action did not achieve expected result")
        
        # ═════════════════════════════════════════════════════════
        # AUTO-LEARN COORDINATES (ONLY FOR NEW AI DETECTIONS)
        # ═════════════════════════════════════════════════════════
        if overall_passed:
            coordinates = state.get("target_coordinates")
            
            # Determine coordinate source
            coord_source = None
            coord_x = None
            coord_y = None
            
            if isinstance(coordinates, dict):
                coord_source = coordinates.get("source")
                coord_x = coordinates.get("x")
                coord_y = coordinates.get("y")
            elif isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
                coord_x = coordinates[0]
                coord_y = coordinates[1]
                coord_source = "detection"  # Assume new detection if no source info
            
            # CRITICAL: Only save coordinates if from new AI detection
            should_save_coordinates = (
                coord_source not in ["learned", "device_profile", "profile"] and
                not using_learned and
                target_element and
                coord_x is not None and
                coord_y is not None
            )
            
            if should_save_coordinates:
                target_lower = target_element.lower() if target_element else ""
                
                # Check if this is a non-texted icon that should be learned
                is_non_texted = any(keyword in target_lower for keyword in [
                    'launcher', 'drawer', 'grid', 'icon', 'home', 'back',
                    'hvac', 'temperature', 'temp', 'fan', 'climate',
                    'media', 'play', 'pause', 'volume', 'next', 'previous',
                    'phone', 'call', 'navigation', 'map', 'settings'
                ])
                
                if is_non_texted:
                    try:
                        profile_service = get_device_profile_service()
                        profile_service.add_coordinate(
                            icon_name=target_element,
                            x=int(coord_x),
                            y=int(coord_y),
                            verified_by="ai_detection"
                        )
                        logger.info(f"🎓 Learned coordinate for '{target_element}': ({coord_x}, {coord_y})")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to learn coordinate: {e}")
            elif using_learned or coord_source in ["learned", "device_profile", "profile"]:
                logger.debug(f"📍 Skipping coordinate save (source: {coord_source or 'learned_solution'})")

        # ═════════════════════════════════════════════════════════
        # RECORD STEP IN TEST HISTORY
        # ═════════════════════════════════════════════════════════
        execution_id = state.get("execution_id")
        if execution_id:
            try:
                from backend.services.test_history_service import get_test_history_service
                history_service = get_test_history_service()

                # Extract coordinates info
                coordinates = state.get("target_coordinates")
                coord_x, coord_y, coord_source = None, None, None
                if isinstance(coordinates, dict):
                    coord_x = coordinates.get("x")
                    coord_y = coordinates.get("y")
                    coord_source = coordinates.get("source", "unknown")
                elif isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
                    coord_x, coord_y = coordinates[0], coordinates[1]
                    coord_source = "detection"

                # Get comparison image path from SSIM result
                comparison_image_path = None
                if ssim_result and ssim_result.get("comparison_image"):
                    comparison_image_path = ssim_result.get("comparison_image")

                # Add step to history
                history_service.add_step(
                    execution_id=execution_id,
                    step_number=current_step + 1,  # 1-based
                    description=step_description,
                    goal=reference_image_name.replace("_", " ") if reference_image_name else None,
                    action_type=state.get("action_type"),
                    action_target=state.get("target_element"),
                    coordinates_x=int(coord_x) if coord_x else None,
                    coordinates_y=int(coord_y) if coord_y else None,
                    coordinate_source=coord_source,
                    used_learned_solution=using_learned,
                    before_screenshot_path=before_screenshot
                )

                # Update step with verification results
                history_service.update_step(
                    execution_id=execution_id,
                    step_number=current_step + 1,
                    status="success" if overall_passed else "failure",
                    ssim_score=ssim_result.get("similarity") if ssim_result else None,
                    ssim_passed=ssim_result.get("passed") if ssim_result else None,
                    ssim_threshold=ssim_result.get("threshold") if ssim_result else None,
                    reference_image_name=reference_image_name,
                    after_screenshot_path=after_screenshot,
                    comparison_image_path=comparison_image_path
                )
                logger.debug(f"📊 Recorded step {current_step + 1} in test history")
            except Exception as hist_err:
                logger.warning(f"⚠️ Failed to record step in history: {hist_err}")

        return {
            **state,
            "current_screenshot": after_screenshot,
            "verification_result": {
                "verified": overall_passed,
                "ssim_verification": ssim_result,
                "pixel_verification": pixel_result,
                "ai_verification": ai_result
            },
            # Re-enable learned solution for next step if we have one
            "use_learned": overall_passed and state.get("has_learned_solution", False),
            "execution_log": state.get("execution_log", []) + [
                f"Verification: {'Success' if overall_passed else 'Failed'}",
                f"SSIM: {ssim_result.get('similarity', 0):.4f}" if ssim_result else "SSIM: N/A",
                f"Pixel: {pixel_result.get('change_percentage', 0):.2f}%" if pixel_result else "Pixel: N/A"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Verify result error: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return {
            **state,
            "verification_result": {"verified": False, "error": str(e)},
            "errors": state.get("errors", []) + [f"Verify result error: {e}"]
        }


# ═══════════════════════════════════════════════════════════════
# Node 10: Save Learned Solution
# ═══════════════════════════════════════════════════════════════

def save_learned(state: AgentState) -> AgentState:
    """
    Save learned solution after successful test execution.

    Uses the captured executed_steps data - fully dynamic, no parsing.
    """
    # Check execution control (stop/pause) FIRST
    should_continue, stopped_state = _check_execution_control(state)
    if not should_continue:
        return stopped_state

    test_id = state.get("test_id")
    logger.info(f"💾 Saving learned solution: {test_id}")
    
    if not test_id:
        logger.warning("⚠️ No test_id to save")
        return state
    
    try:
        # Get the executed steps that were captured during execution
        executed_steps = state.get("executed_steps", [])
        
        if not executed_steps:
            logger.warning("⚠️ No executed steps to save, building from execution history")
            # Build steps from current execution data as fallback
            test_steps = state.get("test_steps", [])
            for i, step_desc in enumerate(test_steps):
                executed_steps.append({
                    "step": i + 1,
                    "description": step_desc,
                    "action": "tap",
                    "target_element": None,
                    "coordinates": None,
                    "input_text": None,
                    "success": True
                })
        
        # Log what we're saving
        logger.info(f"   Steps to save: {len(executed_steps)}")
        for step in executed_steps:
            logger.info(f"      Step {step.get('step')}: {step.get('action')} on '{step.get('target_element')}' at {step.get('coordinates')}")
        
        # Save to RAG
        success = toolkit.rag.save_learned_solution(
            test_id=test_id,
            title=state.get("test_description", f"Test {test_id}"),
            component="Learned",
            steps=executed_steps
        )
        
        if success:
            logger.info(f"✅ Learned solution saved: {test_id}")
            logger.info(f"   Steps saved: {len(executed_steps)}")
        else:
            logger.warning(f"⚠️ Failed to save learned solution: {test_id}")
        
        return {
            **state,
            "execution_log": state.get("execution_log", []) + [
                f"Learned solution saved: {test_id}" if success else "Failed to save learned solution"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Save learned error: {e}")
        return {
            **state,
            "errors": state.get("errors", []) + [f"Save learned error: {e}"]
        }


# ═══════════════════════════════════════════════════════════════
# Node 11: Next Step
# ═══════════════════════════════════════════════════════════════

def next_step(state: AgentState) -> AgentState:
    """
    Move to next test step after successful action.

    Preserves learned solution state for subsequent steps.
    """
    # Check for stop/pause before proceeding to next step
    should_continue, stopped_state = _check_execution_control(state)
    if not should_continue:
        return stopped_state

    current_step = state.get("current_step", 1)
    total_steps = state.get("total_steps", 1)
    test_steps = state.get("test_steps", [])

    logger.info(f"➡️ Moving to next step: {current_step}/{total_steps}")

    # CRITICAL FIX: Check if we just completed a HITL retry
    hitl_retry_pending = state.get("hitl_retry_pending", False)
    
    if hitl_retry_pending:
        logger.info(f"🔄 HITL retry completed - Staying at Step {current_step} to retry")
        
        # Capture executed step but DON'T increment
        executed_steps = list(state.get("executed_steps", []))
        
        return {
            **state,
            "current_step": current_step,  # ← STAY at current step
            "hitl_retry_pending": False,   # ← Clear retry flag
            "executed_steps": executed_steps,
            # Clear step-specific state to prepare for retry
            "planned_action": None,
            "action_type": None,
            "target_element": None,
            "target_coordinates": None,
            "action_parameters": None,
            "last_action_result": None,
            "action_success": None,
            "verification_result": None,
            "retry_count": 0,
            "has_learned_solution": state.get("has_learned_solution", False),
            "learned_solution": state.get("learned_solution"),
            "use_learned": True,
            "waiting_for_hitl": False,
            "hitl_guidance": None,
            "hitl_coordinates": None,
            "hitl_action_type": None,
            "hitl_applied": False,
            "execution_log": state.get("execution_log", []) + [
                f"Reset action completed - Ready to retry Step {current_step}"
            ]
        }
    
    # Capture the executed step data for learning
    executed_steps = list(state.get("executed_steps", []))
    
    # Get the step description
    step_description = ""
    if current_step <= len(test_steps):
        step_description = test_steps[current_step - 1]
    
    # Get coordinates in proper format
    target_coords = state.get("target_coordinates")
    coords_tuple = None
    if target_coords:
        if isinstance(target_coords, dict):
            coords_tuple = (target_coords.get("x"), target_coords.get("y"))
        elif hasattr(target_coords, 'x') and hasattr(target_coords, 'y'):
            coords_tuple = (target_coords.x, target_coords.y)
        elif isinstance(target_coords, (list, tuple)) and len(target_coords) >= 2:
            coords_tuple = (target_coords[0], target_coords[1])
    
    # Capture what was actually executed
    executed_step = {
        "step": current_step,  # Use 1-based indexing
        "description": step_description,
        "action": state.get("action_type") or state.get("planned_action"),
        "target_element": state.get("target_element"),
        "coordinates": coords_tuple,
        "input_text": state.get("action_parameters", {}).get("text") if state.get("action_parameters") else None,
        "success": state.get("action_success", True)
    }
    
    # Only add if we have valid action data
    if executed_step["action"]:
        executed_steps.append(executed_step)
        logger.info(f"   📝 Captured: {executed_step['action']} on '{executed_step['target_element']}' at {executed_step['coordinates']}")
    
    # Check if test complete
    if current_step >= total_steps:
        logger.info("✅ All test steps completed!")
        return {
            **state,
            "current_step": current_step + 1,
            "executed_steps": executed_steps,
            "status": AgentStatus.SUCCESS,
            "should_continue": True,
            # Preserve learned solution state
            "has_learned_solution": state.get("has_learned_solution", False),
            "learned_solution": state.get("learned_solution"),
            "use_learned": state.get("use_learned", True),
            # Clear HITL state
            "waiting_for_hitl": False,
            "hitl_guidance": None,
            "hitl_coordinates": None,
            "hitl_action_type": None,
            "hitl_applied": False,
            "retry_count": 0,
            "execution_log": state.get("execution_log", []) + [
                f"Step {current_step} completed",
                "All steps completed successfully"
            ]
        }
    
    logger.info(f"📝 Next step: {current_step + 1}/{total_steps}")
    
    return {
        **state,
        "current_step": current_step + 1,
        "executed_steps": executed_steps,
        # Clear step-specific state
        "planned_action": None,
        "action_type": None,
        "target_element": None,
        "target_coordinates": None,
        "action_parameters": None,
        "last_action_result": None,
        "action_success": None,
        "verification_result": None,
        "retry_count": 0,
        # IMPORTANT: Preserve learned solution state for next step
        "has_learned_solution": state.get("has_learned_solution", False),
        "learned_solution": state.get("learned_solution"),
        "use_learned": True,  # Re-enable for next step
        # Clear HITL state
        "waiting_for_hitl": False,
        "hitl_guidance": None,
        "hitl_coordinates": None,
        "hitl_action_type": None,
        "hitl_applied": False,
        "execution_log": state.get("execution_log", []) + [
            f"Step {current_step} completed"
        ]
    }


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTION: Determine Test Status
# ═══════════════════════════════════════════════════════════════

def determine_test_status(state: AgentState) -> str:
    """
    Determine final test status based on execution state.
    
    CRITICAL FIX: Uses current_step (which exists) instead of 
    completed_steps (which doesn't exist in state).
    
    Logic:
    1. If errors exist → "failed"
    2. If current_step < total_steps → "incomplete"
    3. If waiting for HITL → "waiting"
    4. Otherwise → "passed"
    
    Args:
        state: Current agent state
        
    Returns:
        Status string: "passed", "failed", "incomplete", or "waiting"
    """
    # Priority 1: Check for errors
    if state.get("errors"):
        return "failed"
    
    # Priority 2: Check completion
    # CRITICAL FIX: Use current_step, not completed_steps
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    if total_steps > 0 and current_step < total_steps:
        return "incomplete"
    
    # Priority 3: Check execution mode
    if state.get("execution_mode") == "hitl_waiting":
        return "waiting"
    
    # Default: All steps completed without errors
    if current_step >= total_steps and total_steps > 0:
        return "passed"
    
    # Unknown state
    return "unknown"


# ═══════════════════════════════════════════════════════════════
# Node 12: Log Results (WITH STATUS FIX)
# ═══════════════════════════════════════════════════════════════

def log_results(state: AgentState) -> AgentState:
    """
    Log final execution results.
    
    FIXED: Correctly determines final status (passed/failed/incomplete/waiting)
    instead of always returning "running".
    
    Saves execution summary and results to file.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with correct status
    """
    test_id = state.get("test_id")
    execution_log = state.get("execution_log", [])
    errors = state.get("errors", [])
    
    logger.info("📊 Logging execution results...")
    
    # ═══════════════════════════════════════════════════════════
    # FIX: Determine final status correctly
    # ═══════════════════════════════════════════════════════════
    final_status = determine_test_status(state)
    
    # Log status with appropriate message
    status_messages = {
        "passed": "✅ Test PASSED: All steps completed successfully",
        "failed": f"❌ Test FAILED: {len(errors)} errors",
        "incomplete": f"⚠️ Test INCOMPLETE: {state.get('current_step', 0)}/{state.get('total_steps', 0)} steps",
        "waiting": "⏸️ Test WAITING: Human guidance needed",
        "unknown": "❓ Test status unknown"
    }
    
    logger.info(status_messages.get(final_status, status_messages["unknown"]))
    
    try:
        # Build results summary with CORRECT status
        results = {
            "test_id": test_id,
            "status": final_status,  # ✅ FIX: Use determined status, not "running"
            "total_steps": state.get("total_steps", 0),
            "completed_steps": state.get("current_step", 0),
            "errors": errors,
            "log_entries": len(execution_log),
            "execution_time": state.get("execution_time", 0),
            "timestamp": None
        }
        
        logger.info(f"✅ Results summary: {results}")
        
        # Save to results directory
        import json
        from datetime import datetime
        from pathlib import Path
        
        results_dir = Path("./data/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results["timestamp"] = datetime.now().isoformat()
        result_file = results_dir / f"{test_id}_{timestamp}.json"
        
        with open(result_file, 'w') as f:
            json.dump({
                "summary": results,
                "execution_log": execution_log,
                "state": {k: str(v) for k, v in state.items() if k not in ['execution_log', 'errors']}
            }, f, indent=2)
        
        logger.info(f"✅ Results saved: {result_file}")
        
        # Update state with correct final status
        return {
            **state,
            "status": final_status,
            "results": results
        }
    
    except Exception as e:
        logger.error(f"❌ Log results error: {e}")
        return {
            **state,
            "status": "failed",
            "errors": errors + [f"Log results error: {e}"]
        }


# ═══════════════════════════════════════════════════════════════
# PART 3: HITL & STANDALONE NODES
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# Node 13: Wait Human
# ═══════════════════════════════════════════════════════════════

def wait_human(state: AgentState) -> AgentState:
    """
    Wait for human intervention.
    
    Sets waiting_for_hitl flag and describes the problem
    that requires human help.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with waiting_for_hitl=True and hitl_problem
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    current_step_desc = ""
    
    # Get current step description - CRITICAL FIX: Use current step
    current_step_desc = ""
    current_idx = state.get("current_step", 0)
    failed_step = current_idx
    steps = state.get("test_steps", [])
    
    if state.get("current_mode") == AgentMode.TEST_EXECUTION:
        if steps and current_idx < len(steps):
            current_step_desc = steps[current_idx]
    elif state.get("current_mode") == AgentMode.STANDALONE:
        # CRITICAL FIX: Use current step if multi-step
        if steps and current_idx < len(steps):
            current_step_desc = steps[current_idx]
        else:
            current_step_desc = state.get("standalone_command", "")
    
    # Build problem description
    problem = f"Unable to complete: {current_step_desc}\n"
    problem += f"Attempts: {retry_count}/{max_retries}\n"
    
    # Add context from last errors
    errors = state.get("errors", [])
    if errors:
        problem += f"Last error: {errors[-1]}\n"
    
    # Add screen analysis context
    screen_analysis = state.get("screen_analysis", "")
    if screen_analysis:
        problem += f"Current screen: {screen_analysis[:200]}...\n"
    
    logger.info("🙋 Requesting human intervention...")
    logger.info(f"   Problem: {problem[:200]}")
    
    return {
        **state,
        "waiting_for_hitl": True,
        "hitl_problem": problem,
        "failed_step": failed_step,
        "status": AgentStatus.WAITING_HITL,
        "execution_log": state.get("execution_log", []) + [
            "Waiting for human intervention",
            f"Problem: {current_step_desc}",
            f"Failed at step: {failed_step}"
        ]
    }


# ═══════════════════════════════════════════════════════════════
# Node 14: Apply Guidance
# ═══════════════════════════════════════════════════════════════

def apply_guidance(state: AgentState) -> AgentState:
    """
    Apply human guidance - FULLY AI-DRIVEN.
    
    NO hardcoded keyword checks.
    AI determines everything.
    """
    guidance = state.get("hitl_guidance", "")
    hitl_coordinates = state.get("hitl_coordinates")
    hitl_action_type = state.get("hitl_action_type")
    
    # Get failed step context
    failed_step = state.get("failed_step", state.get("current_step", 0))
    failed_goal = ""
    if state.get('test_steps') and failed_step < len(state.get('test_steps', [])):
        failed_goal = state.get('test_steps')[failed_step]
    
    logger.info("👤 Applying human guidance...")
    logger.info(f"   Guidance: {guidance[:100] if guidance else 'None'}")
    logger.info(f"   Coordinates: {hitl_coordinates}")
    
    if not guidance and not hitl_coordinates:
        logger.warning("⚠️ No guidance provided")
        return {
            **state,
            "waiting_for_hitl": False,
            "errors": state.get("errors", []) + ["No HITL guidance provided"]
        }
    
    try:
        # If coordinates provided directly, use them
        coordinates_to_use = hitl_coordinates
        
        if not coordinates_to_use and guidance:
            # Try parsing coordinates from text
            import re
            
            coord_patterns = [
                r'(?:click|tap|press)\s+at\s+(\d+)[,\s]+(\d+)',
                r'(?:click|tap|press)\s+\(?\s*(\d+)[,\s]+(\d+)\s*\)?',
                r'coordinates?\s*:?\s*\(?\s*(\d+)[,\s]+(\d+)\s*\)?',
                r'\(?\s*(\d+)[,\s]+(\d+)\s*\)',
                r'x\s*[=:]\s*(\d+).*?y\s*[=:]\s*(\d+)',
            ]
            
            for pattern in coord_patterns:
                match = re.search(pattern, guidance, re.IGNORECASE)
                if match:
                    coordinates_to_use = (int(match.group(1)), int(match.group(2)))
                    logger.info(f"✅ Parsed coordinates: {coordinates_to_use}")
                    break
        
        # If we have coordinates, use them
        if coordinates_to_use:
            if isinstance(coordinates_to_use, list):
                coordinates_to_use = tuple(coordinates_to_use)
            
            return {
                **state,
                "target_coordinates": coordinates_to_use,
                "action_type": hitl_action_type or "tap",
                "waiting_for_hitl": False,
                "hitl_applied": True,
                "hitl_guidance": None,
                "hitl_coordinates": None,
                "hitl_action_type": None,
                "status": AgentStatus.RUNNING,
                "retry_count": 0,
                "execution_log": state.get("execution_log", []) + [
                    f"Applied guidance: {coordinates_to_use}"
                ]
            }
        
        # FULLY AI-DRIVEN: Let AI interpret the guidance
        elif guidance:
            logger.info("🤖 Asking AI to interpret guidance (NO HARDCODING)...")
            
            from backend.config import settings
            import requests
            import json
            import re
            
            # AI determines EVERYTHING - no hardcoded rules
            prompt = f"""
Human gave this guidance after a failed action: {guidance}

Context:
- Failed goal: {failed_goal}
- Failed at step: {failed_step}

Your task: Interpret what the human wants.

Respond with JSON:
{{
    "action_type": "tap|press_home|press_back|swipe|input_text",
    "target_element": "what to interact with",
    "then_retry": true/false,
    "reasoning": "brief explanation"
}}

Rules:
- If human says anything about retrying/trying again, set then_retry=true
- Determine the action type based on the guidance semantics
- Don't make assumptions - interpret literally

Example:
- "click home icon and try again" → {{"action_type": "press_home", "then_retry": true}}
- "try tapping at different spot" → {{"action_type": "tap", "then_retry": true}}
"""
            
            payload = {
                "username": settings.vio_username,
                "token": settings.vio_api_token,
                "type": "QUESTION",
                "payload": prompt,
                "vio_model": "Default",
                "ai_model": settings.vio_primary_model,
                "knowledge": False,
                "webSearch": False,
                "reason": False
            }
            
            response = requests.post(
                f"{settings.vio_base_url}/message",
                json=payload,
                verify=settings.vio_verify_ssl,
                timeout=settings.vio_timeout
            )
            
            response.raise_for_status()
            result = response.json()
            message = result.get('message', result.get('response', ''))
            
            # Parse AI response
            json_match = re.search(r'\{.*?\}', message, re.DOTALL)
            if json_match:
                interpreted = json.loads(json_match.group())
                
                logger.info(f"🤖 AI interpreted: {interpreted}")
                
                then_retry = interpreted.get('then_retry', False)
                
                if then_retry:
                    logger.info(f"🔄 AI detected retry intent - will retry step {failed_step}")
                    
                    return {
                        **state,
                        "action_type": interpreted.get('action_type'),
                        "target_element": interpreted.get('target_element'),
                        "current_step": failed_step,
                        "hitl_retry_pending": True,
                        "waiting_for_hitl": False,
                        "hitl_applied": True,
                        "hitl_guidance": None,
                        "hitl_coordinates": None,
                        "hitl_action_type": None,
                        "status": AgentStatus.RUNNING,
                        "retry_count": 0,
                        "execution_log": state.get("execution_log", []) + [
                            f"AI guidance: {interpreted.get('action_type')} then retry"
                        ]
                    }
                
                # No retry - just execute action
                return {
                    **state,
                    "action_type": interpreted.get('action_type'),
                    "target_element": interpreted.get('target_element'),
                    "waiting_for_hitl": False,
                    "hitl_applied": True,
                    "hitl_guidance": None,
                    "hitl_coordinates": None,
                    "hitl_action_type": None,
                    "status": AgentStatus.RUNNING,
                    "retry_count": 0,
                    "execution_log": state.get("execution_log", []) + [
                        f"AI guidance: {interpreted.get('action_type')}"
                    ]
                }
            else:
                logger.warning("⚠️ Could not parse AI response")
                return {
                    **state,
                    "waiting_for_hitl": False,
                    "errors": state.get("errors", []) + ["Could not interpret guidance"]
                }
    
    except Exception as e:
        logger.error(f"❌ Apply guidance error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            **state,
            "waiting_for_hitl": False,
            "hitl_guidance": None,
            "hitl_coordinates": None,
            "hitl_action_type": None,
            "errors": state.get("errors", []) + [f"Apply guidance error: {e}"]
        }


# ═══════════════════════════════════════════════════════════════
# Node 15: Parse Intent - FULLY AI-DRIVEN (NO HARDCODED LOGIC)
# ═══════════════════════════════════════════════════════════════

def parse_intent(state: AgentState) -> AgentState:
    """
    Parse standalone command intent - FULLY AI-DRIVEN.
    
    NO hardcoded keyword checks for single/multi-step.
    NO word count checks.
    NO pattern matching.
    AI decides EVERYTHING based on command semantics.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with parsed_intent, test_steps, total_steps
    """
    command = state.get("standalone_command", "")
    
    logger.info("🧠 Parsing standalone command intent...")
    logger.info(f"   Command: {command}")
    
    if not command:
        logger.error("❌ No standalone command to parse")
        return {
            **state,
            "errors": state.get("errors", []) + ["No standalone command"]
        }
    
    try:
        from backend.config import settings
        import requests
        import json
        import re
        
        # IMPROVED PROMPT: Explicitly ask AI to determine number of steps
        parsing_prompt = f"""
Analyze this Android Automotive UI command:

COMMAND: {command}

CRITICAL: Determine if this is ONE action or MULTIPLE actions.

Examples:
- "click app launcher icon" = ONE action (just tap the launcher)
- "open app launcher and tap Media" = TWO actions (open launcher, then tap Media)
- "launch Settings" = ONE action (tap Settings app)
- "go to Settings and enable Bluetooth" = TWO actions (open Settings, enable Bluetooth)

Respond with JSON:
{{
    "intent": "clear description of what user wants to achieve",
    "number_of_steps": <integer 1, 2, 3, etc>,
    "steps": [
        "concise action description 1",
        "concise action description 2"
    ],
    "initial_action": {{
        "action_type": "tap|swipe|input_text|press_key",
        "target": "element to interact with first"
    }}
}}

IMPORTANT: 
- Be precise about number_of_steps
- Don't split single actions into multiple steps
- Each step should be a distinct user action
"""
        
        payload = {
            "username": settings.vio_username,
            "token": settings.vio_api_token,
            "type": "QUESTION",
            "payload": parsing_prompt,
            "vio_model": "Default",
            "ai_model": settings.vio_primary_model,
            "knowledge": False,
            "webSearch": False,
            "reason": False
        }
        
        response = requests.post(
            f"{settings.vio_base_url}/message",
            json=payload,
            verify=settings.vio_verify_ssl,
            timeout=settings.vio_timeout
        )
        
        response.raise_for_status()
        result = response.json()
        message = result.get('message', result.get('response', ''))
        
        # Parse JSON response
        json_match = re.search(r'\{.*\}', message, re.DOTALL)
        if json_match:
            parsed_intent = json.loads(json_match.group())
            
            steps = parsed_intent.get('steps', [])
            num_steps = parsed_intent.get('number_of_steps', len(steps))
            intent = parsed_intent.get('intent', command)
            
            logger.info(f"✅ Intent parsed: {intent}")
            logger.info(f"   AI decided: {num_steps} step(s)")
            logger.info(f"   Steps: {steps}")
            
            initial_action = parsed_intent.get('initial_action', {})
            
            return {
                **state,
                "parsed_intent": parsed_intent,
                "test_steps": steps,
                "total_steps": len(steps),
                "current_step": 0,
                "action_type": initial_action.get('action_type', 'tap'),
                "target_element": initial_action.get('target', ''),
                "execution_log": state.get("execution_log", []) + [
                    f"Intent: {intent}",
                    f"AI decided: {len(steps)} step(s)"
                ]
            }
        else:
            logger.warning("⚠️ Could not parse JSON - treating as single step")
            return {
                **state,
                "parsed_intent": {"intent": command, "steps": [command]},
                "test_steps": [command],
                "total_steps": 1,
                "current_step": 0,
                "execution_log": state.get("execution_log", []) + [
                    "JSON parse failed - single step fallback"
                ]
            }
    
    except Exception as e:
        logger.error(f"❌ Parse intent error: {e}")
        
        # Fallback: treat as single step
        return {
            **state,
            "parsed_intent": {"intent": command, "steps": [command]},
            "test_steps": [command],
            "total_steps": 1,
            "current_step": 0,
            "errors": state.get("errors", []) + [f"Parse intent error: {e}"]
        }