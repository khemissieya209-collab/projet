"""
ESG Analysis Agent (Agent 1).
Extraction-first agent — never invents data.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.services.ollama_service import generate_json
from backend.schemas.esg_schema import (
    ESGAnalysisResult,
    ESGPillarSummary,
    ESGClaim,
    ESGIndicator,
)

# ---------------------------------------------------------------------------
# Chunk configuration
# ---------------------------------------------------------------------------
# Increased from 6000→7000 to cover more content per LLM call.
# Overlap increased from 200→500 so that company name / reporting period
# found on the cover page are still visible in later chunks.
_SINGLE_PASS_LIMIT = 7_000
_CHUNK_OVERLAP = 500

# ---------------------------------------------------------------------------
# Placeholder rejection
# ---------------------------------------------------------------------------
_PLACEHOLDER_STRINGS = {
    "strength 1", "weakness 1", "indicator name", "factual summary.",
    "4-6 sentence factual summary", "no statement provided", "unknown indicator",
    "exact claim from report", "exact sentence", "topic", "risk", "opportunity",
    "missing area", "brief explanation", "brief reason", "summary here",
    "insert summary", "n/a", "not applicable", "none identified", "none",
    "no data", "not available", "not provided", "placeholder",
}


def _is_placeholder(value: str) -> bool:
    if not value:
        return True
    cleaned = value.strip().lower().rstrip(".")
    return cleaned in _PLACEHOLDER_STRINGS or len(cleaned) < 4


def _clean_list(items) -> list:
    """Remove empty/placeholder strings from a list."""
    if not isinstance(items, list):
        return []
    return [s for s in items if isinstance(s, str) and not _is_placeholder(s)]


def sanitize_claim(raw: dict) -> dict | None:
    """
    Validate a raw claim dict. Returns None if the claim is invalid or a
    placeholder — callers must filter out None results before constructing
    ESGClaim objects.
    """
    stmt = raw.get("statement", "")
    if not stmt or _is_placeholder(stmt):
        return None
    # Reject structural-noise claims (section headings, one-word phrases)
    if len(stmt.split()) < 4:
        return None
    return {
        "statement": stmt,
        "pillar": raw.get("pillar") or "Environnement",
        "has_supporting_data": (
            raw.get("has_supporting_data")
            if isinstance(raw.get("has_supporting_data"), bool)
            else False
        ),
        "supporting_data": raw.get("supporting_data"),
        "page_number": (
            raw.get("page_number")
            if isinstance(raw.get("page_number"), int)
            else None
        ),
        "evidence_sentence": raw.get("evidence_sentence"),
    }


def sanitize_indicator(raw: dict) -> dict | None:
    """
    Validate a raw indicator dict. Returns None if name or value are
    placeholders. ESGIndicator now accepts Optional[str] so None is safe.
    """
    name = raw.get("name", "")
    value = raw.get("value", "")
    if _is_placeholder(str(name)) or _is_placeholder(str(value)):
        return None
    return {
        "name": name,
        "pillar": raw.get("pillar") or "Environnement",
        "value": str(value),
        "year": str(raw.get("year")) if raw.get("year") is not None else None,
        "trend": raw.get("trend"),
        "unit": raw.get("unit"),
        "page_number": (
            raw.get("page_number")
            if isinstance(raw.get("page_number"), int)
            else None
        ),
        "evidence_sentence": raw.get("evidence_sentence"),
    }


def sanitize_pillar_summary(raw: dict, default_name: str) -> dict:
    if not isinstance(raw, dict):
        raw = {}
    score = raw.get("score")
    if score is not None:
        try:
            score = int(score)
        except (ValueError, TypeError):
            score = None
    summary = raw.get("summary", "") or ""
    return {
        "pillar_name": raw.get("pillar_name") or default_name,
        "summary": summary if not _is_placeholder(summary) else None,
        "strengths": _clean_list(raw.get("strengths")),
        "weaknesses": _clean_list(raw.get("weaknesses")),
        "score": score,
    }


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = (
    "You are a senior ESG auditor extracting information from corporate sustainability reports. "
    "Extract ONLY information explicitly stated in the provided text. "
    "NEVER invent company names, KPIs, percentages, years, budgets, or targets. "
    "If information is absent, return null or an empty array. "
    "Do NOT copy the JSON field names as values."
)

# ---------------------------------------------------------------------------
# Analysis prompt — instructs extraction, not template-filling
# ---------------------------------------------------------------------------
def _build_analysis_prompt(text: str) -> str:
    return (
        "Read the following ESG report excerpt carefully and extract the information below.\n"
        "Rules:\n"
        "- Only include information EXPLICITLY stated in the text.\n"
        "- For company_name: extract the actual company or organisation name.\n"
        "- For reporting_period: extract the actual year or date range (e.g. '2023', '2022-2023').\n"
        "- For industry: extract the company's sector (e.g. 'Energy', 'Finance', 'Retail').\n"
        "- For country: extract the country of headquarters.\n"
        "- For summaries: write 2-4 factual sentences describing what the report says about each pillar.\n"
        "- For strengths/weaknesses: list specific items explicitly mentioned, not generic advice.\n"
        "- For indicators: only include named metrics with an actual numeric value.\n"
        "- For claims: only include specific sentences from the text making a sustainability commitment or achievement.\n"
        "- If information is not present, use null or [].\n"
        "- Do NOT use field names (like 'summary', 'strength') as values.\n\n"
        f"REPORT TEXT:\n{text}\n\n"
        "Return ONLY valid JSON with this exact structure:\n"
        "{\n"
        '  "company_name": "actual company name or null",\n'
        '  "reporting_period": "actual year/period or null",\n'
        '  "industry": "actual industry or null",\n'
        '  "country": "actual country or null",\n'
        '  "overall_score": null,\n'
        '  "score_methodology": null,\n'
        '  "confidence_level": "High",\n'
        '  "confidence_justification": "reason or null",\n'
        '  "environmental_summary": {\n'
        '    "pillar_name": "Environmental",\n'
        '    "summary": "factual description of environmental performance from the text, or null",\n'
        '    "strengths": ["specific environmental achievement mentioned in text"],\n'
        '    "weaknesses": ["specific environmental gap mentioned in text"],\n'
        '    "score": null\n'
        "  },\n"
        '  "social_summary": {\n'
        '    "pillar_name": "Social",\n'
        '    "summary": "factual description of social performance from the text, or null",\n'
        '    "strengths": ["specific social achievement mentioned in text"],\n'
        '    "weaknesses": ["specific social gap mentioned in text"],\n'
        '    "score": null\n'
        "  },\n"
        '  "governance_summary": {\n'
        '    "pillar_name": "Governance",\n'
        '    "summary": "factual description of governance from the text, or null",\n'
        '    "strengths": ["specific governance achievement mentioned in text"],\n'
        '    "weaknesses": ["specific governance gap mentioned in text"],\n'
        '    "score": null\n'
        "  },\n"
        '  "indicators": [\n'
        '    {"name": "metric name", "pillar": "Environmental", "value": "numeric value", "unit": "unit", "year": "year", "trend": "improving/stable/declining or null", "page_number": null, "evidence_sentence": "exact sentence from text"}\n'
        "  ],\n"
        '  "claims": [\n'
        '    {"statement": "exact sentence making a sustainability commitment or achievement", "pillar": "Environmental", "has_supporting_data": true, "supporting_data": "KPI or figure cited", "page_number": null}\n'
        "  ],\n"
        '  "global_summary": "2-3 sentence overall ESG profile summary from the text, or null",\n'
        '  "material_topics": ["topic explicitly listed as material in the report"],\n'
        '  "esg_risks": ["risk explicitly mentioned in the report"],\n'
        '  "esg_opportunities": ["opportunity explicitly mentioned in the report"],\n'
        '  "missing_information": ["ESG topic completely absent from the report"]\n'
        "}"
    )


# ---------------------------------------------------------------------------
# Chunk merging
# ---------------------------------------------------------------------------
def _merge_chunk_results(results: list[dict]) -> dict:
    if len(results) == 1:
        return results[0]

    merged = {
        "company_name": None,
        "reporting_period": None,
        "industry": None,
        "country": None,
        "overall_score": None,
        "score_methodology": "",
        "confidence_level": "Medium",
        "confidence_justification": "Analysis across multiple document sections.",
        "environmental_summary": {
            "pillar_name": "Environmental",
            "summary": "",
            "strengths": [],
            "weaknesses": [],
            "score": None,
        },
        "social_summary": {
            "pillar_name": "Social",
            "summary": "",
            "strengths": [],
            "weaknesses": [],
            "score": None,
        },
        "governance_summary": {
            "pillar_name": "Governance",
            "summary": "",
            "strengths": [],
            "weaknesses": [],
            "score": None,
        },
        "indicators": [],
        "claims": [],
        "global_summary": "",
        "material_topics": [],
        "esg_risks": [],
        "esg_opportunities": [],
        "missing_information": [],
    }

    scores: list[int] = []
    pillar_scores: dict[str, list[int]] = {
        "environmental_summary": [],
        "social_summary": [],
        "governance_summary": [],
    }
    seen_indicators: set[tuple] = set()
    seen_claims: set[str] = set()
    seen_summaries: dict[str, set[str]] = {
        k: set()
        for k in ("environmental_summary", "social_summary", "governance_summary")
    }
    seen_global: set[str] = set()

    for r in results:
        # Scalar fields — first non-null wins
        for key in ("company_name", "reporting_period", "industry", "country"):
            if merged[key] is None and r.get(key) and not _is_placeholder(str(r[key])):
                merged[key] = r[key]

        if r.get("overall_score") is not None:
            try:
                scores.append(int(r["overall_score"]))
            except (ValueError, TypeError):
                pass

        if r.get("score_methodology") and not _is_placeholder(str(r["score_methodology"])):
            merged["score_methodology"] = r["score_methodology"]

        # Pillar summaries — concatenate unique sentences, deduplicate lists
        for pillar_key in ("environmental_summary", "social_summary", "governance_summary"):
            pillar = r.get(pillar_key, {})
            if not isinstance(pillar, dict):
                continue
            s = (pillar.get("summary") or "").strip()
            if s and not _is_placeholder(s) and s not in seen_summaries[pillar_key]:
                seen_summaries[pillar_key].add(s)
                sep = " " if merged[pillar_key]["summary"] else ""
                merged[pillar_key]["summary"] += sep + s
            for list_key in ("strengths", "weaknesses"):
                for item in _clean_list(pillar.get(list_key)):
                    if item not in merged[pillar_key][list_key]:
                        merged[pillar_key][list_key].append(item)
            if pillar.get("score") is not None:
                try:
                    pillar_scores[pillar_key].append(int(pillar["score"]))
                except (ValueError, TypeError):
                    pass

        # Indicators — deduplicate by (name, value)
        for ind in r.get("indicators", []):
            if not isinstance(ind, dict):
                continue
            name = ind.get("name", "")
            value = ind.get("value", "")
            if _is_placeholder(str(name)) or _is_placeholder(str(value)):
                continue
            key = (str(name).lower(), str(value).lower())
            if key not in seen_indicators:
                seen_indicators.add(key)
                merged["indicators"].append(ind)

        # Claims — deduplicate by statement text
        for claim in r.get("claims", []):
            if not isinstance(claim, dict):
                continue
            stmt = claim.get("statement", "")
            if not stmt or _is_placeholder(stmt) or len(stmt.split()) < 4:
                continue
            if stmt not in seen_claims:
                seen_claims.add(stmt)
                merged["claims"].append(claim)

        # Lists — deduplicate
        for list_key in ("material_topics", "esg_risks", "esg_opportunities", "missing_information"):
            for item in _clean_list(r.get(list_key)):
                if item not in merged[list_key]:
                    merged[list_key].append(item)

        gs = (r.get("global_summary") or "").strip()
        if gs and not _is_placeholder(gs) and gs not in seen_global:
            seen_global.add(gs)
            sep = " " if merged["global_summary"] else ""
            merged["global_summary"] += sep + gs

    # Aggregate scores
    if scores:
        merged["overall_score"] = round(sum(scores) / len(scores))
    for pillar_key, ps in pillar_scores.items():
        if ps:
            merged[pillar_key]["score"] = round(sum(ps) / len(ps))

    return merged


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def _split_into_chunks(
    text: str,
    max_size: int = _SINGLE_PASS_LIMIT,
    overlap: int = _CHUNK_OVERLAP,
) -> list[str]:
    if len(text) <= max_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_size
        if end < len(text):
            # Try to break at a newline for cleaner chunk boundaries
            newline_pos = text.rfind("\n", start + max_size - overlap, end)
            if newline_pos > start:
                end = newline_pos
        chunks.append(text[start:end])
        start = end - overlap if end < len(text) else len(text)
    return chunks


# ---------------------------------------------------------------------------
# Parallel chunk processor
# ---------------------------------------------------------------------------
def _process_chunk(args: tuple) -> tuple[int, dict]:
    """
    Process a single chunk and return (index, result).

    Each call to generate_json uses the thread-local Ollama client, so
    parallel invocations from ThreadPoolExecutor are thread-safe.
    """
    i, chunk, n_total = args
    print(f"[ESG Agent] Chunk {i + 1}/{n_total} ({len(chunk)} chars)")
    prompt = _build_analysis_prompt(chunk)
    return i, generate_json(prompt, system_prompt=_SYSTEM_PROMPT, num_ctx=8192, max_retries=1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def analyze_esg(text: str) -> ESGAnalysisResult:
    """
    Analyse the full extracted report text and return a structured ESGAnalysisResult.

    For short documents (≤ _SINGLE_PASS_LIMIT chars) a single LLM call is made.
    Longer documents are split into overlapping chunks and processed in parallel
    with up to 4 workers, each using their own thread-local Ollama client.
    """
    chunks = _split_into_chunks(text)

    if len(chunks) == 1:
        prompt = _build_analysis_prompt(chunks[0])
        data = generate_json(prompt, system_prompt=_SYSTEM_PROMPT, num_ctx=8192, max_retries=1)
    else:
        print(f"[ESG Agent] {len(chunks)} chunks — processing in parallel (thread-local clients)")
        chunk_results: list[dict | None] = [None] * len(chunks)
        args_list = [(i, chunk, len(chunks)) for i, chunk in enumerate(chunks)]
        with ThreadPoolExecutor(max_workers=min(4, len(chunks))) as executor:
            futures = {executor.submit(_process_chunk, a): a[0] for a in args_list}
            for future in as_completed(futures):
                idx, result = future.result()
                chunk_results[idx] = result
        # Filter out any None results from failed chunks
        valid_results = [r for r in chunk_results if r is not None]
        data = _merge_chunk_results(valid_results) if valid_results else {}

    env_raw = data.get("environmental_summary", {})
    soc_raw = data.get("social_summary", {})
    gov_raw = data.get("governance_summary", {})

    # Filter and sanitize claims — reject any that return None from sanitize_claim()
    raw_claims = data.get("claims", []) if isinstance(data.get("claims"), list) else []
    sanitized_claims = [
        sanitize_claim(c)
        for c in raw_claims
        if isinstance(c, dict)
    ]
    valid_claims = [c for c in sanitized_claims if c is not None]

    # Filter and sanitize indicators — reject any that return None
    raw_indicators = (
        data.get("indicators", []) if isinstance(data.get("indicators"), list) else []
    )
    sanitized_indicators = [
        sanitize_indicator(ind)
        for ind in raw_indicators
        if isinstance(ind, dict)
    ]
    valid_indicators = [ind for ind in sanitized_indicators if ind is not None]

    overall_score = data.get("overall_score")
    if overall_score is not None:
        try:
            overall_score = int(overall_score)
        except (ValueError, TypeError):
            overall_score = None

    gs = (data.get("global_summary") or "").strip()
    gs = gs if not _is_placeholder(gs) else None

    return ESGAnalysisResult(
        company_name=data.get("company_name"),
        reporting_period=data.get("reporting_period"),
        industry=data.get("industry"),
        country=data.get("country"),
        overall_score=overall_score,
        score_methodology=data.get("score_methodology"),
        confidence_level=data.get("confidence_level") or "Medium",
        confidence_justification=data.get("confidence_justification"),
        environmental_summary=ESGPillarSummary(
            **sanitize_pillar_summary(env_raw, "Environmental")
        ),
        social_summary=ESGPillarSummary(
            **sanitize_pillar_summary(soc_raw, "Social")
        ),
        governance_summary=ESGPillarSummary(
            **sanitize_pillar_summary(gov_raw, "Governance")
        ),
        indicators=[ESGIndicator(**ind) for ind in valid_indicators],
        claims=[ESGClaim(**c) for c in valid_claims],
        global_summary=gs,
        material_topics=_clean_list(data.get("material_topics")),
        esg_risks=_clean_list(data.get("esg_risks")),
        esg_opportunities=_clean_list(data.get("esg_opportunities")),
        missing_information=_clean_list(data.get("missing_information")),
    )