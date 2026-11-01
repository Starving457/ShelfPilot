from datetime import date

from database.models import Product
from services.classification_service import set_product_attributes
from services.inventory_service import record_count, get_day_report

DAY = date(2026, 11, 2)
OTHER_DAY = date(2026, 11, 3)


def _make_classified(session, code, manufacturer="Vortex", category="Lornetka", wapro_quantity=3, name=None):
    product = Product(code=code, name=name or f"Product {code}", wapro_quantity=wapro_quantity)
    session.add(product)
    session.commit()
    set_product_attributes(session, product, manufacturer, category)
    return product


def test_report_for_day_without_counts_is_empty(session):
    report = get_day_report(session, DAY)

    assert report.day == DAY
    assert report.lines == []
    assert report.counted_products == 0
    assert report.coverage == []
    assert report.net_difference == 0


def test_difference_is_counted_minus_wapro(session):
    product = _make_classified(session, "A", wapro_quantity=4)
    record_count(session, product, 3, counted_at=DAY)

    report = get_day_report(session, DAY)

    assert len(report.lines) == 1
    line = report.lines[0]
    assert line.counted_quantity == 3
    assert line.wapro_quantity == 4
    assert line.difference == -1


def test_difference_uses_snapshot_not_current_stock(session):
    product = _make_classified(session, "A", wapro_quantity=4)
    record_count(session, product, 4, counted_at=DAY)
    product.wapro_quantity = 3  # a sale after counting
    session.commit()

    report = get_day_report(session, DAY)

    assert report.lines == []  # still matches, because WAPRO was 4 when counting
    assert report.matching == 1


def test_matching_products_are_only_counted_in_summary(session):
    a = _make_classified(session, "A", wapro_quantity=3)
    b = _make_classified(session, "B", wapro_quantity=3)
    record_count(session, a, 3, counted_at=DAY)
    record_count(session, b, 2, counted_at=DAY)

    report = get_day_report(session, DAY)

    assert report.counted_products == 2
    assert report.matching == 1
    assert [line.product.code for line in report.lines] == ["B"]


def test_lines_are_sorted_by_absolute_difference(session):
    small = _make_classified(session, "A", wapro_quantity=3)
    big_short = _make_classified(session, "B", wapro_quantity=10)
    big_surplus = _make_classified(session, "C", wapro_quantity=1)
    record_count(session, small, 2, counted_at=DAY)  # -1
    record_count(session, big_short, 4, counted_at=DAY)  # -6
    record_count(session, big_surplus, 5, counted_at=DAY)  # +4

    report = get_day_report(session, DAY)

    assert [line.product.code for line in report.lines] == ["B", "C", "A"]


def test_summary_counts_and_net_difference(session):
    short = _make_classified(session, "A", wapro_quantity=5)
    surplus = _make_classified(session, "B", wapro_quantity=1)
    ok = _make_classified(session, "C", wapro_quantity=2)
    record_count(session, short, 3, counted_at=DAY)  # -2
    record_count(session, surplus, 4, counted_at=DAY)  # +3
    record_count(session, ok, 2, counted_at=DAY)  # 0

    report = get_day_report(session, DAY)

    assert report.counted_products == 3
    assert report.matching == 1
    assert report.shortages == 1
    assert report.surpluses == 1
    assert report.net_difference == 1


def test_found_product_with_zero_wapro_is_flagged_as_extra(session):
    extra = _make_classified(session, "A", wapro_quantity=0)
    record_count(session, extra, 2, counted_at=DAY)

    report = get_day_report(session, DAY)

    assert report.surpluses == 1
    assert report.lines[0].difference == 2
    assert report.lines[0].is_extra is True


def test_normal_surplus_is_not_flagged_as_extra(session):
    product = _make_classified(session, "A", wapro_quantity=1)
    record_count(session, product, 3, counted_at=DAY)

    assert get_day_report(session, DAY).lines[0].is_extra is False


def test_only_requested_day_is_included(session):
    product = _make_classified(session, "A", wapro_quantity=3)
    record_count(session, product, 1, counted_at=OTHER_DAY)

    assert get_day_report(session, DAY).counted_products == 0
    assert get_day_report(session, OTHER_DAY).counted_products == 1


def test_recount_on_same_day_last_entry_wins(session):
    product = _make_classified(session, "A", wapro_quantity=3)
    record_count(session, product, 1, counted_at=DAY)
    record_count(session, product, 3, counted_at=DAY)  # corrected

    report = get_day_report(session, DAY)

    assert report.counted_products == 1
    assert report.matching == 1
    assert report.lines == []


def test_unknown_wapro_quantity_is_listed_last_and_not_in_totals(session):
    unknown = _make_classified(session, "A", wapro_quantity=None)
    short = _make_classified(session, "B", wapro_quantity=3)
    record_count(session, unknown, 2, counted_at=DAY)
    record_count(session, short, 2, counted_at=DAY)

    report = get_day_report(session, DAY)

    assert [line.product.code for line in report.lines] == ["B", "A"]
    assert report.lines[1].difference is None
    assert report.unknown_wapro == 1
    assert report.shortages == 1
    assert report.net_difference == -1


def test_coverage_shows_partial_groups(session):
    a = _make_classified(session, "A", "Vortex", "Lornetka")
    _make_classified(session, "B", "Vortex", "Lornetka")
    _make_classified(session, "C", "Vortex", "Lornetka")
    d = _make_classified(session, "D", "Swarovski", "Lornetka")
    _make_classified(session, "E", "Zeiss", "Luneta")  # not counted today
    record_count(session, a, 3, counted_at=DAY)
    record_count(session, d, 3, counted_at=DAY)

    report = get_day_report(session, DAY)

    assert [(c.manufacturer, c.category, c.counted, c.total) for c in report.coverage] == [
        ("Swarovski", "Lornetka", 1, 1),
        ("Vortex", "Lornetka", 1, 3),
    ]


def test_coverage_ignores_extras_outside_rotation(session):
    normal = _make_classified(session, "A", "Vortex", "Lornetka", wapro_quantity=3)
    extra = _make_classified(session, "B", "Vortex", "Lornetka", wapro_quantity=0)
    record_count(session, normal, 3, counted_at=DAY)
    record_count(session, extra, 1, counted_at=DAY)

    report = get_day_report(session, DAY)

    assert report.counted_products == 2
    assert [(c.counted, c.total) for c in report.coverage] == [(1, 1)]


def test_report_can_be_filtered_by_group(session):
    vortex = _make_classified(session, "A", "Vortex", "Lornetka", wapro_quantity=3)
    zeiss = _make_classified(session, "B", "Zeiss", "Luneta", wapro_quantity=3)
    record_count(session, vortex, 1, counted_at=DAY)
    record_count(session, zeiss, 1, counted_at=DAY)

    report = get_day_report(session, DAY, manufacturer="Vortex", category="Lornetka")

    assert report.counted_products == 1
    assert [line.product.code for line in report.lines] == ["A"]
    assert [(c.manufacturer, c.category) for c in report.coverage] == [("Vortex", "Lornetka")]


def test_unclassified_product_appears_in_lines_but_not_in_coverage(session):
    product = Product(code="A", name="Unclassified", wapro_quantity=3)
    session.add(product)
    session.commit()
    record_count(session, product, 1, counted_at=DAY)

    report = get_day_report(session, DAY)

    assert report.counted_products == 1
    assert [line.product.code for line in report.lines] == ["A"]
    assert report.coverage == []