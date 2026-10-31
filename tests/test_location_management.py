from database.models import Product
from services.location_service import (
    find_location,
    add_product_to_location,
    create_location,
    delete_location,
    list_locations,
)


def test_create_location_success(session):
    result = create_location(session, "A1")

    assert result == "ok"
    location = find_location(session, "A1")
    assert location is not None
    assert location.rack == "A1"
    assert location.shelf is None


def test_create_location_duplicate(session):
    create_location(session, "A1")

    result = create_location(session, "A1")

    assert result == "already_exists"


def test_list_locations_empty(session):
    assert list_locations(session) == []


def test_list_locations_natural_order(session):
    for code in ["A10", "A2", "B1", "A1"]:
        create_location(session, code)

    codes = [loc.code for loc in list_locations(session)]

    assert codes == ["A1", "A2", "A10", "B1"]


def test_delete_location_success(session):
    create_location(session, "A1")

    result = delete_location(session, "A1")

    assert result == "ok"
    assert find_location(session, "A1") is None


def test_delete_location_nonexistent(session):
    result = delete_location(session, "NONEXISTENT")

    assert result == "location_not_found"


def test_delete_location_with_products_is_blocked(session):
    product = Product(code="TEST123", name="Test Screw", wapro_quantity=5)
    session.add(product)
    session.commit()
    create_location(session, "A1")
    add_product_to_location(session, product, "A1")

    result = delete_location(session, "A1")

    assert result == "has_products"
    assert find_location(session, "A1") is not None