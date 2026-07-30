from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.esg_analyzer import analyze_esg
from backend.agents.greenwashing_detector import detect_greenwashing
from backend.agents.strategy_generator import generate_strategy
from backend.schemas.esg_schema import ESGAnalysisResult
from backend.schemas.greenwashing_schema import GreenwashingResult
from backend.schemas.strategy_schema import StrategyResult

router = APIRouter()


class TextInput(BaseModel):
    text: str


@router.post("/analyze/esg", response_model=ESGAnalysisResult)
def analyze(data: TextInput):
    """
    Run ESG analysis on the provided text.
    The full text is passed — no truncation.
    """
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=422, detail="text field must not be empty.")
    return analyze_esg(data.text)


@router.post("/analyze/greenwashing", response_model=GreenwashingResult)
def greenwashing(data: TextInput):
    """
    Run ESG analysis then audit claims for greenwashing risk.
    The full text is passed to both agents — no truncation.
    """
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=422, detail="text field must not be empty.")
    text = data.text
    esg_result = analyze_esg(text)
    return detect_greenwashing(esg_result, text)


@router.post("/analyze/strategy", response_model=StrategyResult)
def strategy(data: TextInput):
    """
    Run the full pipeline (ESG → Greenwashing → Strategy) on the provided text.
    The full text is passed — no truncation.
    """
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=422, detail="text field must not be empty.")
    text = data.text
    esg_result = analyze_esg(text)
    gw_result = detect_greenwashing(esg_result, text)
    return generate_strategy(esg_result, gw_result)


@router.post("/analyze/full")
def full_analysis(data: TextInput):
    """
    Run the full three-agent pipeline and return all results.
    The full text is passed — no truncation.
    """
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=422, detail="text field must not be empty.")
    text = data.text
    esg_result = analyze_esg(text)
    gw_result = detect_greenwashing(esg_result, text)
    strategy_result = generate_strategy(esg_result, gw_result)
    return {
        "esg": esg_result.model_dump(),
        "greenwashing": gw_result.model_dump(),
        "strategy": strategy_result.model_dump(),
    }