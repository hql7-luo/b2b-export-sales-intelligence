"""Fictional creative-printing demo data for portfolio use."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from database.connection import get_connection
from database.init_db import initialize_database
from database.repository import create_customer, update_customer
from services.quotation import calculate_quotation


# All names, contacts, domains, amounts, and costs below are synthetic.
DEMO_CUSTOMERS = [
    ("Northstar Paper Boutique", "Mira Solen", "Canada", "mira@northstar-paper.example.com", "Custom notebooks", "Quarterly", 18000, "Requirement Confirmed", "Referral"),
    ("Fable Harbor Studio", "Theo Marin", "United States", "theo@fable-harbor.example.com", "Festival gift boxes", "Monthly", 32000, "Quoted", "Trade Show"),
    ("Juniper Moon Retail", "Elara Quinn", "United Kingdom", "elara@juniper-moon.example.com", "Greeting card sets", "Quarterly", 12000, "Replied", "Website"),
    ("Canvas Kite Concepts", "Niko Vale", "Australia", "niko@canvas-kite.example.com", "Creative packaging boxes", "Biannual", 9000, "Contacted", "LinkedIn"),
    ("Lumen Leaf Mercantile", "Aya Fen", "Singapore", "aya@lumen-leaf.example.com", "Desk calendars", "Annual", 7500, "Sample", "Marketplace"),
    ("Paper Comet Collective", "Owen Rill", "Germany", "owen@paper-comet.example.com", "Die-cut sticker packs", "Monthly", 26000, "Negotiation", "Trade Show"),
    ("Wildmint Gift House", "Sofia Dune", "France", "sofia@wildmint-gift.example.com", "Custom rigid gift boxes", "Quarterly", 21000, "Quoted", "Cold Outreach"),
    ("Orbit & Ink Market", "Luca Venn", "Italy", "luca@orbit-ink.example.com", "Recycled paper notebooks", "Biannual", 11000, "Requirement Confirmed", "Website"),
    ("Amber Finch Goods", "Iris Morrow", "Netherlands", "iris@amber-finch.example.com", "Holiday greeting cards", "Annual", 6200, "New Lead", "Referral"),
    ("Pebble Sky Trading", "Jae Rowan", "South Korea", "jae@pebble-sky.example.com", "Foil-stamped packaging boxes", "Quarterly", 24000, "Replied", "Marketplace"),
    ("Mosaic Fern Stores", "Amara Lark", "United Arab Emirates", "amara@mosaic-fern.example.com", "Premium gift box sets", "Monthly", 42000, "Negotiation", "Trade Show"),
    ("Cobalt Nest Design", "Noah Ember", "New Zealand", "noah@cobalt-nest.example.com", "Custom wall calendars", "Annual", 8200, "Contacted", "LinkedIn"),
    ("Silver Acorn Retail", "Lina Crest", "Sweden", "lina@silver-acorn.example.com", "Eco sticker sheets", "Quarterly", 13800, "Sample", "Website"),
    ("Tideglass Stationery", "Evan Moss", "Spain", "evan@tideglass.example.com", "Linen cover notebooks", "Monthly", 29500, "Quoted", "Cold Outreach"),
    ("Pine Halo Concepts", "Zara Bly", "Japan", "zara@pine-halo.example.com", "Minimal greeting card sets", "Biannual", 10500, "Requirement Confirmed", "Referral"),
    ("Velvet Atlas Gifts", "Milo Arden", "Belgium", "milo@velvet-atlas.example.com", "Magnetic closure gift boxes", "Quarterly", 22500, "Replied", "Trade Show"),
    ("Sunward Craft Supply", "Tara Wren", "Chile", "tara@sunward-craft.example.com", "Planner sticker packs", "Annual", 5800, "New Lead", "Marketplace"),
    ("Cloudberry Paper Co", "Remy Lake", "Denmark", "remy@cloudberry-paper.example.com", "Weekly planner notebooks", "Quarterly", 16800, "Contacted", "Website"),
    ("Copper Bloom Bazaar", "Nia Frost", "South Africa", "nia@copper-bloom.example.com", "Seasonal desk calendars", "Biannual", 9700, "Quoted", "LinkedIn"),
    ("Dawn Parcel Studio", "Kian Grove", "Mexico", "kian@dawn-parcel.example.com", "E-commerce mailer boxes", "Monthly", 36000, "Order Confirmed", "Referral"),
]

def _demo_customer_payload(index: int, customer: tuple[Any, ...]) -> dict[str, Any]:
    """Build varied but rule-scoreable fictional profiles for every grade band."""
    company, contact, country, email, interest, frequency, volume, stage, source = customer
    payload = {
        "company_name": company,
        "contact_name": contact,
        "job_title": "Sourcing Coordinator",
        "country": country,
        "website": "",
        "email": email,
        "phone": "",
        "lead_source": source,
        "product_interest": interest,
        "import_frequency": frequency,
        "estimated_purchase_volume": volume,
        "last_contact_date": "",
        "next_follow_up_date": f"2026-07-{(index % 10) + 16:02d}",
        "current_stage": stage,
        "notes": "Entirely fictional portfolio demonstration record.",
    }
    if index <= 2:
        payload.update(
            website=f"https://demo-customer-{index}.example.com",
            phone=f"+00 555 01{index:02d}",
            last_contact_date=f"2026-07-{(index % 15) + 1:02d}",
        )
    elif index <= 7:
        payload["current_stage"] = "Replied"
    elif index == 8:
        payload.update(
            import_frequency="Quarterly",
            estimated_purchase_volume=18000,
            current_stage="Order Confirmed",
        )
    elif index <= 13:
        payload.update(
            import_frequency="Annual",
            estimated_purchase_volume=3000,
            current_stage="New Lead",
        )
    else:
        payload.update(
            import_frequency="",
            estimated_purchase_volume=0,
            current_stage="New Lead",
        )
    return payload

DEMO_PRODUCTS = [
    ("Aurora Custom Notebook", "Notebook", "Corporate gifts and retail stationery", "FSC paper, PU or linen cover", "A5, 160 pages, custom logo", 500, "5-7 days", "20-25 days", "Individual paper sleeve", 13.80, "Can paper and binding be customized?", "Low MOQ; FSC options; foil stamping", "Synthetic demo cost"),
    ("Starlight Festival Gift Box", "Gift Box", "Holiday gifts and product bundles", "Rigid greyboard with art paper", "250 x 180 x 80 mm, magnetic closure", 1000, "7-9 days", "25-30 days", "Export carton with corner protection", 18.60, "Can inserts be customized?", "Premium finish; custom inserts; recyclable board", "Synthetic demo cost"),
    ("Meadow Greeting Card Set", "Greeting Card", "Seasonal and everyday greetings", "350 gsm coated or recycled card", "A6 folded, six designs with envelopes", 1000, "4-6 days", "15-20 days", "Six-card paper band set", 5.40, "Are envelopes and foil details included?", "Coordinated sets; soy ink option; foil accents", "Synthetic demo cost"),
    ("Orbit Creative Packaging Box", "Packaging Box", "Retail and e-commerce packaging", "E-flute corrugated board", "Custom dieline, CMYK exterior", 1500, "5-7 days", "18-24 days", "Flat packed in export cartons", 7.90, "Can you provide structural samples?", "Flat-pack freight saving; flexible print; sturdy structure", "Synthetic demo cost"),
    ("Harbor Desk Calendar", "Calendar", "Office gifts and retail planning", "250 gsm card with metal wire", "210 x 150 mm, 13 sheets", 800, "5-7 days", "18-22 days", "Shrink-free paper wrap", 9.20, "Can holidays vary by market?", "Localized dates; stable base; plastic-free packing", "Synthetic demo cost"),
    ("Comet Die-cut Sticker Pack", "Sticker", "Planner decoration and brand promotion", "Matte vinyl or coated paper", "10 custom shapes, 60-80 mm", 2000, "3-5 days", "12-16 days", "Ten-piece recyclable pouch", 2.30, "Are stickers waterproof and removable?", "Precise die cutting; multiple materials; vivid color", "Synthetic demo cost"),
]

DEMO_INQUIRIES = [
    (1, "We need 2,000 A5 recycled-paper notebooks with gold foil logos for Toronto by 15 October. Please quote samples and 30% deposit terms.", "Custom notebooks", "A5, recycled paper, gold foil logo", "2000", "Retail stationery", "Gold foil logo", None, "Toronto, Canada", "2026-10-15", None, "Required", "30% deposit"),
    (2, "Please quote 3,000 rigid Christmas gift boxes, magnetic closure and red paper insert, delivery to Seattle in September.", "Festival gift boxes", "Rigid box with magnetic closure", "3000", "Christmas gift bundles", "Red paper insert", "Export cartons", "Seattle, USA", "2026-09", None, None, None),
    (3, "Interested in 5,000 six-card greeting sets using soy ink. Destination Felixstowe. Target below USD 1.50 per set.", "Greeting card sets", "Six cards, soy ink", "5000", "Retail", None, "Card set with envelopes", "Felixstowe, UK", None, "USD 1.50/set", None, None),
    (4, "Could you make 10,000 CMYK mailer boxes using an existing dieline? Need flat packing to Melbourne and a structural sample.", "Creative packaging boxes", "CMYK custom dieline", "10000", "E-commerce shipping", "Existing dieline", "Flat packed", "Melbourne, Australia", None, None, "Structural sample", None),
    (5, "We are sourcing 1,500 localized 2027 desk calendars for Singapore offices, individual paper sleeves, arrival before November.", "Desk calendars", "Localized 2027 calendar", "1500", "Corporate gifts", "Localized holidays", "Paper sleeve", "Singapore", "Before 2026-11", None, None, None),
    (6, "Monthly order estimate is 20,000 waterproof die-cut stickers. Ten designs per pouch. Please advise MOQ and lead time.", "Die-cut sticker packs", "Waterproof, ten designs", "20000/month", "Retail planners", "Custom shapes", "Ten-piece pouch", None, None, None, None, None),
    (7, "Need 2,500 premium magnetic gift boxes with molded pulp inserts for a Paris launch. Can you send a blank sample next week?", "Premium gift boxes", "Magnetic closure, molded pulp insert", "2500", "Product launch", "Molded pulp insert", None, "Paris, France", None, None, "Blank sample", None),
    (8, "We would like pricing for 4,000 A5 linen notebooks, 192 pages, embossed logo, shipped FOB. Payment by T/T.", "Linen cover notebooks", "A5, 192 pages, linen cover", "4000", "Boutique retail", "Embossed logo", None, None, None, None, None, "T/T"),
    (9, "RFQ: 8,000 foil greeting cards, four designs, envelopes included, delivery Rotterdam, sample approval required.", "Holiday greeting cards", "Four foil designs with envelopes", "8000", "Holiday retail", "Four custom designs", "Envelopes included", "Rotterdam, Netherlands", None, None, "Approval sample", None),
    (10, "Please provide DDP Dubai pricing for 6,000 luxury gift boxes, black soft-touch finish and gold logo. Required in 45 days.", "Luxury gift boxes", "Soft-touch black finish", "6000", "Premium retail", "Gold logo", None, "Dubai, UAE", "45 days", None, None, None),
]

# Input assumptions only. Stored outputs are always generated by the calculator.
DEMO_QUOTATION_INPUTS = [
    (1, "Aurora Custom Notebook", "FOB", 2000, 13.8, 1.2, 850, 1200, 0, 0, 0, 160, 7.2, "gross_margin", 0.25, "2026-08-15", 500, "25 days", "30% deposit, balance before shipment"),
    (2, "Starlight Festival Gift Box", "CIF", 3000, 18.6, 1.5, 1100, 1450, 7800, 550, 0, 240, 7.2, "gross_margin", 0.28, "2026-08-20", 1000, "30 days", "30% deposit, 70% before shipment"),
    (3, "Meadow Greeting Card Set", "FOB", 5000, 5.4, 0.4, 900, 1250, 0, 0, 0, 180, 7.2, "markup", 0.22, "2026-08-10", 1000, "20 days", "T/T"),
    (4, "Orbit Creative Packaging Box", "CIF", 10000, 7.9, 0.35, 1800, 2100, 14500, 900, 0, 420, 7.2, "gross_margin", 0.2, "2026-08-25", 1500, "24 days", "30% deposit"),
    (5, "Harbor Desk Calendar", "EXW", 1500, 9.2, 0.6, 0, 0, 0, 0, 0, 90, 7.2, "gross_margin", 0.25, "2026-09-01", 800, "22 days", "T/T"),
    (6, "Comet Die-cut Sticker Pack", "DDP", 20000, 2.3, 0.2, 1600, 1200, 9600, 620, 6800, 310, 7.2, "markup", 0.18, "2026-08-18", 2000, "18 days", "Monthly settlement after first order"),
    (7, "Starlight Festival Gift Box", "FOB", 2500, 18.6, 1.7, 980, 1320, 0, 0, 0, 210, 7.2, "gross_margin", 0.3, "2026-08-22", 1000, "30 days", "30% deposit"),
    (8, "Aurora Custom Notebook", "CIF", 4000, 14.6, 1.1, 1250, 1550, 6200, 430, 0, 260, 7.2, "gross_margin", 0.24, "2026-08-30", 500, "28 days", "T/T"),
]

DEMO_FOLLOW_UPS = [
    (1, "2026-07-12", "Email", "Confirmed paper weight and foil artwork format.", "Specification confirmed", "2026-07-14", "High"),
    (2, "2026-07-12", "Video Call", "Reviewed insert structure and holiday delivery window.", "Quotation requested", "2026-07-15", "High"),
    (3, "2026-07-12", "Email", "Asked whether envelopes require printed liners.", "Awaiting clarification", "2026-07-19", "Medium"),
    (4, "2026-07-11", "Chat", "Shared flat-pack structural sample photos.", "Sample requested", "2026-07-16", "High"),
    (5, "2026-07-10", "Email", "Sent calendar holiday localization checklist.", "Customer reviewing", "2026-07-20", "Medium"),
    (6, "2026-07-15", "Chat", "Discussed waterproof vinyl option and pouch label.", "Price negotiation", "2026-07-17", "High"),
    (7, "2026-07-09", "Email", "Offered molded pulp insert prototype timeline.", "Sample address received", "2026-07-18", "Medium"),
    (8, "2026-07-08", "Email", "Provided linen swatch choices and embossing limits.", "Artwork pending", "2026-07-21", "Medium"),
    (9, "2026-07-07", "Chat", "Clarified four-design quantity split.", "Customer replied", "2026-07-16", "High"),
    (10, "2026-07-15", "Video Call", "Reviewed DDP cost assumptions and delivery address.", "Commercial review", "2026-07-18", "High"),
]

DEMO_INQUIRY_PRODUCT_NAMES = (
    "Aurora Custom Notebook",
    "Starlight Festival Gift Box",
    "Meadow Greeting Card Set",
    "Orbit Creative Packaging Box",
    "Harbor Desk Calendar",
    "Comet Die-cut Sticker Pack",
    "Starlight Festival Gift Box",
    "Aurora Custom Notebook",
    "Meadow Greeting Card Set",
    "Starlight Festival Gift Box",
)


def _insert_products(connection: Any) -> dict[str, int]:
    product_ids: dict[str, int] = {}
    columns = (
        "product_name",
        "category",
        "application",
        "material",
        "specification",
        "moq",
        "sample_lead_time",
        "production_lead_time",
        "packaging",
        "unit_cost",
        "common_customer_questions",
        "selling_points",
        "notes",
    )
    for product in DEMO_PRODUCTS:
        existing = connection.execute(
            "SELECT id FROM products WHERE product_name = ?",
            (product[0],),
        ).fetchone()
        if existing:
            assignments = ", ".join(f"{column} = ?" for column in columns[1:])
            connection.execute(
                f"UPDATE products SET {assignments}, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (*product[1:], existing["id"]),
            )
            product_id = int(existing["id"])
        else:
            cursor = connection.execute(
                f"INSERT INTO products ({', '.join(columns)}) "
                f"VALUES ({', '.join('?' for _ in columns)})",
                product,
            )
            product_id = int(cursor.lastrowid)
        product_ids[product[0]] = product_id
    return product_ids


def _replace_activity(
    connection: Any,
    *,
    customer_id: int,
    inquiry_id: int | None,
    quotation_id: int | None,
    activity_type: str,
    description: str,
    metadata: dict[str, Any],
) -> None:
    connection.execute(
        "DELETE FROM activities WHERE customer_id = ? "
        "AND inquiry_id IS ? AND quotation_id IS ? AND activity_type = ?",
        (customer_id, inquiry_id, quotation_id, activity_type),
    )
    connection.execute(
        "INSERT INTO activities "
        "(customer_id, inquiry_id, quotation_id, activity_type, "
        "description, metadata) VALUES (?, ?, ?, ?, ?, ?)",
        (
            customer_id,
            inquiry_id,
            quotation_id,
            activity_type,
            description,
            json.dumps(metadata),
        ),
    )


def _insert_inquiries(
    connection: Any,
    customer_ids: dict[str, int],
    product_ids: dict[str, int],
) -> dict[int, int]:
    inquiry_ids: dict[int, int] = {}
    for customer_number, inquiry in enumerate(DEMO_INQUIRIES, start=1):
        customer_id = customer_ids[DEMO_CUSTOMERS[customer_number - 1][0]]
        product_id = product_ids[DEMO_INQUIRY_PRODUCT_NAMES[customer_number - 1]]
        extracted = {
            "product": inquiry[2],
            "specification": inquiry[3],
            "quantity": inquiry[4],
            "application": inquiry[5],
            "customization_requirement": inquiry[6],
            "packaging_requirement": inquiry[7],
            "destination": inquiry[8],
            "required_delivery_time": inquiry[9],
            "target_price": inquiry[10],
            "sample_requirement": inquiry[11],
            "payment_requirement": inquiry[12],
        }
        confirmed = [key for key, value in extracted.items() if value]
        missing = [key for key, value in extracted.items() if not value]
        score = round(len(confirmed) / len(extracted) * 100)
        analysis = {
            "extracted_fields": extracted,
            "confirmed_info": confirmed,
            "missing_info": missing,
            "risks": [],
            "next_questions": [f"Please confirm {field.replace('_', ' ')}." for field in missing],
            "completeness_score": score,
            "suggested_reply": "Thank you for your inquiry. We will review the details and confirm the remaining points.",
        }
        values = (
            customer_id,
            product_id,
            inquiry[1],
            *inquiry[2:],
            json.dumps(confirmed),
            json.dumps(missing),
            json.dumps([]),
            json.dumps(analysis["next_questions"]),
            score,
            analysis["suggested_reply"],
            "rule",
            json.dumps(analysis),
        )
        existing = connection.execute(
            "SELECT id FROM inquiries WHERE raw_text = ?",
            (inquiry[1],),
        ).fetchone()
        columns = (
            "customer_id",
            "matched_product_id",
            "raw_text",
            "product",
            "specification",
            "quantity",
            "application",
            "customization_requirement",
            "packaging_requirement",
            "destination",
            "required_delivery_time",
            "target_price",
            "sample_requirement",
            "payment_requirement",
            "confirmed_info",
            "missing_info",
            "risks",
            "next_questions",
            "completeness_score",
            "suggested_reply",
            "analysis_mode",
            "analysis_json",
        )
        if existing:
            assignments = ", ".join(f"{column} = ?" for column in columns)
            connection.execute(
                f"UPDATE inquiries SET {assignments} WHERE id = ?",
                (*values, existing["id"]),
            )
            inquiry_id = int(existing["id"])
        else:
            cursor = connection.execute(
                f"INSERT INTO inquiries ({', '.join(columns)}) "
                f"VALUES ({', '.join('?' for _ in columns)})",
                values,
            )
            inquiry_id = int(cursor.lastrowid)
        inquiry_ids[customer_number] = inquiry_id
        _replace_activity(
            connection,
            customer_id=customer_id,
            inquiry_id=inquiry_id,
            quotation_id=None,
            activity_type="inquiry_created",
            description="Fictional demo inquiry created",
            metadata={"inquiry_id": inquiry_id},
        )
        _replace_activity(
            connection,
            customer_id=customer_id,
            inquiry_id=inquiry_id,
            quotation_id=None,
            activity_type="product_matched",
            description="Fictional demo product matched",
            metadata={"product_id": product_id},
        )
    return inquiry_ids


def _insert_quotations(
    connection: Any,
    customer_ids: dict[str, int],
    product_ids: dict[str, int],
    inquiry_ids: dict[int, int],
) -> dict[int, int]:
    quotation_ids: dict[int, int] = {}
    for scenario in DEMO_QUOTATION_INPUTS:
        (
            customer_number,
            product_name,
            incoterm,
            quantity,
            unit_cost,
            packaging,
            domestic,
            handling,
            freight,
            insurance,
            tariff_tax,
            fee,
            exchange_rate,
            pricing_method,
            pricing_rate,
            valid_until,
            moq,
            lead_time,
            payment_terms,
        ) = scenario
        customer_id = customer_ids[DEMO_CUSTOMERS[customer_number - 1][0]]
        product_id = product_ids[product_name]
        inquiry_id = inquiry_ids[customer_number]
        inquiry = DEMO_INQUIRIES[customer_number - 1]
        result = calculate_quotation(
            product_unit_cost_cny=unit_cost,
            packaging_unit_cost_cny=packaging,
            quantity=quantity,
            domestic_transport_cny=domestic,
            export_handling_cny=handling,
            international_freight_cny=freight,
            insurance_cny=insurance,
            tariff_tax_cny=tariff_tax,
            platform_bank_fee_cny=fee,
            exchange_rate_cny_per_usd=exchange_rate,
            pricing_method=pricing_method,
            pricing_rate=pricing_rate,
        )
        term = result["terms"][incoterm]
        values = (
            customer_id,
            inquiry_id,
            product_id,
            product_name,
            inquiry[3],
            inquiry[8],
            incoterm,
            quantity,
            unit_cost,
            packaging,
            domestic,
            handling,
            freight,
            insurance,
            tariff_tax,
            fee,
            exchange_rate,
            pricing_method,
            pricing_rate,
            float(term["cost_total_cny"]),
            float(term["unit_usd"]),
            float(term["total_usd"]),
            float(term["gross_profit_usd"]),
            float(term["gross_margin"]),
            valid_until,
            moq,
            lead_time,
            payment_terms,
            json.dumps(result, default=str),
        )
        columns = (
            "customer_id",
            "inquiry_id",
            "product_id",
            "product_name",
            "specification",
            "destination",
            "incoterm",
            "quantity",
            "unit_product_cost",
            "packaging_cost",
            "domestic_transportation_cost",
            "export_handling_cost",
            "international_freight",
            "insurance_cost",
            "tariff_and_tax",
            "platform_or_bank_fee",
            "exchange_rate",
            "pricing_method",
            "pricing_rate",
            "total_cost_cny",
            "unit_quote_usd",
            "total_quote_usd",
            "gross_profit_usd",
            "gross_margin",
            "valid_until",
            "moq",
            "lead_time",
            "payment_terms",
            "calculation_json",
        )
        existing = connection.execute(
            "SELECT id FROM quotations WHERE customer_id = ? "
            "AND product_name = ? AND incoterm = ? AND quantity = ? "
            "AND valid_until = ?",
            (customer_id, product_name, incoterm, quantity, valid_until),
        ).fetchone()
        if existing:
            assignments = ", ".join(f"{column} = ?" for column in columns)
            connection.execute(
                f"UPDATE quotations SET {assignments} WHERE id = ?",
                (*values, existing["id"]),
            )
            quotation_id = int(existing["id"])
        else:
            cursor = connection.execute(
                f"INSERT INTO quotations ({', '.join(columns)}) "
                f"VALUES ({', '.join('?' for _ in columns)})",
                values,
            )
            quotation_id = int(cursor.lastrowid)
        quotation_ids[customer_number] = quotation_id
        _replace_activity(
            connection,
            customer_id=customer_id,
            inquiry_id=inquiry_id,
            quotation_id=quotation_id,
            activity_type="quotation_created",
            description=f"Fictional {incoterm} quotation created",
            metadata={
                "quotation_id": quotation_id,
                "product_id": product_id,
            },
        )
    return quotation_ids


def _insert_follow_ups(
    connection: Any,
    customer_ids: dict[str, int],
    inquiry_ids: dict[int, int],
    quotation_ids: dict[int, int],
) -> None:
    for follow_up in DEMO_FOLLOW_UPS:
        (
            customer_number,
            follow_up_date,
            communication_type,
            content,
            outcome,
            next_follow_up_date,
            priority,
        ) = follow_up
        customer_id = customer_ids[DEMO_CUSTOMERS[customer_number - 1][0]]
        inquiry_id = inquiry_ids[customer_number]
        quotation_id = quotation_ids.get(customer_number)
        stage = connection.execute(
            "SELECT current_stage FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()["current_stage"]
        values = (
            customer_id,
            inquiry_id,
            quotation_id,
            stage,
            follow_up_date,
            communication_type,
            content,
            outcome,
            next_follow_up_date,
            priority,
        )
        existing = connection.execute(
            "SELECT id FROM follow_ups WHERE customer_id = ? "
            "AND follow_up_date = ? AND content = ?",
            (customer_id, follow_up_date, content),
        ).fetchone()
        columns = (
            "customer_id",
            "inquiry_id",
            "quotation_id",
            "customer_stage",
            "follow_up_date",
            "communication_type",
            "content",
            "outcome",
            "next_follow_up_date",
            "priority",
        )
        if existing:
            assignments = ", ".join(f"{column} = ?" for column in columns)
            connection.execute(
                f"UPDATE follow_ups SET {assignments} WHERE id = ?",
                (*values, existing["id"]),
            )
            follow_up_id = int(existing["id"])
        else:
            cursor = connection.execute(
                f"INSERT INTO follow_ups ({', '.join(columns)}) "
                f"VALUES ({', '.join('?' for _ in columns)})",
                values,
            )
            follow_up_id = int(cursor.lastrowid)
        _replace_activity(
            connection,
            customer_id=customer_id,
            inquiry_id=inquiry_id,
            quotation_id=quotation_id,
            activity_type="follow_up_scheduled",
            description=content,
            metadata={
                "follow_up_id": follow_up_id,
                "follow_up_date": follow_up_date,
                "next_follow_up_date": next_follow_up_date,
                "outcome": outcome,
            },
        )


def seed_demo_data(db_path: str | Path | None = None) -> dict[str, int]:
    """Seed the portfolio database once and return visible table counts."""
    initialize_database(db_path)
    existing_customers: dict[str, int]
    connection = get_connection(db_path)
    try:
        existing_customers = {
            row["company_name"]: row["id"]
            for row in connection.execute("SELECT id, company_name FROM customers").fetchall()
        }
    finally:
        connection.close()

    for index, customer in enumerate(DEMO_CUSTOMERS, start=1):
        payload = _demo_customer_payload(index, customer)
        company = payload["company_name"]
        if company in existing_customers:
            update_customer(existing_customers[company], payload, db_path=db_path)
        else:
            create_customer(payload, db_path=db_path)

    connection = get_connection(db_path)
    try:
        customer_ids = {
            row["company_name"]: int(row["id"])
            for row in connection.execute(
                "SELECT id, company_name FROM customers"
            ).fetchall()
        }
        product_ids = _insert_products(connection)
        inquiry_ids = _insert_inquiries(connection, customer_ids, product_ids)
        quotation_ids = _insert_quotations(
            connection,
            customer_ids,
            product_ids,
            inquiry_ids,
        )
        _insert_follow_ups(
            connection,
            customer_ids,
            inquiry_ids,
            quotation_ids,
        )
        connection.commit()
        tables = ("customers", "inquiries", "quotations", "follow_ups", "products")
        return {
            table: connection.execute(
                f"SELECT COUNT(*) AS count FROM {table}"
            ).fetchone()["count"]
            for table in tables
        }
    finally:
        connection.close()


def reset_demo_data(db_path: str | Path | None = None) -> dict[str, int]:
    """Reset only bundled fictional records while preserving user-owned data."""
    initialize_database(db_path)
    connection = get_connection(db_path)
    try:
        demo_customer_rows = connection.execute(
            f"SELECT id FROM customers WHERE company_name IN "
            f"({', '.join('?' for _ in DEMO_CUSTOMERS)})",
            tuple(customer[0] for customer in DEMO_CUSTOMERS),
        ).fetchall()
        customer_ids = [int(row["id"]) for row in demo_customer_rows]
        demo_raw_texts = tuple(inquiry[1] for inquiry in DEMO_INQUIRIES)
        demo_product_names = tuple(product[0] for product in DEMO_PRODUCTS)
        if customer_ids:
            placeholders = ", ".join("?" for _ in customer_ids)
            connection.execute(
                f"DELETE FROM activities WHERE customer_id IN ({placeholders})",
                tuple(customer_ids),
            )
            connection.execute(
                f"DELETE FROM follow_ups WHERE customer_id IN ({placeholders})",
                tuple(customer_ids),
            )
            connection.execute(
                f"DELETE FROM quotations WHERE customer_id IN ({placeholders})",
                tuple(customer_ids),
            )
        connection.execute(
            f"DELETE FROM inquiries WHERE raw_text IN "
            f"({', '.join('?' for _ in demo_raw_texts)})",
            demo_raw_texts,
        )
        connection.execute(
            f"DELETE FROM customers WHERE company_name IN "
            f"({', '.join('?' for _ in DEMO_CUSTOMERS)})",
            tuple(customer[0] for customer in DEMO_CUSTOMERS),
        )
        connection.execute(
            f"DELETE FROM products WHERE product_name IN "
            f"({', '.join('?' for _ in demo_product_names)})",
            demo_product_names,
        )
        connection.commit()
    finally:
        connection.close()
    return seed_demo_data(db_path)


if __name__ == "__main__":
    print(seed_demo_data())
