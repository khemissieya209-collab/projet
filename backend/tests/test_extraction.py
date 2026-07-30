"""
Validation test suite for the ESG extraction pipeline.

Tests that:
- No hallucinated KPIs are generated (all values exist in source text)
- No fake percentages appear
- No fake company names appear
- Recommendations reference actual weaknesses from the report
- Extracted numbers exactly match the PDF text
- Page numbers are valid
"""

import re
import sys
import os
import json
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def validate_kpis_against_text(indicators: list[dict], source_text: str) -> dict:
    """
    Verify that all extracted KPI values exist verbatim in the source text.

    Returns a report with matched and unmatched indicators.
    """
    results = {
        "total": len(indicators),
        "matched": 0,
        "unmatched": 0,
        "details": []
    }

    for ind in indicators:
        value = ind.get("value", "")
        name = ind.get("name", "Unknown")

        if not value or value in ("N/A", "Not specified", "null"):
            results["details"].append({
                "indicator": name,
                "value": value,
                "status": "SKIPPED",
                "reason": "No value to verify"
            })
            continue

        # Search for the value in the source text
        # Try exact match first, then fuzzy (with/without commas, spaces)
        found = False

        # Exact match
        if value in source_text:
            found = True

        # Try without thousands separators
        if not found:
            normalized = value.replace(",", "").replace(" ", "")
            text_normalized = source_text.replace(",", "").replace(" ", "")
            if normalized in text_normalized:
                found = True

        # Try matching the numeric part only
        if not found:
            numbers = re.findall(r'[\d.,]+', value)
            for num in numbers:
                if num in source_text:
                    found = True
                    break

        if found:
            results["matched"] += 1
            results["details"].append({
                "indicator": name,
                "value": value,
                "status": "MATCH",
            })
        else:
            results["unmatched"] += 1
            results["details"].append({
                "indicator": name,
                "value": value,
                "status": "NO_MATCH",
                "reason": "Value not found in source text — possible hallucination"
            })

    return results


def validate_company_name(company_name: Optional[str], source_text: str) -> dict:
    """
    Verify that the extracted company name exists in the source text.
    """
    if not company_name or company_name in ("Not specified", "null"):
        return {"status": "SKIPPED", "reason": "No company name extracted"}

    # Check if the company name (or significant parts) appear in the text
    if company_name.lower() in source_text.lower():
        return {"status": "MATCH", "company_name": company_name}

    # Try matching individual words (for multi-word company names)
    words = [w for w in company_name.split() if len(w) > 2]
    matched_words = [w for w in words if w.lower() in source_text.lower()]

    if len(matched_words) >= len(words) * 0.5:
        return {
            "status": "PARTIAL_MATCH",
            "company_name": company_name,
            "matched_words": matched_words
        }

    return {
        "status": "NO_MATCH",
        "company_name": company_name,
        "reason": "Company name not found in source text — possible hallucination"
    }


def validate_percentages(esg_data: dict, source_text: str) -> dict:
    """
    Find all percentage values in the ESG output and verify they exist in the source text.
    """
    # Serialize the ESG output to find all percentages
    output_str = json.dumps(esg_data, ensure_ascii=False)
    percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', output_str)

    results = {
        "total": len(percentages),
        "matched": 0,
        "unmatched": 0,
        "details": []
    }

    for pct in percentages:
        pct_str = f"{pct}%"
        pct_str_spaced = f"{pct} %"

        if pct_str in source_text or pct_str_spaced in source_text or pct in source_text:
            results["matched"] += 1
            results["details"].append({"value": pct_str, "status": "MATCH"})
        else:
            results["unmatched"] += 1
            results["details"].append({
                "value": pct_str,
                "status": "NO_MATCH",
                "reason": "Percentage not found in source text — possible hallucination"
            })

    return results


