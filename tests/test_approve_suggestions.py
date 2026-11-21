from database.models import Product
from services.classification_service import (
    approve_suggestions,
    confidence_of,
    list_suggestion_groups,
    reject_suggestions,
)


def _suggested(session, code, suggested_manufacturer, suggested_category, source="ai-high", name=None, **fields):
    product = Product(
        code=code,
        name=name or f"Product {code}",
        wapro_quantity=2,
        suggested_manufacturer=suggested_manufacturer,
        suggested_category=suggested_category,
        suggested_source=source,
        **fields,
    )
    session.add(product)
    session.commit()
    return product


def test_confidence_levels(session):
    assert confidence_of(_suggested(session, "A", "V", "L", "ai-high")) == "high"
    assert confidence_of(_suggested(session, "B", "V", "L", "ai-medium")) == "medium"
    assert confidence_of(_suggested(session, "C", "V", "L", "ai-low")) == "low"
    assert confidence_of(_suggested(session, "D", "V", "L", None)) == "low"
    assert confidence_of(_suggested(session, "E", "V", "L", "wapro")) == "low"


def test_groups_by_suggested_manufacturer_and_category(session):
    _suggested(session, "A", "Vortex", "Lornetki")
    _suggested(session, "B", "Vortex", "Lornetki")
    _suggested(session, "C", "Vortex", "Lunety celownicze")

    groups = list_suggestion_groups(session)

    assert [(m, c, [p.code for p in items]) for m, c, items in groups] == [
        ("Vortex", "Lornetki", ["A", "B"]),
        ("Vortex", "Lunety celownicze", ["C"]),
    ]


def test_groups_treat_different_case_as_one_group(session):
    _suggested(session, "A", "Vortex", "Lornetki")
    _suggested(session, "B", "VORTEX", "lornetki")

    groups = list_suggestion_groups(session)

    assert len(groups) == 1
    assert len(groups[0][2]) == 2


def test_groups_sorted_alphabetically_ignoring_case(session):
    _suggested(session, "A", "zeiss", "Lornetki")
    _suggested(session, "B", "Atomicus", "Narty")

    assert [m for m, _, _ in list_suggestion_groups(session)] == ["Atomicus", "zeiss"]


def test_groups_skip_wapro_hints_and_incomplete_suggestions(session):
    _suggested(session, "A", "Nikon", "Aparaty", source="wapro")
    _suggested(session, "B", "Vortex", None)
    _suggested(session, "C", None, "Lornetki")
    _suggested(session, "D", "Sony", "Aparaty")

    groups = list_suggestion_groups(session)

    assert [p.code for _, _, items in groups for p in items] == ["D"]


def test_groups_skip_confirmed_products(session):
    _suggested(session, "A", "Vortex", "Lornetki", manufacturer="Zeiss", category="Lunety", review_status="confirmed")

    assert list_suggestion_groups(session) == []


def test_approve_confirms_and_clears_suggestions(session):
    product = _suggested(session, "A", "Vortex", "Lornetki", source="ai-medium")

    count = approve_suggestions(session, [product])

    assert count == 1
    assert product.manufacturer == "Vortex"
    assert product.category == "Lornetki"
    assert product.review_status == "confirmed"
    assert product.classification_source == "ai"
    assert product.suggested_manufacturer is None
    assert product.suggested_category is None
    assert product.suggested_source is None


def test_approve_uses_existing_spelling(session):
    existing = Product(code="X", name="X", manufacturer="Vortex", category="Lornetki", review_status="confirmed")
    session.add(existing)
    session.commit()
    product = _suggested(session, "A", "VORTEX", "lornetki")

    approve_suggestions(session, [product])

    assert (product.manufacturer, product.category) == ("Vortex", "Lornetki")


def test_approve_uses_one_spelling_within_a_batch(session):
    a = _suggested(session, "A", "Vortex", "Lornetki")
    b = _suggested(session, "B", "VORTEX", "LORNETKI")

    approve_suggestions(session, [a, b])

    assert (a.manufacturer, a.category) == (b.manufacturer, b.category)


def test_approve_skips_products_without_full_suggestion(session):
    product = _suggested(session, "A", "Vortex", None)

    assert approve_suggestions(session, [product]) == 0
    assert product.review_status != "confirmed"


def test_reject_clears_suggestions_and_returns_product_to_fill_list(session):
    product = _suggested(session, "A", "Vortex", "Lornetki")

    count = reject_suggestions(session, [product])

    assert count == 1
    assert product.suggested_manufacturer is None
    assert product.suggested_category is None
    assert product.suggested_source is None
    assert product.review_status == "pending"
    assert list_suggestion_groups(session) == []