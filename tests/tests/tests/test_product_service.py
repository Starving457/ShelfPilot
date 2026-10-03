from database.models import Product
from services.product_service import search_products


def test_search_po_dokladnym_kodzie(session):
    produkt = Product(code="ABC123", ean="5901234567890", name="Lornetka Vortex", quantity=3)
    session.add(produkt)
    session.commit()

    wyniki = search_products(session, "ABC123")

    assert len(wyniki) == 1
    assert wyniki[0].name == "Lornetka Vortex"