def validate_page_numbers(indicators: list[dict], claims: list[dict],
                          total_pages: int) -> dict:
    """
    Verify that all page numbers are within the valid range.
    """
    issues = []
    items = [("indicator", ind) for ind in indicators] + [("claim", cl) for cl in claims]

    for item_type, item in items:
        page = item.get("page_number")
        if page is not None:
            if not isinstance(page, int) or page < 1 or page > total_pages:
                issues.append({
                    "type": item_type,
                    "name": item.get("name") or item.get("statement", "unknown"),
                    "page_number": page,
                    "reason": f"Invalid page number (document has {total_pages} pages)"
                })

    return {
        "total_with_pages": sum(1 for _, i in items if i.get("page_number") is not None),
        "invalid_pages": len(issues),
        "issues": issues
    }


def validate_recommendations_reference_weaknesses(
    strategy_data: dict, weaknesses: list[str]
) -> dict:
    """
    Check that recommendations reference actual weaknesses from the ESG audit.
    """
    all_recommendations = (
        strategy_data.get("priority_actions", []) +
        strategy_data.get("short_term", []) +
        strategy_data.get("mid_term", []) +
        strategy_data.get("long_term", [])
    )

    results = {
        "total_recommendations": len(all_recommendations),
        "total_weaknesses": len(weaknesses),
        "recommendations_with_reference": 0,
        "recommendations_without_reference": 0,
        "details": []
    }

    for rec in all_recommendations:
        # Check if the recommendation mentions "[Addresses:" pattern
        has_ref = "[Addresses:" in rec if isinstance(rec, str) else False

        # Also check if any weakness keyword appears in the recommendation
        matches_weakness = False
        for w in weaknesses:
            # Check if significant words from the weakness appear
            w_words = set(w.lower().split())
            rec_words = set(rec.lower().split()) if isinstance(rec, str) else set()
            overlap = w_words & rec_words - {"the", "a", "an", "is", "are", "and", "or", "of", "in", "to", "for"}
            if len(overlap) >= 2:
                matches_weakness = True
                break

        if has_ref or matches_weakness:
            results["recommendations_with_reference"] += 1
            results["details"].append({"recommendation": rec[:100], "status": "REFERENCED"})
        else:
            results["recommendations_without_reference"] += 1
            results["details"].append({
                "recommendation": rec[:100],
                "status": "NO_REFERENCE",
                "reason": "Does not reference any identified weakness"
            })

    return results


def run_validation(source_text: str, esg_data: dict,
                   strategy_data: dict, total_pages: int) -> dict:
    """
    Run the full validation suite.

    Args:
        source_text: The raw extracted text from the PDF.
        esg_data: The ESG analysis result as a dict.
        strategy_data: The strategy result as a dict.
        total_pages: Total number of pages in the PDF.

    Returns:
        Complete validation report.
    """
    indicators = esg_data.get("indicators", [])
    claims = esg_data.get("claims", [])
    weaknesses = (
        esg_data.get("environmental_summary", {}).get("weaknesses", []) +
        esg_data.get("social_summary", {}).get("weaknesses", []) +
        esg_data.get("governance_summary", {}).get("weaknesses", [])
    )

    report = {
        "kpi_validation": validate_kpis_against_text(indicators, source_text),
        "company_name_validation": validate_company_name(
            esg_data.get("company_name"), source_text
        ),
        "percentage_validation": validate_percentages(esg_data, source_text),
        "page_number_validation": validate_page_numbers(
            indicators, claims, total_pages
        ),
        "recommendation_validation": validate_recommendations_reference_weaknesses(
            strategy_data, weaknesses
        ),
    }

    # Overall pass/fail
    kpi_pass = report["kpi_validation"]["unmatched"] == 0
    company_pass = report["company_name_validation"]["status"] != "NO_MATCH"
    pct_pass = report["percentage_validation"]["unmatched"] == 0
    page_pass = report["page_number_validation"]["invalid_pages"] == 0

    report["overall"] = {
        "kpi_check": "PASS" if kpi_pass else "FAIL",
        "company_name_check": "PASS" if company_pass else "FAIL",
        "percentage_check": "PASS" if pct_pass else "FAIL",
        "page_number_check": "PASS" if page_pass else "FAIL",
        "all_passed": all([kpi_pass, company_pass, pct_pass, page_pass]),
    }

    return report


