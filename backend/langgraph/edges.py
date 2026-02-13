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

def route_after_execution(state: AgentState) -> Literal["verify", "retry", "end"]:
    """
    Route after executing action.

    CRITICAL: Must check for stop conditions FIRST.

    Args:
        state: Current agent state

    Returns:
        "verify" | "retry" | "end"
    """
    # CRITICAL: Check stop conditions FIRST
    stop_requested = state.get("stop_requested", False)
    status = state.get("status", AgentStatus.RUNNING)

    if stop_requested or status == AgentStatus.STOPPED:
        logger.debug(f"→ Route: end (stop_requested={stop_requested}, status={status})")
        return "end"

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

def route_after_verification(state: AgentState) -> Literal["success", "retry", "end"]:
    """
    Route after verification.

    CRITICAL: Must check for stop conditions FIRST.

    Args:
        state: Current agent state

    Returns:
        "success" | "retry" | "end"
    """
    # CRITICAL: Check stop conditions FIRST
    stop_requested = state.get("stop_requested", False)
    status = state.get("status", AgentStatus.RUNNING)

    if stop_requested or status == AgentStatus.STOPPED:
        logger.debug(f"→ Route: end (stop_requested={stop_requested}, status={status})")
        return "end"

    verification_result = state.get("verification_result", {})
    verified = verification_result.get("verified", False)

    if verified:
        logger.debug("→ Route: success")
        return "success"
    else:
        logger.debug("→ Route: retry")
        return "retry"


# ═══════════════════════════════════════════════════════════════
# Route 7: Should Retry (ENHANCED - Error Category Aware)
# ═══════════════════════════════════════════════════════════════

def should_retry(state: AgentState) -> Literal["retry", "hitl", "end", "test_failed"]:
    """
    Check if should retry failed action based on error category.

    CRITICAL ARCHITECTURE:
    - Technical errors (screenshot failure, system errors) → "end" (handle_technical_error)
    - Verification/decision failures at max retries (test execution) → "test_failed" (log_results)
    - Standalone/idle mode: max retries reached → "hitl" (HITL only for standalone)

    Returns:
        "retry"       - Retry the action (retry_count < max_retries)
        "hitl"        - Trigger HITL (standalone mode only, max retries reached)
        "end"         - Technical error, cannot be fixed by retry (handle_technical_error)
        "test_failed" - Test step failed verification after max retries (log_results)
    """
    from backend.models.enums import ErrorCategory

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    last_error_category = state.get("last_error_category")
    current_mode = state.get("current_mode")

    # Check if we're in test execution mode (HITL disabled)
    is_test_execution = (
        current_mode == AgentMode.TEST_EXECUTION
        or (isinstance(current_mode, str) and current_mode == "test_execution")
    )

    # CRITICAL: Check error category first
    if last_error_category:
        try:
            error_cat = ErrorCategory(last_error_category)

            # Technical errors: DO NOT retry or trigger HITL - end immediately
            if error_cat.is_technical():
                logger.warning(f"→ Route: end (technical error: {error_cat.value})")
                logger.warning("  Technical errors cannot be fixed by retry - ending test")
                return "end"

            # Decision errors: Retry or test_failed/hitl based on mode
            if error_cat.is_decision():
                if retry_count < max_retries:
                    logger.debug(f"→ Route: retry (decision error, attempt {retry_count + 1}/{max_retries})")
                    return "retry"
                else:
                    if is_test_execution:
                        logger.info(f"→ Route: test_failed (decision error, max retries reached, test_execution mode)")
                        return "test_failed"
                    else:
                        logger.debug(f"→ Route: hitl (decision error, max retries reached, standalone mode)")
                        return "hitl"

        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid error category: {last_error_category}, using fallback logic")

    # Fallback: No error category specified (e.g., verification failure without error category)
    # This is a TEST FAILURE, not a technical error
    if retry_count < max_retries:
        logger.debug(f"→ Route: retry (no error category, attempt {retry_count + 1}/{max_retries})")
        return "retry"
    else:
        if is_test_execution:
            logger.info("→ Route: test_failed (max retries reached, test_execution mode - verification/action failure)")
            return "test_failed"
        else:
            logger.debug("→ Route: hitl (max retries reached, standalone mode)")
            return "hitl"


# ═══════════════════════════════════════════════════════════════
# Route 8: Route from Planning
# ═══════════════════════════════════════════════════════════════

