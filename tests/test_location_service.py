from database.models import Product, Location
from services.location_service import (
    find_product,
    find_location,
    get_product_locations,
    find_products_by_location,
    add_product_to_location,
    remove_product_from_location,
    move_product_location,
)


def test_find_product_when_exists(session):
    product = Product(code="TEST123", name="Test Screw", wapro_quantity=5)
    session.add(product)
    session.commit()

    result = find_product(session, "TEST123")

    assert result is not None
    assert result.name == "Test Screw"


def test_find_product_when_not_exists(session):
    result = find_product(session, "NONEXISTENT_CODE")

    assert result is None


def test_find_location_when_exists(session):
    location = Location(code="A1", rack="A", shelf="1")
    session.add(location)
    session.commit()

    result = find_location(session, "A1")

    assert result is not None
    assert result.rack == "A"
    assert result.shelf == "1"


def test_find_location_when_not_exists(session):
    result = find_location(session, "NONEXISTENT")

    assert result is None


def test_add_product_to_location_success(session):
    product = Product(code="TEST123", name="Test Screw", wapro_quantity=5)
    location = Location(code="A1", rack="A", shelf="1")
    session.add_all([product, location])
    session.commit()

    result = add_product_to_location(session, product, "A1")

    assert result == "ok"
    codes = [loc.code for loc in get_product_locations(session, product)]
    assert codes == ["A1"]


def test_add_product_to_location_nonexistent_location(session):
    product = Product(code="TEST123", name="Test Screw", wapro_quantity=5)
    session.add(product)
    session.commit()

    result = add_product_to_location(session, product, "NONEXISTENT")

    assert result == "location_not_found"
    assert get_product_locations(session, product) == []


def test_add_product_to_location_already_assigned(session):
    product = Product(code="TEST123", name="Test Screw", wapro_quantity=5)
    location = Location(code="A1", rack="A", shelf="1")
    session.add_all([product, location])
    session.commit()

    add_product_to_location(session, product, "A1")
    result = add_product_to_location(session, product, "A1")

    assert result == "already_assigned"
    assert len(get_product_locations(session, product)) == 1


def test_product_on_multiple_locations(session):
    product = Product(code="TEST123", name="Test Screw", wapro_quantity=50)
    a1 = Location(code="A1", rack="A", shelf="1")
    a2 = Location(code="A2", rack="A", shelf="2")
    session.add_all([product, a1, a2])
    session.commit()

    add_product_to_location(session, product, "A1")
    add_product_to_location(session, product, "A2")

    codes = sorted(loc.code for loc in get_product_locations(session, product))
    assert codes == ["A1", "A2"]


def test_remove_product_from_location_success(session):
    product = Product(code="TEST123", name="Test Screw", wapro_quantity=50)
    a1 = Location(code="A1", rack="A", shelf="1")
    a2 = Location(code="A2", rack="A", shelf="2")
    session.add_all([product, a1, a2])
    session.commit()
    add_product_to_location(session, product, "A1")
    add_product_to_location(session, product, "A2")

    result = remove_product_from_location(session, product, "A1")

    assert result == "ok"
    codes = [loc.code for loc in get_product_locations(session, product)]
    assert codes == ["A2"]


def test_remove_product_from_location_not_assigned(session):
    product = Product(code="TEST123", name="Test Screw", wapro_quantity=5)
    location = Location(code="A1", rack="A", shelf="1")
    session.add_all([product, location])
    session.commit()

    result = remove_product_from_location(session, product, "A1")

    assert result == "not_assigned"


def test_remove_product_from_location_nonexistent_location(session):
    product = Product(code="TEST123", name="Test Screw", wapro_quantity=5)
    session.add(product)
    session.commit()

    result = remove_product_from_location(session, product, "NONEXISTENT")

    assert result == "location_not_found"


def test_move_product_location_success(session):
    product = Product(code="TEST123", name="Test Screw", wapro_quantity=5)
    a1 = Location(code="A1", rack="A", shelf="1")
    a2 = Location(code="A2", rack="A", shelf="2")
    session.add_all([product, a1, a2])
    session.commit()
    add_product_to_location(session, product, "A1")

    result = move_product_location(session, product, "A1", "A2")

    assert result == "ok"
    codes = [loc.code for loc in get_product_locations(session, product)]
    assert codes == ["A2"]


def test_move_product_location_not_assigned(session):
    product = Product(code="TEST123", name="Test Screw", wapro_quantity=5)
    a1 = Location(code="A1", rack="A", shelf="1")
    a2 = Location(code="A2", rack="A", shelf="2")
    session.add_all([product, a1, a2])
    session.commit()

    result = move_product_location(session, product, "A1", "A2")

    assert result == "not_assigned"
    assert get_product_locations(session, product) == []


def test_move_product_location_already_assigned(session):
    product = Product(code="TEST123", name="Test Screw", wapro_quantity=5)
    a1 = Location(code="A1", rack="A", shelf="1")
    a2 = Location(code="A2", rack="A", shelf="2")
    session.add_all([product, a1, a2])
    session.commit()
    add_product_to_location(session, product, "A1")
    add_product_to_location(session, product, "A2")

    result = move_product_location(session, product, "A1", "A2")

    assert result == "already_assigned"
    codes = sorted(loc.code for loc in get_product_locations(session, product))
    assert codes == ["A1", "A2"]


def test_find_products_by_location_with_products(session):
    a1 = Location(code="A1", rack="A", shelf="1")
    a2 = Location(code="A2", rack="A", shelf="2")
    product1 = Product(code="ABC123", name="Screw", wapro_quantity=5)
    product2 = Product(code="XYZ789", name="Nut", wapro_quantity=10)
    product3 = Product(code="QQQ111", name="Hammer", wapro_quantity=2)
    session.add_all([a1, a2, product1, product2, product3])
    session.commit()

    add_product_to_location(session, product1, "A1")
    add_product_to_location(session, product2, "A1")
    add_product_to_location(session, product3, "A2")

    results = find_products_by_location(session, "A1")

    codes = sorted(p.code for p in results)
    assert codes == ["ABC123", "XYZ789"]


def test_find_products_by_location_empty_or_nonexistent(session):
    results = find_products_by_location(session, "NONEXISTENT")

    assert results == []