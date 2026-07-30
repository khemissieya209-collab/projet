"""
Greenwashing Detection Agent (Agent 2).

This agent does NOT perform ESG analysis — that is done by Agent 1.
Its sole mission is to audit sustainability claims for greenwashing risk
by verifying them against evidence found in the extracted report text.

Rules:
- Never invent claims or evidence.
- For each claim: extract exact sentence, search for evidence in the report.
- If evidence exists: quote it with page number.
- If evidence is missing: write exactly "Evidence not found in report."
"""

from backend.services.ollama_service import generate_json
from backend.schemas.esg_schema import ESGAnalysisResult
from backend.schemas.greenwashing_schema import GreenwashingResult, Claim, EvidenceTableItem


# ---------------------------------------------------------------------------
# Sanitizers
# ---------------------------------------------------------------------------

def sanitize_claim(raw: dict) -> dict:
    """Apply safe defaults to a raw claim dict from the LLM."""
    return {
        "text": raw.get("text") or "No claim text provided",
        "category": raw.get("category") or "E",
        "risk_level": raw.get("risk_level") or "High",
        "justification": raw.get("justification") or "No justification provided",
        "is_verifiable": (
            raw.get("is_verifiable")
            if isinstance(raw.get("is_verifiable"), bool)
            else False
        ),
        "evidence_found": raw.get("evidence_found") or "Evidence not found in report.",
        "evidence_missing": raw.get("evidence_missing") or "Not specified",
        "confidence": raw.get("confidence") or "Medium",
        "page_number": (
            raw.get("page_number")
            if isinstance(raw.get("page_number"), int)
            else None
        ),
    }


def sanitize_evidence_item(raw: dict) -> dict:
    """Apply safe defaults to a raw EvidenceTableItem dict from the LLM."""
    return {
        "claim": raw.get("claim") or "No claim statement",
        "evidence_found": raw.get("evidence_found") or "Evidence not found in report.",
        "evidence_missing": raw.get("evidence_missing") or "Not specified",
        "is_verifiable": (
            raw.get("is_verifiable")
            if isinstance(raw.get("is_verifiable"), bool)
            else False
        ),
        "source_reference": raw.get("source_reference"),
        "page_number": (
            raw.get("page_number")
            if isinstance(raw.get("page_number"), int)
            else None
        ),
    }


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a Forensic Greenwashing Auditor. Your ONLY mission is to audit and verify "
    "corporate sustainability claims against evidence found in the report text.\n\n"
    "ABSOLUTE RULES:\n"
    "1. Do NOT perform ESG analysis — that has already been done by another agent.\n"
    "2. Do NOT invent any claim that is not listed in the CLAIMS TO AUDIT section.\n"
    "3. If no claims are provided, scan the REPORT TEXT and extract 3-8 actual "
    "sustainability statements made by the company, then audit each one.\n"
    "4. Do NOT invent any evidence. Only quote text that actually appears in the report.\n"
    "5. If evidence for a claim does NOT exist in the report, write EXACTLY: "
    "\"Evidence not found in report.\"\n"
    "6. For every piece of evidence you find, include the page number from PAGE markers "
    "(e.g., '--- PAGE 5 ---') and quote the exact sentence.\n"
    "7. Be rigorous and objective. A claim with no supporting data is HIGH risk."
)