def route_from_planning(state: AgentState) -> Literal["execute", "direct", "error", "end"]:
    """
    Route from plan_action to appropriate execution.

    CRITICAL: Must check for stop conditions FIRST.
    In test_execution mode, planning errors go to "end" (NO HITL).
    In standalone mode, planning errors go to "error" (HITL).

    Args:
        state: Current agent state

    Returns:
        "execute" | "direct" | "error" | "end"
    """
    # CRITICAL: Check stop conditions FIRST
    stop_requested = state.get("stop_requested", False)
    status = state.get("status", AgentStatus.RUNNING)

    if stop_requested or status == AgentStatus.STOPPED:
        logger.debug(f"→ Route: end (stop_requested={stop_requested}, status={status})")
        return "end"

    action_type = state.get("action_type", "")
    target_coordinates = state.get("target_coordinates")

    # Check for errors
    errors = state.get("errors", [])
    if errors and "No goal for action planning" in errors[-1]:
        # In test execution mode, planning errors end the test (no HITL)
        current_mode = state.get("current_mode")
        is_test_execution = (
            current_mode == AgentMode.TEST_EXECUTION
            or (isinstance(current_mode, str) and current_mode == "test_execution")
        )
        if is_test_execution:
            logger.info("→ Route: end (planning error in test_execution mode - NO HITL)")
            return "end"
        logger.debug("→ Route: error (planning error, standalone mode - HITL)")
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

    if status in [AgentStatus.SUCCESS, AgentStatus.FAILURE, AgentStatus.STOPPED]:
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


def route_after_direct_execute(state: AgentState) -> Literal["verify", "end"]:
    """
    Route after direct_execute - verify or end if stopped.

    CRITICAL: Must check for stop conditions FIRST.

    Args:
        state: Current agent state

    Returns:
        "verify" | "end"
    """
    # CRITICAL: Check stop conditions FIRST
    stop_requested = state.get("stop_requested", False)
    status = state.get("status", AgentStatus.RUNNING)

    if stop_requested or status == AgentStatus.STOPPED:
        logger.debug(f"→ Route: end (stop_requested={stop_requested}, status={status})")
        return "end"

    logger.debug("→ Route: verify")
    return "verify"


def route_after_capture(state: AgentState) -> Literal["analyze", "end"]:
    """
    Route after capture_screen - analyze or end if stopped.

    Args:
        state: Current agent state

    Returns:
        "analyze" | "end"
    """
    stop_requested = state.get("stop_requested", False)
    status = state.get("status", AgentStatus.RUNNING)

    if stop_requested or status == AgentStatus.STOPPED:
        logger.debug(f"→ Route: end (stop_requested={stop_requested}, status={status})")
        return "end"

    logger.debug("→ Route: analyze")
    return "analyze"


def route_after_analyze(state: AgentState) -> Literal["plan", "end"]:
    """
    Route after ai_analyze - plan or end if stopped.

    Args:
        state: Current agent state

    Returns:
        "plan" | "end"
    """
    stop_requested = state.get("stop_requested", False)
    status = state.get("status", AgentStatus.RUNNING)

    if stop_requested or status == AgentStatus.STOPPED:
        logger.debug(f"→ Route: end (stop_requested={stop_requested}, status={status})")
        return "end"

    logger.debug("→ Route: plan")
    return "plan"


def route_after_save_learned(state: AgentState) -> Literal["log", "end"]:
    """
    Route after save_learned - log or end if stopped.

    Args:
        state: Current agent state

    Returns:
        "log" | "end"
    """
    stop_requested = state.get("stop_requested", False)
    status = state.get("status", AgentStatus.RUNNING)

    if stop_requested or status == AgentStatus.STOPPED:
        logger.debug(f"→ Route: end (stop_requested={stop_requested}, status={status})")
        return "end"

    logger.debug("→ Route: log")
    return "log"


def route_after_next_step(state: AgentState) -> str:
    """
    Route after next_step - check if we should continue with learned solution.

    CRITICAL: Must check for stop/end conditions FIRST before routing.
    """
    # CRITICAL: Check stop conditions FIRST
    stop_requested = state.get("stop_requested", False)
    status = state.get("status", AgentStatus.RUNNING)
    should_continue = state.get("should_continue", True)

    if stop_requested or status == AgentStatus.STOPPED or not should_continue:
        logger.debug(f"→ Route: end (stop_requested={stop_requested}, status={status})")
        return "end"

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


# ═══════════════════════════════════════════════════════════════
# CLEANUP SYSTEM ROUTING FUNCTIONS (Phase 5)
# ═══════════════════════════════════════════════════════════════


