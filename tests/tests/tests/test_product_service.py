from database.models import Product
from services.product_service import search_products


def test_search_po_dokladnym_kodzie(session):
    produkt = Product(code="ABC123", ean="5901234567890", name="Lornetka Vortex", quantity=3)
    session.add(produkt)
    session.commit()

    wyniki = search_products(session, "ABC123")

    assert len(wyniki) == 1
    assert wyniki[0].name == "Lornetka Vortex"

def test_search_po_ean(session):
    produkt = Product(code="ABC123", ean="5901234567890", name="Lornetka Vortex", quantity=3)
    session.add(produkt)
    session.commit()

    wyniki = search_products(session, "5901234567890")

    assert len(wyniki) == 1
    assert wyniki[0].code == "ABC123"

def test_search_po_fragmencie_nazwy(session):
    produkt = Product(code="ABC123", ean="5901234567890", name="Vortex Diamondback Super Edition 8x32 pro", quantity=3)
    session.add(produkt)
    session.commit()

    wyniki = search_products(session, "8x32 Diamondback")

    assert len(wyniki) == 1
    assert wyniki[0].code == "ABC123"

def test_search_brak_wynikow(session):
    wyniki = search_products(session, "COSNIEISTNIEJACEGO")

    assert wyniki == []