def _build_audit_prompt(esg_result: ESGAnalysisResult, raw_text: str) -> str:
    """Build the greenwashing audit prompt."""

    # Format claims from Agent 1 for auditing
    claims_text = "\n".join([
        f'- [{c.pillar}] "{c.statement}" | has_data: {c.has_supporting_data} | '
        f'data: {c.supporting_data or "none"} | page: {c.page_number or "unknown"}'
        for c in esg_result.claims
    ])

    if not claims_text:
        claims_text = (
            "No specific claims were extracted by Agent 1. "
            "You must scan the REPORT TEXT below and identify 3-8 actual sustainability "
            "statements or commitments made by the company, then audit each one."
        )

    # Format indicators as available evidence
    indicators_text = "\n".join([
        f"- [{i.pillar}] {i.name}: {i.value} "
        f"{f'({i.unit})' if getattr(i, 'unit', None) else ''} "
        f"({i.year or 'no year'}) [page {i.page_number or 'unknown'}]"
        for i in esg_result.indicators
    ]) or "No indicators extracted."

    # Limit raw text to protect context window (~25k chars)
    report_text = raw_text[:25000] if raw_text else "Not provided"

    return f"""Audit the following ESG claims for greenwashing risk.
Verify each claim ONLY against evidence found in the REPORT TEXT below.

CLAIMS TO AUDIT (extracted by Agent 1):
{claims_text}

AVAILABLE EVIDENCE — INDICATORS (extracted by Agent 1):
{indicators_text}

GLOBAL SUMMARY (from Agent 1):
{esg_result.global_summary or "Not available"}

FULL REPORT TEXT (use this to verify claims — look for supporting evidence):
{report_text}

Instructions:
1. For EVERY claim listed above, determine whether the report contains supporting evidence.
2. For each claim produce:
   - "text": the exact claim sentence being audited.
   - "category": "E" (Environmental), "S" (Social), or "G" (Governance).
   - "evidence_found": Quote the EXACT sentence or KPI from the report that supports this claim.
     If no evidence exists, write EXACTLY: "Evidence not found in report."
   - "evidence_missing": What specific data or verification is missing.
   - "risk_level": "High" (no evidence/vague), "Medium" (partial evidence), "Low" (fully backed).
   - "is_verifiable": true if concrete data exists in the report, false otherwise.
   - "page_number": The page number where you found evidence (from PAGE markers), or null.
   - "confidence": "High", "Medium", or "Low".
   - "justification": Why you assigned this risk level — be specific.
3. Do NOT add any claims not mentioned above (or not found in the report text if the list is empty).
4. Build an "evidence_table" summarising each audited claim.
5. Calculate "integrity_score" (0-100): 100 = fully transparent, 0 = total greenwashing.
6. Determine "overall_risk": "High", "Medium", or "Low".
7. Write a 3-5 sentence "summary" of the greenwashing risk assessment.
8. Provide "risk_distribution" (e.g., "5 claims audited: 2 High, 2 Medium, 1 Low risk").

Return ONLY a valid JSON object:
{{"claims":[{{"text":"exact claim","category":"E","risk_level":"High","justification":"specific reason","is_verifiable":false,"evidence_found":"Evidence not found in report.","evidence_missing":"missing data","confidence":"Medium","page_number":null}}],"integrity_score":60,"overall_risk":"Medium","summary":"3-5 sentence assessment","evidence_table":[{{"claim":"exact claim","evidence_found":"quote or Evidence not found in report.","evidence_missing":"missing","is_verifiable":false,"source_reference":"Page X, Section Y or null","page_number":null}}],"risk_distribution":"N claims audited: X High, Y Medium, Z Low risk"}}"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_greenwashing(esg_result: ESGAnalysisResult, raw_text: str = "") -> GreenwashingResult:
    """
    Audit ESG claims for greenwashing risk.

    This agent does NOT re-analyse ESG. It only verifies claims from Agent 1
    against evidence in the raw report text. If Agent 1 found no claims, the
    agent scans the report text directly for sustainability statements.

    Args:
        esg_result: The ESG analysis result from Agent 1.
        raw_text: The full extracted text from the PDF (with page markers).

    Returns:
        GreenwashingResult with audited claims and integrity assessment.
    """
    prompt = _build_audit_prompt(esg_result, raw_text)
    data = generate_json(prompt, system_prompt=_SYSTEM_PROMPT, num_ctx=8192, num_predict=2048)

    # --- Sanitize claims ---
    raw_claims = data.get("claims", [])
    if not isinstance(raw_claims, list) or len(raw_claims) == 0:
        raw_claims = [{
            "text": "No specific verifiable claims found",
            "category": "E",
            "risk_level": "High",
            "justification": "Report lacks specific measurable commitments with supporting data",
            "is_verifiable": False,
            "evidence_found": "Evidence not found in report.",
            "evidence_missing": "No quantified commitments or verified metrics found",
            "confidence": "Low",
            "page_number": None,
        }]

    sanitized_claims = [sanitize_claim(c) for c in raw_claims]

    # --- Sanitize evidence table ---
    raw_evidence_table = data.get("evidence_table", [])
    if not isinstance(raw_evidence_table, list):
        raw_evidence_table = []
    sanitized_evidence_table = [sanitize_evidence_item(item) for item in raw_evidence_table]

    # --- Sanitize scores ---
    integrity_score = data.get("integrity_score")
    if not isinstance(integrity_score, (int, float)):
        integrity_score = 50

    overall_risk = data.get("overall_risk")
    if not isinstance(overall_risk, str) or overall_risk not in ("Low", "Medium", "High"):
        overall_risk = "Medium"

    return GreenwashingResult(
        claims=[Claim(**c) for c in sanitized_claims],
        integrity_score=int(integrity_score),
        overall_risk=overall_risk,
        summary=data.get("summary") or "",
        evidence_table=[EvidenceTableItem(**item) for item in sanitized_evidence_table],
        risk_distribution=data.get("risk_distribution"),
    )