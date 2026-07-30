"""
Strategy Generator Agent (Agent 3).

Generates ESG improvement recommendations ONLY from weaknesses
detected by Agent 1 and greenwashing risks from Agent 2.

Rules:
- Never invent budgets, investments, percentages, deadlines, or company projects.
- Every recommendation must directly reference a specific weakness.
- If no weaknesses are identified for a pillar, do not generate recommendations for it.
"""

import json

from backend.services.ollama_service import generate_json
from backend.schemas.esg_schema import ESGAnalysisResult
from backend.schemas.greenwashing_schema import GreenwashingResult
from backend.schemas.strategy_schema import StrategyResult


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a strict, objective corporate ESG Strategy Consultant. "
    "Your mission is to generate practical remediation plans ONLY from the detected weaknesses.\n\n"
    "ABSOLUTE RULES:\n"
    "1. NEVER invent any budget amount, investment figure, percentage target, or specific deadline.\n"
    "2. NEVER invent company-specific projects, initiatives, or programme names.\n"
    "3. Every recommendation MUST directly reference a specific weakness from the list below.\n"
    "4. If no weaknesses were identified for a pillar, do NOT generate recommendations for that pillar.\n"
    "5. Recommendations must be practical, actionable, and directly solve the identified weaknesses.\n"
    "6. Avoid promotional language, creative suggestions, or speculation.\n"
    "7. Do NOT assume the company has specific resources, capabilities, or ongoing projects "
    "unless explicitly stated in the audit results."
)


