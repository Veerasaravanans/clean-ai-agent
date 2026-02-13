"""
nodes.py - LangGraph Node Implementations

Part 1: Analysis & Planning Nodes (6 nodes)
Part 2: Execution & Verification Nodes (6 nodes)
Part 3: HITL & Standalone Nodes (3 nodes)

UPDATED: Includes SSIM-based verification and status fix
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
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


def _add_error_context(
    state: AgentState,
    error_message: str,
    error_category: str,
    node_name: str,
    additional_context: Optional[Dict[str, Any]] = None
) -> AgentState:
    """
    Add structured error context to state for intelligent routing.

    CRITICAL ARCHITECTURE FIX:
    - Categorizes errors as technical (system/infrastructure) or decision (AI needs help)
    - Technical errors will route to end (not HITL)
    - Decision errors will route to retry → HITL

    Args:
        state: Current agent state
        error_message: Human-readable error message
        error_category: ErrorCategory enum value (e.g., "capture", "element_not_found")
        node_name: Name of node where error occurred
        additional_context: Optional extra context (screenshot path, coordinates, etc.)

    Returns:
        Updated state with error context added
    """
    from backend.models.enums import ErrorCategory

    # Build error context
    error_context = {
        "message": error_message,
        "category": error_category,
        "node": node_name,
        "step": state.get("current_step", 0),
        "timestamp": state.get("execution_id", ""),  # Use execution_id as proxy timestamp
    }

    if additional_context:
        error_context.update(additional_context)

    # Update state
    error_contexts = state.get("error_contexts", [])
    errors = state.get("errors", [])
    technical_count = state.get("technical_error_count", 0)
    decision_count = state.get("decision_error_count", 0)

    # Increment appropriate counter
    try:
        cat = ErrorCategory(error_category)
        if cat.is_technical():
            technical_count += 1
            logger.warning(f"❌ Technical error in {node_name}: {error_message}")
        elif cat.is_decision():
            decision_count += 1
            logger.warning(f"⚠️ Decision error in {node_name}: {error_message}")
    except (ValueError, KeyError):
        logger.warning(f"Invalid error category: {error_category}")

    return {
        **state,
        "error_contexts": error_contexts + [error_context],
        "last_error_category": error_category,
        "errors": errors + [error_message],
        "technical_error_count": technical_count,
        "decision_error_count": decision_count,
    }


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
            step_verification_configs = test_data.get("step_verification_configs", [])

            # ═══════════════════════════════════════════════════════════
            # CLEANUP SYSTEM: Load cleanup configs from RAG
            # ═══════════════════════════════════════════════════════════
            step_cleanup_configs = test_data.get("step_cleanup_configs", [])
            test_cleanup_config = test_data.get("test_cleanup_config", None)

            # ═══════════════════════════════════════════════════════════
            # POST CONDITION: Load raw ADB intents for end-of-test cleanup
            # ═══════════════════════════════════════════════════════════
            post_condition_intents = test_data.get("post_condition_intents", [])

            logger.info(f"✅ Retrieved test: {test_data.get('title', test_id)}")
            logger.info(f"✅ Steps: {len(steps)}")
            if step_verification_configs:
                logger.info(f"✅ Verification configs: {len(step_verification_configs)} steps configured")
            if step_cleanup_configs:
                active_cleanup_count = sum(
                    1 for c in step_cleanup_configs if c.get("cleanup_type", "none") != "none"
                )
                logger.info(f"✅ Cleanup configs: {len(step_cleanup_configs)} steps ({active_cleanup_count} with active cleanup)")
                if active_cleanup_count == 0:
                    logger.warning("⚠️ All cleanup configs have cleanup_type='none' - Excel cleanup cells may be empty")
                for i, cfg in enumerate(step_cleanup_configs):
                    logger.info(f"   Step {i+1}: type={cfg.get('cleanup_type', 'none')}, trigger={cfg.get('cleanup_trigger', 'end_of_test')}")

            if post_condition_intents:
                logger.info(f"✅ Post condition intents: {len(post_condition_intents)} commands (OVERRIDES default cleanup)")
                for i, intent in enumerate(post_condition_intents):
                    logger.info(f"   Intent {i+1}: {intent}")
            else:
                logger.info("   ℹ️ No post condition intents - using step cleanup configs only")

            return {
                **state,
                "test_description": description,
                "test_steps": steps,
                "total_steps": len(steps),
                "step_verification_configs": step_verification_configs,
                "step_cleanup_configs": step_cleanup_configs,
                "test_cleanup_config": test_cleanup_config,
                "post_condition_intents": post_condition_intents if post_condition_intents else None,
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
            # CRITICAL FIX: Categorize as TECHNICAL error (CAPTURE)
            return _add_error_context(
                state,
                error_message="Screenshot capture failed",
                error_category="capture",  # ErrorCategory.CAPTURE
                node_name="capture_screen",
                additional_context={"current_screenshot": None}
            )

    except Exception as e:
        logger.error(f"❌ Capture screen error: {e}")
        # CRITICAL FIX: Categorize as TECHNICAL error (CAPTURE)
        return _add_error_context(
            state,
            error_message=f"Capture screen error: {e}",
            error_category="capture",  # ErrorCategory.CAPTURE
            node_name="capture_screen",
            additional_context={"exception": str(e), "current_screenshot": None}
        )


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
        # CRITICAL FIX: Categorize as TECHNICAL error (CAPTURE dependency)
        return _add_error_context(
            state,
            error_message="No screenshot for AI analysis",
            error_category="capture",  # ErrorCategory.CAPTURE (screenshot missing)
            node_name="ai_analyze"
        )
    
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
        # CRITICAL FIX: Categorize as TECHNICAL error (SYSTEM - AI service failure)
        return _add_error_context(
            state,
            error_message=f"AI analyze error: {e}",
            error_category="system",  # ErrorCategory.SYSTEM (AI service failure)
            node_name="ai_analyze",
            additional_context={"exception": str(e), "screen_analysis": None, "detected_elements": []}
        )


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
        from backend.utils import CoordinateParser

        # Initialize coordinate parser for Stage 0
        coord_parser = CoordinateParser()

        # ═══════════════════════════════════════════════════════════
        # STAGE 0: Fast Path Pre-Processing (Regex Detection)
        # ═══════════════════════════════════════════════════════════
        # Priority 1: Raw ADB Command (Highest Priority)
        raw_command = coord_parser.extract_raw_command(goal)
        if raw_command:
            logger.info(f"💻 Detected raw ADB command: {raw_command}")
            return {
                **state,
                "planned_action": f"execute raw command: {raw_command}",
                "action_type": "raw_adb",
                "target_element": None,
                "target_coordinates": None,
                "raw_command": raw_command,
                "coordinate_source": "explicit",
                "action_parameters": {
                    "reasoning": "Raw ADB command execution",
                    "raw_command": raw_command
                },
                "execution_log": state.get("execution_log", []) + [
                    f"Raw command detected: {raw_command}"
                ]
            }

        # Priority 2: Explicit Single Coordinates (for tap/press actions)
        single_coords = coord_parser.extract_single_coordinate(goal)
        if single_coords and any(keyword in goal.lower() for keyword in ['tap', 'press', 'click']):
            x, y = single_coords

            # Detect action type from keywords
            if 'double' in goal.lower() or 'twice' in goal.lower():
                action_type = 'double_tap'
            elif 'long' in goal.lower() or 'hold' in goal.lower():
                action_type = 'long_press'
                # Extract duration if specified
                duration_seconds = coord_parser.extract_duration(goal)
                long_press_duration_seconds = int(duration_seconds) if duration_seconds else 1
            else:
                action_type = 'tap'

            logger.info(f"📍 Detected explicit {action_type} at ({x}, {y})")

            result = {
                **state,
                "planned_action": f"{action_type} at ({x}, {y})",
                "action_type": action_type,
                "target_element": None,
                "target_coordinates": (x, y),
                "coordinate_source": "explicit",
                "action_parameters": {
                    "reasoning": "Explicit coordinates from test step"
                },
                "execution_log": state.get("execution_log", []) + [
                    f"Explicit {action_type} at ({x}, {y})"
                ]
            }

            # Add duration for long press
            if action_type == 'long_press':
                result["long_press_duration_seconds"] = long_press_duration_seconds
                result["action_parameters"]["duration_ms"] = long_press_duration_seconds * 1000

            return result

        # Priority 3: Explicit Swipe Coordinates
        swipe_coords = coord_parser.extract_swipe_coordinates(goal)
        if swipe_coords:
            x1, y1, x2, y2 = swipe_coords

            # Extract speed modifier
            speed = coord_parser.extract_swipe_speed(goal)
            duration_ms = coord_parser.speed_to_duration_ms(speed) if speed else 300

            logger.info(f"📍 Detected explicit swipe: ({x1},{y1}) -> ({x2},{y2}) at {speed or 'medium'} speed")

            return {
                **state,
                "planned_action": f"swipe ({x1},{y1}) to ({x2},{y2})" + (f" ({speed})" if speed else ""),
                "action_type": "swipe",
                "target_element": None,
                "target_coordinates": (x1, y1, x2, y2),
                "swipe_speed": speed,
                "swipe_duration_ms": duration_ms,
                "coordinate_source": "explicit",
                "action_parameters": {
                    "reasoning": "Explicit swipe coordinates from test step",
                    "swipe_speed": speed,
                    "duration_ms": duration_ms
                },
                "execution_log": state.get("execution_log", []) + [
                    f"Explicit swipe: ({x1},{y1}) -> ({x2},{y2})",
                    f"Speed: {speed or 'medium'} ({duration_ms}ms)"
                ]
            }

        # Priority 4: Drag-Drop Detection
        drag_params = coord_parser.extract_drag_drop(goal)
        if drag_params:
            logger.info(f"🎯 Detected drag-drop: {drag_params}")
            return {
                **state,
                "planned_action": f"move {drag_params['app_name']} app {drag_params['pixel_offset']} pixel {drag_params['direction']}",
                "action_type": "drag_drop",
                "target_element": f"{drag_params['app_name']} app",
                "target_coordinates": None,  # Will be found via vision tool
                "drag_drop_params": drag_params,
                "coordinate_source": "vision_tool",  # Will use vision to find app first
                "action_parameters": {
                    "reasoning": "Drag-drop app movement",
                    "drag_drop": drag_params
                },
                "execution_log": state.get("execution_log", []) + [
                    f"Drag-drop: {drag_params['app_name']} app {drag_params['pixel_offset']}px {drag_params['direction']}"
                ]
            }

        # ═══════════════════════════════════════════════════════════
        # STEP 1: Ask AI to extract BOTH action type AND target element
        # ═══════════════════════════════════════════════════════════
        logger.info("🤖 Asking AI to extract action type and target element...")

        # Enhanced prompt with stronger JSON enforcement and role instruction
        extraction_prompt = f"""You are a test automation parser. Your ONLY job is to analyze the test step and return JSON.

DO NOT provide explanations, documentation, or examples. ONLY return the JSON object.

TEST STEP TO ANALYZE:
"{goal}"

AVAILABLE ACTION TYPES:
- tap: Single tap on an element
- double_tap: Double tap on an element
- long_press: Long press on an element
- swipe: Swipe gesture (up/down/left/right) - for screen navigation
- drag_drop: Drag and drop an app icon to reposition it
- input_text: Enter text into a field
- press_key: Press a hardware/navigation key

REQUIRED JSON FORMAT:
{{
    "action_type": "tap|double_tap|long_press|swipe|input_text|press_key|drag_drop",
    "target_element": "element name or null",
    "swipe_direction": "up|down|left|right or null",
    "swipe_start_position": "left|center|right|top|bottom or null",
    "swipe_speed": "slow|medium|fast or null",
    "text_input": "text to enter or null",
    "key_name": "HOME|BACK|ENTER or null",
    "duration_seconds": null or number,
    "drag_drop_params": {{
        "app_name": "name of app to drag",
        "pixel_offset": 250,
        "direction": "left|right|up|down"
    }} or null
}}

SWIPE POSITION EXTRACTION RULES:
- "left side" / "left" / "left edge" → swipe_start_position: "left"
- "right side" / "right" / "right edge" → swipe_start_position: "right"
- "center" / "middle" → swipe_start_position: "center"
- "top" / "top area" → swipe_start_position: "top"
- "bottom" / "bottom area" → swipe_start_position: "bottom"
- If no position specified → swipe_start_position: "center"

