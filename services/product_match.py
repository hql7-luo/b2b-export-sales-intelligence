"""Simple explainable product matching for analyzed inquiries."""

from __future__ import annotations

import re
from typing import Any, Iterable

STOP_WORDS = {
    "and", "the", "for", "with", "our", "need", "please", "custom", "product",
    "products", "quote", "quotation", "we", "to", "a", "an", "of", "in",
}


def _tokens(value: str) -> set[str]:
    tokens = {token.lower().rstrip("s") for token in re.findall(r"[A-Za-z0-9]+", value)}
    return {token for token in tokens if len(token) > 1 and token not in STOP_WORDS}


def recommend_products(
    inquiry_text: str, products: Iterable[dict[str, Any]], limit: int = 3
) -> list[dict[str, Any]]:
    """Rank products by visible keyword overlap and return the reasons."""
    inquiry_tokens = _tokens(inquiry_text)
    ranked: list[dict[str, Any]] = []
    for product in products:
        searchable = " ".join(
            str(product.get(field) or "")
            for field in ("product_name", "category", "application", "material", "specification", "selling_points")
        )
        overlap = sorted(inquiry_tokens & _tokens(searchable))
        if not overlap:
            continue
        ranked.append(
            {
                **product,
                "match_score": min(len(overlap) * 20, 100),
                "match_reasons": [f"Shared keyword: {word}" for word in overlap],
            }
        )
    return sorted(ranked, key=lambda row: (-row["match_score"], row.get("product_name", "")))[:limit]