def _build_strategy_prompt(esg_result: ESGAnalysisResult,
                            gw_result: GreenwashingResult) -> str:
    """Build the strategy generation prompt."""

    weaknesses = "\n".join(
        [f"- [Environmental] {w}" for w in esg_result.environmental_summary.weaknesses] +
        [f"- [Social] {w}" for w in esg_result.social_summary.weaknesses] +
        [f"- [Governance] {w}" for w in esg_result.governance_summary.weaknesses]
    )

    strengths = "\n".join(
        [f"- [Environmental] {s}" for s in esg_result.environmental_summary.strengths] +
        [f"- [Social] {s}" for s in esg_result.social_summary.strengths] +
        [f"- [Governance] {s}" for s in esg_result.governance_summary.strengths]
    )

    indicators = "\n".join(
        [f"- {i.name}: {i.value} {f'({i.unit})' if getattr(i, 'unit', None) else ''}"
         for i in esg_result.indicators]
    )

    high_risk_claims = "\n".join([
        f'- [{c.category}] "{c.text}" → {c.justification}'
        for c in gw_result.claims
        if c.risk_level.lower() == "high"
    ])

    medium_risk_claims = "\n".join([
        f'- [{c.category}] "{c.text}" → {c.justification}'
        for c in gw_result.claims
        if c.risk_level.lower() == "medium"
    ])

    missing_info = "\n".join(
        [f"- {m}" for m in esg_result.missing_information]
    ) if esg_result.missing_information else "None identified"

    return f"""Generate an ESG improvement strategy based ONLY on the detected weaknesses and greenwashing claims from the audit.

IDENTIFIED WEAKNESSES (from ESG Audit — these are the ONLY problems you should address):
{weaknesses or "None identified"}

IDENTIFIED STRENGTHS (for context only — do NOT generate recommendations for these):
{strengths or "None identified"}

EXTRACTED ESG INDICATORS (for context):
{indicators or "None identified"}

MISSING INFORMATION (areas not disclosed in the report):
{missing_info}

HIGH RISK GREENWASHING CLAIMS:
{high_risk_claims or "None identified"}

MEDIUM RISK GREENWASHING CLAIMS:
{medium_risk_claims or "None identified"}

INTEGRITY SCORE: {gw_result.integrity_score}/100
OVERALL GREENWASHING RISK: {gw_result.overall_risk}

Instructions:
1. For EACH weakness listed above, generate one specific recommendation that directly addresses it.
   Begin each recommendation with "[Addresses: <weakness description>]".
2. Group recommendations into:
   - priority_actions: Most urgent — address high-risk greenwashing or critical data gaps.
   - short_term: 0-6 months — operational or policy actions with low complexity.
   - mid_term: 6-24 months — data systems, reporting frameworks, training programmes.
   - long_term: 2+ years — strategic alignment, certifications, supply-chain transformation.
3. If there are NO weaknesses for a pillar, do NOT generate recommendations for that pillar.
4. Do NOT invent budget figures, percentages, deadlines, or project names.
5. Also provide:
   - "improvement_plan": A 3-5 sentence overall improvement roadmap summary.
   - "expected_impact": Factual description of the ESG profile improvement expected.
   - "implementation_difficulty": "High", "Medium", or "Low" with a brief reason.
   - "strategic_roadmap": A 2-4 sentence roadmap connecting weaknesses to solutions.

Return ONLY valid JSON:
{{
  "priority_actions": ["[Addresses: weakness] specific action"],
  "short_term": ["[Addresses: weakness] specific action"],
  "mid_term": ["[Addresses: weakness] specific action"],
  "long_term": ["[Addresses: weakness] specific action"],
  "improvement_plan": "3-5 sentence summary",
  "expected_impact": "factual impact description",
  "implementation_difficulty": "High/Medium/Low — reason",
  "strategic_roadmap": "2-4 sentence roadmap"
}}"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_strategy(
    esg_result: ESGAnalysisResult,
    gw_result: GreenwashingResult,
) -> StrategyResult:
    """
    Generate ESG improvement strategy from detected weaknesses.

    Recommendations are generated ONLY from weaknesses identified by Agent 1
    and greenwashing risks from Agent 2. Nothing is invented.

    If no weaknesses and no greenwashing risks exist, returns a minimal
    StrategyResult without calling Ollama (saves an unnecessary round-trip).

    Args:
        esg_result: ESG analysis from Agent 1.
        gw_result: Greenwashing audit from Agent 2.

    Returns:
        StrategyResult with grouped recommendations.
    """
    # Early-exit: nothing to address
    all_weaknesses = (
        esg_result.environmental_summary.weaknesses
        + esg_result.social_summary.weaknesses
        + esg_result.governance_summary.weaknesses
    )
    has_risks = any(c.risk_level.lower() in ("high", "medium") for c in gw_result.claims)

    if not all_weaknesses and not has_risks:
        return StrategyResult(
            priority_actions=[],
            short_term=[],
            mid_term=[],
            long_term=[],
            improvement_plan=(
                "No specific weaknesses or greenwashing risks were detected. "
                "Maintain current ESG practices and continue transparent disclosure."
            ),
            expected_impact="Continued strong ESG performance if current practices are sustained.",
            implementation_difficulty="Low — no critical gaps identified.",
            strategic_roadmap=(
                "Focus on maintaining disclosure quality and monitoring emerging ESG regulations."
            ),
        )

    prompt = _build_strategy_prompt(esg_result, gw_result)
    data = generate_json(prompt, system_prompt=_SYSTEM_PROMPT, num_ctx=8192, num_predict=1024)

    # Guard against null or non-list values from the LLM
    priority_actions = data.get("priority_actions")
    short_term = data.get("short_term")
    mid_term = data.get("mid_term")
    long_term = data.get("long_term")

    # Normalise string fields (LLM may return list or dict)
    def _to_str(v) -> str | None:
        if v is None:
            return None
        if isinstance(v, (list, dict)):
            return json.dumps(v, ensure_ascii=False)
        return str(v)

    return StrategyResult(
        priority_actions=priority_actions if isinstance(priority_actions, list) else [],
        short_term=short_term if isinstance(short_term, list) else [],
        mid_term=mid_term if isinstance(mid_term, list) else [],
        long_term=long_term if isinstance(long_term, list) else [],
        improvement_plan=data.get("improvement_plan") or "",
        expected_impact=_to_str(data.get("expected_impact")),
        implementation_difficulty=_to_str(data.get("implementation_difficulty")),
        strategic_roadmap=_to_str(data.get("strategic_roadmap")),
    )