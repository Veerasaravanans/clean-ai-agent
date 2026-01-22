"""
test_history_service.py - Test History Management Service

Manages test execution history, analytics, and dashboard data.
Stores data in JSON files for persistence.

Structure:
data/test_history/
    index.json                  # Index with execution IDs and metadata
    executions/
        {execution_id}.json     # Full execution details
"""

import logging
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

from backend.models.test_history import (
    TestExecutionRecord,
    StepRecord,
    ExecutionStatus,
    TestAnalytics,
    DashboardSummary,
    DailyStats,
    TestCaseStats
)

logger = logging.getLogger(__name__)


class TestHistoryService:
    """Service for managing test execution history."""

    def __init__(self, base_dir: str = "data/test_history"):
        """
        Initialize test history service.

        Args:
            base_dir: Base directory for history storage
        """
        self.base_dir = Path(base_dir)
        self.executions_dir = self.base_dir / "executions"
        self.index_file = self.base_dir / "index.json"

        # Create directories
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.executions_dir.mkdir(parents=True, exist_ok=True)

        # Load or create index
        self.index = self._load_index()

        logger.info(f"Test History Service initialized - Base: {self.base_dir}")
        logger.info(f"Total executions in history: {len(self.index.get('executions', []))}")

    # ═══════════════════════════════════════════════════════════
    # Index Management
    # ═══════════════════════════════════════════════════════════

    def _load_index(self) -> Dict:
        """Load index file."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
                return {"executions": [], "stats": {}}
        return {"executions": [], "stats": {}}

    def _save_index(self):
        """Save index file."""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    # ═══════════════════════════════════════════════════════════
    # Execution CRUD
    # ═══════════════════════════════════════════════════════════

    def create_execution(
        self,
        test_id: str,
        test_title: Optional[str] = None,
        use_learned: bool = True,
        max_retries: int = 3,
        device_id: Optional[str] = None,
        device_model: Optional[str] = None,
        device_resolution: Optional[str] = None,
        model_used: Optional[str] = None
    ) -> TestExecutionRecord:
        """
        Create a new test execution record.

        Args:
            test_id: Test case ID
            test_title: Test case title
            use_learned: Whether learned solutions are used
            max_retries: Maximum retry count
            device_id: Device identifier
            device_model: Device model name
            device_resolution: Device resolution
            model_used: VIO model used

        Returns:
            New TestExecutionRecord
        """
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        record = TestExecutionRecord(
            execution_id=execution_id,
            test_id=test_id,
            test_title=test_title,
            use_learned=use_learned,
            max_retries=max_retries,
            device_id=device_id,
            device_model=device_model,
            device_resolution=device_resolution,
            model_used=model_used
        )

        # Save execution file
        self._save_execution(record)

        # Update index
        self.index["executions"].insert(0, {
            "execution_id": execution_id,
            "test_id": test_id,
            "status": record.status.value,
            "started_at": record.started_at
        })
        self._save_index()

        logger.info(f"Created execution record: {execution_id} for test {test_id}")
        return record

    def update_execution(self, record: TestExecutionRecord) -> bool:
        """
        Update an existing execution record.

        Args:
            record: Updated TestExecutionRecord

        Returns:
            Success boolean
        """
        try:
            self._save_execution(record)

            # Update index entry
            for entry in self.index["executions"]:
                if entry["execution_id"] == record.execution_id:
                    entry["status"] = record.status.value if isinstance(record.status, ExecutionStatus) else record.status
                    entry["completed_at"] = record.completed_at
                    break

            self._save_index()
            return True
        except Exception as e:
            logger.error(f"Failed to update execution {record.execution_id}: {e}")
            return False

    def complete_execution(
        self,
        execution_id: str,
        status: ExecutionStatus,
        errors: Optional[List[str]] = None
    ) -> Optional[TestExecutionRecord]:
        """
        Mark an execution as complete.

        Args:
            execution_id: Execution identifier
            status: Final status
            errors: List of error messages

        Returns:
            Updated record or None
        """
        record = self.get_execution(execution_id)
        if not record:
            return None

        now = datetime.now()
        record.status = status
        record.completed_at = now.isoformat()

        # Calculate duration
        started = datetime.fromisoformat(record.started_at)
        record.duration_ms = int((now - started).total_seconds() * 1000)

        # Calculate step stats
        record.passed_steps = sum(1 for s in record.steps if s.status == "success")
        record.failed_steps = sum(1 for s in record.steps if s.status in ["failure", "error"])

        # Calculate SSIM stats
        ssim_scores = [s.ssim_score for s in record.steps if s.ssim_score is not None]
        record.ssim_verifications = len(ssim_scores)
        record.ssim_passed = sum(1 for s in record.steps if s.ssim_passed)
        record.ssim_failed = record.ssim_verifications - record.ssim_passed
        if ssim_scores:
            record.average_ssim = sum(ssim_scores) / len(ssim_scores)

        if errors:
            record.errors.extend(errors)

        self.update_execution(record)
        logger.info(f"Completed execution {execution_id} with status {status.value}")
        return record

    def add_step(
        self,
        execution_id: str,
        step_number: int,
        description: str = "",
        goal: Optional[str] = None,
        action_type: Optional[str] = None,
        action_target: Optional[str] = None,
        action_details: Optional[Dict] = None,
        coordinates_x: Optional[int] = None,
        coordinates_y: Optional[int] = None,
        coordinate_source: Optional[str] = None,
        used_learned_solution: Optional[bool] = None,
        before_screenshot_path: Optional[str] = None
    ) -> Optional[StepRecord]:
        """
        Add a step to an execution record.

        Args:
            execution_id: Execution identifier
            step_number: Step number (1-based)
            description: Step description from test case
            goal: Goal/expected outcome
            action_type: Action type (tap, swipe, etc.)
            action_target: Target element name
            action_details: Action parameters
            coordinates_x: X coordinate used
            coordinates_y: Y coordinate used
            coordinate_source: Source of coordinates (learned, device_profile, ai_detection)
            used_learned_solution: Whether learned solution was used
            before_screenshot_path: Screenshot before action

        Returns:
            New StepRecord or None
        """
        record = self.get_execution(execution_id)
        if not record:
            return None

        step = StepRecord(
            step_number=step_number,
            description=description,
            goal=goal,
            action_type=action_type,
            action_target=action_target,
            action_details=action_details,
            coordinates_x=coordinates_x,
            coordinates_y=coordinates_y,
            coordinate_source=coordinate_source,
            used_learned_solution=used_learned_solution,
            before_screenshot_path=before_screenshot_path
        )

        record.steps.append(step)
        record.total_steps = max(record.total_steps, step_number)
        self.update_execution(record)

        return step

    def update_step(
        self,
        execution_id: str,
        step_number: int,
        status: str,
        ssim_score: Optional[float] = None,
        ssim_passed: Optional[bool] = None,
        ssim_threshold: Optional[float] = None,
        reference_image_name: Optional[str] = None,
        screenshot_path: Optional[str] = None,
        after_screenshot_path: Optional[str] = None,
        comparison_image_path: Optional[str] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> bool:
        """
        Update a step in an execution record.

        Args:
            execution_id: Execution identifier
            step_number: Step number to update
            status: New status
            ssim_score: SSIM verification score
            ssim_passed: Whether SSIM passed
            ssim_threshold: SSIM threshold used
            reference_image_name: Reference image name used
            screenshot_path: Alias for after_screenshot_path
            after_screenshot_path: Screenshot after action
            comparison_image_path: Side-by-side comparison image
            error_message: Error message
            duration_ms: Step duration

        Returns:
            Success boolean
        """
        record = self.get_execution(execution_id)
        if not record:
            return False

        for step in record.steps:
            if step.step_number == step_number:
                step.status = status
                if ssim_score is not None:
                    step.ssim_score = float(ssim_score)  # Ensure Python float
                if ssim_passed is not None:
                    step.ssim_passed = bool(ssim_passed)  # Ensure Python bool
                if ssim_threshold is not None:
                    step.ssim_threshold = float(ssim_threshold)
                if reference_image_name:
                    step.reference_image_name = reference_image_name
                if screenshot_path:
                    step.screenshot_path = screenshot_path
                    step.after_screenshot_path = screenshot_path
                if after_screenshot_path:
                    step.after_screenshot_path = after_screenshot_path
                    step.screenshot_path = after_screenshot_path
                if comparison_image_path:
                    step.comparison_image_path = comparison_image_path
                if error_message:
                    step.error_message = error_message
                if duration_ms is not None:
                    step.duration_ms = int(duration_ms)

                # Update completed steps count
                record.completed_steps = sum(1 for s in record.steps if s.status in ["success", "failure", "error"])

                self.update_execution(record)
                return True

        return False

    def get_execution(self, execution_id: str) -> Optional[TestExecutionRecord]:
        """
        Get a specific execution record.

        Args:
            execution_id: Execution identifier

        Returns:
            TestExecutionRecord or None
        """
        file_path = self.executions_dir / f"{execution_id}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return TestExecutionRecord(**data)
        except Exception as e:
            logger.error(f"Failed to load execution {execution_id}: {e}")
            return None

    def delete_execution(self, execution_id: str) -> bool:
        """
        Delete an execution record.

        Args:
            execution_id: Execution identifier

        Returns:
            Success boolean
        """
        try:
            # Delete file
            file_path = self.executions_dir / f"{execution_id}.json"
            if file_path.exists():
                file_path.unlink()

            # Remove from index
            self.index["executions"] = [
                e for e in self.index["executions"]
                if e["execution_id"] != execution_id
            ]
            self._save_index()

            logger.info(f"Deleted execution: {execution_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete execution {execution_id}: {e}")
            return False

    def _save_execution(self, record: TestExecutionRecord):
        """Save execution record to file."""
        file_path = self.executions_dir / f"{record.execution_id}.json"
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(record.model_dump(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save execution {record.execution_id}: {e}")

    # ═══════════════════════════════════════════════════════════
    # List & Filter
    # ═══════════════════════════════════════════════════════════

    def list_executions(
        self,
        page: int = 1,
        page_size: int = 20,
        test_id: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort_by: str = "started_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        List executions with pagination and filters.

        Args:
            page: Page number
            page_size: Items per page
            test_id: Filter by test ID
            status: Filter by status
            date_from: Start date filter
            date_to: End date filter
            sort_by: Sort field
            sort_order: asc or desc

        Returns:
            Dict with executions, total, and pagination info
        """
        # Filter executions
        filtered = self.index["executions"].copy()

        if test_id:
            filtered = [e for e in filtered if e["test_id"] == test_id]

        if status:
            filtered = [e for e in filtered if e["status"] == status]

        if date_from:
            filtered = [e for e in filtered if e["started_at"][:10] >= date_from]

        if date_to:
            filtered = [e for e in filtered if e["started_at"][:10] <= date_to]

        # Sort
        reverse = sort_order == "desc"
        filtered.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)

        # Paginate
        total = len(filtered)
        total_pages = (total + page_size - 1) // page_size
        start = (page - 1) * page_size
        end = start + page_size
        paginated = filtered[start:end]

        # Load full records for paginated results
        executions = []
        for entry in paginated:
            record = self.get_execution(entry["execution_id"])
            if record:
                executions.append({
                    "execution_id": record.execution_id,
                    "test_id": record.test_id,
                    "test_title": record.test_title,
                    "status": record.status.value if isinstance(record.status, ExecutionStatus) else record.status,
                    "started_at": record.started_at,
                    "completed_at": record.completed_at,
                    "duration_ms": record.duration_ms,
                    "total_steps": record.total_steps,
                    "passed_steps": record.passed_steps,
                    "failed_steps": record.failed_steps,
                    "pass_rate": (record.passed_steps / record.total_steps * 100) if record.total_steps > 0 else 0,
                    "ssim_pass_rate": (record.ssim_passed / record.ssim_verifications * 100) if record.ssim_verifications > 0 else 0,
                    "device_model": record.device_model,
                    "model_used": record.model_used
                })

        return {
            "executions": executions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    def get_test_history(self, test_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get execution history for a specific test.

        Args:
            test_id: Test case ID
            limit: Maximum results

        Returns:
            List of execution summaries
        """
        filtered = [
            e for e in self.index["executions"]
            if e["test_id"] == test_id
        ][:limit]

        history = []
        for entry in filtered:
            record = self.get_execution(entry["execution_id"])
            if record:
                history.append({
                    "execution_id": record.execution_id,
                    "status": record.status.value if isinstance(record.status, ExecutionStatus) else record.status,
                    "started_at": record.started_at,
                    "completed_at": record.completed_at,
                    "duration_ms": record.duration_ms,
                    "passed_steps": record.passed_steps,
                    "failed_steps": record.failed_steps,
                    "average_ssim": record.average_ssim
                })

        return history

    # ═══════════════════════════════════════════════════════════
    # Analytics
    # ═══════════════════════════════════════════════════════════

    def get_analytics(self) -> TestAnalytics:
        """
        Get comprehensive test analytics.

        Returns:
            TestAnalytics with trends and statistics
        """
        now = datetime.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Initialize counters
        total_executions = 0
        total_passed = 0
        total_failed = 0
        total_ssim_verifications = 0
        total_ssim_passed = 0
        total_duration_ms = 0
        durations = []
        ssim_scores = []
        daily_data = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "durations": [], "ssims": []})
        test_data = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0, "last_execution": None, "last_status": None, "durations": []})

        # Process all executions
        for entry in self.index["executions"]:
            record = self.get_execution(entry["execution_id"])
            if not record:
                continue

            total_executions += 1
            status = record.status.value if isinstance(record.status, ExecutionStatus) else record.status

            if status == "success":
                total_passed += 1
            elif status in ["failure", "error"]:
                total_failed += 1

            # SSIM stats
            total_ssim_verifications += record.ssim_verifications
            total_ssim_passed += record.ssim_passed
            if record.average_ssim is not None:
                ssim_scores.append(record.average_ssim)

            # Duration
            if record.duration_ms:
                total_duration_ms += record.duration_ms
                durations.append(record.duration_ms)

            # Daily stats
            date_str = record.started_at[:10]
            daily_data[date_str]["total"] += 1
            if status == "success":
                daily_data[date_str]["passed"] += 1
            elif status in ["failure", "error"]:
                daily_data[date_str]["failed"] += 1
            if record.duration_ms:
                daily_data[date_str]["durations"].append(record.duration_ms)
            if record.average_ssim is not None:
                daily_data[date_str]["ssims"].append(record.average_ssim)

            # Test case stats
            test_data[record.test_id]["total"] += 1
            test_data[record.test_id]["title"] = record.test_title
            if status == "success":
                test_data[record.test_id]["passed"] += 1
            elif status in ["failure", "error"]:
                test_data[record.test_id]["failed"] += 1
            test_data[record.test_id]["last_execution"] = record.started_at
            test_data[record.test_id]["last_status"] = status
            if record.duration_ms:
                test_data[record.test_id]["durations"].append(record.duration_ms)

        # Build daily stats for last 30 days
        daily_stats = []
        for i in range(30):
            date = (today - timedelta(days=i)).isoformat()
            data = daily_data[date]
            pass_rate = (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0
            avg_duration = (sum(data["durations"]) / len(data["durations"])) if data["durations"] else None
            avg_ssim = (sum(data["ssims"]) / len(data["ssims"])) if data["ssims"] else None

            daily_stats.append(DailyStats(
                date=date,
                total_executions=data["total"],
                passed=data["passed"],
                failed=data["failed"],
                pass_rate=pass_rate,
                average_duration_ms=avg_duration,
                average_ssim=avg_ssim
            ))

        # Build test case stats
        test_stats = []
        for test_id, data in test_data.items():
            pass_rate = (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0
            avg_duration = (sum(data["durations"]) / len(data["durations"])) if data["durations"] else None

            test_stats.append(TestCaseStats(
                test_id=test_id,
                test_title=data.get("title"),
                total_executions=data["total"],
                passed=data["passed"],
                failed=data["failed"],
                pass_rate=pass_rate,
                last_execution=data["last_execution"],
                last_status=data["last_status"],
                average_duration_ms=avg_duration
            ))

        # Sort for most executed and most failed
        most_executed = sorted(test_stats, key=lambda x: x.total_executions, reverse=True)[:10]
        most_failed = sorted([t for t in test_stats if t.failed > 0], key=lambda x: x.failed, reverse=True)[:10]

        # Count time-based stats
        executions_today = sum(1 for e in self.index["executions"] if e["started_at"][:10] == str(today))
        executions_week = sum(1 for e in self.index["executions"] if e["started_at"][:10] >= str(week_ago))
        executions_month = sum(1 for e in self.index["executions"] if e["started_at"][:10] >= str(month_ago))

        # Get last execution time
        last_execution_time = self.index["executions"][0]["started_at"] if self.index["executions"] else None

        return TestAnalytics(
            total_executions=total_executions,
            total_passed=total_passed,
            total_failed=total_failed,
            overall_pass_rate=(total_passed / total_executions * 100) if total_executions > 0 else 0,
            executions_today=executions_today,
            executions_this_week=executions_week,
            executions_this_month=executions_month,
            daily_stats=daily_stats,
            most_executed_tests=most_executed,
            most_failed_tests=most_failed,
            total_ssim_verifications=total_ssim_verifications,
            ssim_pass_rate=(total_ssim_passed / total_ssim_verifications * 100) if total_ssim_verifications > 0 else 0,
            average_ssim_score=(sum(ssim_scores) / len(ssim_scores)) if ssim_scores else None,
            average_execution_duration_ms=(total_duration_ms / total_executions) if total_executions > 0 else None,
            fastest_execution_ms=min(durations) if durations else None,
            slowest_execution_ms=max(durations) if durations else None,
            last_execution_time=last_execution_time
        )

    def get_summary(self) -> DashboardSummary:
        """
        Get dashboard summary data.

        Returns:
            DashboardSummary for quick display
        """
        today = datetime.now().date().isoformat()
        yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()

        # Count totals
        total = len(self.index["executions"])
        passed = sum(1 for e in self.index["executions"] if e["status"] == "success")
        failed = sum(1 for e in self.index["executions"] if e["status"] in ["failure", "error"])

        # Today's stats
        today_execs = [e for e in self.index["executions"] if e["started_at"][:10] == today]
        today_total = len(today_execs)
        today_passed = sum(1 for e in today_execs if e["status"] == "success")
        today_failed = sum(1 for e in today_execs if e["status"] in ["failure", "error"])

        # Yesterday's stats for trend
        yesterday_execs = [e for e in self.index["executions"] if e["started_at"][:10] == yesterday]
        yesterday_passed = sum(1 for e in yesterday_execs if e["status"] == "success")
        yesterday_total = len(yesterday_execs)

        # Calculate trend
        today_rate = (today_passed / today_total * 100) if today_total > 0 else 0
        yesterday_rate = (yesterday_passed / yesterday_total * 100) if yesterday_total > 0 else 0

        if today_rate > yesterday_rate:
            trend = "up"
            trend_pct = today_rate - yesterday_rate
        elif today_rate < yesterday_rate:
            trend = "down"
            trend_pct = yesterday_rate - today_rate
        else:
            trend = "stable"
            trend_pct = 0

        # Get recent executions
        recent = []
        for entry in self.index["executions"][:10]:
            record = self.get_execution(entry["execution_id"])
            if record:
                recent.append({
                    "execution_id": record.execution_id,
                    "test_id": record.test_id,
                    "status": record.status.value if isinstance(record.status, ExecutionStatus) else record.status,
                    "started_at": record.started_at,
                    "duration_ms": record.duration_ms
                })

        # Calculate SSIM pass rate
        total_ssim = 0
        ssim_passed = 0
        for entry in self.index["executions"][:100]:  # Last 100 for performance
            record = self.get_execution(entry["execution_id"])
            if record:
                total_ssim += record.ssim_verifications
                ssim_passed += record.ssim_passed

        ssim_rate = (ssim_passed / total_ssim * 100) if total_ssim > 0 else 0

        return DashboardSummary(
            total_executions=total,
            total_passed=passed,
            total_failed=failed,
            pass_rate=(passed / total * 100) if total > 0 else 0,
            today_executions=today_total,
            today_passed=today_passed,
            today_failed=today_failed,
            recent_executions=recent,
            trend=trend,
            trend_percentage=trend_pct,
            ssim_pass_rate=ssim_rate
        )


# ═══════════════════════════════════════════════════════════
# Singleton instance
# ═══════════════════════════════════════════════════════════

_history_service: Optional[TestHistoryService] = None


def get_test_history_service() -> TestHistoryService:
    """Get or create test history service singleton."""
    global _history_service

    if _history_service is None:
        _history_service = TestHistoryService()

    return _history_service
