"""系统使用的固定选项，集中管理便于后续维护。"""

STAGES = [
    "New Lead",
    "Contacted",
    "Replied",
    "Requirement Confirmed",
    "Quoted",
    "Sample",
    "Negotiation",
    "Order Confirmed",
    "Lost",
]

LEAD_GRADES = ["A", "B", "C", "D"]

LEAD_SOURCES = [
    "Trade Show",
    "B2B Platform",
    "Website",
    "Referral",
    "LinkedIn",
    "Marketplace",
    "Cold Outreach",
    "Social Media",
    "Outbound Research",
    "Other",
]

IMPORT_FREQUENCIES = [
    "Unknown",
    "One-time",
    "Annual",
    "Biannual",
    "Quarterly",
    "Monthly",
    "Weekly",
]

PRICING_METHODS = {
    "gross_margin": "Gross Margin",
    "markup": "Markup",
}

INCOTERM_DESCRIPTIONS = {
    "EXW": "Product + packaging + platform/bank fee",
    "FOB": "EXW + domestic transportation + export handling",
    "CIF": "FOB + international freight + insurance",
    "DDP": "CIF + tariff and tax",
}
