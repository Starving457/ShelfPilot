from database.models import Product
from services.classification_service import (
    set_product_attributes,
    set_products_attributes,
    list_products_to_fill,
    group_products_by_hint,
    list_manufacturers,
)
from services.inventory_service import count_products_outside_rotation


def _make_product(session, code, name="Product", quantity=3, hint=None):
    product = Product(
        code=code,
        name=f"{name} {code}",
        wapro_quantity=quantity,
        suggested_manufacturer=hint,
        suggested_source="wapro" if hint else None,
    )
    session.add(product)
    session.commit()
    return product


def test_set_products_attributes_updates_all_at_once(session):
    a = _make_product(session, "A", hint="ATOMICUS")
    b = _make_product(session, "B", hint="ATOMICUS")

    result = set_products_attributes(session, [a, b], "Atomicus", "Narty")

    assert result == "ok"
    for product in (a, b):
        assert (product.manufacturer, product.category) == ("Atomicus", "Narty")
        assert product.review_status == "confirmed"
        assert product.classification_source == "manual"
        assert product.suggested_manufacturer is None


def test_set_products_attributes_rejects_empty_values_without_changing_anything(session):
    a = _make_product(session, "A")

    assert set_products_attributes(session, [a], "", "Narty") == "invalid"
    assert set_products_attributes(session, [a], "Atomicus", "  ") == "invalid"
    assert a.review_status == "pending"
    assert a.manufacturer is None


def test_existing_spelling_is_reused_ignoring_case(session):
    first = _make_product(session, "A")
    second = _make_product(session, "B")
    set_product_attributes(session, first, "Vortex", "Lornetka")

    set_product_attributes(session, second, "VORTEX", "lornetka")

    assert second.manufacturer == "Vortex"
    assert second.category == "Lornetka"
    assert list_manufacturers(session) == ["Vortex"]


def test_new_spelling_is_kept_when_nothing_matches(session):
    product = _make_product(session, "A")

    set_product_attributes(session, product, "Zeiss", "Luneta")

    assert (product.manufacturer, product.category) == ("Zeiss", "Luneta")


def test_list_products_to_fill_returns_only_products_with_stock_missing_attributes(session):
    needs = _make_product(session, "NEEDS")
    done = _make_product(session, "DONE")
    set_product_attributes(session, done, "Vortex", "Lornetka")
    _make_product(session, "NOSTOCK", quantity=0)
    _make_product(session, "UNKNOWN", quantity=None)

    result = list_products_to_fill(session)

    assert result == [needs]


def test_product_with_only_a_suggestion_still_needs_filling(session):
    product = _make_product(session, "A", hint="ATOMICUS")

    assert list_products_to_fill(session) == [product]


def test_list_products_to_fill_matches_the_rotation_warning_count(session):
    _make_product(session, "A")
    _make_product(session, "B", hint="X")
    done = _make_product(session, "C")
    set_product_attributes(session, done, "Vortex", "Lornetka")

    assert len(list_products_to_fill(session)) == count_products_outside_rotation(session) == 2


def test_list_products_to_fill_is_empty_when_everything_is_filled(session):
    product = _make_product(session, "A")
    set_product_attributes(session, product, "Vortex", "Lornetka")

    assert list_products_to_fill(session) == []


def test_list_products_to_fill_sorts_by_hint_then_name_with_no_hint_last(session):
    no_hint = _make_product(session, "N")
    zeiss = _make_product(session, "Z", hint="ZEISS")
    atom_b = _make_product(session, "B", hint="ATOMICUS")
    atom_a = _make_product(session, "A", hint="ATOMICUS")

    assert list_products_to_fill(session) == [atom_a, atom_b, zeiss, no_hint]


def test_group_products_by_hint(session):
    a1 = _make_product(session, "A1", hint="ATOMICUS")
    a2 = _make_product(session, "A2", hint="ATOMICUS")
    z = _make_product(session, "Z", hint="ZEISS")
    n = _make_product(session, "N")

    groups = group_products_by_hint([n, z, a1, a2])

    assert [(hint, [p.code for p in products]) for hint, products in groups] == [
        ("ATOMICUS", ["A1", "A2"]),
        ("ZEISS", ["Z"]),
        (None, ["N"]),
    ]


def test_group_products_by_hint_treats_case_variants_as_one_group(session):
    upper = _make_product(session, "U", hint="ATOMICUS")
    lower = _make_product(session, "L", hint="Atomicus")

    groups = group_products_by_hint([upper, lower])

    assert len(groups) == 1
    assert len(groups[0][1]) == 2


def test_group_products_by_hint_empty(session):
    assert group_products_by_hint([]) == []