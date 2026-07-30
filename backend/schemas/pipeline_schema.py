from pydantic import BaseModel

from backend.schemas.esg_schema import ESGAnalysisResult
from backend.schemas.greenwashing_schema import GreenwashingResult
from backend.schemas.strategy_schema import StrategyResult


class PipelineResult(BaseModel):
    esg_analysis: ESGAnalysisResult
    greenwashing: GreenwashingResult
    strategy: StrategyResult
