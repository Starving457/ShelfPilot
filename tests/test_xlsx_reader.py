import pytest
from openpyxl import Workbook

from services.wapro_reader import WaproArticle
from services.xlsx_reader import (
    article_from_xlsx_row,
    articles_from_rows,
    find_missing_columns,
    read_articles_from_xlsx,
    REQUIRED_COLUMNS,
)

HEADER = ["Nazwa cała", "R", "Stan", "Indeks katalogowy", "Kod kreskowy", "Producent", "Nr artykułu"]


def _row(**overrides):
    row = {
        "Nazwa cała": "Lornetka Vortex Diamondback 10x42",
        "R": "Towar",
        "Stan": 4,
        "Indeks katalogowy": "VOR000001",
        "Kod kreskowy": "5901234567890",
        "Producent": " ",
        "Nr artykułu": "101",
    }
    row.update(overrides)
    return row


def test_find_missing_columns_none_missing():
    assert find_missing_columns(REQUIRED_COLUMNS) == []


def test_find_missing_columns_reports_missing():
    assert find_missing_columns(["Nazwa cała", "R"]) == [
        "Nr artykułu", "Indeks katalogowy", "Kod kreskowy", "Stan", "Producent",
    ]


def test_article_maps_all_fields():
    article, reason = article_from_xlsx_row(_row(Producent="NIKON EUROPE B.V"))

    assert reason is None
    assert article == WaproArticle(
        wapro_id=101,
        code="VOR000001",
        ean="5901234567890",
        name="Lornetka Vortex Diamondback 10x42",
        quantity=4,
        producer="NIKON EUROPE B.V",
    )


def test_space_means_empty_value():
    article, _ = article_from_xlsx_row(_row(**{"Kod kreskowy": " ", "Producent": " "}))

    assert article.ean is None
    assert article.producer is None


def test_numeric_ean_loses_the_decimal_part():
    article, _ = article_from_xlsx_row(_row(**{"Kod kreskowy": 5901234567890.0}))

    assert article.ean == "5901234567890"


def test_other_kinds_are_skipped():
    article, reason = article_from_xlsx_row(_row(R="Usługa"))

    assert article is None
    assert reason == "other_kind"


def test_row_without_code_is_skipped():
    article, reason = article_from_xlsx_row(_row(**{"Indeks katalogowy": " "}))

    assert article is None
    assert reason == "no_code"


def test_row_with_bad_id_is_skipped():
    assert article_from_xlsx_row(_row(**{"Nr artykułu": None}))[1] == "bad_id"
    assert article_from_xlsx_row(_row(**{"Nr artykułu": "abc"}))[1] == "bad_id"


def test_missing_name_falls_back_to_code():
    article, _ = article_from_xlsx_row(_row(**{"Nazwa cała": " "}))

    assert article.name == "VOR000001"


def test_missing_stock_stays_unknown():
    article, _ = article_from_xlsx_row(_row(Stan=None))

    assert article.quantity is None


def test_articles_from_rows_counts_skipped_rows():
    rows = [
        HEADER,
        ["Lornetka", "Towar", 2, "A1", "111", " ", "1"],
        ["Usługa serwisowa", "Usługa", 0, "U1", " ", " ", "2"],
        ["Bez kodu", "Towar", 1, " ", " ", " ", "3"],
        ["Zły numer", "Towar", 1, "A4", " ", " ", "x"],
        [None, None, None, None, None, None, None],
    ]

    result = articles_from_rows(rows)

    assert [a.code for a in result.articles] == ["A1"]
    assert result.skipped_other_kind == 1
    assert result.skipped_no_code == 1
    assert result.skipped_bad_id == 1


def test_articles_from_rows_requires_columns():
    with pytest.raises(ValueError, match="brakuje kolumn"):
        articles_from_rows([["Nazwa cała", "R"], ["x", "Towar"]])


def test_articles_from_rows_rejects_empty_file():
    with pytest.raises(ValueError):
        articles_from_rows([])


def test_read_articles_from_xlsx_file(tmp_path):
    path = tmp_path / "export.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADER)
    sheet.append(["Lornetka Vortex", "Towar", 5, "VOR1", "5901234567890", " ", "10"])
    sheet.append(["Usługa", "Usługa", 0, "USL1", " ", " ", "11"])
    workbook.save(path)

    result = read_articles_from_xlsx(path)

    assert len(result.articles) == 1
    assert result.articles[0].code == "VOR1"
    assert result.articles[0].quantity == 5
    assert result.skipped_other_kind == 1