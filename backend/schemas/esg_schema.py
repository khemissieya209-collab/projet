from pydantic import BaseModel
from typing import List, Optional


class ESGClaim(BaseModel):
    statement: str
    pillar: str  # Environnement / Social / Gouvernance
    has_supporting_data: bool
    supporting_data: Optional[str] = None
    page_number: Optional[int] = None
    evidence_sentence: Optional[str] = None


class ESGIndicator(BaseModel):
    # name and value are Optional so sanitize_indicator() returning None
    # does not trigger a Pydantic ValidationError when the LLM produces
    # placeholder text that gets rejected.
    name: Optional[str] = None
    pillar: str
    value: Optional[str] = None
    year: Optional[str] = None
    trend: Optional[str] = None
    unit: Optional[str] = None
    page_number: Optional[int] = None
    evidence_sentence: Optional[str] = None


class ESGPillarSummary(BaseModel):
    pillar_name: str
    # Optional so we can distinguish "not found" from ""
    summary: Optional[str] = None
    strengths: List[str] = []
    weaknesses: List[str] = []
    score: Optional[int] = None


class ESGAnalysisResult(BaseModel):
    company_name: Optional[str] = None
    reporting_period: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    overall_score: Optional[int] = None
    score_methodology: Optional[str] = None
    confidence_level: Optional[str] = None
    confidence_justification: Optional[str] = None
    environmental_summary: ESGPillarSummary
    social_summary: ESGPillarSummary
    governance_summary: ESGPillarSummary
    indicators: List[ESGIndicator] = []
    claims: List[ESGClaim] = []
    global_summary: Optional[str] = None
    material_topics: List[str] = []
    esg_risks: List[str] = []
    esg_opportunities: List[str] = []
    missing_information: List[str] = []