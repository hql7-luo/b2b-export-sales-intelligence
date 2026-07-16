from services.product_match import recommend_products


def test_recommends_relevant_products_by_name_category_and_specification() -> None:
    products = [
        {"id": 1, "product_name": "Aurora Notebook", "category": "Notebook", "specification": "A5 hardcover recycled paper"},
        {"id": 2, "product_name": "Comet Sticker Pack", "category": "Sticker", "specification": "Matte vinyl"},
    ]

    matches = recommend_products("We need A5 recycled hardcover notebooks", products)

    assert matches[0]["id"] == 1
    assert matches[0]["match_score"] > 0
    assert matches[0]["match_reasons"]
