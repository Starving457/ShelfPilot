from database.models import Product, Location
from services.location_service import (
    find_location,
    add_product_to_location,
    create_location,
    delete_location,
)


def test_create_location_sukces(session):
    wynik = create_location(session, "A", "1")

    assert wynik == "ok"
    lokalizacja = find_location(session, "A1")
    assert lokalizacja is not None
    assert lokalizacja.rack == "A"
    assert lokalizacja.shelf == "1"


def test_create_location_duplikat(session):
    create_location(session, "A", "1")

    wynik = create_location(session, "A", "1")

    assert wynik == "already_exists"


def test_delete_location_sukces(session):
    create_location(session, "A", "1")

    wynik = delete_location(session, "A1")

    assert wynik == "ok"
    assert find_location(session, "A1") is None


def test_delete_location_nieistniejaca(session):
    wynik = delete_location(session, "NIEISTNIEJACA")

    assert wynik == "location_not_found"


def test_delete_location_z_produktami_jest_blokowane(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", wapro_quantity=5)
    session.add(produkt)
    session.commit()
    create_location(session, "A", "1")
    add_product_to_location(session, produkt, "A1")

    wynik = delete_location(session, "A1")

    assert wynik == "has_products"
    assert find_location(session, "A1") is not None