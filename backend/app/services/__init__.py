# Business Logic Services

from app.services.dart_api import (
    # Core
    get_corp_code,
    get_major_shareholders,
    verify_shareholders,
    get_verified_shareholders,
    initialize_dart_client,
    load_corp_codes,
    Shareholder,
    VerificationResult,
    # P0: Fact-Based
    get_company_info,
    get_company_info_by_name,
    get_largest_shareholders,
    get_largest_shareholders_by_name,
    get_fact_based_profile,
    CompanyInfo,
    LargestShareholder,
    FactBasedProfileData,
    # P2: Financial Statements
    get_financial_statements,
    get_financial_statements_by_name,
    FinancialStatement,
    # P3: Major Events
    get_major_events,
    get_major_events_by_name,
    MajorEvent,
    MajorEventType,
    # P4: Executives
    get_executives,
    get_executives_by_name,
    Executive,
    # Extended Profile
    get_extended_fact_profile,
    ExtendedFactProfile,
)

__all__ = [
    # Core
    "get_corp_code",
    "get_major_shareholders",
    "verify_shareholders",
    "get_verified_shareholders",
    "initialize_dart_client",
    "load_corp_codes",
    "Shareholder",
    "VerificationResult",
    # P0: Fact-Based
    "get_company_info",
    "get_company_info_by_name",
    "get_largest_shareholders",
    "get_largest_shareholders_by_name",
    "get_fact_based_profile",
    "CompanyInfo",
    "LargestShareholder",
    "FactBasedProfileData",
    # P2: Financial Statements
    "get_financial_statements",
    "get_financial_statements_by_name",
    "FinancialStatement",
    # P3: Major Events
    "get_major_events",
    "get_major_events_by_name",
    "MajorEvent",
    "MajorEventType",
    # P4: Executives
    "get_executives",
    "get_executives_by_name",
    "Executive",
    # Extended Profile
    "get_extended_fact_profile",
    "ExtendedFactProfile",
]
