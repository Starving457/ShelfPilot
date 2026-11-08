from datetime import date

from database.models import Product, ProductLocation, InventoryCount
from services.classification_service import set_product_attributes
from services.import_service import import_articles
from services.location_service import create_location, add_product_to_location
from services.inventory_service import record_count
from services.wapro_reader import WaproArticle


def _article(wapro_id=1, code="Tow1", name="Skis A", quantity=5, ean=None, producer=None):
    return WaproArticle(
        wapro_id=wapro_id, code=code, ean=ean, name=name, quantity=quantity, producer=producer
    )


def _all_products(session):
    return session.query(Product).order_by(Product.id).all()


def test_import_creates_new_products(session):
    summary = import_articles(session, [_article(1, "Tow1", "Skis A", 5, "123"), _article(2, "Tow2", "Skis B", 0)])

    products = _all_products(session)
    assert summary.status == "ok"
    assert summary.created == 2
    assert summary.new_products == ["Skis A", "Skis B"]
    assert (products[0].wapro_id, products[0].code, products[0].ean) == (1, "Tow1", "123")
    assert (products[0].name, products[0].wapro_quantity) == ("Skis A", 5)


def test_new_product_waits_for_review(session):
    import_articles(session, [_article()])

    product = _all_products(session)[0]
    assert product.review_status == "pending"
    assert product.manufacturer is None
    assert product.category is None
    assert product.first_seen_at == date.today()


def test_wapro_producer_is_only_a_suggestion(session):
    import_articles(session, [_article(producer="ATOMICUS")])

    product = _all_products(session)[0]
    assert product.manufacturer is None
    assert product.suggested_manufacturer == "ATOMICUS"
    assert product.suggested_source == "wapro"


def test_no_suggestion_without_producer(session):
    import_articles(session, [_article(producer=None)])

    assert _all_products(session)[0].suggested_manufacturer is None


def test_import_updates_existing_product(session):
    import_articles(session, [_article(1, "Tow1", "Old name", 5, "111")])

    summary = import_articles(session, [_article(1, "Tow1", "New name", 9, "222")])

    product = _all_products(session)[0]
    assert summary.updated == 1
    assert summary.created == 0
    assert (product.name, product.wapro_quantity, product.ean) == ("New name", 9, "222")
    assert len(_all_products(session)) == 1


def test_import_updates_changed_code(session):
    import_articles(session, [_article(1, "Tow1")])

    import_articles(session, [_article(1, "Tow1-NEW")])

    product = _all_products(session)[0]
    assert product.code == "Tow1-NEW"
    assert len(_all_products(session)) == 1


def test_second_identical_import_changes_nothing(session):
    articles = [_article(1, "Tow1"), _article(2, "Tow2")]
    import_articles(session, articles)

    summary = import_articles(session, articles)

    assert (summary.created, summary.updated, summary.unchanged) == (0, 0, 2)


def test_import_keeps_locations_counts_and_manual_classification(session):
    import_articles(session, [_article(1, "Tow1", "Old name", 5)])
    product = _all_products(session)[0]
    set_product_attributes(session, product, "Vortex", "Lornetka")
    create_location(session, "A1")
    add_product_to_location(session, product, "A1")
    record_count(session, product, 4, counted_at=date(2026, 11, 1))

    import_articles(session, [_article(1, "Tow1", "New name", 9, producer="SOMEONE ELSE")])

    session.refresh(product)
    assert product.name == "New name"
    assert product.wapro_quantity == 9
    assert (product.manufacturer, product.category) == ("Vortex", "Lornetka")
    assert product.review_status == "confirmed"
    assert session.query(ProductLocation).count() == 1
    assert session.query(InventoryCount).count() == 1


def test_empty_ean_from_wapro_does_not_erase_local_ean(session):
    import_articles(session, [_article(1, "Tow1", ean="555")])

    import_articles(session, [_article(1, "Tow1", ean=None)])

    assert _all_products(session)[0].ean == "555"


def test_import_adopts_manually_added_product_with_same_code(session):
    manual = Product(code="Tow1", name="Typed by hand", wapro_quantity=1)
    session.add(manual)
    session.commit()

    summary = import_articles(session, [_article(7, "Tow1", "From WAPRO", 5)])

    products = _all_products(session)
    assert len(products) == 1
    assert summary.created == 0
    assert summary.updated == 1
    assert (products[0].wapro_id, products[0].name) == (7, "From WAPRO")


def test_code_used_by_another_product_is_a_conflict(session):
    import_articles(session, [_article(1, "Tow1", "First")])

    summary = import_articles(session, [_article(2, "Tow1", "Second")])

    assert summary.conflicts == ["Tow1"]
    assert summary.created == 0
    assert len(_all_products(session)) == 1


def test_missing_product_stays_with_unknown_stock(session):
    import_articles(session, [_article(1, "Tow1", quantity=5), _article(2, "Tow2", quantity=3)])

    summary = import_articles(session, [_article(1, "Tow1", quantity=5)])

    products = _all_products(session)
    assert summary.missing == 1
    assert len(products) == 2
    assert products[1].wapro_quantity is None


def test_already_missing_product_is_not_counted_again(session):
    import_articles(session, [_article(1, "Tow1"), _article(2, "Tow2")])
    import_articles(session, [_article(1, "Tow1")])

    summary = import_articles(session, [_article(1, "Tow1")])

    assert summary.missing == 0


def test_product_returns_after_being_missing(session):
    import_articles(session, [_article(1, "Tow1"), _article(2, "Tow2", quantity=3)])
    import_articles(session, [_article(1, "Tow1")])

    import_articles(session, [_article(1, "Tow1"), _article(2, "Tow2", quantity=8)])

    assert _all_products(session)[1].wapro_quantity == 8


def test_manually_added_product_is_not_marked_missing(session):
    manual = Product(code="HAND1", name="By hand", wapro_quantity=2)
    session.add(manual)
    session.commit()

    summary = import_articles(session, [_article(1, "Tow1")])

    session.refresh(manual)
    assert summary.missing == 0
    assert manual.wapro_quantity == 2


def test_empty_source_changes_nothing(session):
    import_articles(session, [_article(1, "Tow1", quantity=5)])

    summary = import_articles(session, [])

    assert summary.status == "empty_source"
    assert _all_products(session)[0].wapro_quantity == 5


def test_dry_run_does_not_save_anything(session):
    summary = import_articles(session, [_article(1, "Tow1")], apply=False)

    assert summary.created == 1
    assert session.query(Product).count() == 0


def test_dry_run_does_not_change_existing_products(session):
    import_articles(session, [_article(1, "Tow1", "Old", 5)])

    summary = import_articles(session, [_article(1, "Tow1", "New", 9)], apply=False)

    assert summary.updated == 1
    product = _all_products(session)[0]
    assert (product.name, product.wapro_quantity) == ("Old", 5)