"""Cross-validation layer using the SEC CompanyFacts XBRL API.

Fetches ``data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`` and
compares key facts against locally-parsed metrics.  Discrepancies are
logged — never silently overridden — so the edgartools-based pipeline
remains authoritative.

Usage::

    from edgar_analytics.company_facts import CompanyFactsClient
    client = CompanyFactsClient()
    facts = client.fetch("AAPL")
    client.validate_metrics(facts, metrics_dict)
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .logging_utils import get_logger

logger = get_logger(__name__)

_BASE_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

_CONCEPT_MAP: Dict[str, list[str]] = {
    "Revenue": [
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:Revenues",
    ],
    "Net Income": ["us-gaap:NetIncomeLoss"],
    "Total assets": ["us-gaap:Assets"],
    "Total liabilities": ["us-gaap:Liabilities"],
    "Total shareholders' equity": [
        "us-gaap:StockholdersEquity",
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
}

_TOLERANCE_PCT = 1.0


class CompanyFactsClient:
    """Lightweight client for the SEC XBRL CompanyFacts API."""

    def __init__(self, identity: str = "edgar-analytics <edgar-analytics@users.noreply.github.com>") -> None:
        self._headers = {"User-Agent": identity, "Accept": "application/json"}

    def _get_json(self, url: str, max_retries: int = 3) -> Optional[dict]:
        backoff = 1.0
        for attempt in range(max_retries):
            try:
                req = Request(url, headers=self._headers)
                with urlopen(req, timeout=15) as resp:
                    return json.loads(resp.read().decode())
            except HTTPError as exc:
                if exc.code in (429, 503) and attempt < max_retries - 1:
                    wait = backoff * (2 ** attempt)
                    logger.debug("SEC rate-limited (%d) on %s, retrying in %.1fs", exc.code, url, wait)
                    time.sleep(wait)
                    continue
                logger.debug("CompanyFacts HTTP %d for %s: %s", exc.code, url, exc)
                return None
            except (URLError, json.JSONDecodeError, OSError) as exc:
                logger.debug("CompanyFacts request failed for %s: %s", url, exc)
                return None
        return None

    def cik_for_ticker(self, ticker: str) -> Optional[str]:
        """Resolve a ticker to a zero-padded 10-digit CIK string."""
        try:
            from edgar import Company
            comp = Company(ticker)
            cik = getattr(comp, "cik", None)
            if cik is not None:
                return str(cik).zfill(10)
        except Exception:
            pass
        return None

    def fetch(self, ticker: str) -> Optional[dict]:
        """Fetch all company facts for a ticker. Returns the raw JSON dict."""
        cik = self.cik_for_ticker(ticker)
        if not cik:
            logger.warning("Could not resolve CIK for %s", ticker)
            return None
        url = _BASE_URL.format(cik=cik)
        return self._get_json(url)

    def get_latest_value(self, facts: dict, concept: str, unit: str = "USD") -> Optional[float]:
        """Extract the most recent filed value for a given us-gaap concept."""
        if not facts:
            return None
        taxonomy, tag = concept.split(":", 1) if ":" in concept else ("us-gaap", concept)
        try:
            units = facts["facts"][taxonomy][tag]["units"]
            values = units.get(unit, [])
            if not values:
                return None
            annual = [v for v in values if v.get("form") in ("10-K", "20-F")]
            if not annual:
                annual = values
            latest = max(annual, key=lambda v: v.get("end", ""))
            return float(latest["val"])
        except (KeyError, ValueError, TypeError):
            return None

    def validate_metrics(
        self,
        facts: Optional[dict],
        metrics: dict,
        ticker: str = "",
    ) -> list[str]:
        """Compare parsed metrics against SEC CompanyFacts.

        Returns a list of discrepancy strings. Discrepancies are also logged
        as warnings but never modify the input metrics dict.
        """
        if not facts:
            return []

        discrepancies = []
        for metric_key, concepts in _CONCEPT_MAP.items():
            local_val = metrics.get(metric_key)
            if local_val is None or local_val == 0:
                continue
            sec_val = None
            for concept in concepts:
                sec_val = self.get_latest_value(facts, concept)
                if sec_val is not None:
                    break
            if sec_val is None:
                continue

            denom = max(abs(local_val), abs(sec_val), 1.0)
            diff_pct = abs(local_val - sec_val) / denom * 100.0
            if diff_pct > _TOLERANCE_PCT:
                msg = (
                    f"{ticker} {metric_key}: local={local_val:,.0f} vs "
                    f"SEC={sec_val:,.0f} (diff={diff_pct:.1f}%)"
                )
                discrepancies.append(msg)
                logger.warning("CompanyFacts discrepancy: %s", msg)

        return discrepancies
