from pydantic import BaseModel
from typing import List, Optional

class StrategyResult(BaseModel):
    priority_actions: List[str]
    short_term: List[str]
    mid_term: List[str]
    long_term: List[str]
    improvement_plan: str
    expected_impact: Optional[str] = None
    implementation_difficulty: Optional[str] = None
    strategic_roadmap: Optional[str] = None