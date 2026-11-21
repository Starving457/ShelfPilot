from dataclasses import dataclass, field

from services.wapro_reader import WaproArticle, quantity_to_int

# Nazwy kolumn w eksporcie artykułów z WAPRO Mag (przeglądanie artykułów -> eksport do Excela)
COL_ID = "Nr artykułu"
COL_CODE = "Indeks katalogowy"
COL_EAN = "Kod kreskowy"
COL_NAME = "Nazwa cała"
COL_STOCK = "Stan"
COL_PRODUCER = "Producent"
COL_KIND = "R"

REQUIRED_COLUMNS = [COL_ID, COL_CODE, COL_EAN, COL_NAME, COL_STOCK, COL_PRODUCER, COL_KIND]

# Rodzaje artykułów, które importujemy (bez usług, materiałów itp.)
XLSX_KINDS = ("Towar",)


@dataclass
class XlsxReadResult:
    """Wynik czytania pliku: artykuły i liczniki pominiętych wierszy."""

    articles: list = field(default_factory=list)
    skipped_other_kind: int = 0  # np. usługi
    skipped_no_code: int = 0  # brak indeksu katalogowego
    skipped_bad_id: int = 0  # brak numeru artykułu albo numer nie jest liczbą


def _text(value):
    """Zamienia komórkę na tekst. Puste komórki i same spacje (tak WAPRO zapisuje brak wartości)
    dają None. Liczby całkowite zapisane jako 5901234567890.0 wracają jako '5901234567890'."""
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    return text or None


def find_missing_columns(header):
    """Zwraca listę wymaganych kolumn, których nie ma w nagłówku (pusta lista = wszystko jest)."""
    present = {_text(name) for name in header}
    return [name for name in REQUIRED_COLUMNS if name not in present]


def article_from_xlsx_row(row, kinds=XLSX_KINDS):
    """Buduje WaproArticle z wiersza (słownik: nazwa kolumny -> wartość).
    Zwraca (artykuł, powód_pominięcia). Gdy wiersz jest dobry, powód to None;
    gdy go pomijamy, artykuł to None, a powód to "other_kind", "no_code" albo "bad_id"."""
    if _text(row.get(COL_KIND)) not in kinds:
        return None, "other_kind"

    code = _text(row.get(COL_CODE))
    if code is None:
        return None, "no_code"

    raw_id = _text(row.get(COL_ID))
    if raw_id is None or not raw_id.isdigit():
        return None, "bad_id"

    article = WaproArticle(
        wapro_id=int(raw_id),
        code=code,
        ean=_text(row.get(COL_EAN)),
        name=_text(row.get(COL_NAME)) or code,
        quantity=quantity_to_int(row.get(COL_STOCK)),
        producer=_text(row.get(COL_PRODUCER)),
    )
    return article, None


def articles_from_rows(rows, kinds=XLSX_KINDS):
    """Zamienia listę wierszy (pierwszy to nagłówek) na XlsxReadResult.
    Rzuca ValueError, jeśli w nagłówku brakuje wymaganych kolumn."""
    rows = list(rows)
    if not rows:
        raise ValueError("Plik jest pusty.")

    header = [_text(name) for name in rows[0]]
    missing = find_missing_columns(header)
    if missing:
        raise ValueError("W pliku brakuje kolumn: " + ", ".join(missing))

    result = XlsxReadResult()
    for values in rows[1:]:
        if all(_text(value) is None for value in values):
            continue  # pusty wiersz na końcu arkusza

        row = dict(zip(header, values))
        article, reason = article_from_xlsx_row(row, kinds)
        if article is not None:
            result.articles.append(article)
        elif reason == "other_kind":
            result.skipped_other_kind += 1
        elif reason == "no_code":
            result.skipped_no_code += 1
        else:
            result.skipped_bad_id += 1

    return result


def read_articles_from_xlsx(path, kinds=XLSX_KINDS):
    """Czyta pierwszy arkusz pliku .xlsx z eksportu WAPRO i zwraca XlsxReadResult.
    openpyxl ładujemy dopiero tutaj, żeby reszta programu i testy działały też bez niego."""
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = list(workbook.worksheets[0].iter_rows(values_only=True))
    finally:
        workbook.close()

    return articles_from_rows(rows, kinds)