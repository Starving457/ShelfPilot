from database.models import Product
from services.classification_service import (
    set_product_attributes,
    list_manufacturers,
    list_categories,
)


def _produkt(session, code="P1", name="VORTEX DIAMONDBACK HD 10X42 LORNETKA"):
    produkt = Product(code=code, name=name, wapro_quantity=3)
    session.add(produkt)
    session.commit()
    return produkt


def test_nowy_produkt_jest_do_sprawdzenia(session):
    produkt = _produkt(session)

    assert produkt.review_status == "pending"
    assert produkt.first_seen_at is not None
    assert produkt.manufacturer is None


def test_set_attributes_recznie_zatwierdza(session):
    produkt = _produkt(session)

    wynik = set_product_attributes(session, produkt, "Vortex", "Lornetka")

    assert wynik == "ok"
    assert produkt.manufacturer == "Vortex"
    assert produkt.category == "Lornetka"
    assert produkt.classification_source == "manual"
    assert produkt.review_status == "confirmed"


def test_set_attributes_puste_pola_sa_odrzucane(session):
    produkt = _produkt(session)

    assert set_product_attributes(session, produkt, "", "Lornetka") == "invalid"
    assert set_product_attributes(session, produkt, "Vortex", "   ") == "invalid"
    assert produkt.review_status == "pending"


def test_set_attributes_poprawia_pomylke(session):
    produkt = _produkt(session)
    set_product_attributes(session, produkt, "Vortex", "Luneta")

    set_product_attributes(session, produkt, "Vortex", "Lornetka")

    assert produkt.category == "Lornetka"
    assert produkt.classification_source == "manual"


def test_list_manufacturers_i_categories(session):
    a = _produkt(session, "A")
    b = _produkt(session, "B")
    c = _produkt(session, "C")
    set_product_attributes(session, a, "Vortex", "Lornetka")
    set_product_attributes(session, b, "Vortex", "Luneta")
    set_product_attributes(session, c, "Zeiss", "Lornetka")

    assert list_manufacturers(session) == ["Vortex", "Zeiss"]
    assert list_categories(session) == ["Lornetka", "Luneta"]