def route_after_verification_with_cleanup(state: AgentState) -> str:
    """
    Combined routing after verification: check success/retry/end AND cleanup.

    This combines the verification check with cleanup check to maintain the
    existing retry logic while adding cleanup support.

    Args:
        state: Current agent state

    Returns:
        "cleanup" | "next_step" | "retry" | "end"
    """
    # First, check the existing verification logic
    from backend.langgraph.edges import route_after_verification

    # Get verification route (this would be "success", "retry", or "end")
    base_route = route_after_verification(state)

    # If retry or end, pass through
    if base_route in ["retry", "end"]:
        return base_route

    # If success, check if cleanup is needed
    if base_route == "success":
        cleanup_route = should_cleanup_after_step(state)
        if cleanup_route == "cleanup":
            return "cleanup"
        else:
            return "next_step"

    # Default fallback
    return "next_step"


def should_cleanup_after_step(state: AgentState) -> Literal["cleanup", "continue"]:
    """
    Check if in-step cleanup is needed after verify_result.

    CRITICAL: This must execute regardless of step success/failure.
    Cleanup is BLOCKING - next_step waits for cleanup completion.

    Args:
        state: Current agent state

    Returns:
        "cleanup" | "continue"
    """
    current_step = state.get("current_step", 0)
    step_cleanup_configs = state.get("step_cleanup_configs", [])

    # Get current step's cleanup config
    if current_step < len(step_cleanup_configs):
        cleanup_config = step_cleanup_configs[current_step]
        cleanup_type = cleanup_config.get("cleanup_type", "none")
        cleanup_trigger = cleanup_config.get("cleanup_trigger", "end_of_test")

        logger.info(f"🧹 Step {current_step} cleanup check: type={cleanup_type}, trigger={cleanup_trigger}")

        step_failed = not state.get("action_success", True)

        # Check if cleanup should be triggered
        if cleanup_type != "none":
            if cleanup_trigger == "after_step":
                logger.info(f"→ Route: cleanup (trigger=after_step)")
                return "cleanup"
            elif cleanup_trigger == "both":
                logger.info(f"→ Route: cleanup (trigger=both)")
                return "cleanup"
            elif cleanup_trigger == "always":
                logger.info(f"→ Route: cleanup (trigger=always)")
                return "cleanup"
            elif cleanup_trigger == "on_failure" and step_failed:
                logger.info(f"→ Route: cleanup (trigger=on_failure, step_failed={step_failed})")
                return "cleanup"

    # No cleanup needed
    logger.info("→ Route: continue (no in-step cleanup needed)")
    return "continue"


def route_cleanup_type(state: AgentState) -> str:
    """
    Route to appropriate cleanup handler based on cleanup_type.

    Args:
        state: Current agent state

    Returns:
        Cleanup node name
    """
    cleanup_config = state.get("current_cleanup_config", {})
    cleanup_type = cleanup_config.get("cleanup_type", "none")

    logger.info(f"🧹 Cleanup dispatcher: type={cleanup_type}")

    # Map cleanup type to node
    cleanup_routing = {
        "none": "next_step",  # Skip cleanup
        "return_home": "cleanup_home",
        "reverse_action": "cleanup_reverse_action",
        "restore_state": "cleanup_restore_state",
        "close_dialog": "cleanup_close_dialog",
        "ai_driven": "cleanup_ai_driven",
        "reboot": "cleanup_reboot",
        "factory_reset": "cleanup_factory_reset",
        "reverse_and_home": "cleanup_reverse_action",  # Will also press home
        "close_and_reboot": "cleanup_close_dialog"  # Will also reboot
    }

    node = cleanup_routing.get(cleanup_type, "cleanup_home")
    logger.info(f"→ Route: {node}")
    return node


def route_ai_cleanup_decision(state: AgentState) -> str:
    """
    Route based on AI cleanup decision.

    Args:
        state: Current agent state

    Returns:
        Cleanup node name
    """
    ai_decision = state.get("ai_cleanup_decision", "return_home")

    logger.debug(f"→ AI cleanup decision: {ai_decision}")

    # Map AI decision to node
    cleanup_routing = {
        "return_home": "cleanup_home",
        "reverse_action": "cleanup_reverse_action",
        "restore_state": "cleanup_restore_state",
        "close_dialog": "cleanup_close_dialog",
        "reboot": "cleanup_reboot",
        "factory_reset": "cleanup_factory_reset"
    }

    node = cleanup_routing.get(ai_decision, "cleanup_home")
    logger.debug(f"→ Route: {node}")
    return node


