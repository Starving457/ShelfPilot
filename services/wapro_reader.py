from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

# Ustawienia połączenia z WAPRO (na razie wersja demo, logowanie kontem Windows).
# Przy prawdziwej bazie dojdzie konto tylko do odczytu, a ustawienia trafią do pliku poza gitem.
WAPRO_SERVER = "localhost"
WAPRO_DATABASE = "WAPRO_DEMO"
WAPRO_WAREHOUSE_ID = 1  # magazyn, który liczymy (w demo: Magazyn główny - Warszawa)
WAPRO_KINDS = ("Towar",)  # rodzaje artykułów do pobrania (bez usług, materiałów itp.)

PREFERRED_DRIVERS = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server",
]


@dataclass
class WaproArticle:
    """Artykuł odczytany z WAPRO. Tylko pola, które WAPRO ma prawo nam przekazać."""

    wapro_id: int  # ID_ARTYKULU, stały identyfikator w WAPRO
    code: str  # INDEKS_KATALOGOWY
    ean: str  # KOD_KRESKOWY (albo None)
    name: str  # NAZWA
    quantity: int  # STAN zaokrąglony do liczby całkowitej (albo None)
    producer: str  # PRODUCENT (albo None); tylko podpowiedź, program nie traktuje tego jako pewnika


def _clean(value):
    """Zamienia pusty tekst i same spacje na None, resztę przycina."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def quantity_to_int(value):
    """Stan z WAPRO (liczba dziesiętna, np. 13.000000) zamienia na liczbę całkowitą.
    Ułamki zaokrągla do najbliższej całości (0.5 w górę). None zostaje None."""
    if value is None:
        return None
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def article_from_row(row):
    """Buduje WaproArticle z wiersza (id, indeks katalogowy, EAN, nazwa, stan, producent).
    Zwraca None, gdy artykuł nie ma kodu, bo nie da się go rozpoznać przy kolejnych importach."""
    wapro_id, code, ean, name, stock, producer = row

    code = _clean(code)
    if code is None:
        return None

    return WaproArticle(
        wapro_id=int(wapro_id),
        code=code,
        ean=_clean(ean),
        name=_clean(name) or code,
        quantity=quantity_to_int(stock),
        producer=_clean(producer),
    )


def fetch_articles(connection, warehouse_id=WAPRO_WAREHOUSE_ID, kinds=WAPRO_KINDS):
    """Czyta artykuły jednego magazynu WAPRO (tylko odczyt).
    Zwraca parę: (lista WaproArticle, liczba pominiętych wierszy bez kodu).
    WITH (NOLOCK), bo to przybliżony odczyt i nie chcemy blokować pracy WAPRO."""
    placeholders = ", ".join("?" for _ in kinds)
    sql = f"""
        SELECT ID_ARTYKULU, INDEKS_KATALOGOWY, KOD_KRESKOWY, NAZWA, STAN, PRODUCENT
        FROM ARTYKUL WITH (NOLOCK)
        WHERE ID_MAGAZYNU = ? AND RODZAJ IN ({placeholders})
        ORDER BY ID_ARTYKULU
    """
    rows = connection.cursor().execute(sql, warehouse_id, *kinds).fetchall()

    articles = []
    skipped = 0
    for row in rows:
        article = article_from_row(row)
        if article is None:
            skipped += 1
        else:
            articles.append(article)

    return articles, skipped


def connect_wapro():
    """Otwiera połączenie z bazą WAPRO. pyodbc ładujemy dopiero tutaj,
    żeby testy i reszta programu działały też bez niego."""
    import pyodbc

    installed = pyodbc.drivers()
    driver = next((name for name in PREFERRED_DRIVERS if name in installed), None)
    if driver is None:
        raise RuntimeError("Brak sterownika ODBC dla SQL Server.")

    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={WAPRO_SERVER}",
        f"DATABASE={WAPRO_DATABASE}",
        "Trusted_Connection=yes",
    ]
    if driver.startswith("ODBC Driver"):
        parts.append("TrustServerCertificate=yes")

    return pyodbc.connect(";".join(parts), timeout=5)