from datetime import date

from database.models import Product
from services.classification_service import set_product_attributes
from services.inventory_service import (
    record_count,
    list_manufacturer_summaries,
    suggest_next_group,
)


def _make_classified(session, code, manufacturer, category, wapro_quantity=3):
    product = Product(code=code, name=f"Product {code}", wapro_quantity=wapro_quantity)
    session.add(product)
    session.commit()
    set_product_attributes(session, product, manufacturer, category)
    return product


def test_manufacturer_summaries_empty(session):
    assert list_manufacturer_summaries(session) == []


def test_manufacturer_summaries_are_alphabetical(session):
    _make_classified(session, "A", "Zeiss", "Lornetka")
    _make_classified(session, "B", "Vortex", "Lornetka")
    _make_classified(session, "C", "Swarovski", "Luneta")

    names = [m.manufacturer for m in list_manufacturer_summaries(session)]

    assert names == ["Swarovski", "Vortex", "Zeiss"]


def test_manufacturer_summary_merges_categories(session):
    _make_classified(session, "A", "Vortex", "Lornetka")
    _make_classified(session, "B", "Vortex", "Lornetka")
    _make_classified(session, "C", "Vortex", "Luneta")
    _make_classified(session, "D", "Zeiss", "Lornetka")

    vortex, zeiss = list_manufacturer_summaries(session)

    assert vortex.manufacturer == "Vortex"
    assert vortex.group_count == 2
    assert vortex.product_count == 3
    assert zeiss.group_count == 1
    assert zeiss.product_count == 1


def test_manufacturer_summary_counting_stats(session):
    a = _make_classified(session, "A", "Vortex", "Lornetka")
    b = _make_classified(session, "B", "Vortex", "Luneta")
    _make_classified(session, "C", "Vortex", "Luneta")
    record_count(session, a, 3, counted_at=date(2026, 11, 5))
    record_count(session, b, 3, counted_at=date(2026, 11, 2))

    summary = list_manufacturer_summaries(session)[0]

    assert summary.never_counted_count == 1
    assert summary.oldest_last_count == date(2026, 11, 2)


def test_manufacturer_summary_never_counted_has_no_date(session):
    _make_classified(session, "A", "Vortex", "Lornetka")

    summary = list_manufacturer_summaries(session)[0]

    assert summary.never_counted_count == 1
    assert summary.oldest_last_count is None


def test_manufacturer_summary_skips_products_outside_rotation(session):
    _make_classified(session, "A", "Vortex", "Lornetka", wapro_quantity=0)

    assert list_manufacturer_summaries(session) == []


def test_suggest_next_group_limited_to_manufacturer(session):
    _make_classified(session, "A", "Swarovski", "Lornetka")  # never counted, would win globally
    old = _make_classified(session, "B", "Vortex", "Lornetka")
    newer = _make_classified(session, "C", "Vortex", "Luneta")
    record_count(session, old, 3, counted_at=date(2026, 10, 1))
    record_count(session, newer, 3, counted_at=date(2026, 11, 1))

    group = suggest_next_group(session, manufacturer="Vortex")

    assert (group.manufacturer, group.category) == ("Vortex", "Lornetka")


def test_suggest_next_group_unknown_manufacturer(session):
    _make_classified(session, "A", "Vortex", "Lornetka")

    assert suggest_next_group(session, manufacturer="Nikon") is None


def test_suggest_next_group_without_manufacturer_still_global(session):
    _make_classified(session, "A", "Swarovski", "Lornetka")
    counted = _make_classified(session, "B", "Vortex", "Lornetka")
    record_count(session, counted, 3, counted_at=date(2026, 1, 1))

    group = suggest_next_group(session)

    assert group.manufacturer == "Swarovski"