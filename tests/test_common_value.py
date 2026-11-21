from database.models import Product
from services.classification_service import common_value, set_product_attributes
from services.product_service import search_products


def test_common_value_all_equal():
    assert common_value(["Vortex", "Vortex"]) == "Vortex"


def test_common_value_single_item():
    assert common_value(["Vortex"]) == "Vortex"


def test_common_value_different_values():
    assert common_value(["Vortex", "Zeiss"]) is None


def test_common_value_all_empty():
    assert common_value([None, None]) is None


def test_common_value_some_empty():
    assert common_value(["Vortex", None]) is None


def test_common_value_empty_list():
    assert common_value([]) is None


def test_search_finds_zero_stock_product_with_only_manufacturer(session):
    product = Product(code="A1", name="Lornetka Vortex", wapro_quantity=0, manufacturer="Vortex")
    session.add(product)
    session.commit()

    found = search_products(session, "vortex lornetka")

    assert [p.code for p in found] == ["A1"]


def test_correcting_found_product_makes_it_confirmed(session):
    product = Product(code="A1", name="Lornetka Vortex", wapro_quantity=0, manufacturer="Vortex")
    session.add(product)
    session.commit()

    set_product_attributes(session, product, "Vortex", "Lornetka")

    assert product.review_status == "confirmed"
    assert product.category == "Lornetka"