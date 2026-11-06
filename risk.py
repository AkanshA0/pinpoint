"""Risk score calculation for privacy findings."""

from typing import List, Dict, Any

RISK_POINTS = {
    "id_card": 40,
    "license_plate": 30,
    "house_number": 30,
    "document": 35,
    "street_sign": 25,
    "business_sign": 15,
    "other": 10,
}

SEVERITY_MULTIPLIERS = {
    "high": 1.0,
    "medium": 0.7,
    "low": 0.4,
}


def calculate_risk(findings: List[Dict[str, Any]]) -> int:
    """
    Calculate overall risk score from findings.

    Returns a score from 0-100:
    - Green: < 25 (low risk)
    - Amber: 25-59 (medium risk)
    - Red: 60+ (high risk)
    """
    if not findings:
        return 0

    score = 0
    for finding in findings:
        category = finding.get("category", "other")
        severity = finding.get("severity", "medium")

        base_points = RISK_POINTS.get(category, 10)
        multiplier = SEVERITY_MULTIPLIERS.get(severity, 0.7)

        score += base_points * multiplier

    return min(int(score), 100)


def get_risk_level(score: int) -> str:
    """Get risk level category from score."""
    if score < 25:
        return "low"
    elif score < 60:
        return "medium"
    else:
        return "high"
