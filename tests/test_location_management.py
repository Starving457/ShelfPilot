from database.models import Product
from services.location_service import (
    find_location,
    add_product_to_location,
    create_location,
    delete_location,
    list_locations,
)


def test_create_location_sukces(session):
    wynik = create_location(session, "A1")

    assert wynik == "ok"
    lokalizacja = find_location(session, "A1")
    assert lokalizacja is not None
    assert lokalizacja.rack == "A1"
    assert lokalizacja.shelf is None


def test_create_location_duplikat(session):
    create_location(session, "A1")

    wynik = create_location(session, "A1")

    assert wynik == "already_exists"


def test_list_locations_pusta(session):
    assert list_locations(session) == []


def test_list_locations_naturalna_kolejnosc(session):
    for kod in ["A10", "A2", "B1", "A1"]:
        create_location(session, kod)

    kody = [l.code for l in list_locations(session)]

    assert kody == ["A1", "A2", "A10", "B1"]


def test_delete_location_sukces(session):
    create_location(session, "A1")

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
    create_location(session, "A1")
    add_product_to_location(session, produkt, "A1")

    wynik = delete_location(session, "A1")

    assert wynik == "has_products"
    assert find_location(session, "A1") is not None