def should_cleanup_end_of_test(state: AgentState) -> Literal["cleanup", "end"]:
    """
    Check if end-of-test cleanup is needed after log_results.

    CRITICAL: This must execute regardless of test pass/fail.

    PRIORITY ORDER:
    1. If post_condition_intents exist → ALWAYS "cleanup" (runs raw ADB intents)
    2. If explicit cleanup configs exist with end_of_test trigger → "cleanup"
    3. If nothing configured → "end" (NO default cleanup)

    Args:
        state: Current agent state

    Returns:
        "cleanup" | "end"
    """
    logger.info("🧹 Checking end-of-test cleanup...")

    # ═══════════════════════════════════════════════════════════
    # PRIORITY 1: Post condition intents ALWAYS take precedence
    # ═══════════════════════════════════════════════════════════
    post_condition_intents = state.get("post_condition_intents")
    if post_condition_intents:
        logger.info(f"   Post condition intents found: {len(post_condition_intents)} commands")
        logger.info("→ Route: cleanup (POST CONDITION - raw ADB intents will be executed)")
        return "cleanup"

    # ═══════════════════════════════════════════════════════════
    # PRIORITY 2: Explicit cleanup configs from Excel
    # ═══════════════════════════════════════════════════════════
    test_cleanup_config = state.get("test_cleanup_config")
    logger.info(f"   test_cleanup_config: {test_cleanup_config}")

    if not test_cleanup_config:
        step_cleanup_configs = state.get("step_cleanup_configs", [])
        logger.info(f"   step_cleanup_configs count: {len(step_cleanup_configs)}")

        for i, config in enumerate(step_cleanup_configs):
            cleanup_trigger = config.get("cleanup_trigger", "end_of_test")
            cleanup_type = config.get("cleanup_type", "none")
            logger.info(f"   Step {i}: type={cleanup_type}, trigger={cleanup_trigger}")

            if cleanup_trigger in ["end_of_test", "both"] and cleanup_type != "none":
                logger.info(f"→ Route: cleanup (found end_of_test trigger in step {i} config)")
                return "cleanup"

        # NO DEFAULT: Only cleanup if explicitly configured
        logger.info("→ Route: end (no post_condition and no explicit cleanup configured)")
        return "end"

    cleanup_type = test_cleanup_config.get("cleanup_type", "none")
    cleanup_trigger = test_cleanup_config.get("cleanup_trigger", "end_of_test")

    logger.info(f"   Test cleanup: type={cleanup_type}, trigger={cleanup_trigger}")

    test_failed = state.get("status") in [AgentStatus.FAILURE, AgentStatus.ERROR]

    # Check if cleanup should be triggered
    if cleanup_trigger == "end_of_test":
        if cleanup_type != "none":
            logger.info(f"→ Route: cleanup (trigger=end_of_test)")
            return "cleanup"
    elif cleanup_trigger == "both":
        if cleanup_type != "none":
            logger.info(f"→ Route: cleanup (trigger=both)")
            return "cleanup"
    elif cleanup_trigger == "always":
        if cleanup_type != "none":
            logger.info(f"→ Route: cleanup (trigger=always)")
            return "cleanup"
    elif cleanup_trigger == "on_failure" and test_failed:
        logger.info(f"→ Route: cleanup (trigger=on_failure, test_failed={test_failed})")
        return "cleanup"

    # No cleanup needed (explicit none configured at test level)
    logger.info("→ Route: end (test_cleanup_config has cleanup_type=none)")
    return "end"


def route_end_of_test_cleanup(state: AgentState) -> str:
    """
    Route end-of-test cleanup to appropriate handler.

    Args:
        state: Current agent state

    Returns:
        Cleanup node name or "end"
    """
    cleanup_config = state.get("current_cleanup_config", {})
    cleanup_type = cleanup_config.get("cleanup_type", "none")

    logger.info(f"🧹 End-of-test cleanup type: {cleanup_type}")

    # Map cleanup type to node
    cleanup_routing = {
        "none": "end",
        "post_condition": "cleanup_post_condition",  # Raw ADB intents from Excel
        "return_home": "cleanup_home",
        "reverse_action": "cleanup_reverse_action",
        "restore_state": "cleanup_restore_state",
        "close_dialog": "cleanup_close_dialog",
        "reboot": "cleanup_reboot",
        "factory_reset": "cleanup_factory_reset",
        "reverse_and_home": "cleanup_reverse_action",
        "close_and_reboot": "cleanup_close_dialog"
    }

    node = cleanup_routing.get(cleanup_type, "end")
    logger.info(f"→ Route: {node}")
    return node