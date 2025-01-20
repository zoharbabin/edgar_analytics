# edgar_analytics/synonyms.py

"""
MASTER SYNONYMS DICTIONARY for mapping diverse
financial statement labeling to a standardized set of keys.
Covers US GAAP, IFRS and other free text references for broader coverage.
"""

SYNONYMS = {

    # ======================
    #       REVENUE
    # ======================
    "revenue": [
        # US GAAP
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:SalesRevenueNet",
        "us-gaap_SalesRevenueNet",
        "us-gaap:Revenues",
        "us-gaap_Revenues",
        # IFRS
        "ifrs-full:Revenue",
        "ifrs-full:RevenueFromSaleOfGoods",
        "ifrs-full:RevenueFromRenderingOfServices",
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
        # IFRS
        "ifrs-full:GrossProfit",
        # Common textual labels
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
        # IFRS
        "ifrs-full:CostOfSales",
        # Common textual labels
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
        # IFRS
        "ifrs-full:OperatingExpenses",
        "ifrs-full:OtherOperatingExpenses",
        # Common textual labels
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
        # IFRS
        "ifrs-full:ResearchAndDevelopmentExpense",
        # Common textual labels
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
        # IFRS
        "ifrs-full:SellingExpense",
        # Common textual labels
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
        # IFRS
        "ifrs-full:AdministrativeExpense",
        # Common textual labels
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
        # IFRS
        "ifrs-full:OperatingProfitLoss",
        # Common textual labels
        "Operating income",
        "Operating profit",
    ],

    # ======================
    #  NONOPERATING / OTHER
    # ======================
    "other_income_expense": [
        "us-gaap:NonoperatingIncomeExpense",
        "us-gaap_NonoperatingIncomeExpense",
        # IFRS (often "finance income/expense" or "other income/expense")
        "ifrs-full:OtherOperatingIncome",
        "ifrs-full:FinanceIncome",
        # Common textual labels
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
        # IFRS
        "ifrs-full:ProfitLossBeforeTax",
        # Common textual labels
        "Income before provision for income taxes",
        "Pretax income",
    ],

    # ======================
    #    INCOME TAXES
    # ======================
    "income_tax_expense": [
        "us-gaap:IncomeTaxExpenseBenefit",
        "us-gaap_IncomeTaxExpenseBenefit",
        # IFRS
        "ifrs-full:IncomeTaxExpense",
        # Common textual labels
        "Provision for income taxes",
        "Tax expense",
        "Current income tax expense",
        "Deferred income tax expense",
    ],

    # ======================
    # DEPRECIATION & AMORTIZATION
    # ======================
    "depreciation_amortization": [
        "us-gaap:DepreciationDepletionAndAmortization",
        "us-gaap_DepreciationDepletionAndAmortization",
        # Common textual labels
        "Depreciation and amortization",
        "Depreciation & Amortization",
        "Depreciation expense",
        "Amortization expense",
        "Depreciation and amortization expense",
        "D&A",
    ],

    # ======================
    # DEPRECIATION EMBEDDED IN COGS
    # ======================
    "depreciation_in_cost_of_sales": [
        "us-gaap:DepreciationAmortizationInCostOfGoodsSold",
        "us-gaap_DepreciationAmortizationInCostOfGoodsSold",
        # Common textual labels
        "Depreciation in cost of sales",
        "Depreciation included in cost of sales",
        "Depreciation (in cost of sales)",
        "Depr in cost of goods sold",
    ],

    # ======================
    #     NET INCOME
    # ======================
    "net_income": [
        "us-gaap:NetIncomeLoss",
        "us-gaap_NetIncomeLoss",
        # IFRS
        "ifrs-full:ProfitLoss",
        # Common textual labels
        "Net Income",
        "Net Earnings",
        "Income (loss) from continuing operations",
        "BusinessAcquisitionsProFormaNetIncomeLoss",
    ],

    # ======================
    #         EPS
    # ======================
    "earnings_per_share_basic": [
        "us-gaap:EarningsPerShareBasic",
        "us-gaap_EarningsPerShareBasic",
        # IFRS
        "ifrs-full:BasicEarningsLossPerShare",
        # Common textual
        "Basic EPS",
    ],
    "earnings_per_share_diluted": [
        "us-gaap:EarningsPerShareDiluted",
        "us-gaap_EarningsPerShareDiluted",
        # IFRS
        "ifrs-full:DilutedEarningsLossPerShare",
        # Common textual
        "Diluted EPS",
    ],

    # ======================
    # SHARES OUTSTANDING
    # ======================
    "common_shares_outstanding": [
        "dei_EntityCommonStockSharesOutstanding",
        "us-gaap_CommonStockSharesOutstanding",
        # IFRS
        "ifrs-full:IssuedCapitalNumberOfShares",
        # Common textual
        "Common Stock, shares outstanding",
        "Shares outstanding",
        "SharesIssued",
    ],

    # ======================
    #    CASH & EQUIV
    # ======================
    "cash_equivalents": [
        "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "us-gaap_CashAndCashEquivalentsAtCarryingValue",
        # IFRS
        "ifrs-full:CashAndCashEquivalents",
        # Common textual
        "Cash and cash equivalents",
        "CashCashEquivalentsAndShortTermInvestments",
        "Cash, cash equivalents, restricted",
    ],

    # ======================
    #  SHORT-TERM INVESTMENTS
    # ======================
    "short_term_investments": [
        "us-gaap_AvailableForSaleSecuritiesDebtSecuritiesCurrent",
        "us-gaap_MarketableSecuritiesCurrent",
        # IFRS
        "ifrs-full:FinancialAssetsCurrent",
        # Common textual
        "ST investments",
        "Marketable securities, current",
        "Short-term investments",
    ],

    # ======================
    # ACCOUNTS RECEIVABLE
    # ======================
    "accounts_receivable": [
        "us-gaap:AccountsReceivableNetCurrent",
        "us-gaap_AccountsReceivableNetCurrent",
        # IFRS
        "ifrs-full:TradeAndOtherReceivables",
        # Common textual
        "Accounts receivable",
        "Accounts receivable, net",
        "Receivables",
    ],

    # ======================
    #      INVENTORY
    # ======================
    "inventory": [
        "us-gaap:InventoryNet",
        "us-gaap_InventoryNet",
        # IFRS
        "ifrs-full:Inventories",
        # Common textual
        "Inventories",
        "Inventory, net",
        "Inventory",
        "Inventory, finished goods",
        "Finished goods inventory",
        "Inventory, raw materials",
        "us-gaap_InventoryDisclosureTextBlock",
    ],

    # ======================
    # OTHER CURRENT ASSETS
    # ======================
    "other_current_assets": [
        "us-gaap_OtherAssetsCurrent",
        "us-gaap_PrepaidExpenseAndOtherAssetsCurrent",
        # IFRS
        "ifrs-full:OtherCurrentAssets",
        # Common textual
        "Prepaid expenses and other current assets",
        "Other current assets",
    ],

    # ======================
    #  TOTAL CURRENT ASSETS
    # ======================
    "current_assets": [
        "us-gaap:AssetsCurrent",
        "us-gaap_AssetsCurrent",
        # IFRS
        "ifrs-full:CurrentAssets",
        # Common textual
        "Total current assets",
        "Assets, current",
    ],

    # ======================
    # LONG-TERM INVESTMENTS
    # ======================
    "long_term_investments": [
        "us-gaap_LongTermInvestments",
        "us-gaap_MarketableSecuritiesNoncurrent",
        # IFRS
        "ifrs-full:NoncurrentFinancialAssets",
        # Common textual
        "Marketable securities, noncurrent",
        "Equity and other investments",
    ],

    # ======================
    #  PROPERTY & EQUIPMENT
    # ======================
    "ppe_net": [
        "us-gaap:PropertyPlantAndEquipmentNet",
        "us-gaap_PropertyPlantAndEquipmentNet",
        # IFRS
        "ifrs-full:PropertyPlantAndEquipment",
        # Common textual
        "Property, plant and equipment, net",
        "Property and equipment, net",
        "PPE net",
    ],

    # ======================
    #   INTANGIBLE ASSETS
    # ======================
    "intangible_assets": [
        "Intangible assets",
        "us-gaap:IntangibleAssetsNetExcludingGoodwill",
        "us-gaap_IntangibleAssetsNetExcludingGoodwill",
        "FiniteLivedIntangibleAssetsNet",
        "us-gaap_FiniteLivedIntangibleAssetsGross",
        "Intangible assets, net",
        "Acquired intangible assets",
        # IFRS
        "ifrs-full:IntangibleAssets",
        # Common textual
        "Customer-related intangible assets",
        "Technology-based intangible assets",
        "Intellectual property",
        "Brand names",
        "Customer lists",
        "Patents",
        "Trademarks",
        "us-gaap:IntangibleAssetsFiniteLivedNet",
        "us-gaap:IntangibleAssetsIndefiniteLivedExcludingGoodwill",
        "Identifiable intangible assets",
    ],

    # ======================
    #       GOODWILL
    # ======================
    "goodwill": [
        "us-gaap:Goodwill",
        "us-gaap_Goodwill",
        # IFRS
        "ifrs-full:Goodwill",
        # Common textual
        "Goodwill",
    ],

    # ======================
    #  OTHER NON-CURRENT ASSETS
    # ======================
    "other_noncurrent_assets": [
        "us-gaap:AssetsNoncurrent",
        "us-gaap_AssetsNoncurrent",
        # IFRS
        "ifrs-full:NoncurrentAssets",
        # Common textual
        "Total non-current assets",
        "Other non-current assets",
        "Long-lived assets",
    ],

    # ======================
    #     TOTAL ASSETS
    # ======================
    "total_assets": [
        "us-gaap:Assets",
        "us-gaap_Assets",
        # IFRS
        "ifrs-full:Assets",
        # Common textual
        "Total assets",
    ],

    # ======================
    # ACCOUNTS PAYABLE
    # ======================
    "accounts_payable": [
        "us-gaap:AccountsPayableCurrent",
        "us-gaap_AccountsPayableCurrent",
        # IFRS
        "ifrs-full:TradeAndOtherPayables",
        # Common textual
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
        # IFRS
        "ifrs-full:AccrualsAndDeferredIncome",
        # Common textual
        "Accrued expenses",
        "Other accrued liabilities",
    ],

    # ======================
    #  CURRENT LIABILITIES
    # ======================
    "current_liabilities": [
        "us-gaap:LiabilitiesCurrent",
        "us-gaap_LiabilitiesCurrent",
        # IFRS
        "ifrs-full:CurrentLiabilities",
        # Common textual
        "Total current liabilities",
        "Liabilities, current",
    ],

    # ======================
    #   DEFERRED REVENUE
    # ======================
    "deferred_revenue": [
        "us-gaap:ContractWithCustomerLiabilityCurrent",
        "us-gaap_ContractWithCustomerLiabilityCurrent",
        # IFRS (see also "contract_liabilities" below)
        "ifrs-full:ContractLiabilitiesCurrent",
        # Common textual
        "Deferred revenue",
        "Unearned revenue",
        "Contract liability",
    ],

    # ======================
    #   SHORT-TERM DEBT
    # ======================
    "short_term_debt": [
        "us-gaap_CommercialPaper",
        "Commercial paper",
        "LineOfCreditFacility",
        # IFRS
        "ifrs-full:BorrowingsCurrent",
        # Common textual
        "Short-term debt",
    ],

    # ======================
    #   LONG-TERM DEBT
    # ======================
    "long_term_debt": [
        "us-gaap:LongTermDebt",
        "us-gaap_LongTermDebt",
        # IFRS
        "ifrs-full:BorrowingsNoncurrent",
        # Common textual
        "Term debt",
        "Notes payable",
        "Bond obligations",
    ],

    # ======================
    #   LEASE LIABILITIES
    # ======================
    "operating_lease_liabilities": [
        "us-gaap_OperatingLeaseLiability",
        # IFRS has broader "ifrs-full:LeaseLiabilities"
        "Operating lease liabilities",
    ],
    "finance_lease_liabilities": [
        "us-gaap_FinanceLeaseLiability",
        "Finance lease liabilities",
    ],

    # ======================
    #  OTHER LIABILITIES
    # ======================
    "other_noncurrent_liabilities": [
        "us-gaap_LiabilitiesNoncurrent",
        "us-gaap_OtherLiabilitiesNoncurrent",
        # IFRS
        "ifrs-full:NoncurrentLiabilities",
        # Common textual
        "Other non-current liabilities",
        "Total non-current liabilities",
    ],

    # ======================
    #  TOTAL LIABILITIES
    # ======================
    "total_liabilities": [
        "us-gaap:Liabilities",
        "us-gaap_Liabilities",
        # IFRS
        "ifrs-full:Liabilities",
        # Common textual
        "Total liabilities",
    ],

    # ======================
    #   STOCKHOLDERS’ EQUITY
    # ======================
    "total_equity": [
        "us-gaap:StockholdersEquity",
        "us-gaap_StockholdersEquity",
        # IFRS
        "ifrs-full:Equity",
        # Common textual
        "Total shareholders’ equity",
        "Equity",
        "Shareholders' equity",
    ],

    # ======================
    # COMMON STOCK & APIC
    # ======================
    "common_stock_and_apic": [
        "us-gaap_CommonStocksIncludingAdditionalPaidInCapital",
        "us-gaap_AdditionalPaidInCapital",
        # IFRS
        "ifrs-full:ShareCapital",
        "ifrs-full:SharePremium",
        # Common textual
        "Common stock and additional paid-in capital",
        "Additional paid-in capital",
    ],

    # ======================
    #    TREASURY STOCK
    # ======================
    "treasury_stock": [
        "us-gaap_TreasuryStockValue",
        # IFRS
        "ifrs-full:TreasuryShares",
        # Common textual
        "Treasury stock",
    ],

    # ======================
    #  RETAINED EARNINGS
    # ======================
    "retained_earnings": [
        "us-gaap_RetainedEarningsAccumulatedDeficit",
        # IFRS
        "ifrs-full:RetainedEarnings",
        # Common textual
        "Retained earnings",
        "Accumulated deficit",
    ],

    # ======================
    #  ACCUM. OTHER COMP. INC.
    # ======================
    "accumulated_oci": [
        "us-gaap_AccumulatedOtherComprehensiveIncomeLossNetOfTax",
        "us-gaap_OtherComprehensiveIncomeLossNetOfTax",
        # IFRS
        "ifrs-full:OtherReserves",
        # Common textual
        "Accumulated other comprehensive loss",
        "AOCI",
        "Other comprehensive income/loss",
    ],

    # ======================
    # COMPREHENSIVE INCOME
    # ======================
    "comprehensive_income": [
        "us-gaap:ComprehensiveIncomeNetOfTax",
        "us-gaap_ComprehensiveIncomeNetOfTax",
        # IFRS
        "ifrs-full:ComprehensiveIncome",
        # Common textual
        "Total comprehensive income",
        "Other comprehensive income, net of tax",
    ],

    # ======================
    #   CASH FLOW: OCF
    # ======================
    "cash_flow_operating": [
        "us-gaap:NetCashProvidedByUsedInOperatingActivities",
        "us-gaap_NetCashProvidedByUsedInOperatingActivities",
        # IFRS
        "ifrs-full:NetCashFlowsFromUsedInOperatingActivities",
        # Common textual
        "Cash from/(used in) operating activities",
        "Cash generated by operating activities",
    ],

    # ======================
    #  CASH FLOW: INVEST
    # ======================
    "cash_flow_investing": [
        "us-gaap:NetCashProvidedByUsedInInvestingActivities",
        "us-gaap_NetCashProvidedByUsedInInvestingActivities",
        # IFRS
        "ifrs-full:NetCashFlowsFromUsedInInvestingActivities",
        # Common textual
        "Cash from/(used in) investing activities",
        "Cash generated by/(used in) investing activities",
        "NetCashProvidedByUsedInInvestingActivities",
    ],

    # ======================
    #  CASH FLOW: FINANCE
    # ======================
    "cash_flow_financing": [
        "us-gaap:NetCashProvidedByUsedInFinancingActivities",
        "us-gaap_NetCashProvidedByUsedInFinancingActivities",
        # IFRS
        "ifrs-full:NetCashFlowsFromUsedInFinancingActivities",
        # Common textual
        "Cash from/(used in) financing activities",
        "Cash used in financing activities",
    ],

    # ======================
    # SHARE-BASED COMP
    # ======================
    "share_based_compensation": [
        "us-gaap_ShareBasedCompensation",
        "us-gaap_AllocatedShareBasedCompensationExpense",
        # IFRS
        "ifrs-full:ShareBasedPayment",
        # Common textual
        "Stock-based compensation expense",
        "Share-based compensation",
        "Equity compensation",
    ],

    # ======================
    #   DEFERRED TAXES
    # ======================
    "deferred_tax_assets": [
        "us-gaap_DeferredTaxAssetsGross",
        "us-gaap_DeferredTaxAssetsNet",
        # IFRS
        "ifrs-full:DeferredTaxAssets",
        # Common textual
        "Deferred tax assets",
        "DTA",
    ],
    "deferred_tax_liabilities": [
        "us-gaap_DeferredTaxLiabilities",
        "us-gaap_DeferredTaxLiabilitiesNet",
        # IFRS
        "ifrs-full:DeferredTaxLiabilities",
        # Common textual
        "DTL",
    ],

    # ======================
    #  UNRECOGNIZED TAX
    # ======================
    "unrecognized_tax_benefits": [
        "us-gaap_UnrecognizedTaxBenefits",
        "Unrecognized tax benefits",
        "Gross unrecognized tax benefits",
    ],

    # ======================
    #       DIVIDENDS
    # ======================
    "dividends": [
        "us-gaap_Dividends",
        "us-gaap_CommonStockDividendsPerShareDeclared",
        # IFRS
        "ifrs-full:DividendsPaid",
        # Common textual
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
        # IFRS
        "ifrs-full:PaymentsForRepurchaseOfEquityInstruments",
        # Common textual
        "Repurchases of common stock",
        "Stock repurchased and retired",
    ],

    # ======================
    #   BUSINESS COMBOS (M&A)
    # ======================
    "business_combinations": [
        "us-gaap_BusinessCombinationsPolicy",
        "us-gaap_BusinessCombinationDisclosureTextBlock",
        # IFRS
        "ifrs-full:BusinessCombinations",
        # Common textual
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
        # IFRS
        "ifrs-full:Leases",
        # Common textual
        "Leases (general disclosures)",
    ],

    # ======================
    # DERIVATIVES & HEDGES
    # ======================
    "derivatives_hedging": [
        "us-gaap_DerivativeInstrumentsAndHedgingActivitiesDisclosureTextBlock",
        "us-gaap_DerivativeAssetFairValueGrossAssetIncludingNotSubjectToMasterNettingArrangement",
        # IFRS
        "ifrs-full:DerivativeFinancialInstruments",
        # Common textual
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
        # IFRS
        "ifrs-full:FairValueMeasurement",
        # Common textual
        "Fair Value Measurements",
    ],

    # ======================
    #  SEGMENT REPORTING
    # ======================
    "segment_reporting": [
        "us-gaap_SegmentReportingPolicyPolicyTextBlock",
        "us-gaap_SegmentReportingDisclosureTextBlock",
        # IFRS
        "ifrs-full:SegmentReporting",
        # Common textual
        "Segment revenue",
        "Segment operating income",
    ],

    # ======================
    #  COMMITMENTS & CONTINGENCIES
    # ======================
    "commitments_contingencies": [
        "us-gaap_CommitmentsAndContingencies",
        "us-gaap_CommitmentsAndContingenciesDisclosureTextBlock",
        # IFRS
        "ifrs-full:ContingentLiabilities",
        # Common textual
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
    #     RISK FACTORS
    # ======================
    "risk_factors": [
        "Risk Factors",
        "Item 1A. Risk Factors",
        "Business risk, M&A risk, supply chain risk, etc.",
    ],

    # ======================
    #  INSIDER TRADING
    # ======================
    "insider_transactions": [
        "ecd_TrdArrIndName",
        "ecd_TrdArrIndTitle",
        "Insider trading arrangement",
        "Rule 10b5-1 arrangement",
        "InsiderTrdPoliciesProcAdoptedFlag",
    ],

    # ======================
    # RECENT ACCOUNTING PRONOUNCEMENTS
    # ======================
    "recent_accounting_guidance": [
        "us-gaap_NewAccountingPronouncementsPolicyPolicyTextBlock",
        "kltr_RecentAccountingGuidanceNotYetAdoptedPolicyTextBlock",
        # IFRS
        "ifrs-full:StandardsIssuedButNotYetEffective",
        # Common textual
        "Recent accounting guidance",
        "Pronouncements not yet adopted",
    ],

    # ======================
    # CAPITAL EXPENDITURES
    # ======================
    "capital_expenditures": [
        "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
        "us-gaap_PaymentsToAcquirePropertyPlantAndEquipment",
        # IFRS
        "ifrs-full:AcquisitionsOfPropertyPlantAndEquipment",
        # Common textual
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
        "Purchase of property, plant, and equipment",
    ],

    # ======================
    #   RIGHT-OF-USE ASSETS
    # ======================
    "right_of_use_assets": [
        "ifrs-full:RightOfUseAssets",
        "us-gaap:OperatingLeaseRightOfUseAsset",
        "Right-of-use assets",
        "Lease assets",
    ],

    # ======================
    #    LEASE LIABILITIES
    # ======================
    "lease_liabilities_current": [
        "ifrs-full:LeaseLiabilitiesCurrent",
        "us-gaap:OperatingLeaseLiabilityCurrent",
        "Lease liabilities, current",
        "Operating lease liability, current",
    ],
    "lease_liabilities_noncurrent": [
        "ifrs-full:LeaseLiabilitiesNoncurrent",
        "us-gaap:OperatingLeaseLiabilityNoncurrent",
        "Lease liabilities, non-current",
        "Operating lease liability, non-current",
    ],

    # ======================
    #  FINANCIAL INSTRUMENTS
    # ======================
    "financial_assets_fvpl": [
        "ifrs-full:FinancialAssetsAtFairValueThroughProfitOrLoss",
        "us-gaap:MarketableSecuritiesCurrent",
        "Financial assets at fair value through profit or loss",
        "Financial instruments (FVPL)",
    ],
    "financial_assets_fvoci": [
        "ifrs-full:FinancialAssetsAtFairValueThroughOtherComprehensiveIncome",
        "us-gaap:AvailableForSaleSecuritiesCurrent",
        "Financial assets at fair value through other comprehensive income",
        "Financial instruments (FVOCI)",
    ],

    # ======================
    #   GAINS OR LOSSES IN OCI
    # ======================
    "gains_losses_oci": [
        "ifrs-full:OtherComprehensiveIncome",
        "us-gaap:OtherComprehensiveIncomeLossNetOfTax",
        "Gains or losses in other comprehensive income",
        "OCI items",
    ],

    # ======================
    # CONTRACT ASSETS / LIABILITIES
    # ======================
    "contract_assets": [
        "ifrs-full:ContractAssets",
        "us-gaap:ContractWithCustomerAsset",
        "Contract assets",
        "Unbilled receivables",
    ],
    "contract_liabilities": [
        "ifrs-full:ContractLiabilities",
        "us-gaap:ContractWithCustomerLiability",
        "Deferred income including contract liabilities",
        "Contract liabilities",
    ],

    # ======================
    # INTEREST EXPENSE / COVERAGE
    # ======================
    "interest_expense": [
        "us-gaap:InterestExpense",
        "us-gaap_InterestExpense",
        "ifrs-full:FinanceCosts",
        "ifrs-full:InterestExpense",
        "Interest Expense",
        "Finance costs",
        "Interest and debt expense",
    ],

    # ======================
    #   REFINED CAPEX-RELATED
    # ======================
    "purchase_of_intangibles": [
        "us-gaap:PaymentsToAcquireIntangibleAssets",
        "us-gaap_PaymentsToAcquireIntangibleAssets",
        # IFRS
        "ifrs-full:AcquisitionsOfIntangibleAssets",
        # Common textual
        "Purchase of intangible assets",
        "Payments to acquire intangible assets",
        "Additions to intangible assets",
        "PaymentsToAcquireIntangibleAssets",
    ],
    "business_acquisitions_net": [
        "us-gaap:PaymentsToAcquireBusinessesNetOfCashAcquired",
        "us-gaap_PaymentsToAcquireBusinessesNetOfCashAcquired",
        # IFRS
        "ifrs-full:BusinessCombinationsNetOfCashAcquired",
        # Common textual
        "Acquisitions (net of cash acquired)",
        "Acquisition of business net of cash acquired",
        "Purchase of business net of cash acquired",
        "PaymentsToAcquireBusinessesNetOfCashAcquired",
    ],

    # ======================
    #      MISCELLANEOUS
    # ======================
    "miscellaneous": [
        "BasisOfAccountingPolicyPolicyTextBlock",
        "BasisOfPresentationAndSignificantAccountingPoliciesTextBlock",
        "ConsolidationPolicyTextBlock",
        "ForeignCurrencyTransactionsAndTranslationsPolicyTextBlock",
        "NatureOfOperationsPolicyPolicyTextBlock",
        "srt_CondensedFinancialStatementsTextBlock",
        "us-gaap_SignificantAccountingPoliciesTextBlock",
        # IFRS (example of general info)
        "ifrs-full:GeneralInformationAboutFinancialStatements",
    ],

}
