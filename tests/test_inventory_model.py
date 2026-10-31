from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from database.models import Product, InventoryCount


def _make_product(session):
    product = Product(code="P1", name="VORTEX DIAMONDBACK HD 10X42 LORNETKA", wapro_quantity=4)
    session.add(product)
    session.commit()
    return product


def test_save_count(session):
    product = _make_product(session)

    entry = InventoryCount(
        product_id=product.id,
        counted_at=date(2026, 11, 2),
        counted_quantity=3,
        wapro_quantity=4,
    )
    session.add(entry)
    session.commit()

    saved = session.query(InventoryCount).first()
    assert saved.product_id == product.id
    assert saved.counted_at == date(2026, 11, 2)
    assert saved.counted_quantity == 3
    assert saved.wapro_quantity == 4


def test_date_defaults_to_today(session):
    product = _make_product(session)

    session.add(InventoryCount(product_id=product.id, counted_quantity=2))
    session.commit()

    assert session.query(InventoryCount).first().counted_at == date.today()


def test_history_keeps_all_counts(session):
    product = _make_product(session)

    session.add(InventoryCount(product_id=product.id, counted_at=date(2026, 11, 2), counted_quantity=3, wapro_quantity=4))
    session.add(InventoryCount(product_id=product.id, counted_at=date(2026, 12, 1), counted_quantity=4, wapro_quantity=4))
    session.commit()

    entries = (
        session.query(InventoryCount)
        .filter(InventoryCount.product_id == product.id)
        .order_by(InventoryCount.counted_at)
        .all()
    )
    assert [e.counted_quantity for e in entries] == [3, 4]


def test_counted_quantity_is_required(session):
    product = _make_product(session)

    session.add(InventoryCount(product_id=product.id))

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_wapro_quantity_can_be_empty(session):
    product = _make_product(session)

    session.add(InventoryCount(product_id=product.id, counted_quantity=1))
    session.commit()

    assert session.query(InventoryCount).first().wapro_quantity is None