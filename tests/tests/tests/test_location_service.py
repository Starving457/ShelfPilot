from database.models import Product, Location
from services.location_service import (
    find_product,
    find_location,
    assign_new_location,
    update_location,
    remove_location,
    find_products_by_location,
)


def test_find_product_gdy_istnieje(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", quantity=5)
    session.add(produkt)
    session.commit()

    wynik = find_product(session, "TEST123")

    assert wynik is not None
    assert wynik.name == "Testowa Śruba"


def test_find_product_gdy_nie_istnieje(session):
    wynik = find_product(session, "NIEISTNIEJACY_KOD")

    assert wynik is None

def test_find_location_gdy_istnieje(session):
    lokalizacja = Location(code="A1", rack="A", shelf="1")
    session.add(lokalizacja)
    session.commit()

    wynik = find_location(session, "A1")

    assert wynik is not None
    assert wynik.rack == "A"
    assert wynik.shelf == "1"

def test_find_location_gdy_nie_istnieje(session):
    wynik = find_location(session, "NIEISTNIEJACA")

    assert wynik is None

def test_assign_new_location_sukces(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", quantity=5)
    lokalizacja = Location(code="A1", rack="A", shelf="1")
    session.add(produkt)
    session.add(lokalizacja)
    session.commit()

    wynik = assign_new_location(session, produkt, "A1")

    assert wynik is True
    assert produkt.location_id == lokalizacja.id


def test_assign_new_location_nieistniejaca_lokalizacja(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", quantity=5)
    session.add(produkt)
    session.commit()

    wynik = assign_new_location(session, produkt, "NIEISTNIEJACA")

    assert wynik is False
    assert produkt.location_id is None

def test_update_location_sukces(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", quantity=5)
    lokalizacja_a1 = Location(code="A1", rack="A", shelf="1")
    lokalizacja_a2 = Location(code="A2", rack="A", shelf="2")
    session.add(produkt)
    session.add(lokalizacja_a1)
    session.add(lokalizacja_a2)
    session.commit()

    produkt.location_id = lokalizacja_a1.id
    session.commit()

    wynik = update_location(session, produkt, "A2")

    assert wynik is True
    assert produkt.location_id == lokalizacja_a2.id


def test_update_location_nieistniejaca_lokalizacja(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", quantity=5)
    lokalizacja_a1 = Location(code="A1", rack="A", shelf="1")
    session.add(produkt)
    session.add(lokalizacja_a1)
    session.commit()

    produkt.location_id = lokalizacja_a1.id
    session.commit()

    wynik = update_location(session, produkt, "NIEISTNIEJACA")

    assert wynik is False
    assert produkt.location_id == lokalizacja_a1.id

def test_remove_location(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", quantity=5)
    lokalizacja = Location(code="A1", rack="A", shelf="1")
    session.add(produkt)
    session.add(lokalizacja)
    session.commit()

    produkt.location_id = lokalizacja.id
    session.commit()

    remove_location(session, produkt)

    assert produkt.location_id is None

def test_find_products_by_location_z_produktami(session):
    lokalizacja = Location(code="A1", rack="A", shelf="1")
    produkt1 = Product(code="ABC123", name="Śruba", quantity=5)
    produkt2 = Product(code="XYZ789", name="Nakrętka", quantity=10)
    produkt_na_innej_polce = Product(code="QQQ111", name="Młotek", quantity=2)

    session.add_all([lokalizacja, produkt1, produkt2, produkt_na_innej_polce])
    session.commit()

    produkt1.location_id = lokalizacja.id
    produkt2.location_id = lokalizacja.id
    session.commit()

    wyniki = find_products_by_location(session, "A1")

    assert len(wyniki) == 2
    kody = [p.code for p in wyniki]
    assert "ABC123" in kody
    assert "XYZ789" in kody


def test_find_products_by_location_pusta_lub_nieistniejaca(session):
    wyniki = find_products_by_location(session, "NIEISTNIEJACA")

    assert wyniki == []