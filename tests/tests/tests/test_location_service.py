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


def test_find_product_gdy_istnieje(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", wapro_quantity=5)
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


def test_add_product_to_location_sukces(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", wapro_quantity=5)
    lokalizacja = Location(code="A1", rack="A", shelf="1")
    session.add_all([produkt, lokalizacja])
    session.commit()

    wynik = add_product_to_location(session, produkt, "A1")

    assert wynik == "ok"
    kody = [l.code for l in get_product_locations(session, produkt)]
    assert kody == ["A1"]


def test_add_product_to_location_nieistniejaca_lokalizacja(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", wapro_quantity=5)
    session.add(produkt)
    session.commit()

    wynik = add_product_to_location(session, produkt, "NIEISTNIEJACA")

    assert wynik == "location_not_found"
    assert get_product_locations(session, produkt) == []


def test_add_product_to_location_juz_przypisany(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", wapro_quantity=5)
    lokalizacja = Location(code="A1", rack="A", shelf="1")
    session.add_all([produkt, lokalizacja])
    session.commit()

    add_product_to_location(session, produkt, "A1")
    wynik = add_product_to_location(session, produkt, "A1")

    assert wynik == "already_assigned"
    assert len(get_product_locations(session, produkt)) == 1


def test_produkt_na_kilku_polkach(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", wapro_quantity=50)
    a1 = Location(code="A1", rack="A", shelf="1")
    a2 = Location(code="A2", rack="A", shelf="2")
    session.add_all([produkt, a1, a2])
    session.commit()

    add_product_to_location(session, produkt, "A1")
    add_product_to_location(session, produkt, "A2")

    kody = sorted(l.code for l in get_product_locations(session, produkt))
    assert kody == ["A1", "A2"]


def test_remove_product_from_location_sukces(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", wapro_quantity=50)
    a1 = Location(code="A1", rack="A", shelf="1")
    a2 = Location(code="A2", rack="A", shelf="2")
    session.add_all([produkt, a1, a2])
    session.commit()
    add_product_to_location(session, produkt, "A1")
    add_product_to_location(session, produkt, "A2")

    wynik = remove_product_from_location(session, produkt, "A1")

    assert wynik == "ok"
    kody = [l.code for l in get_product_locations(session, produkt)]
    assert kody == ["A2"]


def test_remove_product_from_location_nie_przypisany(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", wapro_quantity=5)
    lokalizacja = Location(code="A1", rack="A", shelf="1")
    session.add_all([produkt, lokalizacja])
    session.commit()

    wynik = remove_product_from_location(session, produkt, "A1")

    assert wynik == "not_assigned"


def test_remove_product_from_location_nieistniejaca_lokalizacja(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", wapro_quantity=5)
    session.add(produkt)
    session.commit()

    wynik = remove_product_from_location(session, produkt, "NIEISTNIEJACA")

    assert wynik == "location_not_found"


def test_move_product_location_sukces(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", wapro_quantity=5)
    a1 = Location(code="A1", rack="A", shelf="1")
    a2 = Location(code="A2", rack="A", shelf="2")
    session.add_all([produkt, a1, a2])
    session.commit()
    add_product_to_location(session, produkt, "A1")

    wynik = move_product_location(session, produkt, "A1", "A2")

    assert wynik == "ok"
    kody = [l.code for l in get_product_locations(session, produkt)]
    assert kody == ["A2"]


def test_move_product_location_nie_przypisany(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", wapro_quantity=5)
    a1 = Location(code="A1", rack="A", shelf="1")
    a2 = Location(code="A2", rack="A", shelf="2")
    session.add_all([produkt, a1, a2])
    session.commit()

    wynik = move_product_location(session, produkt, "A1", "A2")

    assert wynik == "not_assigned"
    assert get_product_locations(session, produkt) == []


def test_move_product_location_juz_przypisany(session):
    produkt = Product(code="TEST123", name="Testowa Śruba", wapro_quantity=5)
    a1 = Location(code="A1", rack="A", shelf="1")
    a2 = Location(code="A2", rack="A", shelf="2")
    session.add_all([produkt, a1, a2])
    session.commit()
    add_product_to_location(session, produkt, "A1")
    add_product_to_location(session, produkt, "A2")

    wynik = move_product_location(session, produkt, "A1", "A2")

    assert wynik == "already_assigned"
    kody = sorted(l.code for l in get_product_locations(session, produkt))
    assert kody == ["A1", "A2"]


def test_find_products_by_location_z_produktami(session):
    a1 = Location(code="A1", rack="A", shelf="1")
    a2 = Location(code="A2", rack="A", shelf="2")
    produkt1 = Product(code="ABC123", name="Śruba", wapro_quantity=5)
    produkt2 = Product(code="XYZ789", name="Nakrętka", wapro_quantity=10)
    produkt3 = Product(code="QQQ111", name="Młotek", wapro_quantity=2)
    session.add_all([a1, a2, produkt1, produkt2, produkt3])
    session.commit()

    add_product_to_location(session, produkt1, "A1")
    add_product_to_location(session, produkt2, "A1")
    add_product_to_location(session, produkt3, "A2")

    wyniki = find_products_by_location(session, "A1")

    kody = sorted(p.code for p in wyniki)
    assert kody == ["ABC123", "XYZ789"]


def test_find_products_by_location_pusta_lub_nieistniejaca(session):
    wyniki = find_products_by_location(session, "NIEISTNIEJACA")

    assert wyniki == []