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
    # Screen Analysis
    # ═══════════════════════════════════════════════════════════
    current_screenshot: Optional[str]  # Path to current screenshot
    screen_analysis: Optional[str]  # AI analysis of current screen
    detected_elements: Optional[List[Dict[str, Any]]]  # OCR detected elements
    
    # ═══════════════════════════════════════════════════════════
    # Action Planning
    # ═══════════════════════════════════════════════════════════
    planned_action: Optional[str]  # Planned action description
    action_type: Optional[str]  # tap, swipe, input_text, press_key, verify
    target_element: Optional[str]  # Target element to interact with
    target_coordinates: Optional[tuple]  # (x, y) coordinates
    action_parameters: Optional[Dict[str, Any]]  # Additional parameters
    
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
    
    # ═══════════════════════════════════════════════════════════
    # Workflow Control
    # ═══════════════════════════════════════════════════════════
    stop_requested: bool  # User requested stop
    should_continue: bool  # Whether workflow should continue


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
        
        # Workflow Control
        stop_requested=False,
        should_continue=True
    )