EXTRACTION EXAMPLES:
1. "double tap on app launcher icon" → {{"action_type": "double_tap", "target_element": "app launcher", "swipe_direction": null, "swipe_start_position": null, "swipe_speed": null, "text_input": null, "key_name": null, "duration_seconds": null, "drag_drop_params": null}}
2. "swipe towards right side" → {{"action_type": "swipe", "target_element": null, "swipe_direction": "right", "swipe_start_position": "center", "swipe_speed": null, "text_input": null, "key_name": null, "duration_seconds": null, "drag_drop_params": null}}
3. "swipe towards up on the left side of the screen" → {{"action_type": "swipe", "target_element": null, "swipe_direction": "up", "swipe_start_position": "left", "swipe_speed": null, "text_input": null, "key_name": null, "duration_seconds": null, "drag_drop_params": null}}
4. "long press for 2 seconds on AC" → {{"action_type": "long_press", "target_element": "AC", "swipe_direction": null, "swipe_start_position": null, "swipe_speed": null, "text_input": null, "key_name": null, "duration_seconds": 2, "drag_drop_params": null}}
5. "swipe down from the top" → {{"action_type": "swipe", "target_element": null, "swipe_direction": "down", "swipe_start_position": "top", "swipe_speed": null, "text_input": null, "key_name": null, "duration_seconds": null, "drag_drop_params": null}}
6. "drag and drop Play Store app 250 pixel right side" → {{"action_type": "drag_drop", "target_element": null, "swipe_direction": null, "swipe_start_position": null, "swipe_speed": null, "text_input": null, "key_name": null, "duration_seconds": null, "drag_drop_params": {{"app_name": "Play Store", "pixel_offset": 250, "direction": "right"}}}}

