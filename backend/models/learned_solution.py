"""
learned_solution.py - Learned Solution Models

Defines schema for learned solutions stored in RAG database.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class LearnedStep(BaseModel):
    """Single step in a learned solution."""
    
    step: int = Field(..., description="Step number")
    description: str = Field(default="", description="Step description")
    action: str = Field(..., description="Action type (tap, swipe, input, etc.)")
    coordinates: Optional[List[int]] = Field(default=None, description="Tap coordinates [x, y]")
    target_element: Optional[str] = Field(default=None, description="Target element name")
    input_text: Optional[str] = Field(default=None, description="Text to input")
    success: bool = Field(default=True, description="Whether step succeeded")
    
    class Config:
        json_schema_extra = {
            "example": {
                "step": 1,
                "description": "Tap Settings icon",
                "action": "tap",
                "coordinates": [850, 450],
                "target_element": "Settings",
                "success": True
            }
        }


class LearnedSolution(BaseModel):
    """Learned solution for a test case."""
    
    test_id: str = Field(..., description="Test case ID")
    title: str = Field(..., description="Test title")
    component: str = Field(..., description="Component name")
    steps: List[LearnedStep] = Field(default_factory=list, description="Execution steps")
    
    # Success tracking
    execution_count: int = Field(default=1, description="Total executions")
    success_count: int = Field(default=1, description="Successful executions")
    success_rate: float = Field(default=1.0, description="Success rate (0.0 - 1.0)")
    
    # Timestamps
    last_execution: str = Field(..., description="Last execution timestamp (ISO format)")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "test_id": "NAID-24430",
                "title": "HVAC: Fan Speed",
                "component": "HVAC",
                "steps": [
                    {
                        "step": 1,
                        "description": "Tap Settings icon",
                        "action": "tap",
                        "coordinates": [850, 450],
                        "success": True
                    },
                    {
                        "step": 2,
                        "description": "Verify Settings screen",
                        "action": "verify",
                        "target_element": "Settings Screen",
                        "success": True
                    }
                ],
                "execution_count": 5,
                "success_count": 4,
                "success_rate": 0.8,
                "last_execution": "2025-12-28T10:00:00",
                "created_at": "2025-12-27T10:00:00"
            }
        }
    
    def update_success(self, success: bool = True):
        """
        Update success metrics after execution.
        
        Args:
            success: Whether latest execution was successful
        """
        self.execution_count += 1
        if success:
            self.success_count += 1
        self.success_rate = self.success_count / self.execution_count
        self.last_execution = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "test_id": self.test_id,
            "title": self.title,
            "component": self.component,
            "steps": [step.model_dump() for step in self.steps],
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "success_rate": self.success_rate,
            "last_execution": self.last_execution,
            "created_at": self.created_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearnedSolution":
        """Create from dictionary."""
        # Convert step dicts to LearnedStep objects
        if "steps" in data and data["steps"]:
            steps = [LearnedStep(**step) if isinstance(step, dict) else step 
                    for step in data["steps"]]
            data["steps"] = steps
        
        return cls(**data)


class LearnedSolutionStats(BaseModel):
    """Statistics for learned solutions."""
    
    total_solutions: int = Field(..., description="Total learned solutions")
    average_success_rate: float = Field(..., description="Average success rate")
    total_executions: int = Field(..., description="Total executions")
    high_success_solutions: int = Field(..., description="Solutions with >80% success")
    low_success_solutions: int = Field(..., description="Solutions with <50% success")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_solutions": 50,
                "average_success_rate": 0.85,
                "total_executions": 250,
                "high_success_solutions": 40,
                "low_success_solutions": 5
            }
        }