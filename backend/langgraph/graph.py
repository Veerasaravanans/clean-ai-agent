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
    
    # Helper node for retry increment
    workflow.add_node("increment_retry", edges.increment_retry)
    
    logger.info("✅ Added 16 nodes + 1 helper")
    
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
    
    # 5. Capture screen → AI analyze
    workflow.add_edge("capture_screen", "ai_analyze")
    
    # 6. AI analyze → plan action
    workflow.add_edge("ai_analyze", "plan_action")
    
    # 7. Plan action → route to execute or direct
    workflow.add_conditional_edges(
        "plan_action",
        edges.route_from_planning,
        {
            "execute": "execute_adb",
            "direct": "direct_execute",
            "error": "wait_human"
        }
    )
    
    # 8. Direct execute → verify
    workflow.add_edge("direct_execute", "verify_result")
    
    # 9. Execute ADB → route based on success
    workflow.add_conditional_edges(
        "execute_adb",
        edges.route_after_execution,
        {
            "verify": "verify_result",
            "retry": "increment_retry"
        }
    )
    
    # 10. Verify result → route based on verification
    workflow.add_conditional_edges(
        "verify_result",
        edges.route_after_verification,
        {
            "success": "next_step",
            "retry": "increment_retry"
        }
    )
    
    # 11. Increment retry → should retry or HITL
    workflow.add_conditional_edges(
        "increment_retry",
        edges.should_retry,
        {
            "retry": "capture_screen",
            "hitl": "wait_human"
        }
    )
    
    # 12. CRITICAL FIX: Wait human → check if guidance received
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
    
    # 14. Next step → check if complete
    workflow.add_conditional_edges(
    "next_step",
    route_after_next_step,
    {
        "save_learned": "save_learned",
        "direct_execute": "direct_execute",
        "capture_screen": "capture_screen"
    }
)
    
    # 15. Save learned → log results
    workflow.add_edge("save_learned", "log_results")
    
    # 16. Log results → END
    workflow.add_edge("log_results", END)
    
    logger.info("✅ Added all edges and routing (with proper HITL flow)")
    
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