RESPOND WITH ONLY THE JSON OBJECT. NO OTHER TEXT."""

        # Try up to 3 times with different strategies
        parsed_intent = None
        ai_response = None
        last_error = None

        for attempt in range(3):
            try:
                logger.info(f"🔄 VIO API call attempt {attempt + 1}/3")

                # Vary the VIO model parameter on retries
                if attempt == 0:
                    vio_model_param = "Default"
                    ai_model = settings.vio_primary_model
                elif attempt == 1:
                    vio_model_param = "Fast"
                    ai_model = settings.vio_fallback_fast
                else:
                    vio_model_param = "Cheap"
                    ai_model = settings.vio_fallback_cheap

                payload = {
                    "username": settings.vio_username,
                    "token": settings.vio_api_token,
                    "type": "QUESTION",
                    "payload": extraction_prompt,
                    "vio_model": vio_model_param,
                    "ai_model": ai_model,
                    "knowledge": False,
                    "webSearch": False,
                    "reason": False
                }

                logger.debug(f"📤 VIO Request: model={ai_model}, vio_model={vio_model_param}")

                response = requests.post(
                    f"{settings.vio_base_url}/message",
                    json=payload,
                    verify=settings.vio_verify_ssl,
                    timeout=settings.vio_timeout
                )

                response.raise_for_status()
                result = response.json()
                ai_response = result.get('message', result.get('response', '{}')).strip()

                logger.debug(f"📥 VIO Response (first 500 chars): {ai_response[:500]}")

                # Enhanced JSON extraction with multiple strategies
                json_match = None

                # Strategy 1: Look for complete JSON with all required fields
                json_match = re.search(
                    r'\{[^{}]*"action_type"[^{}]*"target_element"[^{}]*\}',
                    ai_response,
                    re.DOTALL
                )

                # Strategy 2: Look for JSON in markdown code blocks
                if not json_match:
                    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
                    if code_block_match:
                        json_match = re.search(r'\{.*?\}', code_block_match.group(1), re.DOTALL)

                # Strategy 3: Look for any JSON object with action_type
                if not json_match:
                    json_match = re.search(r'\{[^{}]*"action_type"[^{}]*\}', ai_response, re.DOTALL)

                # Strategy 4: Look for the first complete JSON object
                if not json_match:
                    json_match = re.search(r'\{.*?\}', ai_response, re.DOTALL)

                if not json_match:
                    logger.warning(f"⚠️ Attempt {attempt + 1}: No JSON found in response")
                    last_error = f"No JSON object found in response (length: {len(ai_response)})"
                    continue

                # Try to parse the JSON
                try:
                    parsed_intent = json.loads(json_match.group())

                    # Validate required fields
                    if 'action_type' not in parsed_intent:
                        logger.warning(f"⚠️ Attempt {attempt + 1}: JSON missing 'action_type' field")
                        last_error = "JSON missing required 'action_type' field"
                        continue

                    # Success!
                    logger.info(f"✅ Successfully parsed JSON on attempt {attempt + 1}")
                    break

                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Attempt {attempt + 1}: JSON parse error: {e}")
                    last_error = f"JSON decode error: {e}"
                    continue

            except requests.RequestException as e:
                logger.warning(f"⚠️ Attempt {attempt + 1}: VIO API error: {e}")
                last_error = f"VIO API request error: {e}"
                continue
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt + 1}: Unexpected error: {e}")
                last_error = f"Unexpected error: {e}"
                continue

        # If all attempts failed, use regex fallback parser
        if not parsed_intent:
            logger.error(f"❌ All 3 VIO attempts failed. Last error: {last_error}")
            logger.error(f"❌ Full AI response: {ai_response}")
            logger.info("🔧 Falling back to regex-based action extraction")

            # Fallback: Use regex to extract action type from goal
            parsed_intent = {
                "action_type": "tap",  # default
                "target_element": None,
                "swipe_direction": None,
                "swipe_speed": None,
                "text_input": None,
                "key_name": None,
                "duration_seconds": None
            }

            goal_lower = goal.lower()

            # Detect action type from keywords
            if 'double tap' in goal_lower or 'double click' in goal_lower or 'tap twice' in goal_lower:
                parsed_intent["action_type"] = "double_tap"
            elif 'long press' in goal_lower or 'long tap' in goal_lower or 'hold' in goal_lower and 'press' in goal_lower:
                parsed_intent["action_type"] = "long_press"
                # Extract duration
                duration_match = re.search(r'(\d+)\s*second', goal_lower)
                if duration_match:
                    parsed_intent["duration_seconds"] = int(duration_match.group(1))
            elif 'drag' in goal_lower or ('move' in goal_lower and 'app' in goal_lower):
                parsed_intent["action_type"] = "drag_drop"
                # Extract app name (between "drag/move" and "app")
                app_match = re.search(r'(?:drag|move)(?:\s+and\s+drop)?\s+(?:the\s+)?([A-Za-z0-9\s]+?)\s+app', goal, re.IGNORECASE)
                if app_match:
                    app_name = app_match.group(1).strip()
                else:
                    app_name = "unknown"

                # Extract pixel offset
                pixel_match = re.search(r'(\d+)\s*pixel', goal_lower)
                pixel_offset = int(pixel_match.group(1)) if pixel_match else 250

                # Extract direction
                direction = None
                if 'right' in goal_lower:
                    direction = "right"
                elif 'left' in goal_lower:
                    direction = "left"
                elif 'up' in goal_lower:
                    direction = "up"
                elif 'down' in goal_lower:
                    direction = "down"

                parsed_intent["drag_drop_params"] = {
                    "app_name": app_name,
                    "pixel_offset": pixel_offset,
                    "direction": direction
                }
            elif 'swipe' in goal_lower:
                parsed_intent["action_type"] = "swipe"
                # Extract direction
                if 'right' in goal_lower:
                    parsed_intent["swipe_direction"] = "right"
                elif 'left' in goal_lower:
                    parsed_intent["swipe_direction"] = "left"
                elif 'up' in goal_lower:
                    parsed_intent["swipe_direction"] = "up"
                elif 'down' in goal_lower:
                    parsed_intent["swipe_direction"] = "down"
                # Extract starting position
                if 'left side' in goal_lower or 'left edge' in goal_lower or goal_lower.startswith('left'):
                    parsed_intent["swipe_start_position"] = "left"
                elif 'right side' in goal_lower or 'right edge' in goal_lower or goal_lower.startswith('right'):
                    parsed_intent["swipe_start_position"] = "right"
                elif 'top' in goal_lower:
                    parsed_intent["swipe_start_position"] = "top"
                elif 'bottom' in goal_lower:
                    parsed_intent["swipe_start_position"] = "bottom"
                elif 'center' in goal_lower or 'middle' in goal_lower:
                    parsed_intent["swipe_start_position"] = "center"
                else:
                    parsed_intent["swipe_start_position"] = "center"  # Default
                # Extract speed
                if 'slow' in goal_lower:
                    parsed_intent["swipe_speed"] = "slow"
                elif 'fast' in goal_lower or 'quick' in goal_lower:
                    parsed_intent["swipe_speed"] = "fast"
            elif 'input' in goal_lower or 'enter text' in goal_lower or 'type' in goal_lower:
                parsed_intent["action_type"] = "input_text"
                # Extract text from quotes
                text_match = re.search(r"['\"]([^'\"]+)['\"]", goal)
                if text_match:
                    parsed_intent["text_input"] = text_match.group(1)
            elif 'press back' in goal_lower or 'back button' in goal_lower:
                parsed_intent["action_type"] = "press_key"
                parsed_intent["key_name"] = "BACK"
            elif 'press home' in goal_lower or 'home button' in goal_lower:
                parsed_intent["action_type"] = "press_key"
                parsed_intent["key_name"] = "HOME"
            elif 'tap' in goal_lower or 'click' in goal_lower or 'press' in goal_lower:
                parsed_intent["action_type"] = "tap"

            logger.info(f"✅ Fallback extraction: {parsed_intent['action_type']}")

        # Extract fields from parsed intent
        parsed_intent = parsed_intent or {}

        action_type = parsed_intent.get('action_type', 'tap')
        extracted_target = parsed_intent.get('target_element')
        swipe_direction = parsed_intent.get('swipe_direction')
        swipe_start_position = parsed_intent.get('swipe_start_position')  # NEW: spatial position
        swipe_speed = parsed_intent.get('swipe_speed')
        text_input = parsed_intent.get('text_input')
        key_name = parsed_intent.get('key_name')
        duration_seconds = parsed_intent.get('duration_seconds')
        drag_drop_params = parsed_intent.get('drag_drop_params')

        # Fallback to regex extraction if AI didn't extract
        if not swipe_speed and action_type == 'swipe':
            swipe_speed = coord_parser.extract_swipe_speed(goal)

        if not duration_seconds and action_type == 'long_press':
            duration_seconds = coord_parser.extract_duration(goal)

        # Fallback to coordinate_parser for drag_drop if AI didn't extract
        if not drag_drop_params and action_type == 'drag_drop':
            drag_drop_params = coord_parser.extract_drag_drop(goal)

        logger.info(f"✅ AI extracted action: '{action_type}'")
        logger.info(f"   Target element: '{extracted_target}'")
        if swipe_speed:
            logger.info(f"   Swipe speed: '{swipe_speed}'")
        if duration_seconds:
            logger.info(f"   Duration: {duration_seconds} seconds")
        if drag_drop_params:
            logger.info(f"   Drag-drop params: {drag_drop_params}")

        # ═══════════════════════════════════════════════════════════
        # STEP 2: Handle different action types
        # ═══════════════════════════════════════════════════════════

        # For swipe actions, calculate coordinates based on direction AND spatial position
        if action_type == "swipe":
            logger.info(f"🔄 Swipe action detected")
            logger.info(f"   Direction: {swipe_direction}")
            logger.info(f"   Start position: {swipe_start_position}")

            # Get screen dimensions from ADB tool
            screen_width, screen_height = toolkit.adb.get_screen_dimensions()

            # Default to center if no position specified
            if not swipe_start_position:
                swipe_start_position = "center"

            # ═══════════════════════════════════════════════════════════
            # DYNAMIC COORDINATE CALCULATION BASED ON SPATIAL POSITION
            # ═══════════════════════════════════════════════════════════

            # Define separate X and Y region maps
            x_regions = {
                "left": int(screen_width * 0.25),
                "center": int(screen_width * 0.50),
                "right": int(screen_width * 0.75),
            }
            y_regions = {
                "top": int(screen_height * 0.25),
                "center": int(screen_height * 0.50),
                "bottom": int(screen_height * 0.75),
            }

            # Calculate swipe coordinates based on direction and starting position
            margin = 100  # Margin from edges

            if swipe_direction == "up":
                # Swipe up: vertical movement - X position matters
                x_pos = x_regions.get(swipe_start_position, x_regions["center"])
                coords = (x_pos, screen_height - margin, x_pos, margin)

            elif swipe_direction == "down":
                # Swipe down: vertical movement - X position matters
                x_pos = x_regions.get(swipe_start_position, x_regions["center"])
                coords = (x_pos, margin, x_pos, screen_height - margin)

            elif swipe_direction == "left":
                # Swipe left: horizontal movement - Y position matters
                y_pos = y_regions.get(swipe_start_position, y_regions["center"])
                coords = (screen_width - margin, y_pos, margin, y_pos)

            elif swipe_direction == "right":
                # Swipe right: horizontal movement - Y position matters
                y_pos = y_regions.get(swipe_start_position, y_regions["center"])
                coords = (margin, y_pos, screen_width - margin, y_pos)

            else:
                # Default: swipe right from center
                coords = (margin, screen_height // 2, screen_width - margin, screen_height // 2)

            # Calculate duration based on speed
            duration_ms = coord_parser.speed_to_duration_ms(swipe_speed) if swipe_speed else 300

            logger.info(f"✅ Calculated swipe coordinates:")
            logger.info(f"   From: ({coords[0]}, {coords[1]})")
            logger.info(f"   To: ({coords[2]}, {coords[3]})")
            logger.info(f"   Screen: {screen_width}x{screen_height}")
            logger.info(f"   Position: {swipe_start_position} ({coords[0] if swipe_direction in ['up', 'down'] else coords[1]} px)")

            return {
                **state,
                "planned_action": f"swipe {swipe_direction} from {swipe_start_position}" + (f" ({swipe_speed})" if swipe_speed else ""),
                "action_type": "swipe",
                "target_element": None,
                "target_coordinates": coords,
                "swipe_direction": swipe_direction,
                "swipe_start_position": swipe_start_position,
                "swipe_speed": swipe_speed,
                "swipe_duration_ms": duration_ms,
                "coordinate_source": "spatial_calculation",
                "action_parameters": {
                    "reasoning": f"Swipe {swipe_direction} from {swipe_start_position}",
                    "swipe_direction": swipe_direction,
                    "swipe_start_position": swipe_start_position,
                    "swipe_speed": swipe_speed,
                    "duration_ms": duration_ms
                },
                "execution_log": state.get("execution_log", []) + [
                    f"Action: swipe {swipe_direction} from {swipe_start_position}",
                    f"Speed: {swipe_speed or 'medium'} ({duration_ms}ms)",
                    f"Coords: ({coords[0]},{coords[1]}) → ({coords[2]},{coords[3]})"
                ]
            }

        # For drag_drop actions
        if action_type == "drag_drop":
            if not drag_drop_params:
                logger.error("❌ Drag-drop action requested but no parameters provided")
                # Fall through to full AI planning
            else:
                app_name = drag_drop_params.get("app_name")
                pixel_offset = drag_drop_params.get("pixel_offset", 250)
                direction = drag_drop_params.get("direction")

                logger.info("=" * 60)
                logger.info("🎯 DRAG-AND-DROP ACTION DETECTED")
                logger.info("=" * 60)
                logger.info(f"   App Name: {app_name}")
                logger.info(f"   Pixel Offset: {pixel_offset}")
                logger.info(f"   Direction: {direction}")
                logger.info("=" * 60)

                # Return with drag_drop parameters (actual coordinates will be found in execute_adb)
                return {
                    **state,
                    "planned_action": f"drag {app_name} app {pixel_offset}px {direction}",
                    "action_type": "drag_drop",
                    "target_element": None,
                    "target_coordinates": None,  # Will be calculated in execute_adb
                    "drag_drop_params": drag_drop_params,
                    "coordinate_source": "vision_tool",
                    "action_parameters": {
                        "reasoning": f"Drag {app_name} app {pixel_offset}px {direction}",
                        "drag_drop": drag_drop_params
                    },
                    "execution_log": state.get("execution_log", []) + [
                        f"Action: drag_drop",
                        f"App: {app_name}",
                        f"Offset: {pixel_offset}px {direction}"
                    ]
                }

        # For input_text actions
        if action_type == "input_text":
            logger.info(f"⌨️ Input text action: '{text_input}'")
            return {
                **state,
                "planned_action": f"input text: {text_input}",
                "action_type": "input_text",
                "target_element": None,
                "target_coordinates": None,
                "action_parameters": {
                    "reasoning": "Input text",
                    "text": text_input
                },
                "execution_log": state.get("execution_log", []) + [
                    f"Action: input_text",
                    f"Text: {text_input}"
                ]
            }

        # For press_key actions
        if action_type == "press_key":
            logger.info(f"🔘 Press key action: {key_name}")
            return {
                **state,
                "planned_action": f"press key: {key_name}",
                "action_type": f"press_{key_name.lower()}" if key_name else "press_back",
                "target_element": None,
                "target_coordinates": None,
                "action_parameters": {
                    "reasoning": f"Press {key_name}",
                    "key_name": key_name
                },
                "execution_log": state.get("execution_log", []) + [
                    f"Action: press_key",
                    f"Key: {key_name}"
                ]
            }

        # ═══════════════════════════════════════════════════════════
        # STEP 3: For tap/double_tap/long_press, find coordinates
        # ═══════════════════════════════════════════════════════════
        if action_type in ['tap', 'double_tap', 'long_press']:
            if extracted_target:
                logger.info(f"🔍 Searching for '{extracted_target}' on screen")

                try:
                    coords_result = toolkit.vision.find_element_with_ai(screenshot_path, extracted_target)

                    if coords_result:
                        coords = (coords_result.x, coords_result.y)
                        logger.info(f"✅ Found '{extracted_target}' at {coords}")

                        result = {
                            **state,
                            "planned_action": f"{action_type} on {extracted_target}",
                            "action_type": action_type,
                            "target_element": extracted_target,
                            "target_coordinates": coords,
                            "coordinate_source": "vision_tool",
                            "action_parameters": {"reasoning": "Found via vision tool"},
                            "execution_log": state.get("execution_log", []) + [
                                f"Action: {action_type}",
                                f"Target: {extracted_target}",
                                f"Vision found: {coords}"
                            ]
                        }

                        # Add duration for long_press
                        if action_type == 'long_press' and duration_seconds:
                            result["long_press_duration_seconds"] = int(duration_seconds)
                            result["action_parameters"]["duration_ms"] = int(duration_seconds * 1000)
                            result["execution_log"].append(f"Duration: {duration_seconds} seconds")

                        return result
                    else:
                        logger.warning(f"⚠️ Vision tool couldn't find '{extracted_target}'")
                        # Fall through to full AI planning

                except Exception as e:
                    logger.error(f"❌ Vision tool error: {e}")
                    # Fall through to full AI planning
            else:
                # No target element specified, might be raw coordinates
                logger.info("⚠️ No target element specified for tap action")
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

def _should_capture_before_screenshot(state: AgentState) -> bool:
    """
    Determine if we should capture a before screenshot for verification.

    Returns True if:
    - Verification is configured for current step
    - Verification type is NOT "no_verification"

    Returns False if:
    - No verification config exists (backwards compatibility)
    - Verification type is "no_verification"
    """
    current_step = state.get("current_step", 0)
    step_verification_configs = state.get("step_verification_configs", [])

    # No config = assume verification needed (backwards compatibility)
    if not step_verification_configs:
        return True

    # Check if we have config for this step
    if current_step >= len(step_verification_configs):
        return True  # Default to safe behavior

    # Get config and check verification type
    config_dict = step_verification_configs[current_step]
    verification_type = config_dict.get("verification_type", "image_verification")

    # Don't capture if explicitly set to no_verification
    if verification_type == "no_verification":
        logger.debug(f"   ⏭️ Skipping before screenshot - verification disabled for step {current_step}")
        return False

    return True


def _capture_fresh_before_screenshot(state: AgentState, force: bool = False) -> tuple[str, list[str]]:
    """
    Capture a FRESH before screenshot for verification.

    CRITICAL: Always captures a NEW screenshot, never reuses old ones.
    This ensures each step has the correct "before" state for verification.

    Args:
        state: Current agent state
        force: If True, capture regardless of verification config

    Returns:
        Tuple of (screenshot_path, log_entries)
    """
    current_step = state.get("current_step", 0)
    log_entries = []

    # Check if we should capture
    if not force and not _should_capture_before_screenshot(state):
        # No verification needed, return None
        return None, log_entries

    try:
        # ALWAYS capture fresh screenshot (never reuse from previous step)
        before_screenshot = toolkit.screenshot.capture()
        logger.info(f"   📸 Captured fresh before screenshot for step {current_step}")
        log_entries.append(f"Captured before screenshot for verification")
        return before_screenshot, log_entries
    except Exception as e:
        logger.warning(f"   ⚠️ Could not capture before screenshot: {e}")
        log_entries.append(f"Warning: Before screenshot failed - {e}")
        return None, log_entries


def direct_execute(state: AgentState) -> AgentState:
    """
    Execute action from learned solution.

    SYSTEMATIC VERIFICATION HANDLING:
    - Checks verification config for current step
    - Only captures before screenshot if verification is configured
    - Always captures FRESH screenshot (never reuses from previous step)
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
    # SYSTEMATIC: Capture fresh before screenshot if needed
    # ═══════════════════════════════════════════════════════════
    before_screenshot, screenshot_logs = _capture_fresh_before_screenshot(state)
    
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
            "current_screenshot": before_screenshot,  # Preserve screenshot (may be None if no verification)
            "use_learned": False,
            "execution_log": state.get("execution_log", []) + screenshot_logs + [
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
                "current_screenshot": before_screenshot,  # For verification comparison (may be None)
                "last_action_result": result,
                "action_success": result.success,
                "planned_action": action_type,
                "action_type": action_type,
                "target_element": target_element,
                "use_learned": True,
                "execution_log": state.get("execution_log", []) + screenshot_logs + [
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
            # For swipe: need all 4 coordinates
            if action_type == "swipe" and isinstance(stored_coords, (list, tuple)) and len(stored_coords) >= 4:
                coordinates = (stored_coords[0], stored_coords[1], stored_coords[2], stored_coords[3])
            # For tap/long_press/double_tap: need 2 coordinates
            elif isinstance(stored_coords, (list, tuple)) and len(stored_coords) >= 2:
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
                "current_screenshot": before_screenshot,  # For verification comparison (may be None)
                "last_action_result": result,
                "action_success": result.success,
                "planned_action": "tap",
                "action_type": "tap",
                "target_element": target_element,
                "target_coordinates": {"x": x, "y": y, "source": "learned"},
                "use_learned": True,
                "execution_log": state.get("execution_log", []) + screenshot_logs + [
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
                "current_screenshot": before_screenshot,  # For verification comparison (may be None)
                "last_action_result": result,
                "action_success": result.success,
                "planned_action": "input_text",
                "action_type": "input_text",
                "action_parameters": {"text": input_text},
                "use_learned": True,
                "execution_log": state.get("execution_log", []) + screenshot_logs + [
                    f"Direct execute: input_text"
                ]
            }
        except Exception as e:
            logger.error(f"❌ Direct input error: {e}")
    
    # Execute swipe action
    elif action_type == "swipe":
        try:
            # CRITICAL FIX: Swipe needs 4 coordinates (x1, y1, x2, y2)
            # Get stored coordinates or fallback to stored coords
            stored_coords = learned_step.get("coordinates")
            swipe_duration_ms = learned_step.get("swipe_duration_ms", 300)

            # Check if we have 4-tuple coordinates
            if stored_coords and isinstance(stored_coords, (list, tuple)) and len(stored_coords) >= 4:
                x1, y1, x2, y2 = int(stored_coords[0]), int(stored_coords[1]), int(stored_coords[2]), int(stored_coords[3])
                logger.info(f"   📍 Using stored swipe coords: ({x1}, {y1}) → ({x2}, {y2}) at {swipe_duration_ms}ms")
            elif coordinates and isinstance(coordinates, (list, tuple)) and len(coordinates) >= 4:
                x1, y1, x2, y2 = int(coordinates[0]), int(coordinates[1]), int(coordinates[2]), int(coordinates[3])
                logger.info(f"   📍 Using swipe coords: ({x1}, {y1}) → ({x2}, {y2}) at {swipe_duration_ms}ms")
            else:
                logger.error(f"❌ Swipe requires 4 coordinates, got: {stored_coords or coordinates}")
                raise ValueError(f"Invalid swipe coordinates: {stored_coords or coordinates}")

            # Call swipe with positional args (NOT keyword args!)
            result = toolkit.adb.swipe(x1, y1, x2, y2, swipe_duration_ms)

            logger.info(f"   ✅ Swipe ({x1},{y1})→({x2},{y2}): {'Success' if result.success else 'Failed'}")

            return {
                **state,
                "current_screenshot": before_screenshot,  # For verification comparison (may be None)
                "last_action_result": result,
                "action_success": result.success,
                "planned_action": "swipe",
                "action_type": "swipe",
                "target_coordinates": (x1, y1, x2, y2),
                "swipe_duration_ms": swipe_duration_ms,
                "use_learned": True,
                "execution_log": state.get("execution_log", []) + screenshot_logs + [
                    f"Direct execute: swipe ({x1},{y1})→({x2},{y2}) at {swipe_duration_ms}ms"
                ]
            }
        except Exception as e:
            logger.error(f"❌ Direct swipe error: {e}")

    # Execute double_tap action
    elif action_type == "double_tap" and coordinates:
        try:
            x, y = int(coordinates[0]), int(coordinates[1])
            delay_ms = learned_step.get("double_tap_delay_ms", 50)
            result = toolkit.adb.double_tap(x, y, delay_ms)

            logger.info(f"   ✅ Double tap at ({x}, {y}): {'Success' if result.success else 'Failed'}")

            return {
                **state,
                "current_screenshot": before_screenshot,  # For verification comparison (may be None)
                "last_action_result": result,
                "action_success": result.success,
                "planned_action": "double_tap",
                "action_type": "double_tap",
                "target_element": target_element,
                "target_coordinates": {"x": x, "y": y, "source": "learned"},
                "use_learned": True,
                "execution_log": state.get("execution_log", []) + screenshot_logs + [
                    f"Direct execute: double_tap at ({x}, {y}) on '{target_element}'"
                ]
            }
        except Exception as e:
            logger.error(f"❌ Direct double_tap error: {e}")

    # Execute long_press action
    elif action_type == "long_press" and coordinates:
        try:
            x, y = int(coordinates[0]), int(coordinates[1])

            # CRITICAL FIX: Read long_press_duration_seconds
            # NEVER fallback to swipe_duration_ms (that's for swipe actions only!)
            duration_seconds = learned_step.get("long_press_duration_seconds")

            # If None or invalid, use 1 second default (standard long press)
            if not duration_seconds or duration_seconds <= 0:
                duration_seconds = 1.0  # Default to 1 second

            # Convert to milliseconds for ADB
            duration_ms = int(duration_seconds * 1000)

            logger.info(f"   📍 Long press duration: {duration_seconds}s ({duration_ms}ms)")
            logger.info(f"   📋 Learned step data: {learned_step}")  # Debug logging

            result = toolkit.adb.long_press(x, y, duration_ms)

            logger.info(f"   ✅ Long press at ({x}, {y}) for {duration_ms}ms: {'Success' if result.success else 'Failed'}")

            return {
                **state,
                "current_screenshot": before_screenshot,  # For verification comparison (may be None)
                "last_action_result": result,
                "action_success": result.success,
                "planned_action": "long_press",
                "action_type": "long_press",
                "target_element": target_element,
                "target_coordinates": {"x": x, "y": y, "source": "learned"},
                "long_press_duration_seconds": duration_seconds,
                "use_learned": True,
                "execution_log": state.get("execution_log", []) + screenshot_logs + [
                    f"Direct execute: long_press at ({x}, {y}) for {duration_ms}ms on '{target_element}'"
                ]
            }
        except Exception as e:
            logger.error(f"❌ Direct long_press error: {e}")
    
    # Fall back to AI for this step only
    logger.warning(f"⚠️ Cannot direct execute step {current_step}, using AI for this step")

    return {
        **state,
        "current_screenshot": before_screenshot,  # For verification comparison (may be None)
        "use_learned": False,
        "execution_log": state.get("execution_log", []) + screenshot_logs + [
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

        # ═══════════════════════════════════════════════════════════
        # Raw ADB Command Execution
        # ═══════════════════════════════════════════════════════════
        elif action_type == "raw_adb":
            raw_command = state.get("raw_command") or parameters.get("raw_command")
            if raw_command:
                logger.info(f"💻 Executing raw ADB command: {raw_command}")

                # Execute raw command via ADB tool
                result_dict = toolkit.adb.execute_raw_command(raw_command)

                # Convert dict to ActionResult-like object for consistency
                class RawCommandResult:
                    def __init__(self, result_dict):
                        self.success = result_dict.get("success", False)
                        self.output = result_dict.get("output", "")
                        self.error = result_dict.get("error", "")
                        self.action_type = "raw_adb"

                result = RawCommandResult(result_dict)
                logger.info(f"{'✅' if result.success else '❌'} Raw command: {'Success' if result.success else 'Failed'}")
            else:
                logger.error("❌ No raw command provided for raw_adb action")
                return {
                    **state,
                    "action_success": False,
                    "errors": state.get("errors", []) + ["No raw command provided"]
                }

        elif action_type == "swipe":
            # Get duration from state (set by plan_action)
            duration_ms = state.get("swipe_duration_ms") or parameters.get("duration_ms", 300)

            # Use coordinates from plan_action if available, otherwise auto-generate
            if coordinates and isinstance(coordinates, (list, tuple)) and len(coordinates) >= 4:
                start_x, start_y, end_x, end_y = coordinates[0], coordinates[1], coordinates[2], coordinates[3]
                swipe_speed = state.get("swipe_speed", "medium")
                logger.info(f"📱 Swipe (planned): ({start_x},{start_y}) → ({end_x},{end_y}) at {swipe_speed} speed ({duration_ms}ms)")
                result = toolkit.swipe(start_x, start_y, end_x, end_y, duration_ms)
            else:
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

                logger.info(f"📱 Swipe {direction}: ({start_x},{start_y}) → ({end_x},{end_y}) ({duration_ms}ms)")
                result = toolkit.swipe(start_x, start_y, end_x, end_y, duration_ms)
        
        elif action_type == "swipe_up":
            result = toolkit.swipe_up(parameters.get("distance", 500))
        
        elif action_type == "swipe_down":
            result = toolkit.swipe_down(parameters.get("distance", 500))

        # ═══════════════════════════════════════════════════════════
        # Drag and Drop (App Movement)
        # ═══════════════════════════════════════════════════════════
        elif action_type == "drag_drop":
            drag_params = state.get("drag_drop_params") or parameters.get("drag_drop")

            if drag_params:
                app_name = drag_params.get("app_name")
                pixel_offset = drag_params.get("pixel_offset")
                direction = drag_params.get("direction")

                logger.info("=" * 70)
                logger.info("🎯 DRAG-AND-DROP OPERATION STARTING")
                logger.info("=" * 70)
                logger.info(f"   App Name: {app_name}")
                logger.info(f"   Pixel Offset: {pixel_offset}")
                logger.info(f"   Direction: {direction}")
                logger.info("=" * 70)

                # Step 1: Find current app position via vision tool
                screenshot_path = state.get("current_screenshot")
                if not screenshot_path:
                    logger.error("❌ No screenshot available for drag-drop")
                    return {
                        **state,
                        "action_success": False,
                        "errors": state.get("errors", []) + ["No screenshot for drag-drop"]
                    }

                # Try multiple search variations to find the app
                search_variations = [
                    f"{app_name} app",
                    f"{app_name}",
                    app_name.split()[0] if ' ' in app_name else app_name,  # First word only
                    f"{app_name} icon"
                ]

                coords_result = None
                successful_search_term = None

                logger.info(f"🔍 Searching for app with {len(search_variations)} variations...")

                for idx, search_term in enumerate(search_variations, 1):
                    try:
                        logger.info(f"   Attempt {idx}/{len(search_variations)}: Searching for '{search_term}'")
                        coords_result = toolkit.vision.find_element_with_ai(screenshot_path, search_term)

                        if coords_result:
                            successful_search_term = search_term
                            logger.info(f"✅ FOUND! '{search_term}' located at ({coords_result.x}, {coords_result.y})")
                            break
                        else:
                            logger.warning(f"⚠️ Attempt {idx} failed: '{search_term}' not found")

                    except Exception as e:
                        logger.warning(f"⚠️ Attempt {idx} error: {e}")
                        continue

                if coords_result:
                    start_x, start_y = coords_result.x, coords_result.y

                    logger.info("=" * 70)
                    logger.info("✅ APP LOCATED SUCCESSFULLY")
                    logger.info(f"   Search Term: '{successful_search_term}'")
                    logger.info(f"   App Position: ({start_x}, {start_y})")
                    logger.info("=" * 70)

                    # Step 2: Calculate target position based on direction
                    if direction == "right":
                        end_x = start_x + pixel_offset
                        end_y = start_y
                    elif direction == "left":
                        end_x = start_x - pixel_offset
                        end_y = start_y
                    elif direction == "up":
                        end_x = start_x
                        end_y = start_y - pixel_offset
                    elif direction == "down":
                        end_x = start_x
                        end_y = start_y + pixel_offset
                    else:
                        logger.error(f"❌ Invalid direction: {direction}")
                        return {
                            **state,
                            "action_success": False,
                            "errors": state.get("errors", []) + [f"Invalid drag direction: {direction}"]
                        }

                    logger.info("=" * 70)
                    logger.info("🎯 EXECUTING DRAG-AND-DROP")
                    logger.info("=" * 70)
                    logger.info(f"   Start Position: ({start_x}, {start_y})")
                    logger.info(f"   End Position: ({end_x}, {end_y})")
                    logger.info(f"   Drag Distance: {pixel_offset}px {direction}")
                    logger.info(f"   Hold Duration: 2500ms (2.5 seconds)")
                    logger.info(f"   Method: Low-level touch events (motionevent)")
                    logger.info(f"   Sequence: DOWN → HOLD 2.5s → MOVE → UP")
                    logger.info("=" * 70)

                    # Step 3: Execute proper drag-and-drop gesture using low-level touch events
                    # This uses 'input motionevent' commands with precise timing:
                    # 1. DOWN at start position (x1, y1)
                    # 2. HOLD for 2500ms (2.5 seconds) to trigger AAOS launcher "lift mode"
                    # 3. MOVE to end position (x2, y2) while maintaining continuous touch
                    # 4. UP at end position
                    # This is the ONLY way that works on Android 14 AAOS car display emulator
                    result = toolkit.adb.drag_and_drop(start_x, start_y, end_x, end_y, hold_duration_ms=2500)

                    if result and hasattr(result, 'success') and result.success:
                        logger.info("✅ DRAG-AND-DROP COMPLETED SUCCESSFULLY")
                        logger.info("=" * 70)
                    else:
                        logger.warning("⚠️ Drag-and-drop command executed, result unclear")

                else:
                    logger.error("=" * 70)
                    logger.error(f"❌ APP NOT FOUND AFTER {len(search_variations)} ATTEMPTS")
                    logger.error(f"   App Name: {app_name}")
                    logger.error(f"   Search Variations Tried:")
                    for idx, term in enumerate(search_variations, 1):
                        logger.error(f"      {idx}. '{term}'")
                    logger.error("=" * 70)
                    logger.error("💡 SUGGESTION: Enter HITL mode to manually locate the app")

                    return {
                        **state,
                        "action_success": False,
                        "errors": state.get("errors", []) + [f"Could not find {app_name} app after {len(search_variations)} attempts"]
                    }

            else:
                logger.error("❌ No drag_drop parameters provided")
                return {
                    **state,
                    "action_success": False,
                    "errors": state.get("errors", []) + ["No drag_drop parameters"]
                }

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

        # ═══════════════════════════════════════════════════════════
        # REVERSAL STACK TRACKING (Cleanup System Phase 3)
        # ═══════════════════════════════════════════════════════════
        reversal_stack = state.get("reversal_stack", [])
        reversible_actions = state.get("reversible_actions", ["tap", "double_tap", "long_press", "swipe", "input_text"])

        # If action succeeded and is reversible, add to reversal stack
        if success and action_type in reversible_actions:
            from datetime import datetime

            reversal_entry = {
                "step": state.get("current_step", 0),
                "description": state.get("test_steps", [])[state.get("current_step", 0)] if state.get("test_steps") else "Unknown step",
                "action": action_type,
                "coordinates": coordinates,
                "target_element": target_element,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }

            # Add swipe-specific data for deterministic reversal
            if action_type == "swipe":
                reversal_entry["swipe_direction"] = state.get("swipe_direction")
                reversal_entry["swipe_speed"] = state.get("swipe_speed", "medium")
                reversal_entry["swipe_duration_ms"] = state.get("swipe_duration_ms", 300)

            # Add input_text-specific data
            if action_type == "input_text":
                reversal_entry["text_input"] = parameters.get("text", "")

            reversal_stack.append(reversal_entry)
            logger.debug(f"📚 Added to reversal stack: {action_type} at step {reversal_entry['step']}")

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
            "reversal_stack": reversal_stack,  # Update reversal stack in state
            "execution_log": state.get("execution_log", []) + [
                f"Executed: {action_type} - {'Success' if success else 'Failed'}"
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Execute ADB error: {e}")
        import traceback
        logger.error(traceback.format_exc())

        # CRITICAL FIX: Categorize error based on exception type
        error_message = f"Execute error: {e}"
        exception_str = str(e).lower()

        # Check if it's a device/infrastructure error
        if any(keyword in exception_str for keyword in [
            "device not found", "adb", "connection", "disconnected",
            "device offline", "no devices", "timeout"
        ]):
            error_category = "infrastructure"  # ErrorCategory.INFRASTRUCTURE
        else:
            # Generic system error
            error_category = "system"  # ErrorCategory.SYSTEM

        return _add_error_context(
            state,
            error_message=error_message,
            error_category=error_category,
            node_name="execute_adb",
            additional_context={
                "exception": str(e),
                "traceback": traceback.format_exc(),
                "action_type": action_type,
                "action_success": False,
                "last_action_result": {"error": str(e)}
            }
        )


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
            # CRITICAL FIX: Categorize as TECHNICAL error (CAPTURE)
            return _add_error_context(
                state,
                error_message="Verification screenshot failed",
                error_category="capture",  # ErrorCategory.CAPTURE
                node_name="verify_result",
                additional_context={
                    "verification_result": {"verified": False, "reason": "Screenshot failed"}
                }
            )
        
        # Get step information for verification tracking
        current_step = state.get("current_step", 0)
        test_id = state.get("test_id")
        test_steps = state.get("test_steps", [])
        step_description = ""
        if current_step < len(test_steps):
            step_description = test_steps[current_step]

        # ═════════════════════════════════════════════════════════
        # DYNAMIC VERIFICATION SYSTEM
        # ═════════════════════════════════════════════════════════

        from backend.tools.verification_tool import VerificationTool
        from backend.models.results import StepVerificationConfig
        from backend.models.enums import VerificationType
        verification_tool = VerificationTool()

        # Get step verification config (if available from Excel)
        step_verification_configs = state.get("step_verification_configs", [])
        current_step_config = None

        if current_step < len(step_verification_configs):
            config_dict = step_verification_configs[current_step]
            current_step_config = StepVerificationConfig.from_dict(config_dict)
            logger.info(f"🔧 Using verification config: {current_step_config.verification_type.value}")

        # Get reference image name - PRIORITY: config > AI mapping
        # NOTE: partial_image and ocr verification types don't need reference_image_name
        #       (they use crop_regions or expected_texts instead)
        reference_image_name = None

        # Only get reference image for full image verification
        if current_step_config:
            v_type = current_step_config.verification_type

            # Skip reference image lookup for partial_image, ocr, and no_verification
            if v_type == VerificationType.PARTIAL_IMAGE:
                logger.debug(f"📸 Skipping reference lookup - using crop regions")
            elif v_type == VerificationType.OCR:
                logger.debug(f"📸 Skipping reference lookup - using OCR texts")
            elif v_type == VerificationType.NONE:
                logger.debug(f"📸 Skipping reference lookup - no verification")
            else:
                # Full image verification - check config first, then AI fallback
                if current_step_config.reference_image_name:
                    reference_image_name = current_step_config.reference_image_name
                    logger.info(f"📸 Using reference from config: '{reference_image_name}'")
                else:
                    # Fall back to AI mapping only for image verification without explicit reference
                    reference_image_name = _get_reference_image_name(state)
        else:
            # No config - fall back to AI mapping (backward compatibility)
            reference_image_name = _get_reference_image_name(state)

        # Use dynamic verification if config available, otherwise fall back to comprehensive
        if current_step_config:
            dynamic_result = verification_tool.dynamic_verification(
                screenshot_path=after_screenshot,
                config=current_step_config,
                reference_image_name=reference_image_name,
                test_id=test_id,
                step_number=current_step + 1,
                step_description=step_description
            )

            # Convert dynamic result to verification_result format for compatibility
            verification_result = {
                'overall_passed': dynamic_result.passed,
                'ssim_verification': dynamic_result.ssim_result,
                'ocr_verification': dynamic_result.ocr_result.to_dict() if dynamic_result.ocr_result else None,
                'partial_verification': dynamic_result.partial_result.to_dict() if dynamic_result.partial_result else None,
                'verification_type': dynamic_result.verification_type.value,
                'message': dynamic_result.message
            }
        else:
            # Fall back to comprehensive verification (backward compatibility)
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

        # Get verification type for logging
        verification_type = verification_result.get('verification_type', 'image_verification')
        overall_passed = verification_result.get('overall_passed', False)

        # Initialize result variables to avoid "referenced before assignment" errors
        ssim_result = None
        pixel_result = None
        ai_result = None

        # Log based on verification type
        if verification_type == 'ocr':
            ocr_result = verification_result.get('ocr_verification')
            if ocr_result:
                if overall_passed:
                    logger.info(f"✅ OCR VERIFICATION: PASSED - All texts found")
                    logger.info(f"   Found: {ocr_result.get('found_texts', [])}")
                else:
                    logger.error(f"❌ OCR VERIFICATION: FAILED - Missing texts")
                    logger.error(f"   Missing: {ocr_result.get('missing_texts', [])}")

        elif verification_type == 'partial_image':
            partial_result = verification_result.get('partial_verification')
            if partial_result:
                if overall_passed:
                    logger.info(f"✅ PARTIAL IMAGE VERIFICATION: PASSED - All regions match")
                    logger.info(f"   Overall SSIM: {partial_result.get('overall_ssim', 0):.4f}")
                else:
                    logger.error(f"❌ PARTIAL IMAGE VERIFICATION: FAILED")
                    logger.error(f"   Failed regions: {partial_result.get('failed_regions', [])}")
                # Create ssim_result from partial verification for history tracking compatibility
                ssim_result = {
                    'passed': overall_passed,
                    'similarity': partial_result.get('overall_ssim', 0),
                    'threshold': 0.85,
                    'reference_found': True,
                    'comparison_image': partial_result.get('comparison_image')
                }

        elif verification_type == 'no_verification':
            logger.info("⏭️ NO VERIFICATION: Step skipped (as configured)")

        else:
            # Full image SSIM verification (default)
            ssim_result = verification_result.get('ssim_verification')

            if ssim_result:
                if ssim_result.get('passed', False):
                    logger.info(f"✅ PRIMARY (SSIM): PASSED - Similarity: {ssim_result.get('similarity', 0):.4f}")
                else:
                    if ssim_result.get('reference_found', True):
                        logger.error(f"❌ PRIMARY (SSIM): FAILED - Similarity: {ssim_result.get('similarity', 0):.4f} < {ssim_result.get('threshold', 0.85)}")
                    else:
                        logger.warning(f"⚠️ PRIMARY (SSIM): NO REFERENCE IMAGE - '{reference_image_name}'")
                        # If no reference image, fall back to pixel change for pass/fail
                        pixel_result = verification_result.get('pixel_verification')
                        if pixel_result and pixel_result.get('changed', False):
                            logger.info(f"✅ FALLBACK: Screen changed {pixel_result.get('change_percentage', 0):.2f}%")
                            overall_passed = True

            # SECONDARY: Pixel Change (Informational)
            pixel_result = verification_result.get('pixel_verification')
            if pixel_result:
                logger.info(f"📊 SECONDARY (Pixel Change): {pixel_result.get('change_percentage', 0):.2f}% changed")

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
            # CRITICAL FIX (Bug #1): Don't modify use_learned here - preserve it across steps
            # The verification result should NOT affect whether we use learned solutions
            # "use_learned" should only be disabled when direct_execute explicitly can't proceed
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

        # CRITICAL FIX: Categorize error based on exception type
        exception_str = str(e).lower()

        # Check if it's a system/technical error
        if any(keyword in exception_str for keyword in [
            "file not found", "permission", "i/o error", "cannot open",
            "image", "opencv", "ssim"
        ]):
            error_category = "system"  # ErrorCategory.SYSTEM (image processing failure)
        else:
            # Verification logic failure - could be retried
            error_category = "verification_failed"  # ErrorCategory.VERIFICATION_FAILED

        return _add_error_context(
            state,
            error_message=f"Verify result error: {e}",
            error_category=error_category,
            node_name="verify_result",
            additional_context={
                "exception": str(e),
                "traceback": traceback.format_exc(),
                "verification_result": {"verified": False, "error": str(e)}
            }
        )


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
        
        # Log what we're saving (ENHANCED: show all important fields)
        logger.info(f"   Steps to save: {len(executed_steps)}")
        for step in executed_steps:
            action = step.get('action')
            target = step.get('target_element')
            coords = step.get('coordinates')

            # Build detailed log message
            log_msg = f"      Step {step.get('step')}: {action}"

            # Add target element
            if target:
                log_msg += f" on '{target}'"

            # Add coordinates with proper format
            if coords:
                if action == "swipe" and isinstance(coords, (list, tuple)) and len(coords) >= 4:
                    log_msg += f" from ({coords[0]}, {coords[1]}) → ({coords[2]}, {coords[3]})"
                    if step.get('swipe_duration_ms'):
                        log_msg += f" at {step.get('swipe_duration_ms')}ms"
                    if step.get('swipe_speed'):
                        log_msg += f" ({step.get('swipe_speed')} speed)"
                elif isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    log_msg += f" at ({coords[0]}, {coords[1]})"
                    if action == "long_press" and step.get('long_press_duration_seconds'):
                        log_msg += f" for {step.get('long_press_duration_seconds')}s"

            # Add input text if present
            if step.get('input_text'):
                log_msg += f" [text: '{step.get('input_text')}']"

            logger.info(log_msg)

        # ═══════════════════════════════════════════════════════════
        # CLEANUP SYSTEM: Include cleanup results in learned solution
        # ═══════════════════════════════════════════════════════════
        cleanup_results = state.get("cleanup_results", [])
        if cleanup_results:
            logger.info(f"   Cleanup actions to save: {len(cleanup_results)}")
            for cleanup in cleanup_results:
                cleanup_type = cleanup.get("cleanup_type_executed")
                reversal_count = cleanup.get("reversal_count", 0)
                logger.info(f"      Cleanup: {cleanup_type} (reversed {reversal_count} action(s))")

        # Save to RAG (including cleanup results)
        learned_solution_data = {
            "test_id": test_id,
            "title": state.get("test_description", f"Test {test_id}"),
            "component": "Learned",
            "steps": executed_steps,
            "cleanup_results": cleanup_results  # NEW: Store cleanup actions
        }

        success = toolkit.rag.save_learned_solution(**learned_solution_data)
        
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

def _infer_action_subtype(state: AgentState) -> str:
    """
    Infer action subtype for learned solution storage.

    Returns:
        - "element_based": Action used vision/OCR to find element
        - "coordinate_based": Action used explicit coordinates
        - "raw_command": Raw ADB command execution
        - "app_movement": Drag-drop app repositioning
    """
    action_type = state.get("action_type")
    coordinate_source = state.get("coordinate_source")

    if action_type == "raw_adb":
        return "raw_command"
    elif action_type == "drag_drop":
        return "app_movement"
    elif coordinate_source == "explicit":
        return "coordinate_based"
    else:
        return "element_based"


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
    # CRITICAL: For swipe actions, we need all 4 coordinates (x1, y1, x2, y2)
    # For tap/long_press/double_tap, we only need 2 coordinates (x, y)
    target_coords = state.get("target_coordinates")
    action_type = state.get("action_type") or state.get("planned_action")
    coords_tuple = None

    if target_coords:
        if isinstance(target_coords, dict):
            coords_tuple = (target_coords.get("x"), target_coords.get("y"))
        elif hasattr(target_coords, 'x') and hasattr(target_coords, 'y'):
            coords_tuple = (target_coords.x, target_coords.y)
        elif isinstance(target_coords, (list, tuple)):
            # For swipe: capture all 4 coordinates
            if action_type == "swipe" and len(target_coords) >= 4:
                coords_tuple = (target_coords[0], target_coords[1], target_coords[2], target_coords[3])
            # For tap/long_press/double_tap: capture 2 coordinates
            elif len(target_coords) >= 2:
                coords_tuple = (target_coords[0], target_coords[1])
    
    # Capture what was actually executed (Enhanced with Phase 1 fields)
    # CRITICAL FIX: action_params can be None, so use {} as default and add safety checks
    action_params = state.get("action_parameters") or {}

    # CRITICAL FIX: Calculate long_press_duration_seconds with proper default
    # For long_press actions, ALWAYS store a valid duration (never None)
    long_press_duration = state.get("long_press_duration_seconds")
    if not long_press_duration and action_params and action_params.get("duration_ms"):
        long_press_duration = action_params.get("duration_ms") / 1000.0
    # If action is long_press and duration is still None, use 1.0 second default
    if not long_press_duration and action_type == "long_press":
        long_press_duration = 1.0

    executed_step = {
        "step": current_step,  # Use 1-based indexing
        "description": step_description,
        "action": state.get("action_type") or state.get("planned_action"),
        "action_subtype": _infer_action_subtype(state),
        "target_element": state.get("target_element"),
        "coordinates": coords_tuple,
        "coordinate_source": state.get("coordinate_source", "vision_tool"),
        "input_text": action_params.get("text") if action_params else None,
        "raw_command": state.get("raw_command") or (action_params.get("raw_command") if action_params else None),
        "swipe_speed": state.get("swipe_speed") or (action_params.get("swipe_speed") if action_params else None),
        "swipe_duration_ms": state.get("swipe_duration_ms") or (action_params.get("duration_ms") if action_params else None),
        "long_press_duration_seconds": long_press_duration,  # Use calculated value
        "drag_drop_params": state.get("drag_drop_params") or (action_params.get("drag_drop") if action_params else None),
        "swipe_direction": state.get("swipe_direction") or (action_params.get("swipe_direction") if action_params else None),  # Add swipe direction
        "swipe_start_position": state.get("swipe_start_position") or (action_params.get("swipe_start_position") if action_params else None),  # NEW: Add swipe spatial position
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
# Node: Handle Technical Error (HITL Architecture Fix)
# ═══════════════════════════════════════════════════════════════

def handle_technical_error(state: AgentState) -> AgentState:
    """
    Handle technical errors (infrastructure/system) by ending test with ERROR status.

    CRITICAL ARCHITECTURE FIX:
    - Technical errors (screenshot failures, device disconnects, system errors) should END the test
    - These errors CANNOT be fixed by HITL, so DO NOT trigger human intervention
    - Set status to ERROR or BLOCKED based on error type

    Args:
        state: Current agent state

    Returns:
        Updated state with ERROR/BLOCKED status and should_continue=False
    """
    from backend.models.enums import ErrorCategory

    last_error_category = state.get("last_error_category")
    error_contexts = state.get("error_contexts", [])
    errors = state.get("errors", [])

    # Get error details
    error_message = errors[-1] if errors else "Unknown technical error"
    error_category_name = last_error_category or "unknown"

    logger.error("=" * 70)
    logger.error("🚨 TECHNICAL ERROR - ENDING TEST")
    logger.error("=" * 70)
    logger.error(f"   Category: {error_category_name}")
    logger.error(f"   Message: {error_message}")
    logger.error(f"   Technical errors count: {state.get('technical_error_count', 0)}")
    logger.error("=" * 70)
    logger.error("   ⚠️ Technical errors cannot be fixed by human intervention")
    logger.error("   ⚠️ Test execution stopped - please fix system/infrastructure issues")
    logger.error("=" * 70)

    # Determine status based on error category
    try:
        error_cat = ErrorCategory(error_category_name)
        if error_cat in [ErrorCategory.INFRASTRUCTURE, ErrorCategory.TIMEOUT]:
            status = AgentStatus.BLOCKED  # Blocked by infrastructure
        else:
            status = AgentStatus.ERROR  # General system error
    except (ValueError, KeyError):
        status = AgentStatus.ERROR  # Default to ERROR

    return {
        **state,
        "status": status,
        "should_continue": False,
        "execution_log": state.get("execution_log", []) + [
            f"Technical error encountered: {error_category_name}",
            f"Test ended with {status.value} status",
            "Technical errors require system/infrastructure fixes"
        ]
    }


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTION: Determine Test Status
# ═══════════════════════════════════════════════════════════════

def determine_test_status(state: AgentState) -> str:
    """
    Determine final test status based on execution state.

    CRITICAL FIX: Prioritizes completion status over non-critical errors.
    Screenshot retry warnings and other recoverable errors should not fail the test.

    Logic:
    1. If waiting for HITL → "waiting"
    2. If all steps completed successfully → "passed"
    3. If current_step < total_steps → "incomplete"
    4. If errors exist AND test incomplete → "failed"
    5. Otherwise → "unknown"

    Args:
        state: Current agent state

    Returns:
        Status string: "passed", "failed", "incomplete", or "waiting"
    """
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    errors = state.get("errors", [])
    executed_steps = state.get("executed_steps", [])

    # Priority 1: Check if waiting for HITL
    if state.get("waiting_for_hitl") or state.get("execution_mode") == "hitl_waiting":
        return "waiting"

    # Priority 2: Check if all steps completed successfully
    # CRITICAL FIX: If all steps completed, test passes even if there were non-critical errors
    # (like screenshot retry warnings that didn't prevent execution)
    if total_steps > 0 and current_step >= total_steps:
        # All steps completed - check if any actions actually failed
        failed_actions = [step for step in executed_steps if not step.get("success", True)]

        if failed_actions:
            return "failed"  # Action execution failures are critical

        # Check for critical errors (filter out screenshot retry warnings)
        critical_errors = [e for e in errors if not any(
            recoverable in e for recoverable in [
                "Screenshot capture failed",  # Recoverable - retries and continues
                "No screenshot for AI analysis"  # Recoverable - can plan without screenshot
            ]
        )]

        if critical_errors:
            return "failed"  # Critical errors

        return "passed"  # All steps completed successfully

    # Priority 3: Check if incomplete
    if total_steps > 0 and current_step < total_steps:
        return "incomplete"

    # Priority 4: Errors exist but test didn't complete
    if errors:
        return "failed"

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


# ═══════════════════════════════════════════════════════════════
# CLEANUP SYSTEM NODES (Phase 4)
# ═══════════════════════════════════════════════════════════════


def cleanup_dispatcher(state: AgentState) -> AgentState:
    """
    Cleanup dispatcher node - routes to appropriate cleanup handler.

    This is the entry point for in-step cleanup. It loads the current step's
    cleanup config and prepares state for routing.
    """
    logger.info("🧹 Cleanup dispatcher: Determining cleanup strategy")

    current_step = state.get("current_step", 0)
    step_cleanup_configs = state.get("step_cleanup_configs", [])

    # Get current step's cleanup config
    if current_step < len(step_cleanup_configs):
        current_cleanup_config = step_cleanup_configs[current_step]
    else:
        # No cleanup config for this step
        from backend.models.results import StepCleanupConfig
        current_cleanup_config = StepCleanupConfig.default().to_dict()

    cleanup_type = current_cleanup_config.get("cleanup_type", "none")
    cleanup_trigger = current_cleanup_config.get("cleanup_trigger", "end_of_test")

    logger.info(f"   Cleanup type: {cleanup_type}")
    logger.info(f"   Cleanup trigger: {cleanup_trigger}")
    logger.info(f"   Cleanup phase: in_step")

    return {
        **state,
        "current_cleanup_config": current_cleanup_config,
        "cleanup_in_progress": True,
        "cleanup_phase": "in_step",
        "cleanup_retry_count": 0,
        "cleanup_fallback_attempted": False
    }


def cleanup_home(state: AgentState) -> AgentState:
    """
    Cleanup home node - press home button to return to home screen.

    This is the simplest and most reliable cleanup method. It's also used
    as the default fallback when other cleanup methods fail.
    """
    logger.info("🏠 Cleanup: Pressing HOME button")

    import time
    from datetime import datetime

    start_time = time.time()

    try:
        # Press home button
        result = toolkit.press_home()

        if result and result.success:
            logger.info("✅ Cleanup home: Success")

            # Create cleanup result
            from backend.models.results import DynamicCleanupResult
            from backend.models.enums import CleanupType, CleanupTrigger

            cleanup_config = state.get("current_cleanup_config", {})
            cleanup_result = DynamicCleanupResult(
                success=True,
                cleanup_type_executed=CleanupType.RETURN_HOME,
                cleanup_trigger=CleanupTrigger(cleanup_config.get("cleanup_trigger", "end_of_test")),
                execution_time_seconds=time.time() - start_time
            )

            cleanup_results = state.get("cleanup_results", [])
            cleanup_results.append(cleanup_result.to_dict())

            return {
                **state,
                "cleanup_in_progress": False,
                "cleanup_results": cleanup_results,
                "in_step_cleanup_count": state.get("in_step_cleanup_count", 0) + 1,
                "execution_log": state.get("execution_log", []) + ["Cleanup: Pressed HOME"]
            }
        else:
            logger.warning("⚠️ Cleanup home: Failed")
            raise Exception("Home button press failed")

    except Exception as e:
        logger.error(f"❌ Cleanup home error: {e}")

        # Check if we should try fallback
        cleanup_retry_count = state.get("cleanup_retry_count", 0)
        max_retries = state.get("current_cleanup_config", {}).get("max_retries", 3)

        if cleanup_retry_count < max_retries:
            # Retry
            return {
                **state,
                "cleanup_retry_count": cleanup_retry_count + 1,
                "execution_log": state.get("execution_log", []) + [f"Cleanup home failed, retry {cleanup_retry_count + 1}/{max_retries}"]
            }
        else:
            # Mark as failed
            logger.error(f"❌ Cleanup home failed after {max_retries} retries")
            return {
                **state,
                "cleanup_in_progress": False,
                "cleanup_failed": True,
                "errors": state.get("errors", []) + [f"Cleanup home failed: {e}"]
            }


def cleanup_reverse_action(state: AgentState) -> AgentState:
    """
    Cleanup reverse action node - reverse the last action(s) performed.

    CORE REVERSAL LOGIC:
    - Swipe: Deterministic coordinate swap (x1,y1,x2,y2) → (x2,y2,x1,y1)
    - Tap: AI-driven reversal strategy (toggle, close, or skip)
    - Input text: Select all + delete
    """
    logger.info("🔄 Cleanup: Reversing last action")

    import time
    from datetime import datetime

    start_time = time.time()

    try:
        reversal_stack = state.get("reversal_stack", [])

        if not reversal_stack:
            logger.warning("⚠️ Reversal stack is empty, nothing to reverse")
            return {
                **state,
                "cleanup_in_progress": False,
                "execution_log": state.get("execution_log", []) + ["Cleanup: No actions to reverse"]
            }

        # Pop last action from stack
        last_action = reversal_stack.pop()

        action_type = last_action.get("action")
        coordinates = last_action.get("coordinates")
        target_element = last_action.get("target_element")

        logger.info(f"   Reversing: {action_type} on '{target_element}'")

        reversed_actions = []

        # ═══════════════════════════════════════════════════════════
        # SWIPE: Deterministic reversal (coordinate swap)
        # ═══════════════════════════════════════════════════════════
        if action_type == "swipe":
            if coordinates and len(coordinates) >= 4:
                x1, y1, x2, y2 = coordinates[0], coordinates[1], coordinates[2], coordinates[3]

                # DETERMINISTIC: Swap start and end
                reversed_coords = (x2, y2, x1, y1)

                duration_ms = last_action.get("swipe_duration_ms", 300)

                logger.info(f"   Original: ({x1},{y1}) → ({x2},{y2})")
                logger.info(f"   Reversed: ({x2},{y2}) → ({x1},{y1})")

                result = toolkit.swipe(x2, y2, x1, y1, duration_ms)

                if result and result.success:
                    reversed_actions.append({
                        "original_action": "swipe",
                        "reversal_method": "coordinate_swap",
                        "reversed_coords": reversed_coords,
                        "success": True
                    })
                else:
                    raise Exception("Swipe reversal failed")
            else:
                raise Exception("Invalid swipe coordinates for reversal")

        # ═══════════════════════════════════════════════════════════
        # TAP: AI-driven reversal strategy
        # ═══════════════════════════════════════════════════════════
        elif action_type in ["tap", "double_tap", "long_press"]:
            # Capture current screenshot for AI analysis
            screenshot_path = state.get("current_screenshot")

            if not screenshot_path:
                # Capture new screenshot
                screenshot_path = toolkit.screenshot.capture()

            # Ask AI to determine reversal strategy
            reversal_strategy = _ai_tap_reversal_decision(
                screenshot_path,
                action_type,
                target_element,
                last_action.get("description", "")
            )

            logger.info(f"   AI reversal strategy: {reversal_strategy['strategy']}")

            if reversal_strategy["strategy"] == "same_tap":
                # Toggle action (e.g., AC ON → AC OFF)
                x, y = coordinates[0], coordinates[1]
                result = toolkit.tap(x, y)

                reversed_actions.append({
                    "original_action": action_type,
                    "reversal_method": "same_tap",
                    "reasoning": reversal_strategy["reasoning"],
                    "success": result.success if result else False
                })

            elif reversal_strategy["strategy"] == "different_tap":
                # Tap different element (e.g., close button)
                target = reversal_strategy["target_element"]
                coords_result = toolkit.vision.find_element_with_ai(screenshot_path, target)

                if coords_result:
                    result = toolkit.tap(coords_result.x, coords_result.y)

                    reversed_actions.append({
                        "original_action": action_type,
                        "reversal_method": "different_tap",
                        "target": target,
                        "coordinates": (coords_result.x, coords_result.y),
                        "success": result.success if result else False
                    })
                else:
                    raise Exception(f"Could not find reversal target: {target}")

            elif reversal_strategy["strategy"] == "press_back":
                # Press back button
                result = toolkit.press_back()

                reversed_actions.append({
                    "original_action": action_type,
                    "reversal_method": "press_back",
                    "success": result.success if result else False
                })

            else:
                # no_tap strategy - already reversed (e.g., back button already pressed)
                logger.info("   No reversal needed (AI determined)")
                reversed_actions.append({
                    "original_action": action_type,
                    "reversal_method": "no_tap",
                    "reasoning": reversal_strategy["reasoning"],
                    "success": True
                })

        # ═══════════════════════════════════════════════════════════
        # INPUT_TEXT: Select all + delete
        # ═══════════════════════════════════════════════════════════
        elif action_type == "input_text":
            # Select all (Ctrl+A) and delete
            result1 = toolkit.adb.press_key("ctrl+a")  # Select all
            time.sleep(0.2)
            result2 = toolkit.adb.press_key("del")  # Delete

            reversed_actions.append({
                "original_action": action_type,
                "reversal_method": "select_all_delete",
                "success": True
            })

        else:
            logger.warning(f"⚠️ Action type '{action_type}' not reversible")

        # ═══════════════════════════════════════════════════════════
        # REVERSE_AND_HOME: Also press home after reversal
        # ═══════════════════════════════════════════════════════════
        cleanup_config = state.get("current_cleanup_config", {})
        cleanup_type = cleanup_config.get("cleanup_type", "reverse_action")

        if cleanup_type == "reverse_and_home":
            logger.info("🏠 Cleanup: Also pressing HOME (reverse_and_home)")
            home_result = toolkit.press_home()
            if home_result and home_result.success:
                logger.info("✅ HOME pressed after reversal")
            else:
                logger.warning("⚠️ HOME press failed after reversal")

        # Create cleanup result
        from backend.models.results import DynamicCleanupResult
        from backend.models.enums import CleanupType, CleanupTrigger

        executed_type = CleanupType.REVERSE_AND_HOME if cleanup_type == "reverse_and_home" else CleanupType.REVERSE_ACTION
        cleanup_result = DynamicCleanupResult(
            success=True,
            cleanup_type_executed=executed_type,
            cleanup_trigger=CleanupTrigger(cleanup_config.get("cleanup_trigger", "end_of_test")),
            actions_reversed=reversed_actions,
            reversal_count=len(reversed_actions),
            execution_time_seconds=time.time() - start_time
        )

        cleanup_results = state.get("cleanup_results", [])
        cleanup_results.append(cleanup_result.to_dict())

        logger.info(f"✅ Cleanup reversed {len(reversed_actions)} action(s)")

        return {
            **state,
            "cleanup_in_progress": False,
            "reversal_stack": reversal_stack,  # Updated stack
            "cleanup_results": cleanup_results,
            "in_step_cleanup_count": state.get("in_step_cleanup_count", 0) + 1,
            "execution_log": state.get("execution_log", []) + [f"Cleanup: Reversed {len(reversed_actions)} action(s)"]
        }

    except Exception as e:
        logger.error(f"❌ Cleanup reverse action error: {e}")

        # Check if we should try fallback
        cleanup_retry_count = state.get("cleanup_retry_count", 0)
        cleanup_fallback_attempted = state.get("cleanup_fallback_attempted", False)
        max_retries = state.get("current_cleanup_config", {}).get("max_retries", 3)

        if cleanup_retry_count < max_retries:
            # Retry
            return {
                **state,
                "cleanup_retry_count": cleanup_retry_count + 1,
                "execution_log": state.get("execution_log", []) + [f"Cleanup reversal failed, retry {cleanup_retry_count + 1}/{max_retries}"]
            }
        elif not cleanup_fallback_attempted:
            # Try fallback (return home)
            logger.warning("⚠️ Cleanup reversal failed, falling back to return_home")
            from backend.models.enums import CleanupType
            return {
                **state,
                "current_cleanup_config": {
                    **state.get("current_cleanup_config", {}),
                    "cleanup_type": CleanupType.RETURN_HOME.value
                },
                "cleanup_fallback_attempted": True,
                "cleanup_retry_count": 0
            }
        else:
            # Mark as failed
            logger.error(f"❌ Cleanup reversal failed after fallback")
            return {
                **state,
                "cleanup_in_progress": False,
                "cleanup_failed": True,
                "errors": state.get("errors", []) + [f"Cleanup reversal failed: {e}"]
            }


def cleanup_ai_driven(state: AgentState) -> AgentState:
    """
    Cleanup AI-driven node - let AI decide the cleanup strategy.

    AI analyzes the test context and current screen to determine the best
    cleanup approach.
    """
    logger.info("🤖 Cleanup: AI-driven decision")

    try:
        # Capture current screenshot
        screenshot_path = state.get("current_screenshot")
        if not screenshot_path:
            screenshot_path = toolkit.screenshot.capture()

        # Build context for AI
        test_id = state.get("test_id", "Unknown")
        component = state.get("test_steps", [""])[0].split(":")[0] if state.get("test_steps") else "Unknown"
        current_step = state.get("current_step", 0)
        executed_steps = state.get("executed_steps", [])

        ai_context = state.get("current_cleanup_config", {}).get("ai_context", "")

        # Ask AI to decide cleanup strategy
        cleanup_decision = _ai_cleanup_decision(
            screenshot_path,
            test_id,
            component,
            current_step,
            executed_steps,
            ai_context
        )

        logger.info(f"   AI decision: {cleanup_decision['cleanup_strategy']}")
        logger.info(f"   Confidence: {cleanup_decision['confidence']}")
        logger.info(f"   Reasoning: {cleanup_decision['reasoning']}")

        # Store AI decision in state for routing
        from backend.models.enums import CleanupType
        cleanup_strategy = cleanup_decision["cleanup_strategy"]

        return {
            **state,
            "ai_cleanup_decision": cleanup_strategy,
            "ai_cleanup_confidence": cleanup_decision["confidence"],
            "current_cleanup_config": {
                **state.get("current_cleanup_config", {}),
                "cleanup_type": cleanup_strategy  # Route to chosen strategy
            },
            "execution_log": state.get("execution_log", []) + [
                f"AI cleanup decision: {cleanup_strategy} (confidence: {cleanup_decision['confidence']})"
            ]
        }

    except Exception as e:
        logger.error(f"❌ AI cleanup decision error: {e}")

        # Fallback to return_home
        logger.warning("⚠️ AI cleanup failed, falling back to return_home")
        from backend.models.enums import CleanupType
        return {
            **state,
            "ai_cleanup_decision": "return_home",
            "ai_cleanup_confidence": 0.5,
            "current_cleanup_config": {
                **state.get("current_cleanup_config", {}),
                "cleanup_type": CleanupType.RETURN_HOME.value
            },
            "errors": state.get("errors", []) + [f"AI cleanup error: {e}"]
        }


def cleanup_close_dialog(state: AgentState) -> AgentState:
    """
    Cleanup close dialog node - close dialog/popup and return home.

    Searches for common close buttons (X, Close, Cancel) and taps them.
    """
    logger.info("❌ Cleanup: Closing dialog")

    import time
    from datetime import datetime

    start_time = time.time()

    try:
        # Capture current screenshot
        screenshot_path = state.get("current_screenshot")
        if not screenshot_path:
            screenshot_path = toolkit.screenshot.capture()

        # Get dialog close button text from config
        cleanup_config = state.get("current_cleanup_config", {})
        dialog_button_text = cleanup_config.get("dialog_close_button_text", "")

        # Default close button targets
        close_targets = [
            "X button",
            "Close button",
            "Cancel button",
            "OK button",
            "Dismiss"
        ]

        # Add custom button if specified
        if dialog_button_text:
            close_targets.insert(0, dialog_button_text)

        # Try to find and tap close button
        close_success = False

        for target in close_targets:
            logger.info(f"   Searching for: {target}")

            coords_result = toolkit.vision.find_element_with_ai(screenshot_path, target)

            if coords_result:
                logger.info(f"✅ Found '{target}' at ({coords_result.x}, {coords_result.y})")

                result = toolkit.tap(coords_result.x, coords_result.y)

                if result and result.success:
                    close_success = True
                    logger.info(f"✅ Tapped '{target}'")
                    break

        if not close_success:
            logger.warning("⚠️ Could not find close button, pressing back")
            result = toolkit.press_back()

        # Also press home for good measure
        time.sleep(0.5)
        toolkit.press_home()

        # Create cleanup result
        from backend.models.results import DynamicCleanupResult
        from backend.models.enums import CleanupType, CleanupTrigger

        cleanup_result = DynamicCleanupResult(
            success=True,
            cleanup_type_executed=CleanupType.CLOSE_DIALOG,
            cleanup_trigger=CleanupTrigger(cleanup_config.get("cleanup_trigger", "end_of_test")),
            execution_time_seconds=time.time() - start_time
        )

        cleanup_results = state.get("cleanup_results", [])
        cleanup_results.append(cleanup_result.to_dict())

        logger.info("✅ Cleanup close dialog: Success")

        return {
            **state,
            "cleanup_in_progress": False,
            "cleanup_results": cleanup_results,
            "in_step_cleanup_count": state.get("in_step_cleanup_count", 0) + 1,
            "execution_log": state.get("execution_log", []) + ["Cleanup: Closed dialog and pressed HOME"]
        }

    except Exception as e:
        logger.error(f"❌ Cleanup close dialog error: {e}")

        # Fallback to return_home
        logger.warning("⚠️ Cleanup close dialog failed, falling back to return_home")
        from backend.models.enums import CleanupType
        return {
            **state,
            "current_cleanup_config": {
                **state.get("current_cleanup_config", {}),
                "cleanup_type": CleanupType.RETURN_HOME.value
            },
            "cleanup_fallback_attempted": True,
            "errors": state.get("errors", []) + [f"Cleanup close dialog error: {e}"]
        }


def cleanup_restore_state(state: AgentState) -> AgentState:
    """
    Cleanup restore state node - restore to previous state by reversing N actions.

    Reverses multiple actions from the reversal stack in LIFO order, then
    returns to home screen.
    """
    logger.info("🔄 Cleanup: Restoring previous state")

    import time
    from datetime import datetime

    start_time = time.time()

    try:
        reversal_stack = state.get("reversal_stack", [])
        cleanup_config = state.get("current_cleanup_config", {})
        reverse_count = cleanup_config.get("reverse_count")

        if not reversal_stack:
            logger.warning("⚠️ Reversal stack is empty, nothing to restore")
            # Just return home
            toolkit.press_home()

            return {
                **state,
                "cleanup_in_progress": False,
                "execution_log": state.get("execution_log", []) + ["Cleanup: No actions to restore, pressed HOME"]
            }

        # Determine how many actions to reverse
        if reverse_count is None:
            # Reverse all actions
            actions_to_reverse = len(reversal_stack)
        else:
            # Reverse specified count
            actions_to_reverse = min(reverse_count, len(reversal_stack))

        logger.info(f"   Reversing {actions_to_reverse} action(s)")

        reversed_actions = []

        # Reverse actions in LIFO order
        for i in range(actions_to_reverse):
            if not reversal_stack:
                break

            # Use cleanup_reverse_action logic for each action
            # (Simplified here - in production, extract reversal logic to helper function)

            last_action = reversal_stack.pop()
            action_type = last_action.get("action")

            logger.info(f"   [{i+1}/{actions_to_reverse}] Reversing: {action_type}")

            # Simple reversal (detailed logic same as cleanup_reverse_action)
            if action_type == "swipe":
                coordinates = last_action.get("coordinates")
                if coordinates and len(coordinates) >= 4:
                    x1, y1, x2, y2 = coordinates[0], coordinates[1], coordinates[2], coordinates[3]
                    duration_ms = last_action.get("swipe_duration_ms", 300)
                    result = toolkit.swipe(x2, y2, x1, y1, duration_ms)

                    reversed_actions.append({
                        "action": action_type,
                        "reversal_method": "coordinate_swap",
                        "success": result.success if result else False
                    })

            elif action_type in ["tap", "double_tap", "long_press"]:
                # For simplicity, just press back
                result = toolkit.press_back()
                time.sleep(0.3)

                reversed_actions.append({
                    "action": action_type,
                    "reversal_method": "press_back",
                    "success": result.success if result else False
                })

        # Return to home after restoration
        time.sleep(0.5)
        toolkit.press_home()

        # Create cleanup result
        from backend.models.results import DynamicCleanupResult
        from backend.models.enums import CleanupType, CleanupTrigger

        cleanup_result = DynamicCleanupResult(
            success=True,
            cleanup_type_executed=CleanupType.RESTORE_STATE,
            cleanup_trigger=CleanupTrigger(cleanup_config.get("cleanup_trigger", "end_of_test")),
            actions_reversed=reversed_actions,
            reversal_count=len(reversed_actions),
            execution_time_seconds=time.time() - start_time
        )

        cleanup_results = state.get("cleanup_results", [])
        cleanup_results.append(cleanup_result.to_dict())

        logger.info(f"✅ Cleanup restored {len(reversed_actions)} action(s)")

        return {
            **state,
            "cleanup_in_progress": False,
            "reversal_stack": reversal_stack,  # Updated stack
            "cleanup_results": cleanup_results,
            "in_step_cleanup_count": state.get("in_step_cleanup_count", 0) + 1,
            "execution_log": state.get("execution_log", []) + [f"Cleanup: Restored {len(reversed_actions)} action(s)"]
        }

    except Exception as e:
        logger.error(f"❌ Cleanup restore state error: {e}")

        # Fallback to return_home
        logger.warning("⚠️ Cleanup restore state failed, falling back to return_home")
        from backend.models.enums import CleanupType
        return {
            **state,
            "current_cleanup_config": {
                **state.get("current_cleanup_config", {}),
                "cleanup_type": CleanupType.RETURN_HOME.value
            },
            "cleanup_fallback_attempted": True,
            "errors": state.get("errors", []) + [f"Cleanup restore state error: {e}"]
        }


def cleanup_end_of_test(state: AgentState) -> AgentState:
    """
    Cleanup end of test node - orchestrator for end-of-test cleanup.

    PRIORITY:
    1. If post_condition_intents exist → set cleanup_type to "post_condition"
       (routes to cleanup_post_condition node)
    2. Else → use explicit cleanup configs from step/test level
    3. No default fallback — only what's explicitly configured
    """
    logger.info("🏁 Cleanup: End-of-test cleanup")

    # ═══════════════════════════════════════════════════════════
    # PRIORITY 1: Post condition intents override everything
    # ═══════════════════════════════════════════════════════════
    post_condition_intents = state.get("post_condition_intents")
    if post_condition_intents:
        logger.info(f"   POST CONDITION: {len(post_condition_intents)} raw ADB intents found")
        logger.info("   Routing to cleanup_post_condition (overrides all other cleanup)")
        for i, intent in enumerate(post_condition_intents):
            logger.info(f"     Intent {i+1}: {intent}")

        return {
            **state,
            "current_cleanup_config": {"cleanup_type": "post_condition"},
            "cleanup_in_progress": True,
            "cleanup_phase": "end_of_test",
            "cleanup_retry_count": 0,
            "cleanup_fallback_attempted": False,
            "end_of_test_cleanup_executed": True
        }

    # ═══════════════════════════════════════════════════════════
    # PRIORITY 2: Explicit cleanup configs
    # ═══════════════════════════════════════════════════════════
    test_cleanup_config = state.get("test_cleanup_config")

    if not test_cleanup_config:
        # No test-level cleanup configured - look at step configs for end_of_test trigger
        step_cleanup_configs = state.get("step_cleanup_configs", [])
        found_config = None
        for config in step_cleanup_configs:
            trigger = config.get("cleanup_trigger", "end_of_test")
            ctype = config.get("cleanup_type", "none")
            if trigger in ["end_of_test", "both"] and ctype != "none":
                found_config = config
                break

        if found_config:
            test_cleanup_config = found_config
            logger.info(f"   Using step config: {found_config.get('cleanup_type')}")
        else:
            # No cleanup configured at all — this shouldn't normally reach here
            # since should_cleanup_end_of_test would have returned "end"
            logger.info("   No cleanup config found — ending")
            return {
                **state,
                "current_cleanup_config": {"cleanup_type": "none"},
                "cleanup_in_progress": False,
                "cleanup_phase": None,
                "end_of_test_cleanup_executed": True
            }

    cleanup_type = test_cleanup_config.get("cleanup_type", "none")

    logger.info(f"   Cleanup type: {cleanup_type}")
    logger.info(f"   Cleanup phase: end_of_test")

    return {
        **state,
        "current_cleanup_config": test_cleanup_config,
        "cleanup_in_progress": True,
        "cleanup_phase": "end_of_test",
        "cleanup_retry_count": 0,
        "cleanup_fallback_attempted": False,
        "end_of_test_cleanup_executed": True
    }


def cleanup_post_condition(state: AgentState) -> AgentState:
    """
    Cleanup post condition node - execute raw ADB intent commands.

    Executes all ADB intent commands from the "Post Condition" Excel column.
    This is the PRIMARY end-of-test cleanup when post_condition_intents are present.

    IMPORTANT: When post_condition_intents exist, this is the ONLY cleanup that runs.
    No default return_home or other cleanup types are used.
    """
    logger.info("🧹 Cleanup: Executing POST CONDITION intents")

    import time
    from datetime import datetime

    post_condition_intents = state.get("post_condition_intents", [])

    if not post_condition_intents:
        logger.warning("⚠️ cleanup_post_condition called but no intents found")
        return {
            **state,
            "cleanup_in_progress": False,
            "cleanup_phase": None,
            "end_of_test_cleanup_executed": True
        }

    start_time = time.time()
    results = []
    all_success = True

    for i, intent_cmd in enumerate(post_condition_intents):
        logger.info(f"   [{i+1}/{len(post_condition_intents)}] Executing: {intent_cmd}")

        try:
            # Execute via ADB raw command
            cmd_result = toolkit.adb.execute_raw_command(intent_cmd)

            success = cmd_result.get("success", False)
            output = cmd_result.get("output", "")
            error = cmd_result.get("error", "")

            if success:
                logger.info(f"   ✅ Intent {i+1} executed successfully")
                if output:
                    logger.info(f"      Output: {output[:200]}")
            else:
                logger.warning(f"   ⚠️ Intent {i+1} failed: {error}")
                all_success = False

            results.append({
                "intent": intent_cmd,
                "success": success,
                "output": output,
                "error": error
            })

            # Small delay between intents to let device process
            if i < len(post_condition_intents) - 1:
                time.sleep(1)

        except Exception as e:
            logger.error(f"   ❌ Intent {i+1} error: {e}")
            all_success = False
            results.append({
                "intent": intent_cmd,
                "success": False,
                "output": "",
                "error": str(e)
            })

    execution_time = time.time() - start_time
    logger.info(f"   Post condition complete: {len(results)} intents, "
                f"{'ALL SUCCESS' if all_success else 'SOME FAILED'}, "
                f"time={execution_time:.1f}s")

    # Create cleanup result
    from backend.models.results import DynamicCleanupResult
    from backend.models.enums import CleanupType, CleanupTrigger

    cleanup_result = DynamicCleanupResult(
        success=all_success,
        cleanup_type_executed=CleanupType.NONE,  # Special: post_condition is not a standard type
        cleanup_trigger=CleanupTrigger.END_OF_TEST,
        execution_time_seconds=execution_time,
        ai_decision=f"post_condition: {len(post_condition_intents)} intents"
    )

    cleanup_results = state.get("cleanup_results", []) + [cleanup_result.to_dict()]

    return {
        **state,
        "cleanup_in_progress": False,
        "cleanup_phase": None,
        "cleanup_results": cleanup_results,
        "end_of_test_cleanup_executed": True,
        "cleanup_failed": not all_success,
        "execution_log": state.get("execution_log", []) + [
            f"Post condition cleanup: {len(post_condition_intents)} intents, success={all_success}"
        ]
    }


def cleanup_reboot(state: AgentState) -> AgentState:
    """
    Cleanup reboot node - reboot device.

    ⚠️ WARNING: Destructive operation. Device will restart.
    """
    logger.warning("⚠️ Cleanup: REBOOTING DEVICE")

    import time
    from datetime import datetime

    start_time = time.time()

    try:
        # Reboot device
        logger.info("   Executing: adb reboot")
        result = toolkit.adb.reboot()

        # Wait for device to restart
        logger.info("   Waiting 60 seconds for reboot...")
        time.sleep(60)

        # Wait for device online
        logger.info("   Waiting for device online (120s timeout)...")
        toolkit.adb.wait_for_device(timeout=120)

        # Create cleanup result
        from backend.models.results import DynamicCleanupResult
        from backend.models.enums import CleanupType, CleanupTrigger

        cleanup_config = state.get("current_cleanup_config", {})
        cleanup_result = DynamicCleanupResult(
            success=True,
            cleanup_type_executed=CleanupType.REBOOT,
            cleanup_trigger=CleanupTrigger(cleanup_config.get("cleanup_trigger", "end_of_test")),
            execution_time_seconds=time.time() - start_time
        )

        cleanup_results = state.get("cleanup_results", [])
        cleanup_results.append(cleanup_result.to_dict())

        logger.info("✅ Cleanup reboot: Success")

        return {
            **state,
            "cleanup_in_progress": False,
            "cleanup_results": cleanup_results,
            "execution_log": state.get("execution_log", []) + ["Cleanup: Device rebooted"]
        }

    except Exception as e:
        logger.error(f"❌ Cleanup reboot error: {e}")

        # Mark as failed
        return {
            **state,
            "cleanup_in_progress": False,
            "cleanup_failed": True,
            "errors": state.get("errors", []) + [f"Cleanup reboot failed: {e}"]
        }


def cleanup_factory_reset(state: AgentState) -> AgentState:
    """
    Cleanup factory reset node - factory reset device.

    🚨 CRITICAL WARNING: ALL DATA WILL BE ERASED!
    Only use for critical cleanup scenarios.
    """
    logger.critical("🚨 Cleanup: FACTORY RESET DEVICE - ALL DATA WILL BE ERASED!")

    import time
    from datetime import datetime

    start_time = time.time()

    try:
        # Factory reset device
        logger.critical("   Executing: adb shell am broadcast android.intent.action.FACTORY_RESET")
        result = toolkit.adb.factory_reset()

        # Wait for device to reset
        logger.info("   Waiting 300 seconds for factory reset...")
        time.sleep(300)

        # Wait for device online
        logger.info("   Waiting for device online (300s timeout)...")
        toolkit.adb.wait_for_device(timeout=300)

        # Create cleanup result
        from backend.models.results import DynamicCleanupResult
        from backend.models.enums import CleanupType, CleanupTrigger

        cleanup_config = state.get("current_cleanup_config", {})
        cleanup_result = DynamicCleanupResult(
            success=True,
            cleanup_type_executed=CleanupType.FACTORY_RESET,
            cleanup_trigger=CleanupTrigger(cleanup_config.get("cleanup_trigger", "end_of_test")),
            execution_time_seconds=time.time() - start_time
        )

        cleanup_results = state.get("cleanup_results", [])
        cleanup_results.append(cleanup_result.to_dict())

        logger.info("✅ Cleanup factory reset: Success")

        return {
            **state,
            "cleanup_in_progress": False,
            "cleanup_results": cleanup_results,
            "execution_log": state.get("execution_log", []) + ["Cleanup: Device factory reset"]
        }

    except Exception as e:
        logger.error(f"❌ Cleanup factory reset error: {e}")

        # Mark as failed
        return {
            **state,
            "cleanup_in_progress": False,
            "cleanup_failed": True,
            "errors": state.get("errors", []) + [f"Cleanup factory reset failed: {e}"]
        }


# ═══════════════════════════════════════════════════════════════
# CLEANUP SYSTEM HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def _ai_tap_reversal_decision(
    screenshot_path: str,
    action_type: str,
    target_element: str,
    step_description: str
) -> Dict[str, Any]:
    """
    Use AI to determine tap reversal strategy.

    Returns:
        Dict with keys:
        - strategy: "same_tap" | "different_tap" | "press_back" | "no_tap"
        - reasoning: str
        - target_element: Optional[str] (for different_tap)
        - confidence: float
    """
    import requests
    import json
    import re
    from backend.config import settings

    prompt = f"""
Analyze the screen and determine the reversal strategy for this tap action.

ORIGINAL ACTION:
- Action Type: {action_type}
- Target Element: {target_element}
- Step Description: {step_description}

REVERSAL STRATEGIES:
1. same_tap: Tap the same element again (toggle button, e.g., AC ON → AC OFF)
2. different_tap: Tap a different element (e.g., close button, X button)
3. press_back: Press the back button
4. no_tap: No reversal needed (already at previous state)

Respond with JSON only:
{{
    "strategy": "same_tap|different_tap|press_back|no_tap",
    "reasoning": "brief explanation",
    "target_element": "element name (only if different_tap)",
    "confidence": 0.0-1.0
}}
"""

    try:
        # Encode image
        import base64
        with open(screenshot_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')

        payload = {
            "username": settings.vio_username,
            "token": settings.vio_api_token,
            "type": "IMAGE",
            "payload": prompt,
            "image": image_b64,
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
        message = result.get('message', result.get('response', '{}'))

        # Parse JSON
        json_match = re.search(r'\{.*\}', message, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            return parsed
        else:
            # Fallback
            return {
                "strategy": "press_back",
                "reasoning": "JSON parse failed",
                "confidence": 0.5
            }

    except Exception as e:
        logger.error(f"❌ AI tap reversal decision error: {e}")
        # Fallback to press_back
        return {
            "strategy": "press_back",
            "reasoning": f"AI error: {e}",
            "confidence": 0.3
        }


def _ai_cleanup_decision(
    screenshot_path: str,
    test_id: str,
    component: str,
    current_step: int,
    executed_steps: List[Dict],
    ai_context: str
) -> Dict[str, Any]:
    """
    Use AI to determine cleanup strategy.

    Returns:
        Dict with keys:
        - cleanup_strategy: "return_home" | "reverse_action" | "restore_state" | "reboot" | etc.
        - reasoning: str
        - confidence: float
        - fallback: str
    """
    import requests
    import json
    import re
    from backend.config import settings

    prompt = f"""
Analyze the test context and current screen to determine the best cleanup strategy.

TEST CONTEXT:
- Test ID: {test_id}
- Component: {component}
- Current Step: {current_step}
- Executed Steps: {len(executed_steps)}
- Additional Context: {ai_context}

CLEANUP STRATEGIES:
1. return_home: Simple home button press (low impact)
2. reverse_action: Reverse last action (medium impact)
3. restore_state: Reverse multiple actions (high impact)
4. close_dialog: Close dialog and return home
5. reboot: Reboot device (very high impact, use sparingly)

Choose the MINIMAL cleanup needed to restore device to known state.

Respond with JSON only:
{{
    "cleanup_strategy": "return_home|reverse_action|restore_state|close_dialog|reboot",
    "reasoning": "brief explanation",
    "confidence": 0.0-1.0,
    "fallback": "return_home"
}}
"""

    try:
        # Encode image
        import base64
        with open(screenshot_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')

        payload = {
            "username": settings.vio_username,
            "token": settings.vio_api_token,
            "type": "IMAGE",
            "payload": prompt,
            "image": image_b64,
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
        message = result.get('message', result.get('response', '{}'))

        # Parse JSON
        json_match = re.search(r'\{.*\}', message, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            return parsed
        else:
            # Fallback
            return {
                "cleanup_strategy": "return_home",
                "reasoning": "JSON parse failed",
                "confidence": 0.5,
                "fallback": "return_home"
            }

    except Exception as e:
        logger.error(f"❌ AI cleanup decision error: {e}")
        # Fallback to return_home
        return {
            "cleanup_strategy": "return_home",
            "reasoning": f"AI error: {e}",
            "confidence": 0.3,
            "fallback": "return_home"
        }