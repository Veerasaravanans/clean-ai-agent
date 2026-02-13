"""
graph.py - LangGraph Workflow Graph Compilation

CRITICAL FIX: Proper HITL flow with apply_guidance node and graph resumption
"""

import logging
from langgraph.graph import StateGraph, END
from backend.langgraph.edges import route_after_next_step
from backend.langgraph.state import AgentState
from backend.langgraph import nodes
from backend.langgraph import edges

logger = logging.getLogger(__name__)


def create_agent_graph() -> StateGraph:
    """
    Create and compile the agent workflow graph.
    
    CRITICAL FIX: Added apply_guidance node and proper HITL flow
    
    Returns:
        Compiled StateGraph
    """
    logger.info("🔨 Building agent workflow graph...")
    
    # Initialize graph
    workflow = StateGraph(AgentState)
    
    # ═══════════════════════════════════════════════════════════════
    # Add all nodes (including apply_guidance and check_resume)
    # ═══════════════════════════════════════════════════════════════
    
    # Entry node for HITL resumption check
    workflow.add_node("check_resume", nodes.check_resume)
    
    # Part 1: Analysis & Planning
    workflow.add_node("detect_mode", nodes.detect_mode)
    workflow.add_node("rag_retrieval", nodes.rag_retrieval)
    workflow.add_node("check_learned", nodes.check_learned)
    workflow.add_node("capture_screen", nodes.capture_screen)
    workflow.add_node("ai_analyze", nodes.ai_analyze)
    workflow.add_node("plan_action", nodes.plan_action)
    
    # Part 2: Execution & Verification
    workflow.add_node("direct_execute", nodes.direct_execute)
    workflow.add_node("execute_adb", nodes.execute_adb)
    workflow.add_node("verify_result", nodes.verify_result)
    workflow.add_node("save_learned", nodes.save_learned)
    workflow.add_node("next_step", nodes.next_step)
    workflow.add_node("log_results", nodes.log_results)
    
    # Part 3: HITL & Standalone
    workflow.add_node("wait_human", nodes.wait_human)
    workflow.add_node("apply_guidance", nodes.apply_guidance)  # CRITICAL FIX: Added this node
    workflow.add_node("parse_intent", nodes.parse_intent)

    # Part 4: Error Handling (HITL Architecture Fix)
    workflow.add_node("handle_technical_error", nodes.handle_technical_error)  # NEW: Handle technical errors

    # Part 5: Cleanup System (Phase 5 Integration)
    workflow.add_node("cleanup_dispatcher", nodes.cleanup_dispatcher)
    workflow.add_node("cleanup_home", nodes.cleanup_home)
    workflow.add_node("cleanup_reverse_action", nodes.cleanup_reverse_action)
    workflow.add_node("cleanup_ai_driven", nodes.cleanup_ai_driven)
    workflow.add_node("cleanup_close_dialog", nodes.cleanup_close_dialog)
    workflow.add_node("cleanup_restore_state", nodes.cleanup_restore_state)
    workflow.add_node("cleanup_end_of_test", nodes.cleanup_end_of_test)
    workflow.add_node("cleanup_post_condition", nodes.cleanup_post_condition)  # NEW: Raw ADB intents
    workflow.add_node("cleanup_reboot", nodes.cleanup_reboot)
    workflow.add_node("cleanup_factory_reset", nodes.cleanup_factory_reset)

    # Helper node for retry increment
    workflow.add_node("increment_retry", edges.increment_retry)

    logger.info("✅ Added 27 nodes (including 10 cleanup nodes) + 1 helper")
    
    # ═══════════════════════════════════════════════════════════════
    # Set entry point with HITL resumption check
    # ═══════════════════════════════════════════════════════════════
    
    workflow.set_entry_point("check_resume")
    
    # ═══════════════════════════════════════════════════════════════
    # Add conditional edges
    # ═══════════════════════════════════════════════════════════════
    
    # 0. CRITICAL: Check if resuming from HITL
    workflow.add_conditional_edges(
        "check_resume",
        edges.should_resume_from_hitl,
        {
            "resume_hitl": "apply_guidance",  # Skip directly to apply guidance
            "normal_flow": "detect_mode"  # Normal flow
        }
    )
    
    # 1. Route by mode (test_execution vs standalone)
    workflow.add_conditional_edges(
        "detect_mode",
        edges.route_by_mode,
        {
            "test_execution": "rag_retrieval",
            "standalone": "parse_intent",
            "idle": END
        }
    )
    
    # 2. RAG retrieval → check learned
    workflow.add_edge("rag_retrieval", "check_learned")
    
    # 3. Check learned → use learned or capture screen
    workflow.add_conditional_edges(
        "check_learned",
        edges.should_use_learned,
        {
            "use_learned": "direct_execute",
            "no_learned": "capture_screen"
        }
    )
    
    # 4. Parse intent → capture screen
    workflow.add_edge("parse_intent", "capture_screen")
    
    # 5. Capture screen → AI analyze (CRITICAL: includes stop → END)
    workflow.add_conditional_edges(
        "capture_screen",
        edges.route_after_capture,
        {
            "analyze": "ai_analyze",
            "end": END
        }
    )

    # 6. AI analyze → plan action (CRITICAL: includes stop → END)
    workflow.add_conditional_edges(
        "ai_analyze",
        edges.route_after_analyze,
        {
            "plan": "plan_action",
            "end": END
        }
    )
    
    # 7. Plan action → route to execute or direct (CRITICAL: includes stop → END)
    workflow.add_conditional_edges(
        "plan_action",
        edges.route_from_planning,
        {
            "execute": "execute_adb",
            "direct": "direct_execute",
            "error": "wait_human",
            "end": END  # CRITICAL: Stop condition routes to END
        }
    )
    
    # 8. Direct execute → verify (CRITICAL: includes stop → END)
    workflow.add_conditional_edges(
        "direct_execute",
        edges.route_after_direct_execute,
        {
            "verify": "verify_result",
            "end": END  # CRITICAL: Stop condition routes to END
        }
    )
    
    # 9. Execute ADB → route based on success (CRITICAL: includes stop → END)
    workflow.add_conditional_edges(
        "execute_adb",
        edges.route_after_execution,
        {
            "verify": "verify_result",
            "retry": "increment_retry",
            "end": END  # CRITICAL: Stop condition routes to END
        }
    )
    
    # 10. Verify result → check cleanup → route (CLEANUP SYSTEM INTEGRATED)
    workflow.add_conditional_edges(
        "verify_result",
        edges.route_after_verification_with_cleanup,
        {
            "cleanup": "cleanup_dispatcher",  # Check cleanup first
            "next_step": "next_step",  # No cleanup, proceed to next step
            "retry": "increment_retry",
            "end": END  # CRITICAL: Stop condition routes to END
        }
    )
    
    # 11. Increment retry → should retry, test_failed, or end
    # NOTE: In test_execution mode, HITL is DISABLED
    # - "retry" → try again (capture_screen)
    # - "test_failed" → verification/decision failure at max retries → log_results (then cleanup)
    # - "end" → technical error → handle_technical_error (then cleanup)
    # - "hitl" → standalone mode only → wait_human
    workflow.add_conditional_edges(
        "increment_retry",
        edges.should_retry,
        {
            "retry": "capture_screen",
            "hitl": "wait_human",  # Only reached in standalone mode
            "test_failed": "log_results",  # Verification/decision failure → log as FAILED → cleanup
            "end": "handle_technical_error"  # Technical error only
        }
    )
    
    # 12. Wait human → check if guidance received (STANDALONE MODE ONLY)
    # HITL is only used in standalone/idle mode, NOT in test execution
    # If guidance already in state → apply it
    # Else → END (wait for external HITL via API)
    workflow.add_conditional_edges(
        "wait_human",
        edges.route_hitl_ready,
        {
            "guidance_received": "apply_guidance",
            "waiting": END
        }
    )
    
    # 13. CRITICAL FIX: Apply guidance → execute_adb
    # After applying HITL guidance, retry the action with new coordinates
    workflow.add_edge("apply_guidance", "execute_adb")
    
    # 14. Next step → check if complete (CRITICAL: includes stop → END)
    workflow.add_conditional_edges(
        "next_step",
        route_after_next_step,
        {
            "save_learned": "save_learned",
            "direct_execute": "direct_execute",
            "capture_screen": "capture_screen",
            "end": END  # CRITICAL: Stop condition routes to END
        }
    )
    
    # 15. Save learned → log results (CRITICAL: includes stop → END)
    workflow.add_conditional_edges(
        "save_learned",
        edges.route_after_save_learned,
        {
            "log": "log_results",
            "end": END
        }
    )
    
    # 10b. CLEANUP SYSTEM: Cleanup dispatcher routes to handlers
    workflow.add_conditional_edges(
        "cleanup_dispatcher",
        edges.route_cleanup_type,
        {
            "next_step": "next_step",  # No cleanup (cleanup_type=none)
            "cleanup_home": "cleanup_home",
            "cleanup_reverse_action": "cleanup_reverse_action",
            "cleanup_close_dialog": "cleanup_close_dialog",
            "cleanup_ai_driven": "cleanup_ai_driven",
            "cleanup_restore_state": "cleanup_restore_state",
            "cleanup_reboot": "cleanup_reboot",
            "cleanup_factory_reset": "cleanup_factory_reset"
        }
    )

    # 10c. CLEANUP SYSTEM: Cleanup handlers route based on cleanup_phase
    # If in_step → next_step, if end_of_test → END
    def route_after_cleanup_handler(state: AgentState) -> str:
        """Route after cleanup handler based on cleanup_phase."""
        cleanup_phase = state.get("cleanup_phase", "in_step")
        if cleanup_phase == "end_of_test":
            return "end"
        return "next_step"

    workflow.add_conditional_edges(
        "cleanup_home",
        route_after_cleanup_handler,
        {"next_step": "next_step", "end": END}
    )
    workflow.add_conditional_edges(
        "cleanup_reverse_action",
        route_after_cleanup_handler,
        {"next_step": "next_step", "end": END}
    )
    workflow.add_conditional_edges(
        "cleanup_close_dialog",
        route_after_cleanup_handler,
        {"next_step": "next_step", "end": END}
    )
    workflow.add_conditional_edges(
        "cleanup_restore_state",
        route_after_cleanup_handler,
        {"next_step": "next_step", "end": END}
    )
    workflow.add_conditional_edges(
        "cleanup_reboot",
        route_after_cleanup_handler,
        {"next_step": "next_step", "end": END}
    )
    workflow.add_conditional_edges(
        "cleanup_factory_reset",
        route_after_cleanup_handler,
        {"next_step": "next_step", "end": END}
    )

    # 10d. CLEANUP SYSTEM: AI-driven cleanup routes to chosen handler
    workflow.add_conditional_edges(
        "cleanup_ai_driven",
        edges.route_ai_cleanup_decision,
        {
            "cleanup_home": "cleanup_home",
            "cleanup_reverse_action": "cleanup_reverse_action",
            "cleanup_close_dialog": "cleanup_close_dialog",
            "cleanup_restore_state": "cleanup_restore_state",
            "cleanup_reboot": "cleanup_reboot"
        }
    )

    # 16. CLEANUP SYSTEM: Log results → check end-of-test cleanup → END
    workflow.add_conditional_edges(
        "log_results",
        edges.should_cleanup_end_of_test,
        {
            "cleanup": "cleanup_end_of_test",
            "end": END
        }
    )

    # 16a. CLEANUP SYSTEM: End-of-test cleanup orchestrator routes to handlers
    workflow.add_conditional_edges(
        "cleanup_end_of_test",
        edges.route_end_of_test_cleanup,
        {
            "end": END,  # No cleanup
            "cleanup_post_condition": "cleanup_post_condition",  # Raw ADB intents
            "cleanup_home": "cleanup_home",
            "cleanup_reverse_action": "cleanup_reverse_action",
            "cleanup_close_dialog": "cleanup_close_dialog",
            "cleanup_restore_state": "cleanup_restore_state",
            "cleanup_reboot": "cleanup_reboot",
            "cleanup_factory_reset": "cleanup_factory_reset"
        }
    )

    # 16b. Post condition cleanup → END (always terminates after executing intents)
    workflow.add_edge("cleanup_post_condition", END)

    # Handle technical error → check cleanup before END
    # CRITICAL: Post condition must execute even on test failure
    workflow.add_conditional_edges(
        "handle_technical_error",
        edges.should_cleanup_end_of_test,
        {
            "cleanup": "cleanup_end_of_test",
            "end": END
        }
    )

    logger.info("✅ Added all edges and routing (with HITL flow, cleanup system, and technical error handling)")
    
    # ═══════════════════════════════════════════════════════════════
    # Compile graph WITHOUT interrupts (no checkpointer needed)
    # ═══════════════════════════════════════════════════════════════
    
    try:
        # Simple compilation - orchestrator handles HITL state updates
        compiled_graph = workflow.compile()
        logger.info("✅ Graph compiled successfully with HITL flow!")
        return compiled_graph
    except Exception as e:
        logger.error(f"❌ Graph compilation failed: {e}")
        raise


# ═══════════════════════════════════════════════════════════════
# Create singleton graph instance
# ═══════════════════════════════════════════════════════════════

try:
    agent_graph = create_agent_graph()
    logger.info("✅ Agent graph ready")
except Exception as e:
    logger.error(f"❌ Failed to create agent graph: {e}")
    agent_graph = None