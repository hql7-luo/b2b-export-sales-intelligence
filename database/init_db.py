"""Create the six-table SQLite schema."""

from __future__ import annotations

from pathlib import Path

from database.connection import get_connection


REQUIRED_TABLES = {
    "customers",
    "inquiries",
    "quotations",
    "follow_ups",
    "products",
    "activities",
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    contact_name TEXT,
    job_title TEXT,
    country TEXT,
    website TEXT,
    email TEXT,
    phone TEXT,
    lead_source TEXT,
    product_interest TEXT,
    import_frequency TEXT,
    estimated_purchase_volume REAL DEFAULT 0,
    last_contact_date TEXT,
    next_follow_up_date TEXT,
    current_stage TEXT NOT NULL DEFAULT 'New Lead',
    lead_grade TEXT NOT NULL DEFAULT 'D',
    auto_score INTEGER NOT NULL DEFAULT 0 CHECK (auto_score BETWEEN 0 AND 100),
    auto_grade TEXT NOT NULL DEFAULT 'D',
    score_breakdown TEXT NOT NULL DEFAULT '{}',
    score_reasons TEXT NOT NULL DEFAULT '{}',
    manual_score INTEGER CHECK (manual_score BETWEEN 0 AND 100),
    manual_grade TEXT,
    score_override_reason TEXT,
    score_overridden_at TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    inquiry_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    raw_text TEXT,
    product TEXT,
    specification TEXT,
    quantity TEXT,
    application TEXT,
    customization_requirement TEXT,
    packaging_requirement TEXT,
    destination TEXT,
    required_delivery_time TEXT,
    target_price TEXT,
    sample_requirement TEXT,
    payment_requirement TEXT,
    confirmed_info TEXT NOT NULL DEFAULT '[]',
    missing_info TEXT NOT NULL DEFAULT '[]',
    risks TEXT NOT NULL DEFAULT '[]',
    next_questions TEXT NOT NULL DEFAULT '[]',
    completeness_score INTEGER NOT NULL DEFAULT 0,
    suggested_reply TEXT,
    analysis_mode TEXT NOT NULL DEFAULT 'rule',
    analysis_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS quotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    product_name TEXT NOT NULL,
    quotation_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    incoterm TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_product_cost REAL NOT NULL DEFAULT 0,
    packaging_cost REAL NOT NULL DEFAULT 0,
    domestic_transportation_cost REAL NOT NULL DEFAULT 0,
    export_handling_cost REAL NOT NULL DEFAULT 0,
    international_freight REAL NOT NULL DEFAULT 0,
    insurance_cost REAL NOT NULL DEFAULT 0,
    tariff_and_tax REAL NOT NULL DEFAULT 0,
    platform_or_bank_fee REAL NOT NULL DEFAULT 0,
    exchange_rate REAL NOT NULL DEFAULT 7.2,
    pricing_method TEXT NOT NULL DEFAULT 'gross_margin',
    pricing_rate REAL NOT NULL DEFAULT 0,
    total_cost_cny REAL NOT NULL DEFAULT 0,
    unit_quote_usd REAL NOT NULL DEFAULT 0,
    total_quote_usd REAL NOT NULL DEFAULT 0,
    gross_profit_usd REAL NOT NULL DEFAULT 0,
    gross_margin REAL NOT NULL DEFAULT 0,
    valid_until TEXT,
    moq INTEGER,
    lead_time TEXT,
    payment_terms TEXT,
    notes TEXT,
    calculation_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS follow_ups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    follow_up_date TEXT NOT NULL,
    communication_type TEXT,
    content TEXT NOT NULL,
    outcome TEXT,
    next_follow_up_date TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL UNIQUE,
    category TEXT,
    application TEXT,
    material TEXT,
    specification TEXT,
    moq INTEGER,
    sample_lead_time TEXT,
    production_lead_time TEXT,
    packaging TEXT,
    unit_cost REAL,
    common_customer_questions TEXT,
    selling_points TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    activity_type TEXT NOT NULL,
    activity_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_customers_grade ON customers(lead_grade);
CREATE INDEX IF NOT EXISTS idx_customers_stage ON customers(current_stage);
CREATE INDEX IF NOT EXISTS idx_customers_follow_up ON customers(next_follow_up_date);
CREATE INDEX IF NOT EXISTS idx_inquiries_customer ON inquiries(customer_id);
CREATE INDEX IF NOT EXISTS idx_quotations_customer ON quotations(customer_id);
CREATE INDEX IF NOT EXISTS idx_follow_ups_customer ON follow_ups(customer_id);
CREATE INDEX IF NOT EXISTS idx_activities_customer ON activities(customer_id);
"""


def initialize_database(db_path: str | Path | None = None) -> Path:
    """Create missing tables and return the resolved database path."""
    connection = get_connection(db_path)
    try:
        connection.executescript(SCHEMA_SQL)
        connection.commit()
        row = connection.execute("PRAGMA database_list").fetchone()
        return Path(row["file"])
    finally:
        connection.close()


# Compatibility alias used by small scripts and Streamlit pages.
init_db = initialize_database


if __name__ == "__main__":
    from database.seed_data import seed_demo_data

    database_path = initialize_database()
    seed_demo_data(database_path)
    print(f"Database initialized at {database_path}")