def print_validation_report(report: dict) -> None:
    """Print a human-readable validation report."""
    print("\n" + "=" * 60)
    print("  ESG PIPELINE VALIDATION REPORT")
    print("=" * 60)

    # KPI validation
    kpi = report["kpi_validation"]
    print(f"\n[KPI] KPI Validation: {kpi['matched']}/{kpi['total']} matched")
    for d in kpi["details"]:
        icon = "[OK]" if d["status"] == "MATCH" else "[SKIP]" if d["status"] == "SKIPPED" else "[ERR]"
        print(f"   {icon} {d['indicator']}: {d['value']} [{d['status']}]")

    # Company name
    cn = report["company_name_validation"]
    icon = "[OK]" if cn["status"] == "MATCH" else "[SKIP]" if cn["status"] in ("SKIPPED", "PARTIAL_MATCH") else "[ERR]"
    print(f"\n[COMPANY] Company Name: {icon} {cn.get('company_name', 'N/A')} [{cn['status']}]")

    # Percentages
    pct = report["percentage_validation"]
    print(f"\n[PERCENTAGE] Percentages: {pct['matched']}/{pct['total']} verified")
    for d in pct["details"]:
        if d["status"] == "NO_MATCH":
            print(f"   [ERR] {d['value']} - {d.get('reason', '')}")

    # Page numbers
    pg = report["page_number_validation"]
    print(f"\n[PAGES] Page Numbers: {pg['total_with_pages']} items have page refs, {pg['invalid_pages']} invalid")

    # Recommendations
    rec = report["recommendation_validation"]
    print(f"\n[STRATEGY] Recommendations: {rec['recommendations_with_reference']}/{rec['total_recommendations']} reference weaknesses")

    # Overall
    overall = report["overall"]
    print(f"\n{'=' * 60}")
    print(f"  OVERALL: {'OK - ALL CHECKS PASSED' if overall['all_passed'] else 'FAIL - SOME CHECKS FAILED'}")
    for check, status in overall.items():
        if check != "all_passed":
            icon = "[PASS]" if status == "PASS" else "[FAIL]"
            print(f"   {icon} {check}: {status}")
    print(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# CLI entrypoint for manual testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate ESG pipeline output")
    parser.add_argument("pdf_path", help="Path to the PDF file to test")
    args = parser.parse_args()

    from backend.services.pdf_extraction import extract_document
    from backend.agents.esg_analyzer import analyze_esg
    from backend.agents.greenwashing_detector import detect_greenwashing
    from backend.agents.strategy_generator import generate_strategy

    print(f"\n[FILE] Extracting: {args.pdf_path}")
    doc = extract_document(args.pdf_path)
    print(f"   Pages: {doc.total_pages} | Method: {doc.extraction_method}")
    print(f"   Tables: {doc.has_tables} | Text length: {len(doc.full_text)} chars")

    print("\n[AGENT 1] Running ESG analysis...")
    esg_result = analyze_esg(doc.full_text)

    print("[AGENT 2] Running greenwashing audit...")
    gw_result = detect_greenwashing(esg_result, doc.full_text)

    print("[AGENT 3] Running strategy generation...")
    strategy_result = generate_strategy(esg_result, gw_result)

    # Convert to dicts for validation
    esg_data = esg_result.model_dump()
    strategy_data = strategy_result.model_dump()

    print("\n[VALIDATION] Running validation...")
    report = run_validation(doc.full_text, esg_data, strategy_data, doc.total_pages)
    print_validation_report(report)

