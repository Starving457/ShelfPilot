from datetime import date

from database.models import Product, InventoryCount
from services.classification_service import set_product_attributes
from services.inventory_service import (
    record_count,
    get_last_count,
    list_groups,
    suggest_next_group,
    get_group_products,
    count_products_outside_rotation,
)


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


# --- groups and "what to count today" ---


def _make_classified(session, code, manufacturer, category, wapro_quantity=3, name=None):
    product = Product(code=code, name=name or f"Product {code}", wapro_quantity=wapro_quantity)
    session.add(product)
    session.commit()
    set_product_attributes(session, product, manufacturer, category)
    return product


def test_list_groups_empty(session):
    assert list_groups(session) == []


def test_list_groups_groups_by_manufacturer_and_category(session):
    _make_classified(session, "A", "Vortex", "Lornetka")
    _make_classified(session, "B", "Vortex", "Lornetka")
    _make_classified(session, "C", "Vortex", "Luneta")
    _make_classified(session, "D", "Zeiss", "Lornetka")

    groups = list_groups(session)

    assert [(g.manufacturer, g.category, g.product_count) for g in groups] == [
        ("Vortex", "Lornetka", 2),
        ("Vortex", "Luneta", 1),
        ("Zeiss", "Lornetka", 1),
    ]


def test_list_groups_skips_unconfirmed_and_out_of_stock(session):
    _make_classified(session, "A", "Vortex", "Lornetka")
    _make_classified(session, "B", "Vortex", "Lornetka", wapro_quantity=0)
    unconfirmed = Product(code="C", name="Unconfirmed", wapro_quantity=5)
    session.add(unconfirmed)
    session.commit()

    groups = list_groups(session)

    assert len(groups) == 1
    assert groups[0].product_count == 1


def test_list_groups_counting_stats(session):
    a = _make_classified(session, "A", "Vortex", "Lornetka")
    b = _make_classified(session, "B", "Vortex", "Lornetka")
    _make_classified(session, "C", "Vortex", "Lornetka")
    record_count(session, a, 3, counted_at=date(2026, 11, 2))
    record_count(session, b, 3, counted_at=date(2026, 12, 1))

    group = list_groups(session)[0]

    assert group.product_count == 3
    assert group.never_counted_count == 1
    assert group.oldest_last_count == date(2026, 11, 2)
    assert group.last_counted == date(2026, 12, 1)


def test_list_groups_uses_latest_count_per_product(session):
    a = _make_classified(session, "A", "Vortex", "Lornetka")
    record_count(session, a, 3, counted_at=date(2026, 11, 2))
    record_count(session, a, 4, counted_at=date(2026, 12, 1))

    group = list_groups(session)[0]

    assert group.oldest_last_count == date(2026, 12, 1)
    assert group.never_counted_count == 0


def test_list_groups_never_counted_group(session):
    _make_classified(session, "A", "Vortex", "Lornetka")

    group = list_groups(session)[0]

    assert group.never_counted_count == 1
    assert group.oldest_last_count is None
    assert group.last_counted is None


def test_suggest_next_group_none_when_no_groups(session):
    assert suggest_next_group(session) is None


def test_suggest_next_group_prefers_never_counted(session):
    counted = _make_classified(session, "A", "Vortex", "Lornetka")
    _make_classified(session, "B", "Zeiss", "Luneta")
    record_count(session, counted, 3, counted_at=date(2026, 1, 1))

    group = suggest_next_group(session)

    assert (group.manufacturer, group.category) == ("Zeiss", "Luneta")


def test_suggest_next_group_picks_oldest_when_all_counted(session):
    a = _make_classified(session, "A", "Vortex", "Lornetka")
    b = _make_classified(session, "B", "Zeiss", "Luneta")
    record_count(session, a, 3, counted_at=date(2026, 11, 20))
    record_count(session, b, 3, counted_at=date(2026, 11, 2))

    group = suggest_next_group(session)

    assert (group.manufacturer, group.category) == ("Zeiss", "Luneta")


def test_suggest_next_group_new_product_pulls_group_forward(session):
    old = _make_classified(session, "A", "Vortex", "Lornetka")
    other = _make_classified(session, "B", "Zeiss", "Luneta")
    record_count(session, old, 3, counted_at=date(2026, 11, 1))
    record_count(session, other, 3, counted_at=date(2026, 10, 1))
    _make_classified(session, "C", "Vortex", "Lornetka")  # new, never counted

    group = suggest_next_group(session)

    assert (group.manufacturer, group.category) == ("Vortex", "Lornetka")


def test_suggest_next_group_tie_is_alphabetical(session):
    _make_classified(session, "A", "Zeiss", "Luneta")
    _make_classified(session, "B", "Vortex", "Lornetka")

    group = suggest_next_group(session)

    assert group.manufacturer == "Vortex"


def test_get_group_products_returns_members_with_last_count(session):
    a = _make_classified(session, "A", "Vortex", "Lornetka", name="B product")
    b = _make_classified(session, "B", "Vortex", "Lornetka", name="A product")
    _make_classified(session, "C", "Zeiss", "Lornetka")
    record_count(session, a, 3, counted_at=date(2026, 11, 2))

    pairs = get_group_products(session, "Vortex", "Lornetka")

    assert [p.code for p, _ in pairs] == ["B", "A"]  # sorted by name
    assert pairs[0][1] is None
    assert pairs[1][1].counted_quantity == 3


def test_get_group_products_unknown_group(session):
    assert get_group_products(session, "Nobody", "Nothing") == []


def test_count_products_outside_rotation(session):
    _make_classified(session, "A", "Vortex", "Lornetka")
    _make_classified(session, "B", "Vortex", "Lornetka", wapro_quantity=0)
    for code in ("C", "D"):
        session.add(Product(code=code, name="Unclassified", wapro_quantity=2))
    session.add(Product(code="E", name="Unclassified, no stock", wapro_quantity=0))
    session.commit()

    assert count_products_outside_rotation(session) == 2