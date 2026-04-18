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

    def test_no_textblock_in_quantitative_synonyms(self):
        """TextBlock tags are disclosure-only and must not appear in numeric synonym groups."""
        quantitative_keys = [
            "revenue", "cost_of_revenue", "net_income", "operating_income",
            "total_assets", "total_liabilities", "total_equity",
            "current_assets", "current_liabilities", "inventory",
            "accounts_receivable", "accounts_payable", "long_term_debt",
            "short_term_debt", "cash_equivalents", "rnd_expenses",
            "sales_marketing", "general_administrative", "capital_expenditures",
            "depreciation_amortization", "interest_expense", "income_tax_expense",
            "cash_flow_operating", "cash_flow_investing", "cash_flow_financing",
        ]
        for key in quantitative_keys:
            for tag in SYNONYMS.get(key, []):
                assert "TextBlock" not in tag, (
                    f"TextBlock tag {tag!r} in quantitative synonym {key!r}"
                )

    def test_revenue_includes_assessed_tax_variant(self):
        tags = SYNONYMS["revenue"]
        assert any("IncludingAssessedTax" in t for t in tags), (
            "Missing RevenueFromContractWithCustomerIncludingAssessedTax"
        )

    def test_equity_includes_nci_variant(self):
        tags = SYNONYMS["total_equity"]
        assert any("NoncontrollingInterest" in t for t in tags), (
            "Missing StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
        )

    def test_long_term_debt_includes_noncurrent(self):
        tags = SYNONYMS["long_term_debt"]
        assert any("Noncurrent" in t for t in tags), (
            "Missing LongTermDebtNoncurrent"
        )

    def test_short_term_debt_includes_short_term_borrowings(self):
        tags = SYNONYMS["short_term_debt"]
        assert any("ShortTermBorrowings" in t for t in tags), (
            "Missing ShortTermBorrowings"
        )

    def test_short_term_debt_includes_ltd_current(self):
        tags = SYNONYMS["short_term_debt"]
        assert any("LongTermDebtCurrent" in t for t in tags), (
            "Missing LongTermDebtCurrent (current portion of LTD)"
        )

    def test_revenue_includes_pre_asc606_tags(self):
        tags = SYNONYMS["revenue"]
        assert any("SalesRevenueGoodsNet" in t for t in tags), (
            "Missing SalesRevenueGoodsNet (pre-ASC 606)"
        )
        assert any("SalesRevenueServicesNet" in t for t in tags), (
            "Missing SalesRevenueServicesNet (pre-ASC 606)"
        )

    def test_preferred_stock_synonyms_exist(self):
        assert "preferred_stock" in SYNONYMS
        tags = SYNONYMS["preferred_stock"]
        assert any("PreferredStock" in t for t in tags)

    def test_minority_interest_synonyms_exist(self):
        assert "minority_interest" in SYNONYMS
        tags = SYNONYMS["minority_interest"]
        assert any("MinorityInterest" in t or "NonControlling" in t for t in tags)

    def test_net_income_includes_common_stockholders_basic(self):
        tags = SYNONYMS["net_income"]
        assert any("AvailableToCommonStockholdersBasic" in t for t in tags), (
            "Missing NetIncomeLossAvailableToCommonStockholdersBasic"
        )

    def test_net_income_includes_attributable_to_parent(self):
        tags = SYNONYMS["net_income"]
        assert any("AttributableToParent" in t for t in tags), (
            "Missing NetIncomeLossAttributableToParent"
        )
        assert any("ProfitLossAttributableToOwnersOfParent" in t for t in tags), (
            "Missing ifrs-full:ProfitLossAttributableToOwnersOfParent"
        )

    def test_depreciation_without_depletion(self):
        tags = SYNONYMS["depreciation_amortization"]
        has_depletion = any("DepreciationDepletionAndAmortization" in t for t in tags)
        has_without = any(
            "DepreciationAndAmortization" in t and "Depletion" not in t
            for t in tags
        )
        assert has_depletion, "Missing DepreciationDepletionAndAmortization"
        assert has_without, "Missing DepreciationAndAmortization (without Depletion)"

    def test_sales_marketing_in_expense_labels(self):
        """sales_marketing is in _EXPENSE_LABELS for correct sign-flipping."""
        from edgar_analytics.synonyms_utils import _EXPENSE_LABELS
        assert "sales_marketing" in _EXPENSE_LABELS

    def test_norm_idx_cache_thread_safe(self):
        """_norm_idx_cache uses a threading.Lock for thread safety."""
        import threading
        from edgar_analytics.synonyms_utils import _norm_idx_lock
        assert isinstance(_norm_idx_lock, type(threading.Lock()))
