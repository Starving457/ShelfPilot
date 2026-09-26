from database.models import Product
from services.location_service import find_product


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