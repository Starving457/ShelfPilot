from database.models import Product
from services.classification_service import (
    set_product_attributes,
    list_manufacturers,
    list_categories,
)


def _make_product(session, code="P1", name="VORTEX DIAMONDBACK HD 10X42 LORNETKA"):
    product = Product(code=code, name=name, wapro_quantity=3)
    session.add(product)
    session.commit()
    return product


def test_new_product_is_pending_review(session):
    product = _make_product(session)

    assert product.review_status == "pending"
    assert product.first_seen_at is not None
    assert product.manufacturer is None


def test_set_attributes_manually_confirms(session):
    product = _make_product(session)

    result = set_product_attributes(session, product, "Vortex", "Lornetka")

    assert result == "ok"
    assert product.manufacturer == "Vortex"
    assert product.category == "Lornetka"
    assert product.classification_source == "manual"
    assert product.review_status == "confirmed"


def test_set_attributes_rejects_empty_fields(session):
    product = _make_product(session)

    assert set_product_attributes(session, product, "", "Lornetka") == "invalid"
    assert set_product_attributes(session, product, "Vortex", "   ") == "invalid"
    assert product.review_status == "pending"


def test_set_attributes_corrects_a_mistake(session):
    product = _make_product(session)
    set_product_attributes(session, product, "Vortex", "Luneta")

    set_product_attributes(session, product, "Vortex", "Lornetka")

    assert product.category == "Lornetka"
    assert product.classification_source == "manual"


def test_list_manufacturers_and_categories(session):
    a = _make_product(session, "A")
    b = _make_product(session, "B")
    c = _make_product(session, "C")
    set_product_attributes(session, a, "Vortex", "Lornetka")
    set_product_attributes(session, b, "Vortex", "Luneta")
    set_product_attributes(session, c, "Zeiss", "Lornetka")

    assert list_manufacturers(session) == ["Vortex", "Zeiss"]
    assert list_categories(session) == ["Lornetka", "Luneta"]