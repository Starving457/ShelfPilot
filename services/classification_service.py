import difflib

from database.models import Product
from services.ai_service import SOURCE_PREFIX


def _clean(text):
    """Pomocnicza: obcina spacje. Zwraca None, jeśli tekst jest pusty albo to nie tekst."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    return text if text != "" else None


def common_value(values):
    """Zwraca wartość, jeśli wszystkie podane wartości są takie same i niepuste.
    W przeciwnym razie (różne wartości, same puste albo pusta lista) zwraca None."""
    unique = set(values)
    if len(unique) == 1:
        return unique.pop()
    return None


def load_seed_categories(path):
    """Czyta listę kategorii z pliku tekstowego: jedna kategoria w linii, puste linie i linie
    zaczynające się od # są pomijane. Brak pliku oznacza pustą listę."""
    try:
        with open(path, encoding="utf-8-sig") as file:
            lines = file.read().splitlines()
    except FileNotFoundError:
        return []

    names = []
    for line in lines:
        name = _clean(line)
        if name is not None and not name.startswith("#"):
            names.append(name)
    return names


def merge_options(*lists):
    """Łączy listy nazw w jedną posortowaną listę bez duplikatów.
    Wielkość liter nie ma znaczenia; zostaje pisownia z pierwszej listy, w której nazwa wystąpiła."""
    unique = {}
    for items in lists:
        for item in items:
            unique.setdefault(item.lower(), item)
    return sorted(unique.values(), key=str.lower)


def filter_options(options, text):
    """Zwraca nazwy zawierające wszystkie słowa z tekstu (bez względu na wielkość liter).
    Pusty tekst zwraca wszystkie nazwy."""
    words = text.lower().split()
    return [option for option in options if all(word in option.lower() for word in words)]


def find_similar(name, options, cutoff=0.8, limit=5):
    """Zwraca istniejące nazwy podobne do podanej (ta sama nazwa inną wielkością liter, literówka,
    inna odmiana). Najbardziej podobne są pierwsze. Służy do ostrzeżenia przed dubletami."""
    name_lower = name.lower()
    scored = []
    for option in options:
        ratio = difflib.SequenceMatcher(None, name_lower, option.lower()).ratio()
        if ratio >= cutoff:
            scored.append((ratio, option))
    scored.sort(key=lambda pair: (-pair[0], pair[1].lower()))
    return [option for _, option in scored[:limit]]


def _canonical(session, column, text):
    """Pomocnicza: jeśli taka sama wartość (bez względu na wielkość liter) jest już używana,
    zwraca jej zapisaną postać. Dzięki temu "vortex" i "Vortex" nie staną się dwoma producentami."""
    rows = session.query(column).filter(column.isnot(None)).distinct().all()
    for existing in sorted(row[0] for row in rows):
        if existing.lower() == text.lower():
            return existing
    return text


def set_products_attributes(session, products, manufacturer, category):
    """Ręcznie ustawia ten sam producent i kategorię dla wielu produktów naraz.
    Wynik jest od razu zatwierdzony, a podpowiedzi znikają. Jeśli taki producent albo kategoria
    jest już w bazie (inna wielkość liter), używana jest istniejąca pisownia.
    Zwraca: "ok" albo "invalid" (pusty producent lub kategoria)."""
    manufacturer = _clean(manufacturer)
    category = _clean(category)

    if manufacturer is None or category is None:
        return "invalid"

    manufacturer = _canonical(session, Product.manufacturer, manufacturer)
    category = _canonical(session, Product.category, category)

    for product in products:
        product.manufacturer = manufacturer
        product.category = category
        product.classification_source = "manual"
        product.review_status = "confirmed"
        product.suggested_manufacturer = None
        product.suggested_category = None
        product.suggested_source = None

    session.commit()
    return "ok"


def set_product_attributes(session, product, manufacturer, category):
    """Ręcznie ustawia producenta i kategorię jednego produktu (także poprawia wcześniejszą pomyłkę).
    Zwraca: "ok" albo "invalid" (pusty producent lub kategoria)."""
    return set_products_attributes(session, [product], manufacturer, category)


def list_products_to_fill(session):
    """Zwraca produkty ze stanem WAPRO większym od zera, którym brakuje zatwierdzonego producenta
    lub kategorii (więc nie wchodzą do rotacji). Kolejność: według podpowiedzianego producenta
    (bez podpowiedzi na końcu), potem według nazwy."""
    products = (
        session.query(Product)
        .filter(
            Product.wapro_quantity > 0,
            (Product.review_status != "confirmed")
            | Product.manufacturer.is_(None)
            | Product.category.is_(None),
        )
        .all()
    )
    return sorted(
        products,
        key=lambda p: (
            p.suggested_manufacturer is None,
            (p.suggested_manufacturer or "").lower(),
            p.name or "",
        ),
    )


