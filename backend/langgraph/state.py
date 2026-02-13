"""
state.py - LangGraph Agent State Definition

Defines the complete state structure for the agent workflow.
"""

from typing import TypedDict, Optional, List, Dict, Any
from backend.models import AgentStatus, AgentMode


class AgentState(TypedDict, total=False):
    """
    Complete state for the AI Agent workflow.
    
    All fields are optional (total=False) to allow incremental state updates.
    """
    
    # ═══════════════════════════════════════════════════════════
    # Mode & Execution Control
    # ═══════════════════════════════════════════════════════════
    current_mode: AgentMode  # test_execution, standalone, idle
    status: AgentStatus  # idle, running, waiting_hitl, success, failure, stopped
    
    # ═══════════════════════════════════════════════════════════
    # Test Execution State
    # ═══════════════════════════════════════════════════════════
    test_id: Optional[str]  # Current test ID (e.g., "TEST-001")
    execution_id: Optional[str]  # Execution ID for test history tracking
    test_description: Optional[str]  # Test case description
    test_steps: Optional[List[str]]  # List of test steps to execute
    current_step: int  # Current step index (0-based)
    total_steps: int  # Total number of steps
    
    # ═══════════════════════════════════════════════════════════
    # Learned Solutions (RAG)
    # ═══════════════════════════════════════════════════════════
    has_learned_solution: bool  # Whether learned solution exists
    learned_solution: Optional[Dict[str, Any]]  # Learned solution data
    use_learned: bool  # Whether to use learned solution

    # ═══════════════════════════════════════════════════════════
    # Dynamic Verification System
    # ═══════════════════════════════════════════════════════════
    step_verification_configs: List[Dict[str, Any]]  # Per-step verification configs from Excel
    current_step_verification_config: Optional[Dict[str, Any]]  # Current step's verification config
    
    # ═══════════════════════════════════════════════════════════
    # Screen Analysis
    # ═══════════════════════════════════════════════════════════
    current_screenshot: Optional[str]  # Path to current screenshot
    screen_analysis: Optional[str]  # AI analysis of current screen
    detected_elements: Optional[List[Dict[str, Any]]]  # OCR detected elements
    
    # ═══════════════════════════════════════════════════════════
    # Action Planning
    # ═══════════════════════════════════════════════════════════
    planned_action: Optional[str]  # Planned action description
    action_type: Optional[str]  # tap, swipe, input_text, press_key, verify, raw_adb, drag_drop
    target_element: Optional[str]  # Target element to interact with
    target_coordinates: Optional[tuple]  # (x, y) coordinates
    action_parameters: Optional[Dict[str, Any]]  # Additional parameters

    # Enhanced Action Parameters (Phase 1 - Comprehensive Fix)
    raw_command: Optional[str]  # Raw ADB command for raw_adb action type
    swipe_speed: Optional[str]  # Swipe speed: slow|medium|fast
    swipe_duration_ms: Optional[int]  # Swipe duration in milliseconds
    long_press_duration_seconds: Optional[int]  # Long press duration in seconds
    drag_drop_params: Optional[Dict[str, Any]]  # Drag-drop parameters {app_name, pixel_offset, direction}
    coordinate_source: Optional[str]  # Source of coordinates: explicit|vision_tool|device_profile|hitl
    
    # ═══════════════════════════════════════════════════════════
    # Execution Results
    # ═══════════════════════════════════════════════════════════
    last_action_result: Optional[Dict[str, Any]]  # Result from last action
    action_success: bool  # Whether last action succeeded
    verification_result: Optional[Dict[str, Any]]  # Screen verification result
    retry_count: int  # Number of retries for current step
    max_retries: int  # Maximum retries allowed
    executed_steps: List[Dict[str, Any]]  # History of executed steps
    
    # ═══════════════════════════════════════════════════════════
    # Human-in-the-Loop (HITL)
    # ═══════════════════════════════════════════════════════════
    waiting_for_hitl: bool  # Whether waiting for human input
    hitl_problem: Optional[str]  # Description of problem requiring HITL
    hitl_guidance: Optional[str]  # Human guidance received
    hitl_coordinates: Optional[tuple]  # Coordinates provided by human
    hitl_action_type: Optional[str]  # Action type from human
    hitl_applied: bool  # Whether HITL guidance has been applied
    
    # ═══════════════════════════════════════════════════════════
    # Standalone Mode
    # ═══════════════════════════════════════════════════════════
    standalone_command: Optional[str]  # Natural language command
    parsed_intent: Optional[Dict[str, Any]]  # Parsed command intent
    
    # ═══════════════════════════════════════════════════════════
    # Logging & Error Handling
    # ═══════════════════════════════════════════════════════════
    execution_log: List[str]  # Execution log entries
    errors: List[str]  # Error messages

    # Enhanced Error Tracking (HITL Architecture Fix)
    error_contexts: List[Dict[str, Any]]  # Structured error history with categories
    last_error_category: Optional[str]  # Category of most recent error (ErrorCategory enum value)
    technical_error_count: int  # Count of technical errors in current test
    decision_error_count: int  # Count of decision errors in current test
    
    # ═══════════════════════════════════════════════════════════
    # Workflow Control
    # ═══════════════════════════════════════════════════════════
    stop_requested: bool  # User requested stop
    should_continue: bool  # Whether workflow should continue

    # ═══════════════════════════════════════════════════════════
    # Cleanup System
    # ═══════════════════════════════════════════════════════════
    step_cleanup_configs: List[Dict[str, Any]]  # Per-step cleanup configs from Excel
    test_cleanup_config: Optional[Dict[str, Any]]  # End-of-test cleanup config
    current_cleanup_config: Optional[Dict[str, Any]]  # Current cleanup config being executed

    cleanup_in_progress: bool  # Whether cleanup is currently executing
    cleanup_phase: Optional[str]  # "in_step" or "end_of_test"

    # Reversal Stack (LIFO tracking of reversible actions)
    reversal_stack: List[Dict[str, Any]]  # Stack of actions that can be reversed
    reversible_actions: List[str]  # List of action types that can be reversed

    # Cleanup Results
    cleanup_results: List[Dict[str, Any]]  # History of cleanup operations
    in_step_cleanup_count: int  # Number of in-step cleanups executed
    end_of_test_cleanup_executed: bool  # Whether end-of-test cleanup has run
    cleanup_retry_count: int  # Current cleanup retry count
    cleanup_fallback_attempted: bool  # Whether fallback cleanup was attempted
    cleanup_failed: bool  # Whether cleanup failed after all retries

    # AI-Driven Cleanup
    ai_cleanup_decision: Optional[str]  # AI's cleanup strategy decision
    ai_cleanup_confidence: Optional[float]  # Confidence in AI's decision

    # Post Condition (raw ADB intents for end-of-test cleanup)
    post_condition_intents: Optional[List[str]]  # Raw ADB intent commands from Excel "Post Condition" column


