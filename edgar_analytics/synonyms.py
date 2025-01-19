# edgar_analytics/synonyms.py

"""
MASTER SYNONYMS DICTIONARY (broad coverage) for mapping diverse
financial statement labeling to a standardized set of keys.
"""
SYNONYMS = {

    # ======================
    #       REVENUE
    # ======================
    "revenue": [
        # GAAP concepts
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:SalesRevenueNet",
        "us-gaap_SalesRevenueNet",
        "us-gaap:Revenues",
        "us-gaap_Revenues",
        # Common textual labels 
        "Revenue", 
        "Revenues",
        "Net sales",
        "Net Sales",
        "Operating revenue",
        "Total revenue",
        "RevenueFromContractWithCustomer",
        "BusinessAcquisitionsProFormaRevenue",
    ],

    # ======================
    #     GROSS PROFIT
    # ======================
    "gross_profit": [
        "us-gaap:GrossProfit",
        "us-gaap_GrossProfit",
        "Gross Profit",
        "Gross margin",
        "Gross margin, net",
        "GrossProfit",
    ],

    # ======================
    #   COST OF REVENUE
    # ======================
    "cost_of_revenue": [
        "us-gaap:CostOfGoodsAndServicesSold",
        "us-gaap_CostOfGoodsAndServicesSold",
        "us-gaap_CostOfRevenue",
        "Cost of revenue",
        "Cost of sales",
        "CostOfSalesPolicyTextBlock",
        "Cost of Sales",
        "Cost of sales (including depreciation)",
    ],

    # ======================
    #   OPERATING EXPENSES
    # ======================
    "operating_expenses": [
        "us-gaap:OperatingExpenses",
        "us-gaap_OperatingExpenses",
        "Operating expenses",
        "Operating expense",
        "Total operating expenses",
    ],

    # ======================
    # RESEARCH & DEVELOPMENT
    # ======================
    "rnd_expenses": [
        "us-gaap:ResearchAndDevelopmentExpense",
        "us-gaap_ResearchAndDevelopmentExpense",
        "R&D",
        "Research and development",
        "ResearchAndDevelopmentExpensePolicy",
    ],

    # ======================
    # SELLING & MARKETING
    # ======================
    "sales_marketing": [
        "us-gaap:SellingAndMarketingExpense",
        "us-gaap_SellingAndMarketingExpense",
        "Selling and marketing",
        "Marketing and advertising",
        "MarketingAndAdvertisingExpense",
        "AdvertisingCostsPolicyTextBlock",
    ],

    # ======================
    #  GENERAL & ADMIN
    # ======================
    "general_administrative": [
        "us-gaap:GeneralAndAdministrativeExpense",
        "us-gaap_GeneralAndAdministrativeExpense",
        "General and administrative",
        "SGA",
        "Selling, general and administrative",
    ],

    # ======================
    #  OPERATING INCOME
    # ======================
    "operating_income": [
        "us-gaap:OperatingIncomeLoss",
        "us-gaap_OperatingIncomeLoss",
        "Operating income",
        "Operating profit",
    ],

    # ======================
    #   NONOPERATING / OTHER
    # ======================
    "other_income_expense": [
        "us-gaap:NonoperatingIncomeExpense",
        "us-gaap_NonoperatingIncomeExpense",
        "Other income/(expense), net",
        "Non-operating income/(expense)",
        "OtherNonoperatingIncomeExpense",
    ],

    # ======================
    #   PRETAX INCOME
    # ======================
    "income_before_taxes": [
        "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "us-gaap_IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "Income before provision for income taxes",
        "Pretax income",
    ],

    # ======================
    #     INCOME TAXES
    # ======================
    "income_tax_expense": [
        "us-gaap:IncomeTaxExpenseBenefit",
        "us-gaap_IncomeTaxExpenseBenefit",
        "Provision for income taxes",
        "Tax expense",
        # Detailed lines
        "Current income tax expense",
        "Deferred income tax expense",
    ],

    # ======================
    #       NET INCOME
    # ======================
    "net_income": [
        "us-gaap:NetIncomeLoss",
        "us-gaap_NetIncomeLoss",
        "Net Income",
        "Net Earnings",
        "Income (loss) from continuing operations",
        "BusinessAcquisitionsProFormaNetIncomeLoss",
    ],

    # ======================
    #        E P S
    # ======================
    "earnings_per_share_basic": [
        "us-gaap:EarningsPerShareBasic",
        "us-gaap_EarningsPerShareBasic",
        "Basic EPS",
    ],
    "earnings_per_share_diluted": [
        "us-gaap:EarningsPerShareDiluted",
        "us-gaap_EarningsPerShareDiluted",
        "Diluted EPS",
    ],

    # ======================
    #   SHARES OUTSTANDING
    # ======================
    "common_shares_outstanding": [
        "dei_EntityCommonStockSharesOutstanding",
        "us-gaap_CommonStockSharesOutstanding",
        "Common Stock, shares outstanding",
        "Shares outstanding",
        "SharesIssued",
    ],

    # ======================
    #       CASH & EQUIV
    # ======================
    "cash_equivalents": [
        "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "us-gaap_CashAndCashEquivalentsAtCarryingValue",
        "Cash and cash equivalents",
        "CashCashEquivalentsAndShortTermInvestments",
        "Cash, cash equivalents, restricted",
    ],

    # ======================
    #   SHORT-TERM INVESTMENTS
    # ======================
    "short_term_investments": [
        "us-gaap_AvailableForSaleSecuritiesDebtSecuritiesCurrent",
        "us-gaap_MarketableSecuritiesCurrent",
        "ST investments",
        "Marketable securities, current",
        "Short-term investments",
    ],

    # ======================
    #   ACCOUNTS RECEIVABLE
    # ======================
    "accounts_receivable": [
        "us-gaap:AccountsReceivableNetCurrent",
        "us-gaap_AccountsReceivableNetCurrent",
        "Accounts receivable",
        "Accounts receivable, net",
        "Receivables",
    ],

    # ======================
    #       INVENTORY
    # ======================
    "inventory": [
        "us-gaap:InventoryNet",
        "us-gaap_InventoryNet",
        "Inventories",
        "Inventory, net",
        "Inventory",
        "Inventory, finished goods",
        "Finished goods inventory",
        "Inventory, raw materials",
        "us-gaap_InventoryDisclosureTextBlock", 
    ],

    # ======================
    #  OTHER CURRENT ASSETS
    # ======================
    "other_current_assets": [
        "us-gaap_OtherAssetsCurrent",
        "us-gaap_PrepaidExpenseAndOtherAssetsCurrent",
        "Prepaid expenses and other current assets",
        "Other current assets",
    ],

    # ======================
    #  TOTAL CURRENT ASSETS
    # ======================
    "current_assets": [
        "us-gaap:AssetsCurrent",
        "us-gaap_AssetsCurrent",
        "Total current assets",
        "Assets, current",
    ],

    # ======================
    #  LONG-TERM INVESTMENTS
    # ======================
    "long_term_investments": [
        "us-gaap_LongTermInvestments",
        "us-gaap_MarketableSecuritiesNoncurrent",
        "Marketable securities, noncurrent",
        "Equity and other investments",
    ],

    # ======================
    #  PROPERTY & EQUIPMENT
    # ======================
    "ppe_net": [
        "us-gaap:PropertyPlantAndEquipmentNet",
        "us-gaap_PropertyPlantAndEquipmentNet",
        "Property, plant and equipment, net",
        "Property and equipment, net",
        "PPE net",
    ],

    # ======================
    #     INTANGIBLE ASSETS
    # ======================
    "intangible_assets": [
        "us-gaap:IntangibleAssetsNetExcludingGoodwill",
        "us-gaap_IntangibleAssetsNetExcludingGoodwill",
        "FiniteLivedIntangibleAssetsNet",
        "us-gaap_FiniteLivedIntangibleAssetsGross",
        "Intangible assets, net",
        "Acquired intangible assets",
    ],

    # ======================
    #         GOODWILL
    # ======================
    "goodwill": [
        "us-gaap:Goodwill",
        "us-gaap_Goodwill",
        "Goodwill",
    ],

    # ======================
    #    OTHER NON-CURRENT
    # ======================
    "other_noncurrent_assets": [
        "us-gaap:AssetsNoncurrent",
        "us-gaap_AssetsNoncurrent",
        "Total non-current assets",
        "Other non-current assets",
        "Long-lived assets",
    ],

    # ======================
    #      TOTAL ASSETS
    # ======================
    "total_assets": [
        "us-gaap:Assets",
        "us-gaap_Assets",
        "Total assets",
    ],

    # ======================
    #  ACCOUNTS PAYABLE
    # ======================
    "accounts_payable": [
        "us-gaap:AccountsPayableCurrent",
        "us-gaap_AccountsPayableCurrent",
        "Accounts payable",
        "AP",
        "Trade payables",
    ],

    # ======================
    #   ACCRUED EXPENSES
    # ======================
    "accrued_expenses": [
        "us-gaap_AccruedLiabilitiesCurrent",
        "us-gaap_AccruedExpenses",
        "Accrued expenses",
        "Other accrued liabilities",
    ],

    # ======================
    #   CURRENT LIABILITIES
    # ======================
    "current_liabilities": [
        "us-gaap:LiabilitiesCurrent",
        "us-gaap_LiabilitiesCurrent",
        "Total current liabilities",
        "Liabilities, current",
    ],

    # ======================
    #   DEFERRED REVENUE
    # ======================
    "deferred_revenue": [
        "us-gaap:ContractWithCustomerLiabilityCurrent",
        "us-gaap_ContractWithCustomerLiabilityCurrent",
        "Deferred revenue",
        "Unearned revenue",
        "Contract liability",
    ],

    # ======================
    #  SHORT-TERM DEBT
    # ======================
    "short_term_debt": [
        "us-gaap_CommercialPaper",
        "Commercial paper",
        "LineOfCreditFacility",
        "Short-term debt",
    ],

    # ======================
    #   LONG-TERM DEBT
    # ======================
    "long_term_debt": [
        "us-gaap:LongTermDebt",
        "us-gaap_LongTermDebt",
        "Term debt",
        "Notes payable",
        "Bond obligations",
    ],

    # ======================
    #   LEASE LIABILITIES
    # ======================
    "operating_lease_liabilities": [
        "us-gaap_OperatingLeaseLiability",
        "Operating lease liabilities",
    ],
    "finance_lease_liabilities": [
        "us-gaap_FinanceLeaseLiability",
        "Finance lease liabilities",
    ],

    # ======================
    #    OTHER LIABILITIES
    # ======================
    "other_noncurrent_liabilities": [
        "us-gaap_LiabilitiesNoncurrent",
        "us-gaap_OtherLiabilitiesNoncurrent",
        "Other non-current liabilities",
        "Total non-current liabilities",
    ],

    # ======================
    #    TOTAL LIABILITIES
    # ======================
    "total_liabilities": [
        "us-gaap:Liabilities",
        "us-gaap_Liabilities",
        "Total liabilities",
    ],

    # ======================
    #  STOCKHOLDERS’ EQUITY
    # ======================
    "total_equity": [
        "us-gaap:StockholdersEquity",
        "us-gaap_StockholdersEquity",
        "Total shareholders’ equity",
        "Equity",
        "Shareholders' equity",
    ],

    # ======================
    #   COMMON STOCK & APIC
    # ======================
    "common_stock_and_apic": [
        "us-gaap_CommonStocksIncludingAdditionalPaidInCapital",
        "us-gaap_AdditionalPaidInCapital",
        "Common stock and additional paid-in capital",
        "Additional paid-in capital",
    ],

    # ======================
    #  TREASURY STOCK
    # ======================
    "treasury_stock": [
        "us-gaap_TreasuryStockValue",
        "Treasury stock",
    ],

    # ======================
    # RETAINED EARNINGS
    # ======================
    "retained_earnings": [
        "us-gaap_RetainedEarningsAccumulatedDeficit",
        "Retained earnings",
        "Accumulated deficit",
    ],

    # ======================
    #   ACCUM. OTHER COMP. INC.
    # ======================
    "accumulated_oci": [
        "us-gaap_AccumulatedOtherComprehensiveIncomeLossNetOfTax",
        "us-gaap_OtherComprehensiveIncomeLossNetOfTax",
        "Accumulated other comprehensive loss",
        "AOCI",
        "Other comprehensive income/loss",
    ],

    # ======================
    #  COMPREHENSIVE INCOME
    # ======================
    "comprehensive_income": [
        "us-gaap:ComprehensiveIncomeNetOfTax",
        "us-gaap_ComprehensiveIncomeNetOfTax",
        "Total comprehensive income",
        "Other comprehensive income, net of tax",
    ],

    # ======================
    #     CASH FLOW: OCF
    # ======================
    "cash_flow_operating": [
        "us-gaap:NetCashProvidedByUsedInOperatingActivities",
        "us-gaap_NetCashProvidedByUsedInOperatingActivities",
        "Cash from/(used in) operating activities",
        "Cash generated by operating activities",
    ],

    # ======================
    #    CASH FLOW: INVEST
    # ======================
    "cash_flow_investing": [
        "us-gaap:NetCashProvidedByUsedInInvestingActivities",
        "us-gaap_NetCashProvidedByUsedInInvestingActivities",
        "Cash from/(used in) investing activities",
        "Cash generated by/(used in) investing activities",
    ],

    # ======================
    #   CASH FLOW: FINANCE
    # ======================
    "cash_flow_financing": [
        "us-gaap:NetCashProvidedByUsedInFinancingActivities",
        "us-gaap_NetCashProvidedByUsedInFinancingActivities",
        "Cash from/(used in) financing activities",
        "Cash used in financing activities",
    ],

    # ======================
    #  SHARE-BASED COMP
    # ======================
    "share_based_compensation": [
        "us-gaap_ShareBasedCompensation",
        "us-gaap_AllocatedShareBasedCompensationExpense",
        "Stock-based compensation expense",
        "Share-based compensation",
        "Equity compensation",
    ],

    # ======================
    #    DEFERRED TAXES
    # ======================
    "deferred_tax_assets": [
        "us-gaap_DeferredTaxAssetsGross",
        "us-gaap_DeferredTaxAssetsNet",
        "Deferred tax assets",
        "DTA",
    ],
    "deferred_tax_liabilities": [
        "us-gaap_DeferredTaxLiabilities",
        "us-gaap_DeferredTaxLiabilitiesNet",
        "DTL",
    ],

    # ======================
    #    UNRECOGNIZED TAX
    # ======================
    "unrecognized_tax_benefits": [
        "us-gaap_UnrecognizedTaxBenefits",
        "Unrecognized tax benefits",
        "Gross unrecognized tax benefits",
    ],

    # ======================
    #      DIVIDENDS
    # ======================
    "dividends": [
        "us-gaap_Dividends",
        "us-gaap_CommonStockDividendsPerShareDeclared",
        "Dividends",
        "Dividends declared",
        "PaymentsOfDividends",
    ],

    # ======================
    #  SHARE REPURCHASE
    # ======================
    "share_repurchase": [
        "us-gaap_PaymentsForRepurchaseOfCommonStock",
        "us-gaap_StockRepurchasedAndRetiredDuringPeriodShares",
        "Repurchases of common stock",
        "Stock repurchased and retired",
    ],

    # ======================
    #  BUSINESS COMBOS (M&A)
    # ======================
    "business_combinations": [
        "us-gaap_BusinessCombinationsPolicy",
        "us-gaap_BusinessCombinationDisclosureTextBlock",
        "Business combinations",
        "AcquisitionsNetOfCashAcquiredAndPurchasesOfIntangibleAndOtherAssets",
        "Merger or acquisition references (in textual sections)",
    ],

    # ======================
    #    LEASES (POLICY)
    # ======================
    "lease_disclosures": [
        "us-gaap_LesseeLeasesPolicyTextBlock",
        "us-gaap_LeaseCost",
        "OperatingLeaseLiabilityPaymentsDue",
        "FinanceLeaseLiabilityPaymentsDue",
        "us-gaap_LeaseCostTableTextBlock",
        "Leases (general disclosures)",
    ],

    # ======================
    # DERIVATIVES & HEDGES
    # ======================
    "derivatives_hedging": [
        "us-gaap_DerivativeInstrumentsAndHedgingActivitiesDisclosureTextBlock",
        "us-gaap_DerivativeAssetFairValueGrossAssetIncludingNotSubjectToMasterNettingArrangement",
        "Derivative instruments",
        "Hedging instruments",
        "Cash flow hedges",
        "Net investment hedges",
        "FairValueHedge",
    ],

    # ======================
    #    FAIR VALUE
    # ======================
    "fair_value": [
        "us-gaap_FairValueMeasurementPolicyPolicyTextBlock",
        "us-gaap_FairValueDisclosuresTextBlock",
        "Fair Value Measurements",
    ],

    # ======================
    #   SEGMENT REPORTING
    # ======================
    "segment_reporting": [
        "us-gaap_SegmentReportingPolicyPolicyTextBlock",
        "us-gaap_SegmentReportingDisclosureTextBlock",
        "Segment revenue",
        "Segment operating income",
    ],

    # ======================
    #  COMMITMENTS & CONTINGENCIES
    # ======================
    "commitments_contingencies": [
        "us-gaap_CommitmentsAndContingencies",
        "us-gaap_CommitmentsAndContingenciesDisclosureTextBlock",
        "Contingencies",
        "Litigation, claims",
        "Purchase obligations",
        "Guarantees",
    ],

    # ======================
    #   LITIGATION / LEGAL
    # ======================
    "litigation_legal": [
        "us-gaap_LegalMattersAndContingenciesTextBlock",
        "Loss contingency, loss in period",
        "European Commission fines",
        "Legal proceedings",
    ],

    # ======================
    #   RISK FACTORS
    # ======================
    "risk_factors": [
        # Typically textual items from 10-K “Item 1A”
        "Risk Factors",
        "Item 1A. Risk Factors",
        "Business risk, M&A risk, supply chain risk, etc.",
    ],

    # ======================
    #   INSIDER TRADING
    # ======================
    "insider_transactions": [
        "ecd_TrdArrIndName",
        "ecd_TrdArrIndTitle",
        "Insider trading arrangement",
        "Rule 10b5-1 arrangement",
        "InsiderTrdPoliciesProcAdoptedFlag",
    ],

    # ======================
    #  RECENT ACCOUNTING PRONOUNCEMENTS
    # ======================
    "recent_accounting_guidance": [
        "us-gaap_NewAccountingPronouncementsPolicyPolicyTextBlock",
        "kltr_RecentAccountingGuidanceNotYetAdoptedPolicyTextBlock",
        "Recent accounting guidance",
        "Pronouncements not yet adopted",
    ],

    # ======================
    #   Capital expenditures
    # ======================
    "capital_expenditures": [
        # Many companies label it as "Capital expenditures", "Purchase of property, plant and equipment", etc.
        "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
        "us-gaap_PaymentsToAcquirePropertyPlantAndEquipment",
        "Capital expenditures",
        "Purchase of PP&E",
        "Purchase of fixed assets",
        "Additions to property, plant and equipment",
        "PurchaseOfPropertyAndEquipment",
        "Capital expenditures, net",
        "Capital Expenditures, net",
        "Capital expenditure",
        "Capital Expenditure",
        "Capital investment",
        "CapEx",
        "Capex",
        "Property, plant and equipment acquisitions",
        "Capital asset purchases",
        "Purchase of property, plant, and equipment",
    ],

    # ======================
    #   MISCELLANEOUS
    # ======================
    "miscellaneous": [
        "BasisOfAccountingPolicyPolicyTextBlock",
        "BasisOfPresentationAndSignificantAccountingPoliciesTextBlock",
        "ConsolidationPolicyTextBlock",
        "ForeignCurrencyTransactionsAndTranslationsPolicyTextBlock",
        "NatureOfOperationsPolicyPolicyTextBlock",
        "srt_CondensedFinancialStatementsTextBlock",
        "us-gaap_SignificantAccountingPoliciesTextBlock",
    ],

}
