"""
edges.py - LangGraph Conditional Routing Functions

Defines all conditional edges for the agent workflow graph.
"""

import logging
from typing import Literal

from backend.langgraph.state import AgentState
from backend.models import AgentMode, AgentStatus

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Route 1: Route by Mode
# ═══════════════════════════════════════════════════════════════

def route_by_mode(state: AgentState) -> Literal["test_execution", "standalone", "idle"]:
    """
    Route based on agent mode.
    
    Args:
        state: Current agent state
        
    Returns:
        "test_execution" | "standalone" | "idle"
    """
    mode = state.get("current_mode", AgentMode.IDLE)
    
    if mode == AgentMode.TEST_EXECUTION:
        logger.debug("→ Route: test_execution")
        return "test_execution"
    elif mode == AgentMode.STANDALONE:
        logger.debug("→ Route: standalone")
        return "standalone"
    else:
        logger.debug("→ Route: idle")
        return "idle"


# ═══════════════════════════════════════════════════════════════
# Route 2: Should Use Learned Solution
# ═══════════════════════════════════════════════════════════════

def should_use_learned(state: AgentState) -> Literal["use_learned", "no_learned"]:
    """
    Check if learned solution exists and should be used.
    
    Args:
        state: Current agent state
        
    Returns:
        "use_learned" | "no_learned"
    """
    has_learned = state.get("has_learned_solution", False)
    use_learned = state.get("use_learned", True)
    
    if has_learned and use_learned:
        logger.debug("→ Route: use_learned")
        return "use_learned"
    else:
        logger.debug("→ Route: no_learned")
        return "no_learned"


# ═══════════════════════════════════════════════════════════════
# Route 3: Should Wait for HITL
# ═══════════════════════════════════════════════════════════════

def should_wait_hitl(state: AgentState) -> Literal["wait_hitl", "continue"]:
    """
    Determine if HITL is needed (retry count exceeded).
    
    Args:
        state: Current agent state
        
    Returns:
        "wait_hitl" | "continue"
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    if retry_count >= max_retries:
        logger.debug("→ Route: wait_hitl (retries exceeded)")
        return "wait_hitl"
    else:
        logger.debug("→ Route: continue")
        return "continue"


# ═══════════════════════════════════════════════════════════════
# Route 4: Is Test Complete
# ═══════════════════════════════════════════════════════════════

def is_test_complete(state: AgentState) -> Literal["complete", "continue"]:
    """
    Check if all test steps are done.
    
    Args:
        state: Current agent state
        
    Returns:
        "complete" | "continue"
    """
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    
    if current_step >= total_steps:
        logger.debug("→ Route: complete")
        return "complete"
    else:
        logger.debug("→ Route: continue")
        return "continue"


# ═══════════════════════════════════════════════════════════════
# Route 5: Route After Execution
# ═══════════════════════════════════════════════════════════════

def route_after_execution(state: AgentState) -> Literal["verify", "retry"]:
    """
    Route after executing action.
    
    Args:
        state: Current agent state
        
    Returns:
        "verify" | "retry"
    """
    action_success = state.get("action_success", False)
    
    if action_success:
        logger.debug("→ Route: verify")
        return "verify"
    else:
        logger.debug("→ Route: retry")
        return "retry"


# ═══════════════════════════════════════════════════════════════
# Route 6: Route After Verification
# ═══════════════════════════════════════════════════════════════

def route_after_verification(state: AgentState) -> Literal["success", "retry"]:
    """
    Route after verification.
    
    Args:
        state: Current agent state
        
    Returns:
        "success" | "retry"
    """
    verification_result = state.get("verification_result", {})
    verified = verification_result.get("verified", False)
    
    if verified:
        logger.debug("→ Route: success")
        return "success"
    else:
        logger.debug("→ Route: retry")
        return "retry"


# ═══════════════════════════════════════════════════════════════
# Route 7: Should Retry
# ═══════════════════════════════════════════════════════════════

def should_retry(state: AgentState) -> Literal["retry", "hitl"]:
    """
    Check if should retry failed action.
    
    Args:
        state: Current agent state
        
    Returns:
        "retry" | "hitl"
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    if retry_count < max_retries:
        logger.debug(f"→ Route: retry (attempt {retry_count + 1}/{max_retries})")
        return "retry"
    else:
        logger.debug("→ Route: hitl (max retries reached)")
        return "hitl"


# ═══════════════════════════════════════════════════════════════
# Route 8: Route from Planning
# ═══════════════════════════════════════════════════════════════

def route_from_planning(state: AgentState) -> Literal["execute", "direct", "error"]:
    """
    Route from plan_action to appropriate execution.
    
    Args:
        state: Current agent state
        
    Returns:
        "execute" | "direct" | "error"
    """
    action_type = state.get("action_type", "")
    target_coordinates = state.get("target_coordinates")
    
    # Check for errors
    errors = state.get("errors", [])
    if errors and "No goal for action planning" in errors[-1]:
        logger.debug("→ Route: error")
        return "error"
    
    # Direct actions (no coordinates needed)
    if action_type in ["press_back", "press_home", "press_enter"]:
        logger.debug("→ Route: direct")
        return "direct"
    
    # Regular execution
    logger.debug("→ Route: execute")
    return "execute"


