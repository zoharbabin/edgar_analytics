"""tests/test_synonyms.py — integrity tests for the SYNONYMS dictionary."""

import pytest

from edgar_analytics.synonyms import SYNONYMS


class TestSynonymsIntegrity:
    """Every synonym key must be non-empty, contain no duplicates, and have
    reasonable XBRL tag coverage."""

    def test_all_keys_have_nonempty_lists(self):
        for key, tags in SYNONYMS.items():
            assert isinstance(tags, list), f"{key} is not a list"
            assert len(tags) > 0, f"{key} has an empty synonym list"

    def test_no_duplicate_tags_within_a_key(self):
        for key, tags in SYNONYMS.items():
            seen = set()
            for tag in tags:
                assert tag not in seen, f"Duplicate tag {tag!r} in {key}"
                seen.add(tag)

    def test_no_proforma_tags(self):
        """Pro-forma M&A disclosure tags must not appear in revenue or net_income."""
        for key in ("revenue", "net_income"):
            tags = SYNONYMS.get(key, [])
            for tag in tags:
                assert "ProForma" not in tag, (
                    f"Pro-forma tag {tag!r} found in {key} — these are M&A disclosures, "
                    f"not actual reported values"
                )

    @pytest.mark.parametrize("key", [
        "revenue", "net_income", "total_assets", "total_liabilities",
        "total_equity", "current_assets", "current_liabilities",
        "cash_equivalents", "operating_income", "cost_of_revenue",
        "general_administrative", "depreciation_amortization",
        "capital_expenditures", "cash_flow_operating",
    ])
    def test_critical_keys_exist(self, key):
        assert key in SYNONYMS, f"Critical synonym key {key!r} is missing"
        assert len(SYNONYMS[key]) >= 2, (
            f"Key {key!r} has only {len(SYNONYMS[key])} synonym(s) — "
            f"should have at least a GAAP tag and a textual label"
        )

    def test_sga_includes_combined_tag(self):
        """C2 fix: SellingGeneralAndAdministrativeExpense must be present."""
        sga_tags = SYNONYMS["general_administrative"]
        combined = [t for t in sga_tags if "SellingGeneralAndAdministrative" in t]
        assert len(combined) >= 1, (
            "Missing us-gaap:SellingGeneralAndAdministrativeExpense in "
            "general_administrative synonyms"
        )

    def test_depreciation_includes_british_spelling(self):
        tags = SYNONYMS["depreciation_amortization"]
        british = [t for t in tags if "amortisation" in t.lower()]
        assert len(british) >= 1, (
            "Missing British spelling 'amortisation' in "
            "depreciation_amortization synonyms"
        )

    def test_all_tags_are_strings(self):
        for key, tags in SYNONYMS.items():
            for tag in tags:
                assert isinstance(tag, str), f"Non-string tag {tag!r} in {key}"
                assert tag.strip() == tag, f"Tag {tag!r} in {key} has leading/trailing whitespace"

    def test_no_empty_string_tags(self):
        for key, tags in SYNONYMS.items():
            for tag in tags:
                assert tag != "", f"Empty string tag in {key}"
