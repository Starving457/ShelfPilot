from decimal import Decimal

from services.wapro_reader import (
    WaproArticle,
    article_from_row,
    fetch_articles,
    quantity_to_int,
)


def test_quantity_to_int_whole_decimal():
    assert quantity_to_int(Decimal("13.000000")) == 13


def test_quantity_to_int_rounds_fractions():
    assert quantity_to_int(Decimal("2.4")) == 2
    assert quantity_to_int(Decimal("2.5")) == 3


def test_quantity_to_int_keeps_negative_stock():
    assert quantity_to_int(Decimal("-3.000000")) == -3


def test_quantity_to_int_none_stays_none():
    assert quantity_to_int(None) is None


def test_article_from_row_maps_all_fields():
    row = (1, "Tow000001", "5901234567890", "Narty ATOMICUS LUX", Decimal("13.000000"), "ATOMICUS")

    article = article_from_row(row)

    assert article == WaproArticle(
        wapro_id=1,
        code="Tow000001",
        ean="5901234567890",
        name="Narty ATOMICUS LUX",
        quantity=13,
        producer="ATOMICUS",
    )


def test_article_from_row_strips_whitespace():
    row = (2, "  Tow000002  ", " ", "  Narty POP  ", Decimal("1"), "")

    article = article_from_row(row)

    assert article.code == "Tow000002"
    assert article.name == "Narty POP"
    assert article.ean is None
    assert article.producer is None


def test_article_from_row_without_code_is_skipped():
    assert article_from_row((3, None, None, "No code", Decimal("1"), None)) is None
    assert article_from_row((3, "   ", None, "No code", Decimal("1"), None)) is None


def test_article_from_row_missing_name_falls_back_to_code():
    article = article_from_row((4, "Tow000004", None, None, Decimal("0"), None))

    assert article.name == "Tow000004"


class FakeCursor:
    def __init__(self, rows, log):
        self.rows = rows
        self.log = log

    def execute(self, sql, *params):
        self.log.append((sql, params))
        return self

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.log = []

    def cursor(self):
        return FakeCursor(self.rows, self.log)


def test_fetch_articles_returns_articles_and_skipped_count():
    connection = FakeConnection(
        [
            (1, "Tow000001", None, "First", Decimal("2"), None),
            (2, None, None, "No code", Decimal("5"), None),
            (3, "Tow000003", "123", "Third", Decimal("0"), "ACME"),
        ]
    )

    articles, skipped = fetch_articles(connection, warehouse_id=1, kinds=("Towar",))

    assert [a.code for a in articles] == ["Tow000001", "Tow000003"]
    assert skipped == 1


def test_fetch_articles_passes_warehouse_and_kinds_as_parameters():
    connection = FakeConnection([])

    fetch_articles(connection, warehouse_id=6, kinds=("Towar", "Produkt"))

    sql, params = connection.log[0]
    assert params == (6, "Towar", "Produkt")
    assert sql.count("?") == 3
    assert "SELECT" in sql.upper()
    assert "INSERT" not in sql.upper() and "UPDATE" not in sql.upper() and "DELETE" not in sql.upper()