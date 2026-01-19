"""
agent_orchestrator.py - Agent Orchestrator Service

Manages LangGraph workflow execution, state, and HITL.

MINIMAL FIX: Only send_guidance() changed to async with graph re-invocation.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from backend.langgraph import create_agent_graph, create_initial_state
from backend.langgraph.state import AgentState
from backend.models import AgentMode, AgentStatus

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates agent workflow execution using LangGraph.
    
    Manages:
    - Graph execution
    - State tracking
    - HITL guidance
    - Concurrent executions
    """
    
    def __init__(self):
        """Initialize orchestrator."""
        self.graph = create_agent_graph()
        self.current_state: Optional[AgentState] = None
        self.execution_active = False
        self.execution_task: Optional[asyncio.Task] = None
        
        logger.info("✅ Agent Orchestrator initialized")
    
    # ═══════════════════════════════════════════════════════════════
    # Test Execution
    # ═══════════════════════════════════════════════════════════════
    
    async def run_test(
        self,
        test_id: str,
        use_learned: bool = True,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Run test execution workflow for a single test case.
        
        Args:
            test_id: Single test case ID (e.g., "NAID-NEW-001")
            use_learned: Whether to use learned solutions
            max_retries: Maximum retry attempts
            
        Returns:
            Execution result summary
        """
        # Validate test_id is a single ID
        test_id = test_id.strip()
        if "," in test_id or ";" in test_id:
            logger.error(f"❌ Invalid test_id format (contains separator): {test_id}")
            return {
                "success": False,
                "status": "error",
                "error": "test_id should be a single ID, not comma/semicolon-separated",
                "test_id": test_id,
                "steps_completed": 0,
                "total_steps": 0,
                "errors": ["Invalid test_id format"]
            }
        
        if self.execution_active:
            logger.warning("⚠️ Execution already active, waiting...")
            # Wait for previous execution to complete (with timeout)
            wait_time = 0
            max_wait = 60  # 60 seconds max wait
            while self.execution_active and wait_time < max_wait:
                await asyncio.sleep(1)
                wait_time += 1
            
            if self.execution_active:
                logger.error("❌ Previous execution did not complete in time")
                return {
                    "success": False,
                    "status": "error",
                    "error": "Previous execution still in progress",
                    "test_id": test_id,
                    "steps_completed": 0,
                    "total_steps": 0,
                    "errors": ["Execution timeout"]
                }
        
        logger.info(f"▶️ Starting test execution: {test_id}")
        
        try:
            # Create initial state
            self.current_state = create_initial_state(
                mode=AgentMode.TEST_EXECUTION,
                test_id=test_id,
                use_learned=use_learned,
                max_retries=max_retries
            )
            
            self.execution_active = True
            
            # Run graph synchronously (LangGraph invoke)
            config = {"recursion_limit": 100}
            result_state = await asyncio.to_thread(
                self.graph.invoke,
                self.current_state,
                config
            )
            
            self.current_state = result_state
            self.execution_active = False
            
            # Extract result safely
            status = result_state.get("status", AgentStatus.FAILURE)
            errors = result_state.get("errors", [])
            
            # Handle status safely
            if isinstance(status, str):
                status_str = status
                success = status == "success"
            elif hasattr(status, 'value'):
                status_str = status.value
                success = status == AgentStatus.SUCCESS
            else:
                status_str = str(status) if status else "unknown"
                success = False
            
            logger.info(f"✅ Test execution complete: {status_str}")
            
            return {
                "success": success,
                "status": status_str,
                "test_id": test_id,
                "steps_completed": result_state.get("current_step", 0),
                "total_steps": result_state.get("total_steps", 0),
                "errors": errors
            }
        
        except Exception as e:
            logger.error(f"❌ Test execution error: {e}")
            import traceback
            traceback.print_exc()
            self.execution_active = False
            
            return {
                "success": False,
                "status": "error",
                "error": str(e),
                "test_id": test_id,
                "steps_completed": 0,
                "total_steps": 0,
                "errors": [str(e)]
            }


    async def run_tests_batch(
        self,
        test_ids: List[str],
        use_learned: bool = True,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Run multiple test cases sequentially.
        
        This is an alternative method if you want batch processing in orchestrator.
        
        Args:
            test_ids: List of test case IDs
            use_learned: Whether to use learned solutions
            max_retries: Maximum retry attempts per test
            
        Returns:
            Combined results for all tests
        """
        results = []
        
        for i, test_id in enumerate(test_ids):
            clean_id = test_id.strip()
            if not clean_id:
                continue
            
            logger.info(f"═══════════════════════════════════════")
            logger.info(f"▶️ Running test {i + 1}/{len(test_ids)}: {clean_id}")
            logger.info(f"═══════════════════════════════════════")
            
            result = await self.run_test(
                test_id=clean_id,
                use_learned=use_learned,
                max_retries=max_retries
            )
            results.append(result)
            
            # Small delay between tests for UI stability
            await asyncio.sleep(0.5)
        
        passed = sum(1 for r in results if r.get("success"))
        failed = len(results) - passed
        
        return {
            "success": failed == 0,
            "status": "batch_complete",
            "results": results,
            "total": len(results),
            "passed": passed,
            "failed": failed
        }
    
    # ═══════════════════════════════════════════════════════════════
    # Standalone Execution
    # ═══════════════════════════════════════════════════════════════
    
    async def execute_command(
        self,
        command: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Execute standalone natural language command.
        
        Args:
            command: Natural language command
            max_retries: Maximum retry attempts
            
        Returns:
            Execution result
        """
        if self.execution_active:
            logger.warning("⚠️ Execution already active")
            return {
                "success": False,
                "error": "Execution already in progress"
            }
        
        logger.info(f"▶️ Executing command: {command[:100]}")
        
        try:
            # Create initial state
            self.current_state = create_initial_state(
                mode=AgentMode.STANDALONE,
                standalone_command=command,
                max_retries=max_retries
            )
            
            self.execution_active = True
            
            # Run graph with high recursion limit (100) to allow retries until success
            config = {"recursion_limit": 100}
            result_state = await asyncio.to_thread(
                self.graph.invoke,
                self.current_state,
                config
            )
            
            self.current_state = result_state
            self.execution_active = False
            
            # Extract result safely
            status = result_state.get("status", AgentStatus.FAILURE)
            
            # Handle status safely
            if isinstance(status, str):
                status_str = status
                success = status == "success"
            elif hasattr(status, 'value'):
                status_str = status.value
                success = status == AgentStatus.SUCCESS
            else:
                status_str = str(status) if status else "unknown"
                success = False
            
            logger.info(f"✅ Command execution complete: {status_str}")
            
            return {
                "success": success,
                "status": status_str,
                "command": command,
                "execution_log": result_state.get("execution_log", [])[-5:]
            }
        
        except Exception as e:
            logger.error(f"❌ Command execution error: {e}")
            import traceback
            traceback.print_exc()
            self.execution_active = False
            
            # Return proper error response
            return {
                "success": False,
                "status": "error",
                "error": str(e),
                "command": command,
                "execution_log": []
            }
    
    # ═══════════════════════════════════════════════════════════════
    # HITL (Human-in-the-Loop)
    # ═══════════════════════════════════════════════════════════════
    
    async def send_guidance(
        self,
        guidance: str = "",
        coordinates: Optional[tuple] = None,
        action_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send human guidance to agent and RESUME execution.
        
        CRITICAL FIX: Changed from sync to async and added graph re-invocation.
        Without re-invocation, graph stays ended at wait_human → END.
        
        Args:
            guidance: Text guidance
            coordinates: Tap coordinates (x, y)
            action_type: Action type override
            
        Returns:
            Execution result
        """
        if not self.current_state:
            logger.warning("⚠️ No active execution")
            return {
                "success": False,
                "error": "No active execution"
            }
        
        logger.info("👤 Receiving human guidance")
        logger.info(f"   Guidance: {guidance[:100] if guidance else 'None'}")
        logger.info(f"   Coordinates: {coordinates}")
        
        # Update state with guidance
        self.current_state = {
            **self.current_state,
            "hitl_guidance": guidance,
            "hitl_coordinates": coordinates,
            "hitl_action_type": action_type
        }
        
        logger.info("✅ Guidance received, resuming execution")
        
        # ✅ CRITICAL FIX: Re-invoke graph to resume execution
        try:
            logger.info("🔄 Re-invoking graph with HITL guidance...")
            config = {"recursion_limit": 100}
            result_state = await asyncio.to_thread(
                self.graph.invoke,
                self.current_state,
                config
            )
            
            self.current_state = result_state
            
            # Check result status
            status = result_state.get("status", AgentStatus.RUNNING)
            if isinstance(status, str):
                status_str = status
            elif hasattr(status, 'value'):
                status_str = status.value
            else:
                status_str = str(status)
            
            logger.info(f"✅ Graph resumed - Status: {status_str}")
            
            return {
                "success": True,
                "message": "Guidance applied and execution resumed",
                "status": status_str
            }
        
        except Exception as e:
            logger.error(f"❌ Error resuming execution: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Failed to resume: {e}"
            }
    
    def skip_step(self) -> Dict[str, Any]:
        """
        Skip current test step.
        
        Returns:
            Confirmation
        """
        if not self.current_state:
            return {"success": False, "error": "No active execution"}
        
        logger.info("⏭️ Skipping current step")
        
        current_step = self.current_state.get("current_step", 0)
        self.current_state = {
            **self.current_state,
            "current_step": current_step + 1,
            "retry_count": 0,
            "waiting_for_hitl": False
        }
        
        return {"success": True, "message": "Step skipped"}
    
    def abort_test(self) -> Dict[str, Any]:
        """
        Abort current test execution.
        
        Returns:
            Confirmation
        """
        logger.info("🛑 Aborting test execution")
        
        if self.current_state:
            self.current_state = {
                **self.current_state,
                "stop_requested": True,
                "status": AgentStatus.STOPPED,
                "should_continue": False
            }
        
        self.execution_active = False
        
        return {"success": True, "message": "Test aborted"}
    
    # ═══════════════════════════════════════════════════════════════
    # Status & Control
    # ═══════════════════════════════════════════════════════════════
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current agent status.
        
        Returns:
            Status information
        """
        if not self.current_state:
            return {
                "status": "idle",
                "mode": "idle",
                "active": False
            }
        
        # Safe extraction
        status = self.current_state.get("status", AgentStatus.IDLE)
        mode = self.current_state.get("current_mode", AgentMode.IDLE)
        
        return {
            "status": status.value if hasattr(status, 'value') else str(status),
            "mode": mode.value if hasattr(mode, 'value') else str(mode),
            "active": self.execution_active,
            "current_test_id": self.current_state.get("test_id"),
            "current_step": self.current_state.get("current_step", 0),
            "total_steps": self.current_state.get("total_steps", 0),
            "waiting_for_hitl": self.current_state.get("waiting_for_hitl", False),
            "hitl_problem": self.current_state.get("hitl_problem")
        }
    
    def stop(self) -> Dict[str, Any]:
        """
        Stop current execution.
        
        Returns:
            Confirmation
        """
        logger.info("🛑 Stopping execution")
        
        if self.current_state:
            self.current_state = {
                **self.current_state,
                "stop_requested": True,
                "should_continue": False
            }
        
        self.execution_active = False
        
        return {"success": True, "message": "Execution stopped"}
    
    def reset(self) -> Dict[str, Any]:
        """
        Reset orchestrator state.
        
        Returns:
            Confirmation
        """
        logger.info("🔄 Resetting orchestrator")
        
        self.current_state = None
        self.execution_active = False
        
        return {"success": True, "message": "Orchestrator reset"}
    
    def get_learned_solutions(self) -> List[str]:
        """
        Get list of learned test IDs.
        
        Returns:
            List of test IDs
        """
        # This would query RAG in production
        # For now, return placeholder
        return []


# ═══════════════════════════════════════════════════════════════
# Singleton instance
# ═══════════════════════════════════════════════════════════════

_orchestrator_instance: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """
    Get singleton orchestrator instance.
    
    Returns:
        AgentOrchestrator instance
    """
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    
    return _orchestrator_instance