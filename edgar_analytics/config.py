# edgar_analytics/config.py

ALERTS_CONFIG = {
    "NEGATIVE_MARGIN": 0.0,
    "HIGH_LEVERAGE": 3.0,
    "LOW_ROE": 5.0,
    "LOW_ROA": 2.0,
    # Additional:
    "SUSTAINED_NEG_FCF_QUARTERS": 2,    # 2+ consecutive quarters negative FCF => alert
    "INVENTORY_SPIKE_THRESHOLD": 30.0,  # +30% qoq
    "RECEIVABLE_SPIKE_THRESHOLD": 30.0,  # +30% qoq
}