def group_products_by_hint(products):
    """Grupuje produkty po podpowiedzianym producencie (np. z pola Producent w WAPRO).
    Zwraca listę par (podpowiedź, produkty) alfabetycznie; grupa bez podpowiedzi (None) jest ostatnia.
    Producentów różniących się tylko wielkością liter traktuje jak jednego."""
    groups = {}
    labels = {}
    for product in products:
        hint = product.suggested_manufacturer
        key = hint.lower() if hint else None
        labels.setdefault(key, hint)
        groups.setdefault(key, []).append(product)

    ordered = sorted(groups, key=lambda key: (key is None, key or ""))
    return [(labels[key], groups[key]) for key in ordered]


def list_filled_groups(session):
    """Zwraca produkty z zatwierdzonym producentem i kategorią jako listę trójek
    (producent, kategoria, produkty), alfabetycznie. Produkty w grupie są posortowane po nazwie."""
    products = (
        session.query(Product)
        .filter(
            Product.review_status == "confirmed",
            Product.manufacturer.isnot(None),
            Product.category.isnot(None),
        )
        .all()
    )

    groups = {}
    for product in products:
        groups.setdefault((product.manufacturer, product.category), []).append(product)

    ordered = sorted(groups, key=lambda key: (key[0].lower(), key[1].lower()))
    return [
        (manufacturer, category, sorted(groups[(manufacturer, category)], key=lambda p: p.name or ""))
        for manufacturer, category in ordered
    ]


def confidence_of(product):
    """Pewność podpowiedzi AI: "high", "medium" albo "low" (brak informacji liczymy jako "low")."""
    source = product.suggested_source or ""
    if source.startswith(SOURCE_PREFIX):
        level = source[len(SOURCE_PREFIX):]
        if level in ("high", "medium"):
            return level
    return "low"


def list_suggestion_groups(session):
    """Zwraca podpowiedzi AI, które czekają na decyzję, pogrupowane jako lista trójek
    (producent, kategoria, produkty), alfabetycznie. Bierze tylko produkty, które mają i podpowiedzianego
    producenta, i podpowiedzianą kategorię, a nie są jeszcze zatwierdzone."""
    products = (
        session.query(Product)
        .filter(
            Product.suggested_manufacturer.isnot(None),
            Product.suggested_category.isnot(None),
            Product.suggested_source.like(SOURCE_PREFIX + "%"),
            (Product.review_status != "confirmed")
            | Product.manufacturer.is_(None)
            | Product.category.is_(None),
        )
        .all()
    )

    groups = {}
    labels = {}
    for product in products:
        key = (product.suggested_manufacturer.lower(), product.suggested_category.lower())
        labels.setdefault(key, (product.suggested_manufacturer, product.suggested_category))
        groups.setdefault(key, []).append(product)

    return [
        (labels[key][0], labels[key][1], sorted(groups[key], key=lambda p: p.name or ""))
        for key in sorted(groups)
    ]


def approve_suggestions(session, products):
    """Zatwierdza podpowiedzi AI: podpowiedziany producent i kategoria stają się zatwierdzone
    (źródło "ai"). Jeśli taki producent albo kategoria już istnieje (inna wielkość liter),
    używana jest istniejąca pisownia. Produkty bez pełnej podpowiedzi są pomijane.
    Zwraca liczbę zatwierdzonych produktów."""
    approved = 0
    canonical_cache = {}

    for product in products:
        manufacturer = _clean(product.suggested_manufacturer)
        category = _clean(product.suggested_category)
        if manufacturer is None or category is None:
            continue

        key = (manufacturer.lower(), category.lower())
        if key not in canonical_cache:
            canonical_cache[key] = (
                _canonical(session, Product.manufacturer, manufacturer),
                _canonical(session, Product.category, category),
            )
        product.manufacturer, product.category = canonical_cache[key]
        product.classification_source = "ai"
        product.review_status = "confirmed"
        product.suggested_manufacturer = None
        product.suggested_category = None
        product.suggested_source = None
        approved += 1

    session.commit()
    return approved


def reject_suggestions(session, products):
    """Odrzuca podpowiedzi AI: produkty wracają na listę do ręcznego uzupełnienia.
    Zwraca liczbę produktów, którym wyczyszczono podpowiedź."""
    for product in products:
        product.suggested_manufacturer = None
        product.suggested_category = None
        product.suggested_source = None

    session.commit()
    return len(products)


def list_manufacturers(session):
    """Zwraca posortowaną listę używanych (zatwierdzonych) producentów."""
    rows = (
        session.query(Product.manufacturer)
        .filter(Product.manufacturer.isnot(None))
        .distinct()
        .all()
    )
    return sorted(r[0] for r in rows)


def list_categories(session):
    """Zwraca posortowaną listę używanych (zatwierdzonych) kategorii."""
    rows = (
        session.query(Product.category)
        .filter(Product.category.isnot(None))
        .distinct()
        .all()
    )
    return sorted(r[0] for r in rows)