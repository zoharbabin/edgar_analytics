# edgar_analytics/config.py

from typing import Dict, Any, Optional

ALERTS_CONFIG: Dict[str, Any] = {
    "NEGATIVE_MARGIN": 0.0,
    "HIGH_LEVERAGE": 3.0,
    "LOW_ROE": 5.0,
    "LOW_ROA": 2.0,
    "NET_DEBT_EBITDA_THRESHOLD": 3.5,
    "INTEREST_COVERAGE_THRESHOLD": 2.0,
    "SUSTAINED_NEG_FCF_QUARTERS": 2,
    "INVENTORY_SPIKE_THRESHOLD": 30.0,
    "RECEIVABLE_SPIKE_THRESHOLD": 30.0,
}


def get_alerts_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return alerts config merged with optional user overrides."""
    if not overrides:
        return ALERTS_CONFIG
    merged = {**ALERTS_CONFIG, **overrides}
    return merged