def create_initial_state(
    mode: AgentMode = AgentMode.IDLE,
    test_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    standalone_command: Optional[str] = None,
    use_learned: bool = True,
    max_retries: int = 3
) -> AgentState:
    """
    Create initial agent state.

    Args:
        mode: Agent mode (test_execution, standalone, idle)
        test_id: Test ID for test execution mode
        execution_id: Execution ID for test history tracking
        standalone_command: Command for standalone mode
        use_learned: Whether to use learned solutions
        max_retries: Maximum retry attempts

    Returns:
        Initial AgentState
    """
    return AgentState(
        # Mode & Status
        current_mode=mode,
        status=AgentStatus.IDLE,

        # Test Execution
        test_id=test_id,
        execution_id=execution_id,
        test_description=None,
        test_steps=None,
        current_step=0,
        total_steps=0,
        
        # Learned Solutions
        has_learned_solution=False,
        learned_solution=None,
        use_learned=use_learned,

        # Dynamic Verification System
        step_verification_configs=[],
        current_step_verification_config=None,
        
        # Screen Analysis
        current_screenshot=None,
        screen_analysis=None,
        detected_elements=None,
        
        # Action Planning
        planned_action=None,
        action_type=None,
        target_element=None,
        target_coordinates=None,
        action_parameters=None,

        # Enhanced Action Parameters
        raw_command=None,
        swipe_speed=None,
        swipe_duration_ms=None,
        long_press_duration_seconds=None,
        drag_drop_params=None,
        coordinate_source=None,
        
        # Execution Results
        last_action_result=None,
        action_success=False,
        verification_result=None,
        retry_count=0,
        max_retries=max_retries,
        executed_steps=[],
        
        # HITL
        waiting_for_hitl=False,
        hitl_problem=None,
        hitl_guidance=None,
        hitl_coordinates=None,
        hitl_action_type=None,
        hitl_applied=False,
        
        # Standalone
        standalone_command=standalone_command,
        parsed_intent=None,
        
        # Logging
        execution_log=[],
        errors=[],

        # Enhanced Error Tracking
        error_contexts=[],
        last_error_category=None,
        technical_error_count=0,
        decision_error_count=0,

        # Workflow Control
        stop_requested=False,
        should_continue=True,

        # Cleanup System
        step_cleanup_configs=[],
        test_cleanup_config=None,
        current_cleanup_config=None,
        cleanup_in_progress=False,
        cleanup_phase=None,

        # Reversal Stack
        reversal_stack=[],
        reversible_actions=["tap", "double_tap", "long_press", "swipe", "input_text"],

        # Cleanup Results
        cleanup_results=[],
        in_step_cleanup_count=0,
        end_of_test_cleanup_executed=False,
        cleanup_retry_count=0,
        cleanup_fallback_attempted=False,
        cleanup_failed=False,

        # AI-Driven Cleanup
        ai_cleanup_decision=None,
        ai_cleanup_confidence=None,

        # Post Condition
        post_condition_intents=None
    )