from pydantic import BaseModel
from typing import List, Optional


class Claim(BaseModel):
    text: str
    category: str
    risk_level: str
    justification: str
    is_verifiable: bool
    evidence_found: Optional[str] = None
    evidence_missing: Optional[str] = None
    confidence: Optional[str] = None
    page_number: Optional[int] = None


class EvidenceTableItem(BaseModel):
    claim: str
    evidence_found: str
    evidence_missing: str
    is_verifiable: bool
    source_reference: Optional[str] = None
    page_number: Optional[int] = None


class GreenwashingResult(BaseModel):
    claims: List[Claim]
    integrity_score: int
    overall_risk: str
    summary: str
    evidence_table: List[EvidenceTableItem] = []
    risk_distribution: Optional[str] = None