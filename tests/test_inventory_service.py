from datetime import date

from database.models import Product, InventoryCount
from services.inventory_service import record_count, get_last_count


def _make_product(session, code="P1", wapro_quantity=4):
    product = Product(code=code, name="VORTEX DIAMONDBACK HD 10X42 LORNETKA", wapro_quantity=wapro_quantity)
    session.add(product)
    session.commit()
    return product


def test_record_count_saves_entry(session):
    product = _make_product(session)

    result = record_count(session, product, 3)

    assert result == "ok"
    entry = session.query(InventoryCount).one()
    assert entry.product_id == product.id
    assert entry.counted_quantity == 3
    assert entry.counted_at == date.today()


def test_record_count_saves_wapro_snapshot(session):
    product = _make_product(session, wapro_quantity=4)

    record_count(session, product, 3)
    product.wapro_quantity = 2  # WAPRO changes after a sale
    session.commit()

    entry = session.query(InventoryCount).one()
    assert entry.wapro_quantity == 4


def test_record_count_zero_is_allowed(session):
    product = _make_product(session)

    result = record_count(session, product, 0)

    assert result == "ok"
    assert session.query(InventoryCount).one().counted_quantity == 0


def test_record_count_rejects_negative(session):
    product = _make_product(session)

    result = record_count(session, product, -1)

    assert result == "invalid_quantity"
    assert session.query(InventoryCount).count() == 0


def test_record_count_rejects_non_integers(session):
    product = _make_product(session)

    assert record_count(session, product, "3") == "invalid_quantity"
    assert record_count(session, product, 2.5) == "invalid_quantity"
    assert record_count(session, product, None) == "invalid_quantity"
    assert record_count(session, product, True) == "invalid_quantity"
    assert session.query(InventoryCount).count() == 0


def test_record_count_when_wapro_says_zero(session):
    product = _make_product(session, wapro_quantity=0)

    result = record_count(session, product, 2)

    assert result == "ok"
    entry = session.query(InventoryCount).one()
    assert entry.counted_quantity == 2
    assert entry.wapro_quantity == 0


def test_record_count_with_unknown_wapro_quantity(session):
    product = _make_product(session, wapro_quantity=None)

    record_count(session, product, 1)

    assert session.query(InventoryCount).one().wapro_quantity is None


def test_record_count_accepts_custom_date(session):
    product = _make_product(session)

    record_count(session, product, 3, counted_at=date(2026, 11, 2))

    assert session.query(InventoryCount).one().counted_at == date(2026, 11, 2)


def test_record_count_appends_history(session):
    product = _make_product(session)

    record_count(session, product, 3, counted_at=date(2026, 11, 2))
    record_count(session, product, 4, counted_at=date(2026, 12, 1))

    assert session.query(InventoryCount).count() == 2


def test_get_last_count_never_counted(session):
    product = _make_product(session)

    assert get_last_count(session, product) is None


def test_get_last_count_returns_latest_date(session):
    product = _make_product(session)
    record_count(session, product, 3, counted_at=date(2026, 12, 1))
    record_count(session, product, 9, counted_at=date(2026, 11, 2))

    last = get_last_count(session, product)

    assert last.counted_at == date(2026, 12, 1)
    assert last.counted_quantity == 3


def test_get_last_count_same_day_later_entry_wins(session):
    product = _make_product(session)
    record_count(session, product, 3, counted_at=date(2026, 11, 2))
    record_count(session, product, 5, counted_at=date(2026, 11, 2))

    assert get_last_count(session, product).counted_quantity == 5


def test_get_last_count_is_per_product(session):
    a = _make_product(session, "A")
    b = _make_product(session, "B")
    record_count(session, a, 3)

    assert get_last_count(session, a) is not None
    assert get_last_count(session, b) is None