# ═══════════════════════════════════════════════════════════════
# Route 9: Is Stopped
# ═══════════════════════════════════════════════════════════════

def is_stopped(state: AgentState) -> Literal["stop", "continue"]:
    """
    Check if stop requested.
    
    Args:
        state: Current agent state
        
    Returns:
        "stop" | "continue"
    """
    stop_requested = state.get("stop_requested", False)
    
    if stop_requested:
        logger.debug("→ Route: stop")
        return "stop"
    else:
        logger.debug("→ Route: continue")
        return "continue"


# ═══════════════════════════════════════════════════════════════
# Route 10: Route HITL Ready
# ═══════════════════════════════════════════════════════════════

def route_hitl_ready(state: AgentState) -> Literal["guidance_received", "waiting"]:
    """
    Check if HITL guidance received.
    
    CRITICAL FIX: Must have ACTUAL guidance to proceed
    
    Args:
        state: Current agent state
        
    Returns:
        "guidance_received" | "waiting"
    """
    hitl_guidance = state.get("hitl_guidance")
    hitl_coordinates = state.get("hitl_coordinates")
    
    # CRITICAL FIX: Check for ACTUAL guidance first
    # If no guidance exists, MUST wait (even if hitl_applied=True from previous step)
    if not (hitl_guidance or hitl_coordinates):
        logger.debug("→ Route: waiting (no guidance in state)")
        return "waiting"
    
    # Guidance exists - proceed to apply
    logger.debug("→ Route: guidance_received (guidance found in state)")
    return "guidance_received"


# ═══════════════════════════════════════════════════════════════
# Route 11: Should Continue Workflow
# ═══════════════════════════════════════════════════════════════

def should_continue_workflow(state: AgentState) -> Literal["continue", "end"]:
    """
    Check if workflow should continue.
    
    Args:
        state: Current agent state
        
    Returns:
        "continue" | "end"
    """
    should_continue = state.get("should_continue", True)
    stop_requested = state.get("stop_requested", False)
    status = state.get("status", AgentStatus.RUNNING)
    
    # End conditions
    if not should_continue:
        logger.debug("→ Route: end (should_continue=False)")
        return "end"
    
    if stop_requested:
        logger.debug("→ Route: end (stop requested)")
        return "end"
    
    if status in [AgentStatus.SUCCESS, AgentStatus.FAILURE]:
        logger.debug(f"→ Route: end (status={status})")
        return "end"
    
    logger.debug("→ Route: continue")
    return "continue"


# ═══════════════════════════════════════════════════════════════
# Route 12: Increment Retry Counter
# ═══════════════════════════════════════════════════════════════

def increment_retry(state: AgentState) -> AgentState:
    """
    Increment retry counter.
    
    This is a helper function used before retrying.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with incremented retry_count
    """
    retry_count = state.get("retry_count", 0)
    
    logger.debug(f"Incrementing retry count: {retry_count} → {retry_count + 1}")
    
    return {
        **state,
        "retry_count": retry_count + 1
    }


# ═══════════════════════════════════════════════════════════════
# Route 13: Check HITL Resume
# ═══════════════════════════════════════════════════════════════

def should_resume_from_hitl(state: AgentState) -> Literal["resume_hitl", "normal_flow"]:
    """
    Check if resuming from HITL interruption.
    
    CRITICAL: When graph is re-invoked after HITL guidance, skip directly
    to apply_guidance instead of going through entire flow again.
    
    Args:
        state: Current agent state
        
    Returns:
        "resume_hitl" if HITL guidance pending | "normal_flow" otherwise
    """
    waiting_for_hitl = state.get("waiting_for_hitl", False)
    hitl_guidance = state.get("hitl_guidance")
    hitl_coordinates = state.get("hitl_coordinates")
    hitl_applied = state.get("hitl_applied", False)
    
    # If waiting for HITL AND guidance exists AND not yet applied → resume from apply_guidance
    if waiting_for_hitl and (hitl_guidance or hitl_coordinates) and not hitl_applied:
        logger.debug("→ Route: resume_hitl (HITL guidance pending)")
        return "resume_hitl"
    
    # Normal flow
    logger.debug("→ Route: normal_flow")
    return "normal_flow"


def route_after_next_step(state: AgentState) -> str:
    """
    Route after next_step - check if we should continue with learned solution.
    """
    # Check if test is complete
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 1)
    
    if current_step >= total_steps:
        return "save_learned"
    
    # Check if we should use learned solution for next step
    if state.get("has_learned_solution") and state.get("use_learned", True):
        return "direct_execute"
    
    # Normal AI flow
    return "capture_screen"